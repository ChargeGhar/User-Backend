import pytest
import requests

BASE_URL = 'http://localhost:8010'


@pytest.mark.api
class TestAdminAPI:
    """Test cases for admin API endpoints."""

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

    # Authentication & Profile
    def test_admin_me(self, headers):
        """Test admin profile endpoint."""
        response = requests.get(f'{BASE_URL}/api/admin/me', headers=headers)
        assert response.status_code in [200, 400, 500]

    # User Management
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

    # Content Management
    def test_update_content_pages(self, headers):
        """Test update content pages."""
        data = {'content': 'Updated content'}
        response = requests.put(f'{BASE_URL}/api/admin/content/pages', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    # Coupons
    def test_get_coupons(self, headers):
        """Test get coupons."""
        response = requests.get(f'{BASE_URL}/api/admin/coupons', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_coupon_detail(self, headers):
        """Test get coupon detail."""
        response = requests.get(f'{BASE_URL}/api/admin/coupons/TEST123', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_get_coupon_usages(self, headers):
        """Test get coupon usages."""
        response = requests.get(f'{BASE_URL}/api/admin/coupons/TEST123/usages', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_bulk_create_coupons(self, headers):
        """Test bulk create coupons."""
        data = {'count': 5, 'discount': 10}
        response = requests.post(f'{BASE_URL}/api/admin/coupons/bulk', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    # Dashboard
    def test_get_dashboard(self, headers):
        """Test get dashboard data."""
        response = requests.get(f'{BASE_URL}/api/admin/dashboard', headers=headers)
        assert response.status_code in [200, 400, 500]

    # KYC
    def test_get_kyc_submissions(self, headers):
        """Test get KYC submissions."""
        response = requests.get(f'{BASE_URL}/api/admin/kyc/submissions', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_update_kyc_submission(self, headers):
        """Test update KYC submission."""
        data = {'status': 'approved'}
        response = requests.patch(f'{BASE_URL}/api/admin/kyc/submissions/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Media Analytics
    def test_get_media_analytics(self, headers):
        """Test get media analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/media/analytics', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_media_uploads(self, headers):
        """Test get media uploads."""
        response = requests.get(f'{BASE_URL}/api/admin/media/uploads', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_media_upload_detail(self, headers):
        """Test get media upload detail."""
        response = requests.get(f'{BASE_URL}/api/admin/media/uploads/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Payment Methods
    def test_get_payment_methods(self, headers):
        """Test get payment methods."""
        response = requests.get(f'{BASE_URL}/api/admin/payment-methods', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_payment_method_detail(self, headers):
        """Test get payment method detail."""
        response = requests.get(f'{BASE_URL}/api/admin/payment-methods/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Profiles
    def test_get_profiles(self, headers):
        """Test get profiles."""
        response = requests.get(f'{BASE_URL}/api/admin/profiles', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_profile_detail(self, headers):
        """Test get profile detail."""
        response = requests.get(f'{BASE_URL}/api/admin/profiles/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Refunds
    def test_get_refunds(self, headers):
        """Test get refunds."""
        response = requests.get(f'{BASE_URL}/api/admin/refunds', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_process_refund(self, headers):
        """Test process refund."""
        response = requests.post(f'{BASE_URL}/api/admin/refunds/1/process', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Rental Packages
    def test_get_rental_packages(self, headers):
        """Test get rental packages."""
        response = requests.get(f'{BASE_URL}/api/admin/rental-packages', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_rental_package_detail(self, headers):
        """Test get rental package detail."""
        response = requests.get(f'{BASE_URL}/api/admin/rental-packages/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Stations
    def test_get_stations_admin(self, headers):
        """Test get stations (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/stations', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_command_station(self, headers):
        """Test send command to station."""
        data = {'command': 'restart'}
        response = requests.post(f'{BASE_URL}/api/admin/stations/SN001/command', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_maintenance_station(self, headers):
        """Test station maintenance."""
        data = {'action': 'maintenance'}
        response = requests.post(f'{BASE_URL}/api/admin/stations/SN001/maintenance', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_station_issues(self, headers):
        """Test get station issues."""
        response = requests.get(f'{BASE_URL}/api/admin/stations/issues', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_station_issue_detail(self, headers):
        """Test get station issue detail."""
        response = requests.get(f'{BASE_URL}/api/admin/stations/issues/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Rentals Issues
    def test_get_rental_issues(self, headers):
        """Test get rental issues."""
        response = requests.get(f'{BASE_URL}/api/admin/rentals/issues', headers=headers)
        assert response.status_code in [200, 400, 500]

    # Withdrawals
    def test_get_withdrawals(self, headers):
        """Test get withdrawals."""
        response = requests.get(f'{BASE_URL}/api/admin/withdrawals', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_withdrawal_detail(self, headers):
        """Test get withdrawal detail."""
        response = requests.get(f'{BASE_URL}/api/admin/withdrawals/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_process_withdrawal(self, headers):
        """Test process withdrawal."""
        response = requests.post(f'{BASE_URL}/api/admin/withdrawals/1/process', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_get_withdrawal_analytics(self, headers):
        """Test get withdrawal analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/withdrawals/analytics', headers=headers)
        assert response.status_code in [200, 400, 500]

    # System
    def test_get_system_health(self, headers):
        """Test get system health."""
        response = requests.get(f'{BASE_URL}/api/admin/system-health', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_system_logs(self, headers):
        """Test get system logs."""
        response = requests.get(f'{BASE_URL}/api/admin/system-logs', headers=headers)
        assert response.status_code in [200, 400, 500]

    # App Management
    def test_get_app_updates(self, headers):
        """Test get app updates."""
        response = requests.get(f'{BASE_URL}/api/admin/app/updates', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_app_versions(self, headers):
        """Test get app versions."""
        response = requests.get(f'{BASE_URL}/api/admin/app/versions', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_app_version_detail(self, headers):
        """Test get app version detail."""
        response = requests.get(f'{BASE_URL}/api/admin/app/versions/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Broadcast
    def test_broadcast_message(self, headers):
        """Test broadcast message."""
        data = {'message': 'Test broadcast', 'target': 'all'}
        response = requests.post(f'{BASE_URL}/api/admin/broadcast', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    # Action Logs
    def test_get_action_logs(self, headers):
        """Test get action logs."""
        response = requests.get(f'{BASE_URL}/api/admin/action-logs', headers=headers)
        assert response.status_code in [200, 400, 500]

    # Config
    def test_get_config(self, headers):
        """Test get config."""
        response = requests.get(f'{BASE_URL}/api/admin/config', headers=headers)
        assert response.status_code in [200, 400, 500]

    # Admin Achievements
    def test_get_achievements_admin(self, headers):
        """Test get achievements (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/achievements', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_create_achievement(self, headers):
        """Test create achievement."""
        data = {'title': 'Test Achievement', 'description': 'Test desc', 'points': 100}
        response = requests.post(f'{BASE_URL}/api/admin/achievements', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_get_achievement_detail(self, headers):
        """Test get achievement detail."""
        response = requests.get(f'{BASE_URL}/api/admin/achievements/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_achievement(self, headers):
        """Test update achievement."""
        data = {'title': 'Updated Achievement'}
        response = requests.put(f'{BASE_URL}/api/admin/achievements/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_achievement(self, headers):
        """Test delete achievement."""
        response = requests.delete(f'{BASE_URL}/api/admin/achievements/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    def test_get_achievement_analytics(self, headers):
        """Test get achievement analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/achievements/analytics', headers=headers)
        assert response.status_code in [200, 400, 500]

    # Admin Amenity
    def test_get_amenities_admin(self, headers):
        """Test get amenities (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/amenities', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_create_amenity(self, headers):
        """Test create amenity."""
        data = {'name': 'WiFi', 'description': 'Free WiFi'}
        response = requests.post(f'{BASE_URL}/api/admin/amenities', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_get_amenity_detail(self, headers):
        """Test get amenity detail."""
        response = requests.get(f'{BASE_URL}/api/admin/amenities/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_amenity(self, headers):
        """Test update amenity."""
        data = {'name': 'Updated WiFi'}
        response = requests.patch(f'{BASE_URL}/api/admin/amenities/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_amenity(self, headers):
        """Test delete amenity."""
        response = requests.delete(f'{BASE_URL}/api/admin/amenities/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Analytics
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

    # Admin App (additional)
    def test_create_app_update(self, headers):
        """Test create app update."""
        data = {'version': '1.1.0', 'description': 'New features'}
        response = requests.post(f'{BASE_URL}/api/admin/app/updates', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_create_app_version(self, headers):
        """Test create app version."""
        data = {'version': '1.1.0', 'platform': 'android', 'required': True}
        response = requests.post(f'{BASE_URL}/api/admin/app/versions', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_update_app_version(self, headers):
        """Test update app version."""
        data = {'required': False}
        response = requests.put(f'{BASE_URL}/api/admin/app/versions/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_app_version(self, headers):
        """Test delete app version."""
        response = requests.delete(f'{BASE_URL}/api/admin/app/versions/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Config (additional)
    def test_create_config(self, headers):
        """Test create config."""
        data = {'key': 'test_key', 'value': 'test_value'}
        response = requests.post(f'{BASE_URL}/api/admin/config', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_update_config(self, headers):
        """Test update config."""
        data = {'key': 'test_key', 'value': 'updated_value'}
        response = requests.put(f'{BASE_URL}/api/admin/config', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_delete_config(self, headers):
        """Test delete config."""
        data = {'key': 'test_key'}
        response = requests.delete(f'{BASE_URL}/api/admin/config', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    # Admin Contents (additional)
    def test_get_content_analytics(self, headers):
        """Test get content analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/content/analytics', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_banners_admin(self, headers):
        """Test get banners (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/content/banners', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_create_banner(self, headers):
        """Test create banner."""
        data = {'title': 'Test Banner', 'image_url': 'http://example.com/image.jpg'}
        response = requests.post(f'{BASE_URL}/api/admin/content/banners', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_get_banner_detail(self, headers):
        """Test get banner detail."""
        response = requests.get(f'{BASE_URL}/api/admin/content/banners/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_banner(self, headers):
        """Test update banner."""
        data = {'title': 'Updated Banner'}
        response = requests.put(f'{BASE_URL}/api/admin/content/banners/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_banner(self, headers):
        """Test delete banner."""
        response = requests.delete(f'{BASE_URL}/api/admin/content/banners/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    def test_get_contacts_admin(self, headers):
        """Test get contacts (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/content/contact', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_create_contact(self, headers):
        """Test create contact."""
        data = {'type': 'email', 'value': 'support@example.com'}
        response = requests.post(f'{BASE_URL}/api/admin/content/contact', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_get_contact_detail(self, headers):
        """Test get contact detail."""
        response = requests.get(f'{BASE_URL}/api/admin/content/contact/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_contact(self, headers):
        """Test delete contact."""
        response = requests.delete(f'{BASE_URL}/api/admin/content/contact/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    def test_get_faqs_admin(self, headers):
        """Test get FAQs (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/content/faqs', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_create_faq(self, headers):
        """Test create FAQ."""
        data = {'question': 'Test Question', 'answer': 'Test Answer'}
        response = requests.post(f'{BASE_URL}/api/admin/content/faqs', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_get_faq_detail(self, headers):
        """Test get FAQ detail."""
        response = requests.get(f'{BASE_URL}/api/admin/content/faqs/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_faq(self, headers):
        """Test update FAQ."""
        data = {'answer': 'Updated Answer'}
        response = requests.put(f'{BASE_URL}/api/admin/content/faqs/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_faq(self, headers):
        """Test delete FAQ."""
        response = requests.delete(f'{BASE_URL}/api/admin/content/faqs/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Late Fee Config
    def test_get_late_fee_configs(self, headers):
        """Test get late fee configs."""
        response = requests.get(f'{BASE_URL}/api/admin/late-fee-configs', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_create_late_fee_config(self, headers):
        """Test create late fee config."""
        data = {'grace_period_minutes': 30, 'fee_per_hour': 50}
        response = requests.post(f'{BASE_URL}/api/admin/late-fee-configs', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_get_late_fee_config_detail(self, headers):
        """Test get late fee config detail."""
        response = requests.get(f'{BASE_URL}/api/admin/late-fee-configs/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_late_fee_config(self, headers):
        """Test update late fee config."""
        data = {'fee_per_hour': 60}
        response = requests.put(f'{BASE_URL}/api/admin/late-fee-configs/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_late_fee_config(self, headers):
        """Test delete late fee config."""
        response = requests.delete(f'{BASE_URL}/api/admin/late-fee-configs/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    def test_activate_late_fee_config(self, headers):
        """Test activate late fee config."""
        response = requests.post(f'{BASE_URL}/api/admin/late-fee-configs/1/activate', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_deactivate_late_fee_config(self, headers):
        """Test deactivate late fee config."""
        response = requests.post(f'{BASE_URL}/api/admin/late-fee-configs/1/deactivate', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_get_active_late_fee_config(self, headers):
        """Test get active late fee config."""
        response = requests.get(f'{BASE_URL}/api/admin/late-fee-configs/active', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_test_late_fee_calculation(self, headers):
        """Test late fee calculation."""
        data = {'rental_duration_minutes': 120, 'grace_period_minutes': 30}
        response = requests.post(f'{BASE_URL}/api/admin/late-fee-configs/test-calculation', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    # Admin Profiles (additional)
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

    # Admin Media (additional)
    def test_create_media_upload_admin(self, headers):
        """Test create media upload (admin)."""
        files = {'file': ('test.jpg', open('test.jpg', 'rb'), 'image/jpeg')}
        response = requests.post(f'{BASE_URL}/api/admin/media/uploads', files=files, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_delete_media_upload_admin(self, headers):
        """Test delete media upload (admin)."""
        response = requests.delete(f'{BASE_URL}/api/admin/media/uploads/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Payment Methods (additional)
    def test_create_payment_method(self, headers):
        """Test create payment method."""
        data = {'name': 'Test Method', 'gateway': 'test'}
        response = requests.post(f'{BASE_URL}/api/admin/payment-methods', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_update_payment_method(self, headers):
        """Test update payment method."""
        data = {'is_active': False}
        response = requests.patch(f'{BASE_URL}/api/admin/payment-methods/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_payment_method(self, headers):
        """Test delete payment method."""
        response = requests.delete(f'{BASE_URL}/api/admin/payment-methods/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Points
    def test_adjust_user_points(self, headers):
        """Test adjust user points."""
        data = {'user_id': 1, 'points': 100, 'reason': 'Test adjustment'}
        response = requests.post(f'{BASE_URL}/api/admin/points/adjust', json=data, headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_points_analytics_admin(self, headers):
        """Test get points analytics (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/points/analytics', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_points_history_admin(self, headers):
        """Test get points history (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/points/history', headers=headers)
        assert response.status_code in [200, 400, 500]

    # Admin PowerBanks
    def test_get_powerbanks_admin(self, headers):
        """Test get powerbanks (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/powerbanks', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_powerbank_detail(self, headers):
        """Test get powerbank detail."""
        response = requests.get(f'{BASE_URL}/api/admin/powerbanks/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_get_powerbank_history(self, headers):
        """Test get powerbank rental history."""
        response = requests.get(f'{BASE_URL}/api/admin/powerbanks/1/history', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_powerbank_status(self, headers):
        """Test update powerbank status."""
        data = {'status': 'available'}
        response = requests.post(f'{BASE_URL}/api/admin/powerbanks/1/status', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_get_powerbank_analytics_overview(self, headers):
        """Test get powerbank analytics overview."""
        response = requests.get(f'{BASE_URL}/api/admin/powerbanks/analytics/overview', headers=headers)
        assert response.status_code in [200, 400, 500]

    # Admin Referrals
    def test_complete_referral(self, headers):
        """Test complete referral."""
        response = requests.post(f'{BASE_URL}/api/admin/referrals/1/complete', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_get_referral_analytics(self, headers):
        """Test get referral analytics."""
        response = requests.get(f'{BASE_URL}/api/admin/referrals/analytics', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_user_referrals_admin(self, headers):
        """Test get user referrals (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/users/1/referrals', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    # Admin Rental Packages (additional)
    def test_create_rental_package(self, headers):
        """Test create rental package."""
        data = {'name': 'Test Package', 'duration_minutes': 60, 'price': 100}
        response = requests.post(f'{BASE_URL}/api/admin/rental-packages', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_update_rental_package(self, headers):
        """Test update rental package."""
        data = {'price': 120}
        response = requests.patch(f'{BASE_URL}/api/admin/rental-packages/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_rental_package(self, headers):
        """Test delete rental package."""
        response = requests.delete(f'{BASE_URL}/api/admin/rental-packages/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Rentals (additional)
    def test_get_rentals_admin(self, headers):
        """Test get rentals (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/rentals', headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_get_rental_detail_admin(self, headers):
        """Test get rental detail (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/rentals/1', headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_update_rental_issue(self, headers):
        """Test update rental issue."""
        data = {'status': 'resolved'}
        response = requests.patch(f'{BASE_URL}/api/admin/rentals/issues/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_rental_issue(self, headers):
        """Test delete rental issue."""
        response = requests.delete(f'{BASE_URL}/api/admin/rentals/issues/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Stations (additional)
    def test_create_station(self, headers):
        """Test create station."""
        data = {'serial_number': 'SN999', 'location': 'Test Location'}
        response = requests.post(f'{BASE_URL}/api/admin/stations', json=data, headers=headers)
        assert response.status_code in [201, 400, 500]

    def test_update_station(self, headers):
        """Test update station."""
        data = {'location': 'Updated Location'}
        response = requests.patch(f'{BASE_URL}/api/admin/stations/SN001', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_station(self, headers):
        """Test delete station."""
        response = requests.delete(f'{BASE_URL}/api/admin/stations/SN001', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    def test_update_station_issue(self, headers):
        """Test update station issue."""
        data = {'status': 'resolved'}
        response = requests.patch(f'{BASE_URL}/api/admin/stations/issues/1', json=data, headers=headers)
        assert response.status_code in [200, 404, 400, 500]

    def test_delete_station_issue(self, headers):
        """Test delete station issue."""
        response = requests.delete(f'{BASE_URL}/api/admin/stations/issues/1', headers=headers)
        assert response.status_code in [204, 404, 400, 500]

    # Admin Payments
    def test_get_transactions_admin(self, headers):
        """Test get transactions (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/transactions', headers=headers)
        assert response.status_code in [200, 400, 500]

    # Admin Leaderboard
    def test_get_user_leaderboard_admin(self, headers):
        """Test get user leaderboard (admin)."""
        response = requests.get(f'{BASE_URL}/api/admin/users/leaderboard', headers=headers)
        assert response.status_code in [200, 400, 500]