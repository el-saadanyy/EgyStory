"""
Django settings for EgyStory project.
"""

from pathlib import Path
import os
import urllib.parse
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY', default='django-insecure-egystory-demo-default-key-2026')
DEBUG = config('DEBUG', default=False, cast=bool)

# Production security headers when DEBUG is False
if not DEBUG:
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
    # Required for Render / reverse proxy HTTPS termination
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

def _parse_list(val):
    if isinstance(val, (list, tuple)):
        return list(val)
    return [x.strip() for x in str(val).split(',') if x.strip()]

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,0.0.0.0,testserver,.onrender.com,*.onrender.com,ranting-gliding-saffron.ngrok-free.dev',
    cast=_parse_list
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:8000,http://127.0.0.1:8000,http://0.0.0.0:8000,https://*.onrender.com,https://ranting-gliding-saffron.ngrok-free.dev',
    cast=_parse_list
)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Project apps
    'accounts',
    'administration',
    'campaigns',
    'chatbot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'egystory.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'egystory.wsgi.application'

# Database Configuration
# Default: SQLite (preserves existing SQLite database and records)
# PostgreSQL is enabled when DATABASE_URL or DB_ENGINE=postgres is configured
database_url = config('DATABASE_URL', default='').strip()
db_engine = config('DB_ENGINE', default='').strip().lower()
conn_max_age = config('DB_CONN_MAX_AGE', default=60, cast=int)

if database_url:
    url = urllib.parse.urlparse(database_url)
    qs = urllib.parse.parse_qs(url.query)
    
    db_options = {}
    if 'sslmode' in qs:
        db_options['sslmode'] = qs['sslmode'][0]
    elif config('DB_SSL_REQUIRE', default=False, cast=bool):
        db_options['sslmode'] = 'require'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': urllib.parse.unquote(url.path.lstrip('/')),
            'USER': urllib.parse.unquote(url.username or ''),
            'PASSWORD': urllib.parse.unquote(url.password or ''),
            'HOST': url.hostname or '',
            'PORT': url.port or 5432,
            'CONN_MAX_AGE': conn_max_age,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': db_options,
        }
    }
elif db_engine in ('postgres', 'postgresql'):
    db_options = {}
    if config('DB_SSL_REQUIRE', default=False, cast=bool):
        db_options['sslmode'] = 'require'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='egystory'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': conn_max_age,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': db_options,
        }
    }
else:
    db_custom_path = config('DATABASE_PATH', default='').strip()
    sqlite_file = Path(db_custom_path) if db_custom_path else BASE_DIR / 'db.sqlite3'
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': sqlite_file,
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (user avatars, campaign covers, documents)
MEDIA_URL = '/media/'
media_custom_path = config('MEDIA_ROOT_PATH', default='').strip()
MEDIA_ROOT = Path(media_custom_path) if media_custom_path else BASE_DIR / 'media'
DEMO_MEDIA_ROOT = BASE_DIR / 'demo_media'

# Storage Configuration (Django 4.2+ / 5.0+ standard STORAGES setting)
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='').strip()
USE_S3 = config('USE_S3', default=False, cast=bool) or bool(AWS_STORAGE_BUCKET_NAME)

if USE_S3 and AWS_STORAGE_BUCKET_NAME:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='').strip()
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='').strip()
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='').strip()
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='').strip() or None
    AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default='').strip() or None
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# WhiteNoise: Prevent unmanifested static files from throwing 500 errors in production
WHITENOISE_MANIFEST_STRICT = config('WHITENOISE_MANIFEST_STRICT', default=False, cast=bool)


# Email settings
# Configurable: HTTP email API (Resend/Brevo) for Render Free, real SMTP, or console backend fallback
EMAIL_BACKEND_CONF = config('EMAIL_BACKEND', default='').strip()
EMAIL_HOST = config('EMAIL_HOST', default='').strip()
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='').strip()
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='').strip()
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)

RESEND_API_KEY = config('RESEND_API_KEY', default='').strip()
BREVO_API_KEY = config('BREVO_API_KEY', default='').strip()

if EMAIL_BACKEND_CONF:
    EMAIL_BACKEND = EMAIL_BACKEND_CONF
elif RESEND_API_KEY:
    EMAIL_BACKEND = 'egystory.email_backends.ResendEmailBackend'
elif BREVO_API_KEY:
    EMAIL_BACKEND = 'egystory.email_backends.BrevoEmailBackend'
elif EMAIL_HOST and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@egystory.com')

# Authentication
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
