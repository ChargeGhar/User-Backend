# Flutter Biometric Integration - Implementation Guide

**Backend**: ChargeGhar API  
**Feature**: Biometric Authentication (Fingerprint/Face ID)

---

## Setup

### pubspec.yaml
```yaml
dependencies:
  local_auth: ^2.1.7
  flutter_secure_storage: ^9.0.0
  http: ^1.1.0
```

### Platform Config

**iOS (Info.plist)**:
```xml
<key>NSFaceIDUsageDescription</key>
<string>Login with Face ID</string>
```

**Android (AndroidManifest.xml)**:
```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
```

---

## BiometricService Implementation

```dart
// lib/services/biometric_service.dart
import 'package:local_auth/local_auth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:math';

class BiometricService {
  final LocalAuthentication _auth = LocalAuthentication();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final String _baseUrl = 'https://api.chargegh.com';
  
  // Check device support
  Future<bool> isAvailable() async {
    return await _auth.canCheckBiometrics || await _auth.isDeviceSupported();
  }
  
  // Check if enabled locally
  Future<bool> isEnabled(String deviceId) async {
    final token = await _storage.read(key: 'bio_token_$deviceId');
    return token != null;
  }
  
  // Enable biometric (after OTP login)
  Future<void> enable(String deviceId, String accessToken) async {
    // Verify biometric
    final authenticated = await _auth.authenticate(
      localizedReason: 'Enable biometric login',
      options: const AuthenticationOptions(stickyAuth: true, biometricOnly: true),
    );
    if (!authenticated) throw Exception('Biometric verification failed');
    
    // Generate 256-bit token
    final random = Random.secure();
    final bytes = List<int>.generate(32, (i) => random.nextInt(256));
    final token = base64Url.encode(bytes);
    
    // Store locally
    await _storage.write(key: 'bio_token_$deviceId', value: token);
    
    // Send to server
    final response = await http.post(
      Uri.parse('$_baseUrl/api/auth/biometric/enable'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'device_id': deviceId, 'biometric_token': token}),
    );
    
    if (response.statusCode != 200) {
      await _storage.delete(key: 'bio_token_$deviceId');
      throw Exception(jsonDecode(response.body)['error']['message']);
    }
  }
  
  // Login with biometric
  Future<Map<String, dynamic>> login(String deviceId) async {
    // Get token
    final token = await _storage.read(key: 'bio_token_$deviceId');
    if (token == null) throw Exception('Biometric not enabled');
    
    // Verify biometric
    final authenticated = await _auth.authenticate(
      localizedReason: 'Login to ChargeGhar',
      options: const AuthenticationOptions(stickyAuth: true, biometricOnly: true),
    );
    if (!authenticated) throw Exception('Biometric verification failed');
    
    // Send to server
    final response = await http.post(
      Uri.parse('$_baseUrl/api/auth/biometric/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'device_id': deviceId, 'biometric_token': token}),
    );
    
    if (response.statusCode != 200) {
      throw Exception(jsonDecode(response.body)['error']['message']);
    }
    
    final data = jsonDecode(response.body)['data'];
    
    // Store JWT tokens
    await _storage.write(key: 'access_token', value: data['tokens']['access']);
    await _storage.write(key: 'refresh_token', value: data['tokens']['refresh']);
    
    return data;
  }
  
  // Disable biometric
  Future<void> disable(String deviceId, String accessToken) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/auth/biometric/disable'),
      headers: {
        'Authorization': 'Bearer $accessToken',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'device_id': deviceId}),
    );
    
    if (response.statusCode == 200) {
      await _storage.delete(key: 'bio_token_$deviceId');
    } else {
      throw Exception(jsonDecode(response.body)['error']['message']);
    }
  }
  
  // Get status from server
  Future<Map<String, dynamic>> getStatus(String deviceId, String accessToken) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/api/auth/biometric/status?device_id=$deviceId'),
      headers: {'Authorization': 'Bearer $accessToken'},
    );
    
    if (response.statusCode == 200) {
      return jsonDecode(response.body)['data'];
    }
    throw Exception('Failed to get status');
  }
}
```

---

## Usage

### Enable After Login
```dart
final bioService = BiometricService();
try {
  await bioService.enable(deviceId, accessToken);
} catch (e) {
  print('Error: $e');
}
```

### Login
```dart
try {
  final data = await bioService.login(deviceId);
  // Navigate to home
} catch (e) {
  // Show OTP option
}
```

### Disable
```dart
await bioService.disable(deviceId, accessToken);
```

### Check Status
```dart
final enabled = await bioService.isEnabled(deviceId);
```

---

## Error Handling

```dart
try {
  await bioService.login(deviceId);
} on PlatformException catch (e) {
  switch (e.code) {
    case 'NotAvailable': // Biometric not available
    case 'NotEnrolled': // No biometric enrolled
    case 'LockedOut': // Too many attempts
    case 'PermanentlyLockedOut': // Device locked
  }
} catch (e) {
  // Server/network error
}
```

---

## API Reference

| Method | Endpoint | Auth | Body |
|--------|----------|------|------|
| POST | `/api/auth/biometric/enable` | Required | `{device_id, biometric_token}` |
| POST | `/api/auth/biometric/login` | None | `{device_id, biometric_token}` |
| POST | `/api/auth/biometric/disable` | Required | `{device_id}` |
| GET | `/api/auth/biometric/status` | Required | `?device_id=xxx` |

**Response**:
```json
{"success": true, "message": "...", "data": {...}}
```

**Error**:
```json
{"success": false, "error": {"code": "...", "message": "..."}}
```

---

## Security Notes

- Token: 256-bit (32 bytes) cryptographically secure
- Storage: Platform secure storage (Keychain/Keystore)
- Biometric data: NEVER sent to server
- Always verify locally first

---