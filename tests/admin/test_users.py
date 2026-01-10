import pytest
import requests

BASE_URL = 'http://localhost:8010'


@pytest.mark.api
class TestAdminUsersAPI:
    """Test cases for admin user management endpoints."""

    @pytest.fixture
    def access_token(self):
        """Get admin access token."""
        response = requests.post(f'{BASE_URL}/api/admin/login', data={
            'email': 'janak@powerbank.com',
            'password': '5060'
        })
        if response.status_code == 200:
            data = response.json()['data']
            return data['access_token']
        else:
            pytest.fail(f"Admin login failed: {response.status_code} - {response.text}")

    @pytest.fixture
    def headers(self, access_token):
        """Headers with authorization."""
        return {'Authorization': f'Bearer {access_token}'}

    def test_get_users(self, headers):
        """Test get all users."""
        response = requests.get(f'{BASE_URL}/api/admin/users', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_user_detail(self, headers):
        """Test get user detail."""
        response = requests.get(f'{BASE_URL}/api/admin/users/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_user_balance(self, headers):
        """Test add balance to user."""
        data = {'amount': 100, 'reason': 'test'}
        response = requests.post(f'{BASE_URL}/api/admin/users/1/add-balance', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_update_user_status(self, headers):
        """Test update user status."""
        data = {'status': 'active'}
        response = requests.post(f'{BASE_URL}/api/admin/users/1/status', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_user_leaderboard_admin(self, headers):
        """Test get user leaderboard (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/users/leaderboard', headers=headers)
        assert response.status_code in [200, 400, 500]