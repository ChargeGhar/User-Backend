from __future__ import annotations

from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count, Q
from decimal import Decimal
from typing import Dict, Any

from api.common.tasks.base import BaseTask, PaymentTask
from api.payments.repositories import PaymentIntentRepository

@shared_task(base=BaseTask, bind=True)
def expire_payment_intents(self):
    """Mark expired payment intents as failed"""
    try:
        repository = PaymentIntentRepository()
        expired_intents = repository.get_expired_intents()

        expired_count = 0
        for intent in expired_intents:
            repository.cancel_with_reason(intent, "Expired due to timeout")
            expired_count += 1

        self.logger.info(f"Expired {expired_count} payment intents")
        return {"expired_count": expired_count}

    except Exception as e:
        self.logger.error(f"Failed to expire payment intents: {str(e)}")
        raise