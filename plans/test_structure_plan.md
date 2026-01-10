# Comprehensive Test Directory Structure for Django REST API

## Overview
This plan outlines a scalable, maintainable test structure for the ChargeGhar Django REST API project. The structure mirrors the main application layout while providing clear organization for unit, integration, and API tests.

## Current Analysis
- **Apps Structure**: admin, user (with sub-apps: auth, content, media, notifications, payments, points, promotions, rentals, social, stations, system), franchise, web
- **Current Tests**: Basic tests/ directory with unit/, integration/, load/ subdirs; some app-specific tests in api/admin/tests/ and api/user/auth/tests/
- **Pattern**: DRF with serializers, services, views

## Proposed Test Directory Structure

```
tests/
├── __init__.py
├── conftest.py                           # Global pytest fixtures and setup
├── test_utils/                           # Shared test utilities
│   ├── __init__.py
│   ├── factories.py                      # Model factories (factory_boy)
│   ├── helpers.py                        # Test helper functions
│   ├── base.py                           # Base test classes
│   └── fixtures/                         # Shared JSON fixtures
│       ├── users.json
│       ├── stations.json
│       └── ...
├── admin/                                # Mirror api/admin/
│   ├── __init__.py
│   ├── test_models.py                    # Model validation and business logic
│   ├── test_serializers.py               # Serializer validation and field handling
│   ├── test_services.py                  # Service layer business logic
│   ├── test_views.py                     # View logic tests
│   ├── test_api.py                       # API endpoint integration tests
│   └── fixtures/                         # App-specific fixtures
│       ├── admin_users.json
│       └── ...
├── user/                                 # Mirror api/user/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   ├── test_services.py
│   │   ├── test_views.py
│   │   ├── test_api.py                   # API endpoint tests
│   │   └── fixtures/
│   ├── content/
│   │   └── ...                          # Same structure as auth
│   ├── media/
│   │   └── ...
│   ├── notifications/
│   │   └── ...
│   ├── payments/
│   │   └── ...
│   ├── points/
│   │   └── ...
│   ├── promotions/
│   │   └── ...
│   ├── rentals/
│   │   └── ...
│   ├── social/
│   │   └── ...
│   ├── stations/
│   │   └── ...
│   └── system/
│       └── ...
├── franchise/
│   └── ...                              # Same structure as admin
├── web/
│   └── ...                              # Same structure as admin
├── integration/                         # Cross-app integration tests
│   ├── __init__.py
│   ├── test_user_rental_flow.py         # Full user rental scenarios
│   ├── test_payment_flow.py             # Payment processing flows
│   └── ...
├── load/                                # Load testing (if applicable)
│   └── ...
└── unit/                                # Pure unit tests (no DB required)
    ├── __init__.py
    └── test_utils.py                    # Test utility functions
```

## File Purposes

### Global Files
- **conftest.py**: Contains pytest fixtures for database setup, authenticated clients, common test data
- **test_utils/**: Reusable components across tests
  - `factories.py`: Factory classes for creating test model instances
  - `helpers.py`: Utility functions for test setup and assertions
  - `base.py`: Base test classes with common setup/teardown

### App/Sub-app Test Files
- **test_models.py**: Tests for model validation, custom methods, and constraints
- **test_serializers.py**: Tests for serializer validation, field transformations, and error handling
- **test_services.py**: Tests for business logic in service classes
- **test_views.py**: Tests for view logic (if not API endpoints)
- **test_api.py**: Integration tests for API endpoints using DRF test client
- **fixtures/**: JSON fixtures specific to the app for database setup

### Integration Tests
- End-to-end tests that span multiple apps and test complete user workflows

## Pytest Configuration

Add to `pyproject.toml`:

```toml
[tool:pytest]
addopts = -v --tb=short --cov=api --cov-report=html --cov-report=term
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    api: API endpoint tests
    slow: Slow tests to skip in quick runs
```

### Requirements
- pytest
- pytest-django
- pytest-cov
- factory-boy (for model factories)
- pytest-mock (for mocking)

## Example Test File

### tests/user/auth/test_api.py

```python
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.user.auth.models import User
from tests.test_utils.factories import UserFactory


@pytest.mark.api
class TestAuthAPI(APITestCase):
    """Test cases for authentication API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.login_url = reverse('auth:login')
        self.register_url = reverse('auth:register')

    def test_login_success(self):
        """Test successful user login."""
        data = {
            'username': self.user.username,
            'password': 'testpass123'  # Assuming factory sets this
        }
        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'username': self.user.username,
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_register_user(self):
        """Test user registration."""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        # Verify user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
```

## Test Running Commands

### Basic Commands
- **All tests**: `pytest`
- **With coverage**: `pytest --cov=api --cov-report=html`
- **Verbose output**: `pytest -v`

### Selective Test Runs
- **Specific app**: `pytest tests/admin/`
- **Specific sub-app**: `pytest tests/user/auth/`
- **Unit tests only**: `pytest tests/unit/`
- **Integration tests**: `pytest tests/integration/`
- **API tests only**: `pytest -m api`
- **Skip slow tests**: `pytest -m "not slow"`

### File/Function Specific
- **Specific file**: `pytest tests/user/auth/test_api.py`
- **Specific test**: `pytest tests/user/auth/test_api.py::TestAuthAPI::test_login_success`

### CI/CD Commands
- **With coverage threshold**: `pytest --cov=api --cov-fail-under=80 --junitxml=report.xml`
- **Parallel execution**: `pytest -n auto`

## Implementation Principles

1. **Mirror Structure**: Tests mirror the app structure for easy navigation
2. **Clear Separation**: Unit, integration, and API tests are clearly separated
3. **Reusable Fixtures**: Common test data and setup in conftest.py and test_utils/
4. **Naming Conventions**: `test_*.py` files with descriptive class and method names
5. **DRF Best Practices**: Use APITestCase for API tests, factory_boy for data creation
6. **Coverage Focus**: Tests cover models, serializers, services, and API endpoints
7. **Scalability**: Structure supports adding new apps/sub-apps easily
8. **Maintainability**: Shared utilities reduce code duplication

## Next Steps

1. Create the directory structure as outlined
2. Set up pytest configuration in pyproject.toml
3. Implement conftest.py with basic fixtures
4. Create factories.py for common models
5. Migrate existing tests to the new structure
6. Add comprehensive tests following the patterns shown

This structure provides a solid foundation that will scale with your project while maintaining clarity and ease of maintenance.