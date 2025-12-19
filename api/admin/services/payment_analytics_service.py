"""
Payment Analytics Service
"""
from __future__ import annotations
from typing import Dict, Any
from decimal import Decimal
from django.db.models import Count, Sum, Q
from api.common.services.base import BaseService
from api.payments.models import Transaction, Wallet, WalletTransaction
from api.users.models import User


class PaymentAnalyticsService(BaseService):
    """Service for payment analytics"""
    
    def get_payment_analytics(self) -> Dict[str, Any]:
        """Get payment analytics for chart visualization"""
        try:
            # Summary statistics - only SUCCESS transactions
            transactions_summary = Transaction.objects.filter(
                status='SUCCESS'
            ).aggregate(
                total_count=Count('id'),
                total_revenue=Sum('amount'),
                topup_revenue=Sum('amount', filter=Q(transaction_type='TOPUP')),
                rental_revenue=Sum('amount', filter=Q(transaction_type='RENTAL')),
                rental_due_revenue=Sum('amount', filter=Q(transaction_type='RENTAL_DUE'))
            )
            
            total_transactions = transactions_summary['total_count'] or 0
            total_revenue = transactions_summary['total_revenue'] or Decimal('0')
            total_topups = transactions_summary['topup_revenue'] or Decimal('0')
            total_rental_payments = (transactions_summary['rental_revenue'] or Decimal('0')) + \
                                   (transactions_summary['rental_due_revenue'] or Decimal('0'))
            
            avg_transaction = (total_revenue / total_transactions) if total_transactions > 0 else Decimal('0')
            
            # Payment methods distribution
            payment_methods = Transaction.objects.filter(
                status='SUCCESS'
            ).values('payment_method_type').annotate(
                count=Count('id'),
                amount=Sum('amount')
            )
            
            pm_data = {pm['payment_method_type']: pm for pm in payment_methods}
            
            # Format payment methods for chart
            pm_labels = []
            pm_amounts = []
            pm_counts = []
            pm_percentages = []
            
            for method in ['WALLET', 'GATEWAY', 'POINTS', 'COMBINATION']:
                data = pm_data.get(method, {'count': 0, 'amount': Decimal('0')})
                amount = data['amount']
                percentage = (amount / total_revenue * 100) if total_revenue > 0 else 0
                
                pm_labels.append(method.title())
                pm_amounts.append(float(amount))
                pm_counts.append(data['count'])
                pm_percentages.append(round(percentage, 2))
            
            # Specific gateway usage (Khalti, eSewa, etc.) - aggregated by gateway type
            gateway_transactions = Transaction.objects.filter(
                status='SUCCESS',
                payment_method_type='GATEWAY'
            ).exclude(
                Q(gateway_reference__isnull=True) | Q(gateway_reference='')
            ).values('gateway_reference', 'amount')
            
            # Aggregate by gateway type
            gateway_summary = {}
            for gt in gateway_transactions:
                ref = gt['gateway_reference'] or ''
                gateway_name = 'Unknown'
                
                if 'khalti' in ref.lower():
                    gateway_name = 'Khalti'
                elif 'esewa' in ref.lower():
                    gateway_name = 'eSewa'
                elif 'stripe' in ref.lower():
                    gateway_name = 'Stripe'
                
                if gateway_name not in gateway_summary:
                    gateway_summary[gateway_name] = {'count': 0, 'amount': Decimal('0')}
                
                gateway_summary[gateway_name]['count'] += 1
                gateway_summary[gateway_name]['amount'] += gt['amount']
            
            # Convert to list
            gateway_usage = [
                {
                    'gateway': gateway,
                    'count': data['count'],
                    'amount': float(data['amount'])
                }
                for gateway, data in gateway_summary.items()
            ]
            
            # Transaction types breakdown
            transaction_types = Transaction.objects.filter(
                status='SUCCESS'
            ).values('transaction_type').annotate(
                count=Count('id'),
                amount=Sum('amount')
            )
            
            tt_data = {tt['transaction_type']: tt for tt in transaction_types}
            
            # Format for revenue by type chart
            revenue_labels = ['Top-Up', 'Rental', 'Rental Due', 'Fine']
            revenue_data = [
                float(tt_data.get('TOPUP', {}).get('amount', Decimal('0'))),
                float(tt_data.get('RENTAL', {}).get('amount', Decimal('0'))),
                float(tt_data.get('RENTAL_DUE', {}).get('amount', Decimal('0'))),
                float(tt_data.get('FINE', {}).get('amount', Decimal('0')))
            ]
            
            # Top 10 users by spending with payment method breakdown
            top_users = User.objects.annotate(
                rental_count=Count('rentals'),
                total_spent=Sum('transactions__amount', filter=Q(
                    transactions__status='SUCCESS',
                    transactions__transaction_type__in=['RENTAL', 'RENTAL_DUE']
                )),
                total_topups=Sum('transactions__amount', filter=Q(
                    transactions__status='SUCCESS',
                    transactions__transaction_type='TOPUP'
                )),
                wallet_payments=Count('transactions', filter=Q(
                    transactions__status='SUCCESS',
                    transactions__payment_method_type='WALLET'
                )),
                gateway_payments=Count('transactions', filter=Q(
                    transactions__status='SUCCESS',
                    transactions__payment_method_type='GATEWAY'
                )),
                points_payments=Count('transactions', filter=Q(
                    transactions__status='SUCCESS',
                    transactions__payment_method_type='POINTS'
                )),
                combination_payments=Count('transactions', filter=Q(
                    transactions__status='SUCCESS',
                    transactions__payment_method_type='COMBINATION'
                ))
            ).filter(
                total_spent__isnull=False
            ).select_related('wallet').order_by('-total_spent', '-rental_count')[:10]
            
            # Format top users
            top_users_data = []
            top_users_labels = []
            top_users_spent = []
            
            for user in top_users:
                wallet_balance = user.wallet.balance if hasattr(user, 'wallet') else Decimal('0')
                
                # Determine preferred payment method
                payment_counts = {
                    'wallet': user.wallet_payments,
                    'gateway': user.gateway_payments,
                    'points': user.points_payments,
                    'combination': user.combination_payments
                }
                preferred_method = max(payment_counts, key=payment_counts.get) if sum(payment_counts.values()) > 0 else 'none'
                
                top_users_data.append({
                    'user_id': str(user.id),
                    'username': user.username or 'N/A',
                    'email': user.email or 'N/A',
                    'total_rentals': user.rental_count,
                    'total_spent': float(user.total_spent or Decimal('0')),
                    'total_topups': float(user.total_topups or Decimal('0')),
                    'wallet_balance': float(wallet_balance),
                    'preferred_payment_method': preferred_method
                })
                
                top_users_labels.append(user.username or f'User {str(user.id)[:8]}')
                top_users_spent.append(float(user.total_spent or Decimal('0')))
            
            # Wallet analytics
            wallet_stats = Wallet.objects.aggregate(
                total_wallets=Count('id'),
                active_wallets=Count('id', filter=Q(is_active=True)),
                total_balance=Sum('balance')
            )
            
            wallet_transactions_stats = WalletTransaction.objects.aggregate(
                total_credits=Sum('amount', filter=Q(transaction_type='CREDIT')),
                total_debits=Sum('amount', filter=Q(transaction_type='DEBIT'))
            )
            
            total_wallets = wallet_stats['total_wallets'] or 0
            total_balance = wallet_stats['total_balance'] or Decimal('0')
            avg_balance = (total_balance / total_wallets) if total_wallets > 0 else Decimal('0')
            
            # Transaction breakdown detail
            transaction_breakdown = {}
            for tt_type, label in [('TOPUP', 'topup'), ('RENTAL', 'rental'), 
                                   ('RENTAL_DUE', 'rental_due'), ('REFUND', 'refund')]:
                data = tt_data.get(tt_type, {'count': 0, 'amount': Decimal('0')})
                count = data['count']
                amount = data['amount']
                avg = (amount / count) if count > 0 else Decimal('0')
                
                transaction_breakdown[label] = {
                    'count': count,
                    'amount': float(amount),
                    'average': float(avg)
                }
            
            return {
                'summary': {
                    'total_transactions': total_transactions,
                    'total_revenue': float(total_revenue),
                    'total_topups': float(total_topups),
                    'total_rental_payments': float(total_rental_payments),
                    'average_transaction_value': float(avg_transaction)
                },
                'payment_methods_chart': {
                    'labels': pm_labels,
                    'values': pm_amounts,
                    'counts': pm_counts,
                    'percentages': pm_percentages
                },
                'gateway_usage': gateway_usage,
                'revenue_by_type_chart': {
                    'labels': revenue_labels,
                    'datasets': [{
                        'label': 'Revenue (NPR)',
                        'data': revenue_data
                    }]
                },
                'top_users_chart': {
                    'labels': top_users_labels,
                    'datasets': [{
                        'label': 'Total Spent (NPR)',
                        'data': top_users_spent
                    }]
                },
                'top_performers': top_users_data,
                'wallet_stats': {
                    'total_wallets': total_wallets,
                    'active_wallets': wallet_stats['active_wallets'] or 0,
                    'total_balance': float(total_balance),
                    'average_balance': float(avg_balance),
                    'total_credits': float(wallet_transactions_stats['total_credits'] or Decimal('0')),
                    'total_debits': float(wallet_transactions_stats['total_debits'] or Decimal('0'))
                },
                'transaction_breakdown': transaction_breakdown
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get payment analytics")
