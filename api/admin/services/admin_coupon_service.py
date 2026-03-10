from __future__ import annotations

from typing import Any, Dict

from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from api.admin.models import AdminActionLog
from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import paginate_queryset
from api.user.promotions.models import Coupon, CouponUsage
from api.user.promotions.services import CouponService


class AdminCouponService(BaseService):
    """Admin service for managing coupons."""

    def __init__(self) -> None:
        super().__init__()
        self.coupon_service = CouponService()

    def get_coupons(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get coupons with admin filters."""
        return self.coupon_service.get_coupons_list(filters)

    def create_coupon(self, data: Dict[str, Any], admin_user, request=None) -> Coupon:
        """Create a single coupon."""
        return self.coupon_service.create_coupon(admin_user=admin_user, **data)

    def bulk_create_coupons(self, data: Dict[str, Any], admin_user, request=None):
        """Bulk create coupons."""
        return self.coupon_service.bulk_create_coupons(admin_user=admin_user, **data)

    def get_coupon_detail(self, coupon_code: str) -> Dict[str, Any]:
        """Get coupon and usage stats."""
        coupon = self._get_coupon(coupon_code)
        usage_stats = CouponUsage.objects.filter(coupon=coupon).aggregate(
            total_uses=Count('id'),
            unique_users=Count('user', distinct=True),
            total_points_awarded=Coalesce(Sum('points_awarded'), 0),
        )
        return {'coupon': coupon, 'usage_stats': usage_stats}

    @transaction.atomic
    def update_coupon(self, coupon_code: str, data: Dict[str, Any], admin_user, request=None) -> Coupon:
        """Update coupon visibility/status."""
        coupon = self._get_coupon(coupon_code)
        changes = {}

        for field in ['status', 'is_public']:
            if field in data and getattr(coupon, field) != data[field]:
                changes[field] = {'old': getattr(coupon, field), 'new': data[field]}
                setattr(coupon, field, data[field])

        if not changes:
            return coupon

        update_fields = list(changes.keys()) + ['updated_at']
        coupon.save(update_fields=update_fields)
        CouponService.invalidate_public_active_coupons_cache()

        self._log_admin_action(
            admin_user=admin_user,
            action_type='UPDATE_COUPON',
            target_id=str(coupon.id),
            changes=changes,
            description=f"Updated coupon: {coupon.code}",
            request=request,
        )
        return coupon

    @transaction.atomic
    def soft_delete_coupon(self, coupon_code: str, admin_user, request=None) -> None:
        """Soft delete coupon by setting it inactive."""
        coupon = self._get_coupon(coupon_code)
        previous_status = coupon.status
        coupon.status = Coupon.StatusChoices.INACTIVE
        coupon.save(update_fields=['status', 'updated_at'])
        CouponService.invalidate_public_active_coupons_cache()

        self._log_admin_action(
            admin_user=admin_user,
            action_type='DELETE_COUPON',
            target_id=str(coupon.id),
            changes={'status': {'old': previous_status, 'new': coupon.status}},
            description=f"Deleted coupon: {coupon.code}",
            request=request,
        )

    def get_coupon_usages(self, coupon_code: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get paginated coupon usages."""
        coupon = self._get_coupon(coupon_code)
        queryset = CouponUsage.objects.filter(coupon=coupon).select_related('user', 'coupon').order_by('-used_at')
        return paginate_queryset(queryset, page, page_size)

    def _get_coupon(self, coupon_code: str) -> Coupon:
        try:
            return Coupon.objects.get(code=coupon_code.upper())
        except Coupon.DoesNotExist as exc:
            raise ServiceException(detail='Coupon not found', code='not_found') from exc

    def _log_admin_action(
        self,
        admin_user,
        action_type: str,
        target_id: str,
        changes: Dict[str, Any],
        description: str,
        request=None,
    ) -> None:
        AdminActionLog.objects.create(
            admin_user=admin_user,
            action_type=action_type,
            target_model='Coupon',
            target_id=target_id,
            changes=changes,
            description=description,
            ip_address=request.META.get('REMOTE_ADDR', '') if request else '',
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        )