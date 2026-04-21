from __future__ import annotations

from os import getenv

from api.config.silk import SILKY_MIDDLEWARE_CLASS, USE_SILK

PROJECT_NAME = getenv("PROJECT_NAME", "django_template")
PROJECT_VERBOSE_NAME = getenv("PROJECT_VERBOSE_NAME", "Django Template").strip("'\"")

# Nepal Gateways Configuration
NEPAL_GATEWAYS_CONFIG = {
    'esewa': {
        'product_code': getenv('ESEWA_PRODUCT_CODE', 'EPAYTEST'),
        'secret_key': getenv('ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q'),
        'success_url': getenv('ESEWA_SUCCESS_URL'),
        'failure_url': getenv('ESEWA_FAILURE_URL'),
        'mode': getenv('ESEWA_MODE', 'sandbox'),
    },
    'khalti': {
        'live_secret_key': getenv('KHALTI_LIVE_SECRET_KEY'),
        'return_url_config': getenv('KHALTI_RETURN_URL'),
        'website_url_config': getenv('KHALTI_WEBSITE_URL'),
        'mode': getenv('KHALTI_MODE', 'sandbox'),
    }
}

ENVIRONMENT = getenv("ENVIRONMENT", "local")
HOST = getenv("HOST", "localhost")

INSTALLED_APPS = [
    "admin_interface",
    "colorfield",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "corsheaders",
    "axes",
    "silk",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",  # JWT token blacklisting
    "drf_spectacular",
    # Django Allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    # PowerBank Apps - User Namespace
    "api.user.system",
    "api.user.media",
    "api.common.apps.CommonConfig",
    "api.user.auth.apps.AuthConfig",
    "api.user.stations.apps.StationsConfig",
    "api.user.rentals.apps.RentalsConfig",
    "api.user.payments.apps.PaymentsConfig",
    "api.user.points.apps.PointsConfig",
    "api.user.notifications.apps.NotificationsConfig",
    "api.user.social.apps.SocialConfig",
    "api.user.promotions.apps.PromotionsConfig",
    "api.user.content.apps.ContentConfig",
    "api.user.advertisements.apps.AdvertisementsConfig",
    "api.admin.apps.AdminConfig",
    "api.config.apps.ConfigConfig",
    "api.internal.apps.InternalConfig",
    # Partnership System
    "api.partners.common.apps.PartnersCommonConfig",
]

# Required for django-allauth
SITE_ID = 1

# Allauth Configuration
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'  # We handle verification via OTP
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'

# Social Account Configuration
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_QUERY_EMAIL = True

# Custom adapter to integrate with your User model
SOCIALACCOUNT_ADAPTER = 'api.user.auth.adapters.CustomSocialAccountAdapter'

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # Required by django-allauth
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    SILKY_MIDDLEWARE_CLASS,
    "axes.middleware.AxesMiddleware",
]

if not USE_SILK:
    INSTALLED_APPS.remove("silk")
    MIDDLEWARE.remove(SILKY_MIDDLEWARE_CLASS)

ROOT_URLCONF = "api.web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "api.web.wsgi.application"

LANGUAGE_CODE = getenv("LANGUAGE_CODE", "en-us")

USE_TZ = True
TIME_ZONE = getenv("TIME_ZONE", "UTC")

USE_I18N = True

SPARROW_SMS_TOKEN = getenv("SPARROW_SMS_TOKEN")
SPARROW_SMS_FROM = getenv("SPARROW_SMS_FROM", "Demo")
SPARROW_SMS_BASE_URL = getenv("SPARROW_SMS_BASE_URL", "https://sms.sparrowsms.com/v2/sms/")
ANDROID_SMS_HASH = getenv("ANDROID_SMS_HASH", "")

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH = getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
FIREBASE_CREDENTIALS_BASE64 = getenv("FIREBASE_CREDENTIALS_BASE64")
FCM_SERVER_KEY = getenv("FCM_SERVER_KEY")
FCM_SENDER_ID = getenv("FCM_SENDER_ID")

# Email Configuration
EMAIL_BACKEND = getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = getenv('EMAIL_HOST', 'smtp.hostinger.com')
EMAIL_PORT = int(getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = getenv('EMAIL_USE_TLS', 'TRUE').lower() == 'true'
EMAIL_HOST_USER = getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = getenv('DEFAULT_FROM_EMAIL')

# ========================================
# IoT System Integration Settings
# ========================================

# Shared secret for request signature validation (MUST match Java config)
IOT_SYSTEM_SIGNATURE_SECRET = getenv(
    'IOT_SYSTEM_SIGNATURE_SECRET',
    'ChargeGhar-SystemSecret-TrustKey2025!'
)

# IP whitelist for IoT system (optional but recommended)
IOT_SYSTEM_ALLOWED_IPS = [
    ip.strip() for ip in getenv('IOT_SYSTEM_ALLOWED_IPS', '127.0.0.1,213.210.21.113').split(',')
]

# IoT system timeout settings
IOT_SYSTEM_SIGNATURE_TIMEOUT = int(getenv('IOT_SYSTEM_SIGNATURE_TIMEOUT', 300))  # 5 minutes

# ============================================================
# Device API Configuration (Java Spring API Integration)
# ============================================================
DEVICE_API = {
    'BASE_URL': getenv('DEVICE_API_BASE_URL', 'https://api.chargeghar.com'),
    'CONNECT_TIMEOUT': int(getenv('DEVICE_API_CONNECT_TIMEOUT', '10')),
    'READ_TIMEOUT': int(getenv('DEVICE_API_READ_TIMEOUT', '30')),
    'MAX_RETRIES': int(getenv('DEVICE_API_MAX_RETRIES', '2')),
    
    # Authentication for inter-system communication
    'AUTH_ENABLED': getenv('DEVICE_API_AUTH_ENABLED', 'True').lower() == 'true',
    'AUTH_USERNAME': getenv('DEVICE_API_AUTH_USERNAME', 'admin'),
    'AUTH_PASSWORD': getenv('DEVICE_API_AUTH_PASSWORD', 'Admin@123'),
    'AUTH_LOGIN_ENDPOINT': getenv('DEVICE_API_AUTH_LOGIN_ENDPOINT', '/api/auth/login'),
}