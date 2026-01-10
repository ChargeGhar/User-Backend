# Test helper functions

def authenticate_client(client, user):
    """Authenticate a test client with a user."""
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client

def create_authenticated_client(user):
    """Create an authenticated API client."""
    from rest_framework.test import APIClient
    client = APIClient()
    return authenticate_client(client, user)