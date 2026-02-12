from __future__ import annotations

from base64 import b64decode
from binascii import Error as BinasciiError
from os import getenv
from pathlib import Path


def _load_apple_private_key() -> str | None:
    """Load Apple private key from base64 env or key file path."""
    raw_private_key = getenv('APPLE_OAUTH_PRIVATE_KEY_BASE64')
    if raw_private_key:
        key_value = raw_private_key.strip()

        # Allow passing full PEM text directly.
        if "BEGIN PRIVATE KEY" in key_value:
            return key_value

        # Support base64-encoded .p8 content stored in env.
        try:
            decoded = b64decode(key_value).decode("utf-8")
            if "BEGIN PRIVATE KEY" in decoded:
                return decoded
        except (BinasciiError, UnicodeDecodeError):
            pass

        # Backward compatible fallback: return raw value.
        return key_value

    private_key_path = getenv('APPLE_OAUTH_PRIVATE_KEY_PATH')
    if private_key_path:
        path = Path(private_key_path)
        if path.exists():
            return path.read_text(encoding="utf-8").strip()

    return None


APPLE_TEAM_ID = getenv('APPLE_OAUTH_TEAM_ID') or getenv('APPLE_OAUTH_KEY_ID')
APPLE_KEY_ID = getenv('APPLE_OAUTH_KEY_ID') or getenv('APPLE_OAUTH_CLIENT_SECRET')
APPLE_PRIVATE_KEY = _load_apple_private_key()

# Social Account Providers Configuration
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': getenv('GOOGLE_OAUTH_CLIENT_ID'),
            'secret': getenv('GOOGLE_OAUTH_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    },
    'apple': {
        'APP': {
            'client_id': getenv('APPLE_OAUTH_CLIENT_ID'),
            # allauth/apple expects:
            # secret -> Apple Key ID (kid), key -> Apple Team ID (iss)
            'secret': APPLE_KEY_ID,
            'key': APPLE_TEAM_ID,
            'certificate_key': APPLE_PRIVATE_KEY,
        },
        'SCOPE': [
            'name',
            'email',
        ],
    }
}

# Django-allauth login redirect settings
LOGIN_REDIRECT_URL = getenv('SOCIAL_AUTH_LOGIN_REDIRECT_URL', '/api/auth/social/success/')
LOGIN_ERROR_URL = getenv('SOCIAL_AUTH_LOGIN_ERROR_URL', '/api/auth/social/error/')
SOCIALACCOUNT_LOGIN_ON_GET = True  # Allow GET requests to login URLs

# Additional allauth settings for proper redirect handling
SOCIALACCOUNT_LOGIN_ON_POST = True
SOCIALACCOUNT_STORE_TOKENS = True
