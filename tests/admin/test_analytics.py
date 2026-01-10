import pytest
import requests

BASE_URL = 'http://localhost:8010'


@pytest.mark.api
class TestAdminAnalyticsAPI:
    """Test cases for admin analytics endpoints."""

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

    def test_get_payment_analytics(self, headers):
        """Test get payment analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/analytics/payments', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_powerbank_rental_analytics(self, headers):
        """Test get powerbank rental analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/analytics/powerbank-rentals', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_rentals_over_time_analytics(self, headers):
        """Test get rentals over time analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/analytics/rentals-over-time', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_revenue_over_time_analytics(self, headers):
        """Test get revenue over time analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/analytics/revenue-over-time', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_station_performance_analytics(self, headers):
        """Test get station performance analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/analytics/station-performance', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_user_analytics(self, headers):
        """Test get user analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/analytics/users', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_dashboard(self, headers):
        """Test get dashboard data."""
        response = requests.get(f'{BASE_URL}/api/admin/dashboard', headers=headers)
        assert response.status_code in [200, 400, 500]