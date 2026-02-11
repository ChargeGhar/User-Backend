import pytest
import django
from django.conf import settings
from django.test.utils import get_runner

# Setup Django for pytest
if not settings.configured:
    django.setup()

@pytest.fixture(scope='session')
def django_db_setup():
    """Setup database for tests."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
    }

@pytest.fixture
def api_client():
    """Authenticated API client fixture."""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def admin_client(api_client):
    """Admin authenticated client using curl login data."""
    # This will be used for admin authentication
    # For now, return client; authentication will be handled in tests
    return api_client

@pytest.fixture
def user_client(api_client):
    """Regular user authenticated client."""
    return api_client

# Add more fixtures as needed
