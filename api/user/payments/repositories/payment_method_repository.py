from typing import Optional
from django.db.models import QuerySet
from api.user.payments.models import PaymentMethod

class PaymentMethodRepository:
    """Repository for PaymentMethod data operations"""
    
    @staticmethod
    def get_by_id(method_id: str) -> Optional[PaymentMethod]:
        try:
            return PaymentMethod.objects.get(id=method_id, is_active=True)
        except PaymentMethod.DoesNotExist:
            return None

    @staticmethod
    def get_active_methods() -> QuerySet:
        return PaymentMethod.objects.filter(is_active=True).order_by('name')

    @staticmethod
    def get_by_gateway(gateway: str) -> Optional[PaymentMethod]:
        try:
            return PaymentMethod.objects.get(gateway=gateway, is_active=True)
        except PaymentMethod.DoesNotExist:
            return None
