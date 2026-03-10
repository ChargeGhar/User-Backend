from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from api.user.promotions.models import Coupon
from api.user.promotions.services import CouponService


def create_coupon(code: str, **overrides) -> Coupon:
    now = timezone.now()
    data = {
        'code': code,
        'name': f'{code} coupon',
        'points_value': 25,
        'max_uses_per_user': 1,
        'is_public': True,
        'valid_from': now - timedelta(days=1),
        'valid_until': now + timedelta(days=1),
        'status': Coupon.StatusChoices.ACTIVE,
    }
    data.update(overrides)
    return Coupon.objects.create(**data)


@pytest.fixture(autouse=True)
def clear_coupon_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_public_active_endpoint_returns_only_public_coupons(api_client):
    create_coupon('PUBLIC10', is_public=True)
    create_coupon('PRIVATE10', is_public=False)
    create_coupon('INACTIVE10', status=Coupon.StatusChoices.INACTIVE)
    create_coupon('EXPIRED10', valid_until=timezone.now() - timedelta(hours=1))

    response = api_client.get('/api/promotions/coupons/active')

    assert response.status_code == 200
    codes = {coupon['code'] for coupon in response.data['data']}
    assert 'PUBLIC10' in codes
    assert 'PRIVATE10' not in codes
    assert 'INACTIVE10' not in codes
    assert 'EXPIRED10' not in codes


@pytest.mark.django_db
def test_private_coupon_still_validates_for_user():
    user = get_user_model().objects.create_user(email='coupon-user@example.com')
    create_coupon('PRIVATEOK', is_public=False, points_value=50)

    result = CouponService().validate_coupon('privateok', user)

    assert result['valid'] is True
    assert result['can_use'] is True
    assert result['coupon_code'] == 'PRIVATEOK'
    assert result['points_value'] == 50