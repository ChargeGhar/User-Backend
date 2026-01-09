"""
Tests for IoT system integration
"""
from __future__ import annotations

import json
import time
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.conf import settings

from api.user.stations.services.utils.sign_chargeghar_main import SignChargeGharMain
from api.user.stations.models import Station, StationSlot, PowerBank

User = get_user_model()


class SignatureTestCase(TestCase):
    """Test signature generation and validation"""
    
    def setUp(self):
        self.secret_key = "test-secret-key-for-testing-only"
        self.sign_util = SignChargeGharMain(secret_key=self.secret_key)
    
    def test_signature_generation(self):
        """Test that signature generation is consistent"""
        payload = '{"test":"data"}'
        timestamp = 1698345600
        
        sig1 = self.sign_util.generate_signature(payload, timestamp)
        sig2 = self.sign_util.generate_signature(payload, timestamp)
        
        self.assertEqual(sig1, sig2)
        self.assertIsInstance(sig1, str)
        self.assertGreater(len(sig1), 0)
    
    def test_signature_validation_success(self):
        """Test that valid signature passes validation"""
        payload = '{"test":"data"}'
        timestamp = int(self.sign_util.get_current_timestamp())
        
        signature = self.sign_util.generate_signature(payload, timestamp)
        is_valid, error = self.sign_util.validate_signature(
            payload, timestamp, signature, time_tolerance=10
        )
        
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    def test_signature_validation_invalid_signature(self):
        """Test that invalid signature fails validation"""
        payload = '{"test":"data"}'
        timestamp = int(self.sign_util.get_current_timestamp())
        
        is_valid, error = self.sign_util.validate_signature(
            payload, timestamp, "invalid-signature", time_tolerance=10
        )
        
        self.assertFalse(is_valid)
        self.assertIn("mismatch", error.lower())
    
    def test_signature_validation_expired_timestamp(self):
        """Test that old timestamp fails validation"""
        payload = '{"test":"data"}'
        timestamp = 1609459200  # Jan 1, 2021 (very old)
        
        signature = self.sign_util.generate_signature(payload, timestamp)
        is_valid, error = self.sign_util.validate_signature(
            payload, timestamp, signature, time_tolerance=300
        )
        
        self.assertFalse(is_valid)
        self.assertIn("too old", error.lower())


class StationSyncAPITestCase(TestCase):
    """Test station synchronization API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.admin_user)
        
        # Setup signature utility
        self.secret_key = "test-secret-key-for-testing-only"
        self.sign_util = SignChargeGharMain(secret_key=self.secret_key)
    
    def _create_signed_request(self, payload_data):
        """Helper to create properly signed request"""
        payload = json.dumps(payload_data)
        timestamp = int(time.time())
        signature = self.sign_util.generate_signature(payload, timestamp)
        
        return {
            'data': payload_data,
            'headers': {
                'HTTP_X_SIGNATURE': signature,
                'HTTP_X_TIMESTAMP': str(timestamp),
                'CONTENT_TYPE': 'application/json'
            }
        }
    
    def test_full_station_sync_without_signature(self):
        """Test that request without signature is rejected"""
        payload = {
            "type": "full",
            "timestamp": int(time.time()),
            "device": {
                "serial_number": "TEST12345",
                "status": "ONLINE"
            },
            "station": {
                "total_slots": 2
            },
            "slots": [],
            "power_banks": []
        }
        
        response = self.client.post(
            '/api/internal/stations/data',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertIn('signature', response.json()['error']['message'].lower())
    
    def test_full_station_sync_with_valid_signature(self):
        """Test full station synchronization with valid signature"""
        # Mock the signature validation by temporarily overriding settings
        with self.settings(IOT_SYSTEM_SIGNATURE_SECRET=self.secret_key):
            payload_data = {
                "type": "full",
                "timestamp": int(time.time()),
                "device": {
                    "serial_number": "TEST12345",
                    "imei": "TEST12345",
                    "status": "ONLINE",
                    "last_heartbeat": "2025-10-27T14:30:00Z",
                    "hardware_info": {
                        "firmware_version": "2.1.5"
                    }
                },
                "station": {
                    "total_slots": 2
                },
                "slots": [
                    {
                        "slot_number": 1,
                        "status": "AVAILABLE",
                        "battery_level": 0,
                        "slot_metadata": {}
                    },
                    {
                        "slot_number": 2,
                        "status": "OCCUPIED",
                        "battery_level": 85,
                        "power_bank_serial": "PB12345",
                        "slot_metadata": {}
                    }
                ],
                "power_banks": [
                    {
                        "serial_number": "PB12345",
                        "status": "AVAILABLE",
                        "battery_level": 85,
                        "current_slot": 2,
                        "hardware_info": {
                            "temperature": 30,
                            "voltage": 5000
                        }
                    }
                ]
            }
            
            request_data = self._create_signed_request(payload_data)
            
            response = self.client.post(
                '/api/internal/stations/data',
                data=json.dumps(request_data['data']),
                content_type='application/json',
                **request_data['headers']
            )
            
            self.assertEqual(response.status_code, 200)
            response_data = response.json()
            self.assertTrue(response_data['success'])
            
            # Verify database records
            station = Station.objects.get(serial_number="TEST12345")
            self.assertEqual(station.status, 'ONLINE')
            self.assertEqual(station.total_slots, 2)
            
            slots = StationSlot.objects.filter(station=station)
            self.assertEqual(slots.count(), 2)
            
            powerbanks = PowerBank.objects.filter(serial_number="PB12345")
            self.assertEqual(powerbanks.count(), 1)
            self.assertEqual(powerbanks.first().battery_level, 85)