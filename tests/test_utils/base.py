from rest_framework.test import APITestCase
from django.test import TestCase

class BaseTestCase(TestCase):
    """Base test case with common setup."""
    pass

class BaseAPITestCase(APITestCase):
    """Base API test case with common setup."""
    pass