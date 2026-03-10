from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from api.user.promotions.models import Coupon


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


@pytest.fixture
def admin_user():
    return get_user_model().objects.create_user(
        email='admin-coupons@example.com',
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
def test_admin_can_create_private_coupon_and_filter_by_visibility(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    now = timezone.now()

    response = api_client.post(
        '/api/admin/coupons',
        {
            'code': 'ADMINPRIVATE',
            'name': 'Admin Private Coupon',
            'points_value': 75,
            'max_uses_per_user': 2,
            'is_public': False,
            'valid_from': (now - timedelta(days=1)).isoformat(),
            'valid_until': (now + timedelta(days=7)).isoformat(),
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['data']['is_public'] is False
    assert Coupon.objects.get(code='ADMINPRIVATE').is_public is False

    list_response = api_client.get('/api/admin/coupons?is_public=false')

    assert list_response.status_code == 200
    codes = {coupon['code'] for coupon in list_response.data['data']['results']}
    assert 'ADMINPRIVATE' in codes


@pytest.mark.django_db
def test_admin_bulk_create_private_coupons(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    now = timezone.now()

    response = api_client.post(
        '/api/admin/coupons/bulk',
        {
            'name_prefix': 'Private Batch',
            'points_value': 40,
            'max_uses_per_user': 1,
            'is_public': False,
            'valid_from': (now - timedelta(days=1)).isoformat(),
            'valid_until': (now + timedelta(days=7)).isoformat(),
            'quantity': 2,
            'code_length': 8,
        },
        format='json',
    )

    assert response.status_code == 201
    created_codes = response.data['data']['codes']
    assert len(created_codes) == 2
    assert Coupon.objects.filter(code__in=created_codes, is_public=False).count() == 2


@pytest.mark.django_db
def test_admin_patch_invalidates_public_coupon_cache(api_client, admin_user):
    coupon = create_coupon('CACHEME', is_public=True)

    first_response = api_client.get('/api/promotions/coupons/active')
    assert first_response.status_code == 200
    assert 'CACHEME' in {item['code'] for item in first_response.data['data']}

    api_client.force_authenticate(user=admin_user)
    patch_response = api_client.patch(
        f'/api/admin/coupons/{coupon.code}',
        {'is_public': False},
        format='json',
    )

    assert patch_response.status_code == 200
    assert patch_response.data['data']['is_public'] is False

    api_client.force_authenticate(user=None)
    second_response = api_client.get('/api/promotions/coupons/active')

    assert second_response.status_code == 200
    assert 'CACHEME' not in {item['code'] for item in second_response.data['data']}