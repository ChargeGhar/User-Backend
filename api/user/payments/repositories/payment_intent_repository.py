from typing import Optional, Dict, Any, List
from django.utils import timezone
from api.user.payments.models import PaymentIntent

class PaymentIntentRepository:
    """Repository for PaymentIntent data operations"""
    
    @staticmethod
    def get_by_intent_id(intent_id: str) -> Optional[PaymentIntent]:
        try:
            return PaymentIntent.objects.get(intent_id=intent_id)
        except PaymentIntent.DoesNotExist:
            return None

    @staticmethod
    def get_expired_intents() -> List[PaymentIntent]:
        """Get all pending intents that have passed their expiry time"""
        return PaymentIntent.objects.filter(
            status="PENDING", 
            expires_at__lt=timezone.now()
        )

    @staticmethod
    def create(
        user,
        intent_id: str,
        intent_type: str,
        amount: float,
        currency: str = 'NPR',
        expires_at = None,
        intent_metadata: Dict[str, Any] = None,
        **kwargs
    ) -> PaymentIntent:
        return PaymentIntent.objects.create(
            user=user,
            intent_id=intent_id,
            intent_type=intent_type,
            amount=amount,
            currency=currency,
            expires_at=expires_at,
            intent_metadata=intent_metadata or {},
            **kwargs
        )

    @staticmethod
    def update_status(intent: PaymentIntent, status: str, completed_at=None) -> PaymentIntent:
        intent.status = status
        update_fields = ['status', 'updated_at']
        if completed_at:
            intent.completed_at = completed_at
            update_fields.append('completed_at')
        intent.save(update_fields=update_fields)
        return intent

    @staticmethod
    def cancel_with_reason(intent: PaymentIntent, reason: str) -> PaymentIntent:
        """Cancel an intent with a specific reason in metadata"""
        intent.status = "CANCELLED"
        if not intent.intent_metadata:
            intent.intent_metadata = {}
        intent.intent_metadata["expiry_reason"] = reason
        intent.save(update_fields=["status", "intent_metadata", "updated_at"])
        return intent
