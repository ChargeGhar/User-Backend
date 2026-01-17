"""
Biometric Authentication Tests
==============================
Tests for biometric authentication functionality
"""
import pytest
from django.utils import timezone
from api.user.auth.models import User, UserDevice
from api.user.auth.services.biometric_auth_service import BiometricAuthService
from api.common.services.base import ServiceException


@pytest.fixture
def biometric_service():
    """Biometric service fixture"""
    return BiometricAuthService()


@pytest.fixture
def test_user(db):
    """Create test user"""
    return User.objects.create(
        email="biometric@test.com",
        username="biotest",
        status='ACTIVE',
        is_active=True
    )


@pytest.fixture
def test_device(test_user):
    """Create test device"""
    return UserDevice.objects.create(
        user=test_user,
        device_id="test_device_123",
        fcm_token="test_fcm_token",
        device_type="ANDROID",
        is_active=True
    )


class TestBiometricEnable:
    """Tests for enabling biometric"""
    
    def test_enable_biometric_success(self, biometric_service, test_user, test_device):
        """Test successful biometric enablement"""
        result = biometric_service.enable_biometric(
            user=test_user,
            device_id=test_device.device_id,
            biometric_token="secure_token_256bit_minimum_length_required"
        )
        
        assert result['message'] == 'Biometric authentication enabled successfully'
        assert result['device_id'] == test_device.device_id
        assert 'enabled_at' in result
        
        # Verify device updated
        test_device.refresh_from_db()
        assert test_device.biometric_enabled is True
        assert test_device.biometric_token is not None
        assert test_device.biometric_registered_at is not None
    
    def test_enable_biometric_invalid_device(self, biometric_service, test_user):
        """Test enable with invalid device_id"""
        with pytest.raises(ServiceException) as exc:
            biometric_service.enable_biometric(
                user=test_user,
                device_id="invalid_device",
                biometric_token="secure_token_256bit_minimum"
            )
        assert exc.value.default_code == "device_not_found"
    
    def test_enable_biometric_duplicate_token(self, biometric_service, test_user, test_device):
        """Test enable with duplicate token"""
        # Enable first time
        token = "unique_token_256bit_minimum_length_required_for_security"
        biometric_service.enable_biometric(
            user=test_user,
            device_id=test_device.device_id,
            biometric_token=token
        )
        
        # Create another device
        device2 = UserDevice.objects.create(
            user=test_user,
            device_id="test_device_456",
            fcm_token="test_fcm_token_2",
            device_type="IOS",
            is_active=True
        )
        
        # Try to use same token
        with pytest.raises(ServiceException) as exc:
            biometric_service.enable_biometric(
                user=test_user,
                device_id=device2.device_id,
                biometric_token=token
            )
        assert exc.value.default_code == "invalid_token"


class TestBiometricLogin:
    """Tests for biometric login"""
    
    def test_biometric_login_success(self, biometric_service, test_user, test_device):
        """Test successful biometric login"""
        # Enable biometric first
        token = "login_test_token_256bit_minimum_length_required_for_security_purposes"
        biometric_service.enable_biometric(
            user=test_user,
            device_id=test_device.device_id,
            biometric_token=token
        )
        
        # Login
        result = biometric_service.biometric_login(
            device_id=test_device.device_id,
            biometric_token=token
        )
        
        assert result['message'] == 'Biometric login successful'
        assert result['user']['id'] == str(test_user.id)
        assert result['user']['username'] == test_user.username
        assert 'access' in result['tokens']
        assert 'refresh' in result['tokens']
        
        # Verify timestamps updated
        test_device.refresh_from_db()
        assert test_device.biometric_last_used_at is not None
    
    def test_biometric_login_invalid_token(self, biometric_service, test_device):
        """Test login with invalid token"""
        with pytest.raises(ServiceException) as exc:
            biometric_service.biometric_login(
                device_id=test_device.device_id,
                biometric_token="wrong_token"
            )
        assert exc.value.default_code == "invalid_biometric_credentials"
    
    def test_biometric_login_inactive_user(self, biometric_service, test_user, test_device):
        """Test login with inactive user"""
        # Enable biometric
        token = "inactive_test_token_256bit_minimum_length_required"
        biometric_service.enable_biometric(
            user=test_user,
            device_id=test_device.device_id,
            biometric_token=token
        )
        
        # Deactivate user
        test_user.is_active = False
        test_user.save()
        
        # Try login
        with pytest.raises(ServiceException) as exc:
            biometric_service.biometric_login(
                device_id=test_device.device_id,
                biometric_token=token
            )
        assert exc.value.default_code == "account_inactive"


class TestBiometricDisable:
    """Tests for disabling biometric"""
    
    def test_disable_biometric_success(self, biometric_service, test_user, test_device):
        """Test successful biometric disable"""
        # Enable first
        token = "disable_test_token_256bit_minimum_length_required"
        biometric_service.enable_biometric(
            user=test_user,
            device_id=test_device.device_id,
            biometric_token=token
        )
        
        # Disable
        result = biometric_service.disable_biometric(
            user=test_user,
            device_id=test_device.device_id
        )
        
        assert result['message'] == 'Biometric authentication disabled successfully'
        assert result['device_id'] == test_device.device_id
        
        # Verify device updated
        test_device.refresh_from_db()
        assert test_device.biometric_enabled is False
        assert test_device.biometric_token is None
    
    def test_disable_biometric_invalid_device(self, biometric_service, test_user):
        """Test disable with invalid device"""
        with pytest.raises(ServiceException) as exc:
            biometric_service.disable_biometric(
                user=test_user,
                device_id="invalid_device"
            )
        assert exc.value.default_code == "device_not_found"


class TestBiometricStatus:
    """Tests for biometric status"""
    
    def test_status_enabled(self, biometric_service, test_user, test_device):
        """Test status when biometric is enabled"""
        # Enable biometric
        token = "status_test_token_256bit_minimum_length_required"
        biometric_service.enable_biometric(
            user=test_user,
            device_id=test_device.device_id,
            biometric_token=token
        )
        
        # Check status
        result = biometric_service.get_biometric_status(
            user=test_user,
            device_id=test_device.device_id
        )
        
        assert result['enabled'] is True
        assert result['device_id'] == test_device.device_id
        assert result['registered_at'] is not None
    
    def test_status_disabled(self, biometric_service, test_user, test_device):
        """Test status when biometric is disabled"""
        result = biometric_service.get_biometric_status(
            user=test_user,
            device_id=test_device.device_id
        )
        
        assert result['enabled'] is False
        assert result['device_id'] == test_device.device_id
    
    def test_status_device_not_found(self, biometric_service, test_user):
        """Test status for non-existent device"""
        result = biometric_service.get_biometric_status(
            user=test_user,
            device_id="nonexistent_device"
        )
        
        assert result['enabled'] is False
        assert result['message'] == 'Device not found'
