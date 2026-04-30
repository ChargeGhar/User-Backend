from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from api.user.auth.models import User, UserKYC, UserProfile


@pytest.mark.django_db
def test_admin_user_list_returns_linked_kyc_status() -> None:
    admin_user = User.objects.create_user(
        email='admin-users@example.com',
        username='admin_users',
        is_staff=True,
        is_superuser=True,
    )
    listed_user = User.objects.create_user(
        email='kyc-user@example.com',
        username='kyc_user',
    )

    UserProfile.objects.create(
        user=listed_user,
        full_name='KYC User',
        address='Kathmandu',
        is_profile_complete=True,
    )
    UserKYC.objects.create(
        user=listed_user,
        document_type='CITIZENSHIP',
        document_number='ABC123456',
        document_front_url='https://example.com/front.jpg',
        document_back_url='https://example.com/back.jpg',
        status='PENDING',
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get('/api/admin/users', {'page': 1, 'page_size': 20})

    assert response.status_code == 200
    payload = response.json()['data']['results']
    user_row = next(item for item in payload if item['id'] == listed_user.id)
    assert user_row['kyc_status'] == 'PENDING'
    assert user_row['profile_complete'] is True
    assert user_row['profile']['full_name'] == 'KYC User'
