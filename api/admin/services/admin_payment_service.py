"""
Admin Payment Service
============================================================

Service for managing payment methods, rental packages, and transactions.

Created: 2025-11-06
Updated: 2025-11-08 - Added transactions list with PointsTransaction
"""
from typing import Dict, Any
from django.db.models import Q
from django.db import transaction

from api.common.services import BaseService
from api.common.services.base import ServiceException
from api.common.utils.helpers import paginate_queryset
from api.user.payments.models import PaymentMethod, Transaction, WalletTransaction
from api.user.points.models import PointsTransaction
from api.user.rentals.models import RentalPackage


class AdminPaymentService(BaseService):
    """Service for admin payment and package management operations"""
    
    # ============================================================
    # Payment Method Management
    # ============================================================
    
    def get_payment_methods(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get list of payment methods with filters"""
        try:
            queryset = PaymentMethod.objects.all().order_by('-created_at')
            
            if not filters:
                filters = {}
            
            # Apply filters
            if 'is_active' in filters and filters['is_active'] is not None:
                queryset = queryset.filter(is_active=filters['is_active'])
            
            if filters.get('gateway'):
                queryset = queryset.filter(gateway__icontains=filters['gateway'])
            
            if filters.get('search'):
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(name__icontains=search_term) |
                    Q(gateway__icontains=search_term)
                )
            
            # Pagination
            page = filters.get('page', 1)
            page_size = filters.get('page_size', 20)
            
            return paginate_queryset(queryset, page, page_size)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get payment methods")
    
    def get_payment_method(self, method_id: str):
        """Get single payment method by ID"""
        try:
            return PaymentMethod.objects.get(id=method_id)
        except PaymentMethod.DoesNotExist:
            raise ServiceException(
                detail="Payment method not found",
                code="payment_method_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get payment method")
    
    @transaction.atomic
    def create_payment_method(self, data: Dict[str, Any]) -> PaymentMethod:
        """Create a new payment method"""
        try:
            payment_method = PaymentMethod.objects.create(
                name=data['name'],
                gateway=data['gateway'],
                icon=data.get('icon', ''),
                is_active=data.get('is_active', True),
                configuration=data.get('configuration', {}),
                min_amount=data['min_amount'],
                max_amount=data.get('max_amount'),
                supported_currencies=data.get('supported_currencies', ['NPR'])
            )
            
            return payment_method
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create payment method")
    
    @transaction.atomic
    def update_payment_method(self, method_id: str, data: Dict[str, Any]) -> PaymentMethod:
        """Update an existing payment method"""
        try:
            payment_method = self.get_payment_method(method_id)
            
            # Update fields
            if 'name' in data:
                payment_method.name = data['name']
            if 'gateway' in data:
                payment_method.gateway = data['gateway']
            if 'icon' in data:
                payment_method.icon = data['icon']
            if 'is_active' in data:
                payment_method.is_active = data['is_active']
            if 'configuration' in data:
                payment_method.configuration = data['configuration']
            if 'min_amount' in data:
                payment_method.min_amount = data['min_amount']
            if 'max_amount' in data:
                payment_method.max_amount = data['max_amount']
            if 'supported_currencies' in data:
                payment_method.supported_currencies = data['supported_currencies']
            
            payment_method.save()
            return payment_method
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update payment method")
    
    @transaction.atomic
    def delete_payment_method(self, method_id: str) -> Dict[str, Any]:
        """Delete (soft delete) a payment method"""
        try:
            payment_method = self.get_payment_method(method_id)
            
            # Soft delete by setting is_active to False
            payment_method.is_active = False
            payment_method.save()
            
            return {
                'id': str(payment_method.id),
                'name': payment_method.name,
                'deleted': True
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to delete payment method")
    
    # ============================================================
    # Rental Package Management
    # ============================================================
    
    def get_rental_packages(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get list of rental packages with filters"""
        try:
            queryset = RentalPackage.objects.all().order_by('price')
            
            if not filters:
                filters = {}
            
            # Apply filters
            if 'is_active' in filters and filters['is_active'] is not None:
                queryset = queryset.filter(is_active=filters['is_active'])
            
            if filters.get('package_type'):
                queryset = queryset.filter(package_type=filters['package_type'])
            
            if filters.get('payment_model'):
                queryset = queryset.filter(payment_model=filters['payment_model'])
            
            if filters.get('search'):
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(name__icontains=search_term) |
                    Q(description__icontains=search_term)
                )
            
            # Pagination
            page = filters.get('page', 1)
            page_size = filters.get('page_size', 20)
            
            return paginate_queryset(queryset, page, page_size)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get rental packages")
    
    def get_rental_package(self, package_id: str):
        """Get single rental package by ID"""
        try:
            return RentalPackage.objects.get(id=package_id)
        except RentalPackage.DoesNotExist:
            raise ServiceException(
                detail="Rental package not found",
                code="rental_package_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get rental package")
    
    @transaction.atomic
    def create_rental_package(self, data: Dict[str, Any]) -> RentalPackage:
        """Create a new rental package"""
        try:
            rental_package = RentalPackage.objects.create(
                name=data['name'],
                description=data['description'],
                duration_minutes=data['duration_minutes'],
                price=data['price'],
                package_type=data['package_type'],
                payment_model=data['payment_model'],
                is_active=data.get('is_active', True),
                package_metadata=data.get('package_metadata', {})
            )
            
            return rental_package
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create rental package")
    
    @transaction.atomic
    def update_rental_package(self, package_id: str, data: Dict[str, Any]) -> RentalPackage:
        """Update an existing rental package"""
        try:
            rental_package = self.get_rental_package(package_id)
            
            # Update fields
            if 'name' in data:
                rental_package.name = data['name']
            if 'description' in data:
                rental_package.description = data['description']
            if 'duration_minutes' in data:
                rental_package.duration_minutes = data['duration_minutes']
            if 'price' in data:
                rental_package.price = data['price']
            if 'package_type' in data:
                rental_package.package_type = data['package_type']
            if 'payment_model' in data:
                rental_package.payment_model = data['payment_model']
            if 'is_active' in data:
                rental_package.is_active = data['is_active']
            if 'package_metadata' in data:
                rental_package.package_metadata = data['package_metadata']
            
            rental_package.save()
            return rental_package
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update rental package")
    
    @transaction.atomic
    def delete_rental_package(self, package_id: str) -> Dict[str, Any]:
        """Delete (soft delete) a rental package"""
        try:
            rental_package = self.get_rental_package(package_id)
            
            # Soft delete by setting is_active to False
            rental_package.is_active = False
            rental_package.save()
            
            return {
                'id': str(rental_package.id),
                'name': rental_package.name,
                'deleted': True
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to delete rental package")
    
    # ============================================================
    # Transactions Management
    # ============================================================
    
    def get_transactions(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get combined list of all transactions (Transaction, WalletTransaction, PointsTransaction)"""
        try:
            if not filters:
                filters = {}
            
            combined_transactions = []
            
            # Common filters
            source = filters.get('source', 'all')
            user_id = filters.get('user_id')
            search = filters.get('search')
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            
            # Get Payment Transactions
            if source in ['all', 'payment']:
                txn_query = Transaction.objects.select_related('user', 'related_rental')
                if user_id:
                    txn_query = txn_query.filter(user_id=user_id)
                if search:
                    txn_query = txn_query.filter(
                        Q(transaction_id__icontains=search) | Q(user__username__icontains=search) | Q(user__email__icontains=search)
                    )
                if start_date:
                    txn_query = txn_query.filter(created_at__gte=start_date)
                if end_date:
                    txn_query = txn_query.filter(created_at__lte=end_date)
                
                for txn in txn_query:
                    combined_transactions.append({
                        'source': 'payment',
                        'id': str(txn.id),
                        'transaction_id': txn.transaction_id,
                        'user': {'id': str(txn.user.id), 'username': txn.user.username, 'email': txn.user.email},
                        'type': txn.transaction_type,
                        'amount': float(txn.amount),
                        'status': txn.status,
                        'created_at': txn.created_at,
                        'description': f"{txn.get_transaction_type_display()} - {txn.get_status_display()}"
                    })
            
            # Get Wallet Transactions
            if source in ['all', 'wallet']:
                wallet_query = WalletTransaction.objects.select_related('wallet__user')
                if user_id:
                    wallet_query = wallet_query.filter(wallet__user_id=user_id)
                if search:
                    wallet_query = wallet_query.filter(
                        Q(wallet__user__username__icontains=search) | Q(wallet__user__email__icontains=search)
                    )
                if start_date:
                    wallet_query = wallet_query.filter(created_at__gte=start_date)
                if end_date:
                    wallet_query = wallet_query.filter(created_at__lte=end_date)
                
                for wtxn in wallet_query:
                    combined_transactions.append({
                        'source': 'wallet',
                        'id': str(wtxn.id),
                        'transaction_id': f"W-{wtxn.id}",
                        'user': {'id': str(wtxn.wallet.user.id), 'username': wtxn.wallet.user.username, 'email': wtxn.wallet.user.email},
                        'type': wtxn.transaction_type,
                        'amount': float(wtxn.amount),
                        'status': 'COMPLETED',
                        'balance_before': float(wtxn.balance_before),
                        'balance_after': float(wtxn.balance_after),
                        'created_at': wtxn.created_at,
                        'description': wtxn.description
                    })
            
            # Get Points Transactions
            if source in ['all', 'points']:
                points_query = PointsTransaction.objects.select_related('user')
                if user_id:
                    points_query = points_query.filter(user_id=user_id)
                if search:
                    points_query = points_query.filter(
                        Q(user__username__icontains=search) | Q(user__email__icontains=search)
                    )
                if start_date:
                    points_query = points_query.filter(created_at__gte=start_date)
                if end_date:
                    points_query = points_query.filter(created_at__lte=end_date)
                
                for ptxn in points_query:
                    combined_transactions.append({
                        'source': 'points',
                        'id': str(ptxn.id),
                        'transaction_id': f"P-{ptxn.id}",
                        'user': {'id': str(ptxn.user.id), 'username': ptxn.user.username, 'email': ptxn.user.email},
                        'type': ptxn.transaction_type,
                        'points': ptxn.points,
                        'points_source': ptxn.source,
                        'status': 'COMPLETED',
                        'balance_before': ptxn.balance_before,
                        'balance_after': ptxn.balance_after,
                        'created_at': ptxn.created_at,
                        'description': ptxn.description
                    })
            
            # Sort by date (newest first)
            combined_transactions.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Pagination
            page = filters.get('page', 1)
            page_size = filters.get('page_size', 20)
            total_count = len(combined_transactions)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            return {
                'results': combined_transactions[start_idx:end_idx],
                'pagination': {
                    'total_count': total_count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total_count + page_size - 1) // page_size
                }
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get transactions")
