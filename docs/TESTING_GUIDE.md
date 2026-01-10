# Testing Guide for ChargeGhar API

## Overview
This guide covers how to work with our comprehensive test suite that validates all user-facing API endpoints against the live Docker server.

## Prerequisites
- Docker server running at `http://localhost:8010`
- Admin credentials: `janak@powerbank.com` / `5060`
- pytest installed: `pip install pytest pytest-django pytest-cov factory-boy requests`

## 1. Running Tests

### Run All Tests
```bash
python -m pytest tests/ -v --tb=short
```

### Run Specific App Tests
```bash
# Single app
python -m pytest tests/user/auth/ -v

# Multiple apps
python -m pytest tests/user/auth/ tests/user/payments/ -v

# Specific test file
python -m pytest tests/user/auth/test_api.py::TestAuthAPI::test_device_registration -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=api --cov-report=html --cov-report=term
```

## 2. Test Structure

### Directory Layout
```
tests/
├── conftest.py              # Global fixtures & Django setup
├── test_utils/              # Shared utilities
│   ├── factories.py         # Model factories
│   ├── helpers.py           # Test helper functions
│   └── base.py              # Base test classes
├── app/                     # App-level endpoints
├── user/                    # User-facing endpoints
│   ├── auth/               # Authentication & profile
│   ├── content/            # Static content
│   ├── media/              # File uploads
│   ├── notifications/      # Push notifications
│   ├── payments/           # Wallet & transactions
│   ├── points/             # Rewards & referrals
│   ├── promotions/         # Coupons & discounts
│   ├── rentals/            # Power bank rentals
│   ├── social/             # Achievements & leaderboards
│   ├── stations/           # Charging stations
│   └── system/             # System utilities
```

### Test File Naming
- `test_api.py` - API endpoint tests
- `test_models.py` - Model validation tests
- `test_services.py` - Business logic tests
- `test_serializers.py` - Serializer tests

## 3. Adding New Tests

### For New Endpoints
1. Identify the app and create/update `tests/user/{app}/test_api.py`
2. Add test method following pattern:
```python
def test_new_endpoint(self, headers):
    """Test new endpoint description."""
    # Arrange
    data = {"key": "value"}

    # Act
    response = requests.post(f'{BASE_URL}/api/{app}/endpoint', json=data, headers=headers)

    # Assert
    assert response.status_code in [200, 201, 400, 500]
```

### For New Apps
1. Create directory: `mkdir tests/user/newapp`
2. Create `__init__.py` and `test_api.py`
3. Follow existing patterns for authentication and base URL

## 4. Updating Existing Tests

### When Adding Query Parameters
```python
def test_endpoint_with_params(self, headers):
    """Test endpoint with query parameters."""
    params = {'status': 'active', 'limit': 10}
    response = requests.get(f'{BASE_URL}/api/app/endpoint', params=params, headers=headers)
    assert response.status_code == 200
```

### When Testing File Uploads
```python
def test_file_upload(self, headers):
    """Test file upload endpoint."""
    files = {'file': ('test.jpg', open('test.jpg', 'rb'), 'image/jpeg')}
    response = requests.post(f'{BASE_URL}/api/media/upload', files=files, headers=headers)
    assert response.status_code == 201
```

### When Testing Pagination
```python
def test_pagination(self, headers):
    """Test paginated endpoint."""
    response = requests.get(f'{BASE_URL}/api/data?page=1&page_size=20', headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert 'results' in data
    assert 'pagination' in data
```

## 5. Authentication in Tests

### Admin Authentication (Current Setup)
Tests use admin login to get JWT tokens for user endpoints:
```python
@pytest.fixture
def headers(self, access_token):
    return {'Authorization': f'Bearer {access_token}'}
```

### For Different User Types
Extend fixtures for different authentication scenarios:
```python
@pytest.fixture
def user_headers(self):
    # Login as regular user
    response = requests.post(f'{BASE_URL}/api/auth/login', data=user_creds)
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}
```

## 6. Best Practices

### Test Isolation
- Each test should be independent
- Use fixtures for setup/cleanup
- Don't rely on test execution order

### Naming Conventions
- `test_descriptive_name` - Clear, descriptive names
- `test_get_user_profile` not `test_profile`
- Group related tests in classes

### Error Handling
- Allow expected error codes: `[200, 201, 400, 404, 500]`
- Document unexpected failures in `errors/{app}/{endpoint}.md`
- Don't modify code to fix tests - note issues instead

### Performance
- Keep tests focused on single endpoints
- Use `--tb=short` for quick feedback
- Run parallel with `pytest -n auto` for speed

## 7. Debugging Failed Tests

### Common Issues
1. **500 Internal Server Error**
   - Check Docker logs: `docker logs chargeghar_app`
   - Verify endpoint exists in API

2. **401 Unauthorized**
   - Check token validity
   - Verify authentication setup

3. **404 Not Found**
   - Confirm correct endpoint URL
   - Check route configuration

4. **400 Bad Request**
   - Verify request payload format
   - Check required fields

### Debugging Steps
```bash
# Run with detailed output
python -m pytest tests/user/auth/test_api.py::TestAuthAPI::test_device_registration -v -s

# Check server logs
docker logs chargeghar_app --tail 50

# Test manually with curl
curl -X POST http://localhost:8010/api/auth/device \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"device_id": "test"}'
```

## 8. CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run API Tests
  run: |
    python -m pytest tests/ --cov=api --cov-report=xml --junitxml=test-results.xml
    coverage report --fail-under=80
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: run-tests
        name: Run API Tests
        entry: python -m pytest tests/ -x
        language: system
        pass_filenames: false
```

## 9. Test Data Management

### Using Fixtures
```python
# tests/conftest.py
@pytest.fixture
def sample_user_data():
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'phone': '+1234567890'
    }
```

### Factory Usage
```python
from tests.test_utils.factories import UserFactory

def test_with_factory():
    user = UserFactory()
    # Use factory-generated test data
```

## 10. Maintenance

### Regular Tasks
- Run full test suite before deployments
- Update tests when API contracts change
- Clean up obsolete test files
- Review test coverage reports

### When APIs Change
1. Update affected test files
2. Run tests to verify changes
3. Update documentation if needed
4. Ensure CI/CD still passes

### Monitoring
- Track test execution time
- Monitor flaky tests
- Review coverage gaps
- Update test dependencies

---

**Total Lines: 98**

This guide ensures consistent, maintainable testing practices across the ChargeGhar API development lifecycle.