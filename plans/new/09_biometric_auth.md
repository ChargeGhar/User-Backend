# Feature: Biometric Authentication

**App**: `api/user/auth/`  
**Priority**: Phase 2

---

## Tables

### 9.1 UserDevice Model Updates

| Field | Type | Description | Action |
|-------|------|-------------|--------|
| `biometric_enabled` | BooleanField | Whether biometric is enabled | ADD, default=False |
| `biometric_token` | CharField(512) | Biometric credential token | ADD, NULL, UNIQUE |
| `biometric_registered_at` | DateTimeField | When biometric was registered | ADD, NULL |
| `biometric_last_used_at` | DateTimeField | Last biometric login | ADD, NULL |

---

## Business Logic Notes

### Industry Standard Approach

For mobile biometric authentication, we use a **device-bound token** approach:

1. **Registration** (Enable):
   - User authenticates normally (OTP)
   - App generates a unique token after successful biometric verification
   - Token is stored on device (Keychain/Keystore) and sent to server
   - Server stores token linked to device

2. **Login**:
   - App verifies biometric locally
   - On success, app retrieves stored token
   - App sends token to server
   - Server validates token and issues JWT

### Enable Flow (`POST /api/auth/biometric/enable`)

```python
# Request
{
    "device_id": "abc123",
    "biometric_token": "generated_unique_token_from_app"
}

# Response
{
    "success": true,
    "message": "Biometric authentication enabled"
}
```

**Server Logic**:
```python
def enable_biometric(user, device_id, biometric_token):
    device = UserDevice.objects.get(user=user, device_id=device_id)
    
    # Ensure token is unique
    if UserDevice.objects.filter(biometric_token=biometric_token).exists():
        raise ValidationError("Invalid biometric token")
    
    device.biometric_enabled = True
    device.biometric_token = biometric_token
    device.biometric_registered_at = timezone.now()
    device.save()
    
    return {"success": True}
```

### Login Flow (`POST /api/auth/biometric/login`)

```python
# Request
{
    "device_id": "abc123",
    "biometric_token": "stored_token_from_device"
}

# Response
{
    "success": true,
    "access_token": "jwt_access_token",
    "refresh_token": "jwt_refresh_token",
    "user": {...}
}
```

**Server Logic**:
```python
def biometric_login(device_id, biometric_token):
    try:
        device = UserDevice.objects.get(
            device_id=device_id,
            biometric_enabled=True,
            biometric_token=biometric_token,
            is_active=True
        )
    except UserDevice.DoesNotExist:
        raise AuthenticationError("Invalid biometric credentials")
    
    user = device.user
    
    # Check user status
    if user.status != 'ACTIVE':
        raise AuthenticationError("Account is not active")
    
    # Update last used
    device.biometric_last_used_at = timezone.now()
    device.last_used = timezone.now()
    device.save()
    
    # Generate tokens
    tokens = generate_jwt_tokens(user)
    
    return {
        "success": True,
        "access_token": tokens['access'],
        "refresh_token": tokens['refresh'],
        "user": UserSerializer(user).data
    }
```

### Disable Flow (`POST /api/auth/biometric/disable`)

```python
def disable_biometric(user, device_id):
    device = UserDevice.objects.get(user=user, device_id=device_id)
    
    device.biometric_enabled = False
    device.biometric_token = None
    device.save()
    
    return {"success": True}
```

---

## Security Considerations

1. **Token Generation**:
   - App generates cryptographically secure random token
   - Token should be 256+ bits (32+ bytes, base64 encoded)
   - Token stored in secure enclave (iOS Keychain / Android Keystore)

2. **Token Uniqueness**:
   - Server enforces unique constraint on biometric_token
   - Prevents token reuse across devices

3. **Device Binding**:
   - Token is bound to specific device_id
   - Both must match for successful login

4. **Revocation**:
   - User can disable biometric anytime
   - Admin can deactivate device (is_active=False)

---

## Migration Notes

```python
# Migration: Add biometric fields to UserDevice
operations = [
    migrations.AddField(
        model_name='userdevice',
        name='biometric_enabled',
        field=models.BooleanField(default=False),
    ),
    migrations.AddField(
        model_name='userdevice',
        name='biometric_token',
        field=models.CharField(max_length=512, null=True, blank=True, unique=True),
    ),
    migrations.AddField(
        model_name='userdevice',
        name='biometric_registered_at',
        field=models.DateTimeField(null=True, blank=True),
    ),
    migrations.AddField(
        model_name='userdevice',
        name='biometric_last_used_at',
        field=models.DateTimeField(null=True, blank=True),
    ),
]
```

---

## Related Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/biometric/enable` | Enable biometric for device |
| POST | `/api/auth/biometric/login` | Login with biometric |
| POST | `/api/auth/biometric/disable` | Disable biometric for device |
| GET | `/api/auth/biometric/status` | Check biometric status |
