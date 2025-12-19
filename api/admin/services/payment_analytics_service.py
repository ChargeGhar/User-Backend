"""
Payment Analytics Service
Provides analytics data for transactions, revenue, payment methods, and top users
"""
from decimal import Decimal
from django.db.models import Count, Sum, Q, F
from django.utils import timezone

from api.payments.models import Transaction, Wallet
from api.users.models import User


class PaymentAnalyticsService:
    """Service for payment analytics operations"""
    
    @staticmethod
    def get_payment_analytics():
        """
        Get comprehensive payment analytics data
        
        Returns:
            dict: Payment analytics including revenue, payment methods, and top users
        """
        # Total revenue and counts
        total_stats = Transaction.objects.filter(status='SUCCESS').aggregate(
            total_revenue=Sum('amount'),
            total_count=Count('id')
        )
        
        total_revenue = total_stats['total_revenue'] or Decimal('0')
        total_transactions = total_stats['total_count'] or 0
        
        # Rental revenue
        rental_revenue = Transaction.objects.filter(
            status='SUCCESS',
            related_rental__isnull=False
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Top-up revenue
        topup_revenue = Transaction.objects.filter(
            status='SUCCESS',
            transaction_type='TOPUP'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Overall payment methods
        payment_methods = Transaction.objects.filter(status='SUCCESS').values('payment_method_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        pm_data = {pm['payment_method_type']: pm for pm in payment_methods}
        
        pm_labels = []
        pm_values = []
        pm_counts = []
        
        for method in ['WALLET', 'GATEWAY', 'POINTS', 'COMBINATION']:
            data = pm_data.get(method, {'total': Decimal('0'), 'count': 0})
            pm_labels.append(method.title())
            pm_values.append(float(data['total']))
            pm_counts.append(data['count'])
        
        # Calculate percentages
        pm_percentages = []
        for i, value in enumerate(pm_values):
            if i == len(pm_values) - 1:
                pct = round(100 - sum(pm_percentages), 2) if total_revenue > 0 else 0
            else:
                pct = round((value / float(total_revenue) * 100), 2) if total_revenue > 0 else 0
            pm_percentages.append(pct)
        
        # Gateway breakdown
        gateway_txns = Transaction.objects.filter(
            status='SUCCESS',
            payment_method_type='GATEWAY'
        ).exclude(
            Q(gateway_reference__isnull=True) | Q(gateway_reference='')
        ).values('gateway_reference', 'amount')
        
        gateway_summary = {}
        for txn in gateway_txns:
            ref = (txn['gateway_reference'] or '').lower()
            gateway = None
            
            if 'khalti' in ref:
                gateway = 'Khalti'
            elif 'esewa' in ref:
                gateway = 'eSewa'
            elif 'stripe' in ref:
                gateway = 'Stripe'
            else:
                continue
            
            if gateway not in gateway_summary:
                gateway_summary[gateway] = {'count': 0, 'amount': Decimal('0')}
            
            gateway_summary[gateway]['count'] += 1
            gateway_summary[gateway]['amount'] += txn['amount']
        
        gateway_labels = []
        gateway_values = []
        gateway_counts = []
        gateway_total = sum(data['amount'] for data in gateway_summary.values())
        
        for gateway in ['Khalti', 'eSewa', 'Stripe']:
            if gateway in gateway_summary:
                gateway_labels.append(gateway)
                gateway_values.append(float(gateway_summary[gateway]['amount']))
                gateway_counts.append(gateway_summary[gateway]['count'])
        
        gateway_percentages = []
        for i, value in enumerate(gateway_values):
            if i == len(gateway_values) - 1:
                pct = round(100 - sum(gateway_percentages), 2) if gateway_total > 0 else 0
            else:
                pct = round((value / float(gateway_total) * 100), 2) if gateway_total > 0 else 0
            gateway_percentages.append(pct)
        
        # Top 10 users by total transaction amount
        top_users = User.objects.annotate(
            total_amount=Sum('transactions__amount', filter=Q(transactions__status='SUCCESS')),
            rental_amount=Sum('transactions__amount', filter=Q(
                transactions__status='SUCCESS',
                transactions__related_rental__isnull=False
            )),
            topup_amount=Sum('transactions__amount', filter=Q(
                transactions__status='SUCCESS',
                transactions__transaction_type='TOPUP'
            )),
            rental_count=Count('rentals', filter=Q(
                rentals__status__in=['ACTIVE', 'COMPLETED', 'OVERDUE']
            )),
            transaction_count=Count('transactions', filter=Q(transactions__status='SUCCESS')),
            wallet_count=Count('transactions', filter=Q(
                transactions__status='SUCCESS',
                transactions__payment_method_type='WALLET'
            )),
            gateway_count=Count('transactions', filter=Q(
                transactions__status='SUCCESS',
                transactions__payment_method_type='GATEWAY'
            )),
            points_count=Count('transactions', filter=Q(
                transactions__status='SUCCESS',
                transactions__payment_method_type='POINTS'
            )),
            combination_count=Count('transactions', filter=Q(
                transactions__status='SUCCESS',
                transactions__payment_method_type='COMBINATION'
            ))
        ).filter(
            total_amount__gt=0
        ).order_by('-total_amount')[:10]
        
        top_users_data = []
        for user in top_users:
            # Get wallet balance
            try:
                wallet_balance = float(user.wallet.balance)
            except:
                wallet_balance = 0.0
            
            # Get gateway usage per user
            user_gateways = Transaction.objects.filter(
                status='SUCCESS',
                user=user,
                payment_method_type='GATEWAY'
            ).exclude(
                Q(gateway_reference__isnull=True) | Q(gateway_reference='')
            ).values('gateway_reference')
            
            gateway_usage = {'khalti': 0, 'esewa': 0, 'stripe': 0}
            for txn in user_gateways:
                ref = (txn['gateway_reference'] or '').lower()
                if 'khalti' in ref:
                    gateway_usage['khalti'] += 1
                elif 'esewa' in ref:
                    gateway_usage['esewa'] += 1
                elif 'stripe' in ref:
                    gateway_usage['stripe'] += 1
            
            top_users_data.append({
                'user_id': str(user.id),
                'username': user.username,
                'email': user.email or 'N/A',
                'total_transaction_amount': float(user.total_amount or 0),
                'rental_payment_amount': float(user.rental_amount or 0),
                'topup_amount': float(user.topup_amount or 0),
                'wallet_balance': wallet_balance,
                'rental_count': user.rental_count,
                'transaction_count': user.transaction_count,
                'payment_methods': {
                    'wallet': user.wallet_count,
                    'gateway': user.gateway_count,
                    'points': user.points_count,
                    'combination': user.combination_count
                },
                'gateways_used': gateway_usage
            })
        
        # Payment method by transaction type
        rental_pm = Transaction.objects.filter(
            status='SUCCESS',
            related_rental__isnull=False
        ).values('payment_method_type').annotate(total=Sum('amount'))
        
        topup_pm = Transaction.objects.filter(
            status='SUCCESS',
            transaction_type='TOPUP'
        ).values('payment_method_type').annotate(total=Sum('amount'))
        
        rental_pm_dict = {item['payment_method_type']: float(item['total']) for item in rental_pm}
        topup_pm_dict = {item['payment_method_type']: float(item['total']) for item in topup_pm}
        
        payment_by_type = {
            'rentals': {
                'wallet': rental_pm_dict.get('WALLET', 0),
                'gateway': rental_pm_dict.get('GATEWAY', 0),
                'points': rental_pm_dict.get('POINTS', 0),
                'combination': rental_pm_dict.get('COMBINATION', 0)
            },
            'topups': {
                'wallet': topup_pm_dict.get('WALLET', 0),
                'gateway': topup_pm_dict.get('GATEWAY', 0),
                'points': topup_pm_dict.get('POINTS', 0),
                'combination': topup_pm_dict.get('COMBINATION', 0)
            }
        }
        
        return {
            'summary': {
                'total_revenue': float(total_revenue),
                'total_transactions': total_transactions,
                'rental_revenue': float(rental_revenue),
                'topup_revenue': float(topup_revenue)
            },
            'overall_payment_methods': {
                'labels': pm_labels,
                'values': pm_values,
                'counts': pm_counts,
                'percentages': pm_percentages
            },
            'gateway_breakdown': {
                'labels': gateway_labels,
                'values': gateway_values,
                'counts': gateway_counts,
                'percentages': gateway_percentages
            },
            'top_10_users': top_users_data,
            'revenue_breakdown_chart': {
                'labels': ['Top-ups', 'Rental Payments'],
                'values': [float(topup_revenue), float(rental_revenue)]
            },
            'payment_method_by_transaction_type': payment_by_type
        }
