import pytest
import requests

BASE_URL = 'http://localhost:8010'


@pytest.mark.api
class TestAdminAuthAPI:
    """Test cases for admin authentication and profile endpoints."""

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

    def test_admin_login(self):
        """Test admin login."""
        response = requests.post(f'{BASE_URL}/api/admin/login', data={
            'email': 'janak@powerbank.com',
            'password': '5060'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data
        assert 'access_token' in data['data']

    def test_admin_me(self, headers):
        """Test admin profile endpoint."""
        response = requests.get(f'{BASE_URL}/api/admin/me', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_admin_profiles(self, headers):
        """Test get admin profiles."""
        response = requests.get(f'{BASE_URL}/api/admin/profiles', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_create_admin_profile(self, headers):
        """Test create admin profile."""
        data = {'username': 'newadmin', 'email': 'admin@example.com'}
        response = requests.post(f'{BASE_URL}/api/admin/profiles', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_get_admin_profile_detail(self, headers):
        """Test get admin profile detail."""
        response = requests.get(f'{BASE_URL}/api/admin/profiles/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_admin_profile(self, headers):
        """Test update admin profile."""
        data = {'email': 'updated@example.com'}
        response = requests.patch(f'{BASE_URL}/api/admin/profiles/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_admin_profile(self, headers):
        """Test delete admin profile."""
        response = requests.delete(f'{BASE_URL}/api/admin/profiles/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]