"""
Tests for internal IoT action endpoints.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from api.partners.common.models import Partner, PartnerIotHistory, StationDistribution
from api.user.stations.models import Station

User = get_user_model()


class FakeDeviceAPIService:
    """Simple fake device service for deterministic endpoint tests."""

    def __init__(self):
        self.reboot_called_with = None
        self.check_all_called_with = None
        self.check_called_with = None
        self.popup_specific_called_with = None
        self.popup_random_called_with = None
        self.wifi_connect_called_with = None

    def reboot_station(self, station_sn):
        self.reboot_called_with = station_sn
        return True, {'code': 200, 'msg': 'ok', 'data': None, 'time': 0}, 'ok'

    def check_station_all(self, station_sn):
        self.check_all_called_with = station_sn
        return True, [], 'OK'

    def check_station(self, station_sn):
        self.check_called_with = station_sn
        return True, [], 'OK'

    def wifi_scan(self, station_sn):
        return True, ['TestWiFi'], 'ok'

    def wifi_connect(self, station_sn, ssid, password):
        self.wifi_connect_called_with = (station_sn, ssid, password)
        return True, {'code': 200, 'msg': 'ok', 'data': None, 'time': 0}, 'ok'

    def set_volume(self, station_sn, volume):
        return True, {'code': 200, 'msg': 'ok', 'data': None, 'time': 0}, 'ok'

    def set_mode(self, station_sn, mode):
        return True, {'code': 200, 'msg': 'ok', 'data': None, 'time': 0}, 'ok'

    def popup_random(self, station_sn, min_power=20):
        self.popup_random_called_with = (station_sn, min_power)
        return True, 'PB-RANDOM-001', 'ok'

    def popup_specific(self, station_sn, powerbank_sn):
        self.popup_specific_called_with = (station_sn, powerbank_sn)

        class PopupResult:
            slot = 1
            status = 1
            success = True

            def __init__(self, serial_number):
                self.powerbank_sn = serial_number

        return True, PopupResult(powerbank_sn), 'ok'


class InternalIoTActionsTestCase(TestCase):
    """Endpoint-level tests for /api/internal/iot/* actions."""

    def setUp(self):
        self.client = APIClient()
        self.fake_device_service = FakeDeviceAPIService()

        self.franchise_user = User.objects.create(
            email='franchise@test.com',
            username='franchise',
            is_active=True,
            is_partner=True,
        )
        self.vendor_user = User.objects.create(
            email='vendor@test.com',
            username='vendor',
            is_active=True,
            is_partner=True,
        )
        self.admin_user = User.objects.create(
            email='admin@test.com',
            username='admin',
            is_active=True,
            is_staff=True,
            is_partner=False,
        )

        self.franchise_partner = Partner.objects.create(
            user=self.franchise_user,
            partner_type=Partner.PartnerType.FRANCHISE,
            vendor_type=None,
            code='FR-TEST-001',
            business_name='Franchise Test',
            contact_phone='9800000001',
            status=Partner.Status.ACTIVE,
        )
        self.vendor_partner = Partner.objects.create(
            user=self.vendor_user,
            partner_type=Partner.PartnerType.VENDOR,
            vendor_type=Partner.VendorType.REVENUE,
            parent=self.franchise_partner,
            code='VN-TEST-001',
            business_name='Vendor Test',
            contact_phone='9800000002',
            status=Partner.Status.ACTIVE,
        )

        self.station = Station.objects.create(
            station_name='Internal IoT Station',
            serial_number='ADMIN-CONFIGURED-SN-001',
            imei='868522071408102',
            latitude=Decimal('27.700000000000000'),
            longitude=Decimal('85.300000000000000'),
            address='Kathmandu',
            total_slots=8,
            status='ONLINE',
            hardware_info={},
        )
        self.other_station = Station.objects.create(
            station_name='Other Station',
            serial_number='ADMIN-CONFIGURED-SN-002',
            imei='868522071408103',
            latitude=Decimal('27.700000000000000'),
            longitude=Decimal('85.300000000000000'),
            address='Pokhara',
            total_slots=8,
            status='ONLINE',
            hardware_info={},
        )

        StationDistribution.objects.create(
            station=self.station,
            partner=self.franchise_partner,
            distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE,
            assigned_by=None,
        )
        StationDistribution.objects.create(
            station=self.station,
            partner=self.vendor_partner,
            distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR,
            assigned_by=None,
        )

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_reboot_uses_station_imei_and_logs_history(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.franchise_user)

        response = self.client.post(
            '/api/internal/iot/reboot',
            {'station_id': str(self.station.id)},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(self.fake_device_service.reboot_called_with, self.station.imei)

        history = PartnerIotHistory.objects.get(action_type='REBOOT')
        self.assertEqual(history.station_id, self.station.id)
        self.assertTrue(history.is_successful)

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_vendor_cannot_use_eject_endpoint(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.vendor_user)

        response = self.client.post(
            '/api/internal/iot/eject',
            {'station_id': str(self.station.id)},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(PartnerIotHistory.objects.filter(action_type='EJECT').exists())

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_check_defaults_to_check_all(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.franchise_user)

        response = self.client.post(
            '/api/internal/iot/check',
            {'station_id': str(self.station.id)},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fake_device_service.check_all_called_with, self.station.imei)
        self.assertIsNone(self.fake_device_service.check_called_with)

        history = PartnerIotHistory.objects.filter(action_type='CHECK').latest('created_at')
        self.assertTrue(history.request_payload.get('check_all'))

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_check_uses_partial_when_checkall_false(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.franchise_user)

        response = self.client.post(
            '/api/internal/iot/check',
            {
                'station_id': str(self.station.id),
                'checkAll': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fake_device_service.check_called_with, self.station.imei)
        self.assertIsNone(self.fake_device_service.check_all_called_with)

        history = PartnerIotHistory.objects.filter(action_type='CHECK').latest('created_at')
        self.assertFalse(history.request_payload.get('check_all'))

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_admin_staff_can_check_station(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.admin_user)

        response = self.client.post(
            '/api/internal/iot/check',
            {'station_id': str(self.station.id)},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(self.fake_device_service.check_all_called_with, self.station.imei)

        history = PartnerIotHistory.objects.filter(action_type='CHECK').latest('created_at')
        self.assertEqual(history.performed_from, PartnerIotHistory.PerformedFrom.ADMIN_PANEL)

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_station_access_denied_returns_403(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.vendor_user)

        response = self.client.post(
            '/api/internal/iot/check',
            {'station_id': str(self.other_station.id)},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_franchise_eject_without_powerbank_sn_uses_random_popup(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.franchise_user)

        response = self.client.post(
            '/api/internal/iot/eject',
            {'station_id': str(self.station.id), 'reason': 'random'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fake_device_service.popup_random_called_with[0], self.station.imei)
        self.assertIsNone(self.fake_device_service.popup_specific_called_with)

        payload = response.json()['data']
        self.assertTrue(payload['random_popup'])
        self.assertEqual(payload['powerbank_serial'], 'PB-RANDOM-001')

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_franchise_eject_with_powerbank_sn_uses_specific_popup(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.franchise_user)

        response = self.client.post(
            '/api/internal/iot/eject',
            {
                'station_id': str(self.station.id),
                'powerbank_sn': 'PB-SPEC-001',
                'reason': 'specific',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_device_service.popup_specific_called_with,
            (self.station.imei, 'PB-SPEC-001')
        )
        self.assertIsNone(self.fake_device_service.popup_random_called_with)

        payload = response.json()['data']
        self.assertFalse(payload['random_popup'])
        self.assertEqual(payload['powerbank_serial'], 'PB-SPEC-001')
        self.assertEqual(payload['slot_number'], 1)

    @patch('api.internal.services.iot_action_service.get_device_api_service')
    def test_wifi_connect_masks_password_in_history_payload(self, mocked_device_service):
        mocked_device_service.return_value = self.fake_device_service
        self.client.force_authenticate(self.franchise_user)

        response = self.client.post(
            '/api/internal/iot/wifi/connect',
            {
                'station_id': str(self.station.id),
                'wifi_ssid': 'Office-WiFi',
                'wifi_password': 'SuperSecretPassword',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        history = PartnerIotHistory.objects.filter(action_type='WIFI_CONNECT').latest('created_at')
        self.assertEqual(history.request_payload['wifi_ssid'], 'Office-WiFi')
        self.assertEqual(history.request_payload['wifi_password'], '***')
