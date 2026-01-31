"""
RevenueDistributionService - Revenue calculation and distribution for rental transactions.

This service implements the business rules for revenue distribution:
- BR4.1-3: All transactions collected by ChargeGhar
- BR5.1-5: VAT & Service Charge deducted ONLY at ChargeGhar level
- BR6.1-3: ChargeGhar station revenue distribution
- BR7.1-5: Franchise station revenue distribution
- BR11.1-5: All calculations use Net Revenue

Revenue Distribution Scenarios:
1. ChargeGhar Station (No Partner): ChargeGhar keeps 100%
2. ChargeGhar Station + CG Vendor: Vendor gets x%, CG keeps (100-x)%
3. Franchise Station (No Vendor): Franchise gets y%, CG keeps (100-y)%
4. Franchise Station + F Vendor: CG gets (100-y)%, Franchise gets (y-v)%, Vendor gets v% of y%
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
from django.db import transaction as db_transaction
from django.utils import timezone

from api.common.services.base import BaseService, ServiceException
from api.partners.common.models import (
    Partner,
    StationDistribution,
    StationRevenueShare,
    RevenueDistribution,
)
from api.partners.common.repositories import (
    RevenueDistributionRepository,
    StationDistributionRepository,
)


class RevenueDistributionService(BaseService):
    """
    Service for calculating and creating revenue distribution records.
    
    Called when a rental transaction status becomes SUCCESS:
    - PREPAID: After rental activation (popup success)
    - POSTPAID: After return_powerbank payment collection
    """
    
    # Default values - should be overridden by AppConfig
    DEFAULT_VAT_PERCENT = Decimal('13.00')
    DEFAULT_SERVICE_CHARGE_PERCENT = Decimal('2.50')
    
    def __init__(self):
        super().__init__()
        self._vat_percent: Optional[Decimal] = None
        self._service_charge_percent: Optional[Decimal] = None
    
    @property
    def vat_percent(self) -> Decimal:
        """Get VAT percentage from AppConfig"""
        if self._vat_percent is None:
            self._vat_percent = self._get_config_decimal(
                'PLATFORM_VAT_PERCENT',
                self.DEFAULT_VAT_PERCENT
            )
        return self._vat_percent
    
    @property
    def service_charge_percent(self) -> Decimal:
        """Get Service Charge percentage from AppConfig"""
        if self._service_charge_percent is None:
            self._service_charge_percent = self._get_config_decimal(
                'PLATFORM_SERVICE_CHARGE_PERCENT',
                self.DEFAULT_SERVICE_CHARGE_PERCENT
            )
        return self._service_charge_percent
    
    def _get_config_decimal(self, key: str, default: Decimal) -> Decimal:
        """Get a decimal value from AppConfig"""
        try:
            from api.user.system.models import AppConfig
            config = AppConfig.objects.filter(key=key, is_active=True).first()
            if config:
                return Decimal(str(config.value))
            return default
        except Exception:
            return default
    
    def create_revenue_distribution(
        self,
        transaction,  # payments.Transaction
        rental,  # rentals.Rental
    ) -> Optional[RevenueDistribution]:
        """
        Create revenue distribution for a completed transaction.
        
        This is the main entry point - called when:
        1. PREPAID rental activates successfully
        2. POSTPAID rental payment is collected
        
        Args:
            transaction: The completed RENTAL transaction (status=SUCCESS)
            rental: The associated rental
            
        Returns:
            RevenueDistribution record or None if already exists
        """
        # Validate transaction
        if not transaction or transaction.status != 'SUCCESS':
            self.log_warning(
                f"Cannot create revenue distribution for non-SUCCESS transaction: "
                f"{transaction.id if transaction else 'None'}"
            )
            return None
        
        # Check if already distributed
        existing = RevenueDistributionRepository.get_by_transaction_id(str(transaction.id))
        if existing:
            self.log_info(f"Revenue distribution already exists for transaction {transaction.id}")
            return existing
        
        # Get station from rental
        station = rental.station
        if not station:
            self.log_error(f"No station found for rental {rental.id}")
            return None
        
        # Get gross amount from transaction
        gross_amount = Decimal(str(transaction.amount))
        
        # Calculate VAT and service charge
        vat_amount, service_charge, net_amount = self._calculate_deductions(gross_amount)
        
        # Get station hierarchy (franchise and/or vendor)
        franchise, vendor, distribution_context = self._get_station_hierarchy(str(station.id))
        
        # Calculate shares based on hierarchy
        shares = self._calculate_shares(
            net_amount=net_amount,
            franchise=franchise,
            vendor=vendor,
            distribution_context=distribution_context
        )
        
        # Create the distribution record
        with db_transaction.atomic():
            distribution = RevenueDistributionRepository.create(
                transaction_id=str(transaction.id),
                rental_id=str(rental.id),
                station_id=str(station.id),
                gross_amount=gross_amount,
                vat_amount=vat_amount,
                service_charge=service_charge,
                net_amount=net_amount,
                chargeghar_share=shares['chargeghar_share'],
                franchise_id=str(franchise.id) if franchise else None,
                franchise_share=shares['franchise_share'],
                vendor_id=str(vendor.id) if vendor else None,
                vendor_share=shares['vendor_share'],
                calculation_details=shares['calculation_details']
            )
            
            # Update partner balances immediately
            self._update_partner_balances(distribution, franchise, vendor)
            
            self.log_info(
                f"Created revenue distribution {distribution.id} for transaction {transaction.id}: "
                f"CG={shares['chargeghar_share']}, Franchise={shares['franchise_share']}, "
                f"Vendor={shares['vendor_share']}"
            )
            
            return distribution
    
    def _calculate_deductions(self, gross_amount: Decimal) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Calculate VAT and service charge deductions.
        
        Per BR5: VAT and Service Charge are deducted ONLY at ChargeGhar level.
        
        Returns:
            Tuple of (vat_amount, service_charge, net_amount)
        """
        vat_amount = (gross_amount * self.vat_percent / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        service_charge = (gross_amount * self.service_charge_percent / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        net_amount = gross_amount - vat_amount - service_charge
        
        return vat_amount, service_charge, net_amount
    
    def _get_station_hierarchy(
        self,
        station_id: str
    ) -> Tuple[Optional[Partner], Optional[Partner], dict]:
        """
        Get the franchise and vendor for a station.
        
        Returns:
            Tuple of (franchise, vendor, distribution_context)
            
        Distribution context includes:
        - scenario: CHARGEGHAR_ONLY, CG_VENDOR, FRANCHISE_ONLY, FRANCHISE_VENDOR
        - vendor_revenue_model: PERCENTAGE or FIXED (if vendor exists)
        - vendor_percent: Vendor's percentage (if PERCENTAGE model)
        - franchise_percent: Franchise's percentage (always from partner.revenue_share_percent)
        """
        franchise = StationDistributionRepository.get_station_franchise(station_id)
        vendor = StationDistributionRepository.get_station_vendor(station_id)
        
        context = {
            'scenario': 'CHARGEGHAR_ONLY',
            'vendor_revenue_model': None,
            'vendor_percent': None,
            'franchise_percent': None,
        }
        
        # Determine scenario
        if franchise and vendor:
            context['scenario'] = 'FRANCHISE_VENDOR'
        elif franchise:
            context['scenario'] = 'FRANCHISE_ONLY'
        elif vendor:
            context['scenario'] = 'CG_VENDOR'
        
        # Get franchise percentage
        if franchise:
            context['franchise_percent'] = franchise.revenue_share_percent or Decimal('0')
        
        # Get vendor revenue configuration
        if vendor and vendor.is_revenue_vendor:
            vendor_dist = StationDistribution.objects.filter(
                station_id=station_id,
                partner=vendor,
                is_active=True
            ).first()
            
            if vendor_dist:
                try:
                    revenue_share = vendor_dist.revenue_share
                    if revenue_share:
                        context['vendor_revenue_model'] = revenue_share.revenue_model
                        if revenue_share.is_percentage_model:
                            context['vendor_percent'] = revenue_share.partner_percent or Decimal('0')
                except StationRevenueShare.DoesNotExist:
                    pass
        
        return franchise, vendor, context
    
    def _calculate_shares(
        self,
        net_amount: Decimal,
        franchise: Optional[Partner],
        vendor: Optional[Partner],
        distribution_context: dict
    ) -> dict:
        """
        Calculate share amounts for all parties.
        
        Business Rules:
        - BR6.1: CG Station without partner: 100% to CG
        - BR6.2: CG Station + Revenue Vendor: Vendor gets x%, CG gets (100-x)%
        - BR6.3: CG Station + Non-Revenue Vendor: 100% to CG
        - BR7.1: Franchise Station: Franchise gets y%, CG gets (100-y)%
        - BR7.4: Franchise Station + Revenue Vendor: Vendor gets v% from Franchise's y%
        - BR7.5: Franchise Station + Non-Revenue Vendor: Franchise keeps 100% of y%
        
        For FIXED vendors:
        - vendor_share is set to 0 in revenue distribution
        - Fixed amount is tracked separately (monthly billing)
        """
        scenario = distribution_context['scenario']
        franchise_percent = distribution_context.get('franchise_percent') or Decimal('0')
        vendor_percent = distribution_context.get('vendor_percent') or Decimal('0')
        vendor_model = distribution_context.get('vendor_revenue_model')
        
        chargeghar_share = net_amount
        franchise_share = Decimal('0')
        vendor_share = Decimal('0')
        
        calculation_details = {
            'scenario': scenario,
            'net_amount': str(net_amount),
            'vat_percent': str(self.vat_percent),
            'service_charge_percent': str(self.service_charge_percent),
            'franchise_percent': str(franchise_percent),
            'vendor_percent': str(vendor_percent),
            'vendor_revenue_model': vendor_model,
            'calculated_at': timezone.now().isoformat(),
        }
        
        # Scenario 1: ChargeGhar only (no partners)
        if scenario == 'CHARGEGHAR_ONLY':
            chargeghar_share = net_amount
            calculation_details['logic'] = 'BR6.1: ChargeGhar station, 100% to CG'
        
        # Scenario 2: ChargeGhar + Vendor (direct vendor under CG)
        elif scenario == 'CG_VENDOR':
            if vendor and vendor.is_revenue_vendor and vendor_model == 'PERCENTAGE':
                # BR6.2: Vendor gets x% of net
                vendor_share = (net_amount * vendor_percent / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                chargeghar_share = net_amount - vendor_share
                calculation_details['logic'] = f'BR6.2: CG Vendor gets {vendor_percent}% of net'
            elif vendor and vendor.is_revenue_vendor and vendor_model == 'FIXED':
                # Fixed vendors: No per-transaction share, tracked monthly
                vendor_share = Decimal('0')
                chargeghar_share = net_amount
                calculation_details['logic'] = 'BR6.2: CG Vendor is FIXED model, share tracked monthly'
            else:
                # BR6.3: Non-Revenue vendor or no revenue config
                vendor_share = Decimal('0')
                chargeghar_share = net_amount
                calculation_details['logic'] = 'BR6.3: Non-Revenue Vendor, 100% to CG'
        
        # Scenario 3: Franchise only (no vendor)
        elif scenario == 'FRANCHISE_ONLY':
            # BR7.1-2: Franchise gets y%, CG gets (100-y)%
            franchise_share = (net_amount * franchise_percent / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            chargeghar_share = net_amount - franchise_share
            calculation_details['logic'] = f'BR7.1: Franchise gets {franchise_percent}% of net'
        
        # Scenario 4: Franchise + Vendor
        elif scenario == 'FRANCHISE_VENDOR':
            # First calculate franchise's total share (y% of net)
            total_franchise_portion = (net_amount * franchise_percent / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # ChargeGhar always gets (100-y)%
            chargeghar_share = net_amount - total_franchise_portion
            
            if vendor and vendor.is_revenue_vendor and vendor_model == 'PERCENTAGE':
                # BR7.4: Vendor gets v% FROM franchise's share
                vendor_share = (total_franchise_portion * vendor_percent / Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
                franchise_share = total_franchise_portion - vendor_share
                calculation_details['logic'] = (
                    f'BR7.4: CG gets {100 - franchise_percent}%, '
                    f'Franchise gets {franchise_percent}% minus vendor share, '
                    f'Vendor gets {vendor_percent}% of franchise share'
                )
            elif vendor and vendor.is_revenue_vendor and vendor_model == 'FIXED':
                # Fixed vendor under franchise: tracked monthly
                vendor_share = Decimal('0')
                franchise_share = total_franchise_portion
                calculation_details['logic'] = 'BR7.4: Franchise Vendor is FIXED model, share tracked monthly'
            else:
                # BR7.5: Non-Revenue vendor
                franchise_share = total_franchise_portion
                vendor_share = Decimal('0')
                calculation_details['logic'] = 'BR7.5: Non-Revenue Vendor, Franchise keeps full share'
        
        return {
            'chargeghar_share': chargeghar_share,
            'franchise_share': franchise_share,
            'vendor_share': vendor_share,
            'calculation_details': calculation_details,
        }
    
    def _update_partner_balances(
        self,
        distribution: RevenueDistribution,
        franchise: Optional[Partner],
        vendor: Optional[Partner]
    ) -> None:
        """
        Update partner balances and mark distribution as completed.
        
        This updates:
        - partners.balance (available for payout)
        - partners.total_earnings (lifetime total)
        """
        # Update franchise balance
        if franchise and distribution.franchise_share > 0:
            franchise.balance += distribution.franchise_share
            franchise.total_earnings += distribution.franchise_share
            franchise.save(update_fields=['balance', 'total_earnings', 'updated_at'])
            self.log_info(
                f"Updated franchise {franchise.code} balance: "
                f"+{distribution.franchise_share}, new balance: {franchise.balance}"
            )
        
        # Update vendor balance
        if vendor and distribution.vendor_share > 0:
            vendor.balance += distribution.vendor_share
            vendor.total_earnings += distribution.vendor_share
            vendor.save(update_fields=['balance', 'total_earnings', 'updated_at'])
            self.log_info(
                f"Updated vendor {vendor.code} balance: "
                f"+{distribution.vendor_share}, new balance: {vendor.balance}"
            )
        
        # Mark as distributed
        distribution.is_distributed = True
        distribution.distributed_at = timezone.now()
        distribution.save(update_fields=['is_distributed', 'distributed_at', 'updated_at'])
    
    def recalculate_distribution(self, distribution_id: str) -> Optional[RevenueDistribution]:
        """
        Recalculate an existing distribution (for corrections).
        
        Note: This does NOT update partner balances - those must be corrected manually.
        """
        distribution = RevenueDistributionRepository.get_by_id(distribution_id)
        if not distribution:
            raise ServiceException(
                detail="Distribution not found",
                code="distribution_not_found"
            )
        
        # Recalculate based on current rates and hierarchy
        gross_amount = distribution.gross_amount
        vat_amount, service_charge, net_amount = self._calculate_deductions(gross_amount)
        
        franchise, vendor, context = self._get_station_hierarchy(str(distribution.station_id))
        shares = self._calculate_shares(net_amount, franchise, vendor, context)
        
        # Update the distribution record
        distribution.vat_amount = vat_amount
        distribution.service_charge = service_charge
        distribution.net_amount = net_amount
        distribution.chargeghar_share = shares['chargeghar_share']
        distribution.franchise_share = shares['franchise_share']
        distribution.vendor_share = shares['vendor_share']
        distribution.calculation_details = shares['calculation_details']
        distribution.save()
        
        self.log_info(f"Recalculated distribution {distribution_id}")
        return distribution
    
    def create_reversal_distribution(
        self,
        original_distribution_id: str,
        refund_amount: Decimal,
        reason: str = 'PARTIAL_REFUND'
    ) -> Optional[RevenueDistribution]:
        """
        Create reversal distribution for refund.
        
        Args:
            original_distribution_id: ID of original distribution
            refund_amount: Amount being refunded (positive number)
            reason: FULL_REFUND or PARTIAL_REFUND
            
        Returns:
            Reversal RevenueDistribution with negative amounts
        """
        original = RevenueDistributionRepository.get_by_id(original_distribution_id)
        if not original:
            self.log_error(f"Original distribution {original_distribution_id} not found")
            return None
        
        # Calculate reversal ratio
        ratio = refund_amount / original.gross_amount
        
        # Calculate reversal amounts (negative)
        reversal_gross = -refund_amount
        reversal_vat = -(original.vat_amount * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
        reversal_service_charge = -(original.service_charge * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
        reversal_net = reversal_gross - reversal_vat - reversal_service_charge
        
        # Calculate reversal shares (negative)
        reversal_chargeghar = -(original.chargeghar_share * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
        reversal_franchise = -(original.franchise_share * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
        reversal_vendor = -(original.vendor_share * ratio).quantize(Decimal('0.01'), ROUND_HALF_UP)
        
        # Create reversal distribution
        with db_transaction.atomic():
            reversal = RevenueDistributionRepository.create(
                transaction_id=str(original.transaction.id),
                rental_id=str(original.rental.id) if original.rental else None,
                station_id=str(original.station.id),
                gross_amount=reversal_gross,
                vat_amount=reversal_vat,
                service_charge=reversal_service_charge,
                net_amount=reversal_net,
                chargeghar_share=reversal_chargeghar,
                franchise_id=str(original.franchise.id) if original.franchise else None,
                franchise_share=reversal_franchise,
                vendor_id=str(original.vendor.id) if original.vendor else None,
                vendor_share=reversal_vendor,
                is_reversal=True,
                reversed_distribution_id=original_distribution_id,
                reversal_reason=reason,
                calculation_details={
                    'reversal_ratio': str(ratio),
                    'original_gross': str(original.gross_amount),
                    'refund_amount': str(refund_amount),
                    'reason': reason,
                }
            )
            
            # Update partner balances (deduct)
            self._update_partner_balances(reversal, original.franchise, original.vendor)
            
            self.log_info(
                f"Created reversal distribution {reversal.id} for NPR {refund_amount} "
                f"(original: {original_distribution_id})"
            )
            
            return reversal
