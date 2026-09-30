"""
Django settings for tribel_scholar project.
MoTA SIH Problem Statement 26239 - Foundation Architecture
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables: check test environment file if in test mode or specified
env_file = os.getenv('ENV_FILE')
if not env_file and ('pytest' in sys.modules or any('pytest' in arg for arg in sys.argv)):
    test_env = BASE_DIR / '.env.test'
    if test_env.exists():
        load_dotenv(test_env)
load_dotenv(BASE_DIR / '.env')
load_dotenv()

# Add apps to sys.path
sys.path.insert(0, str(BASE_DIR / 'apps'))

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-mota-sih-26239-foundation-secret-key-tribal-scholar')

DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]

# CSRF Trusted Origins for HTTPS (e.g. Railway domains *.railway.app, *.up.railway.app)
csrf_trusted_env = os.getenv('CSRF_TRUSTED_ORIGINS', 'https://*.railway.app,https://*.up.railway.app')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted_env.split(',') if origin.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'corsheaders',

    # Modular Monolith Modules
    'apps.core',
    'apps.accounts',
    'apps.documents',
    'apps.schemes',
    'apps.workflow',
    'apps.applicants',
    'apps.applications',
    'apps.verification',
    'apps.notifications',
    'apps.audit',
    'apps.integrations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditLoggingMiddleware',
]

ROOT_URLCONF = 'tribel_scholar.urls'

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

WSGI_APPLICATION = 'tribel_scholar.wsgi.application'
ASGI_APPLICATION = 'tribel_scholar.asgi.application'

AUTH_USER_MODEL = 'accounts.User'

# Database Configuration
# Explicit database modes:
# - DATABASE_ENGINE=postgresql (Default for test suite, CI, integration tests, concurrency tests)
# - DATABASE_ENGINE=sqlite (Only permitted when explicitly requested for lightweight local developer experiments)
# Never infer SQLite as a silent fallback!

IS_TESTING = (
    'pytest' in sys.modules
    or any('pytest' in arg for arg in sys.argv)
    or 'test' in sys.argv
    or os.getenv('CI', '').lower() in ('true', '1')
    or os.getenv('TESTING', '').lower() in ('true', '1')
)

DATABASE_ENGINE_ENV = os.getenv('DATABASE_ENGINE', os.getenv('DB_ENGINE', '')).strip().lower()

if not DATABASE_ENGINE_ENV:
    if IS_TESTING:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "PostgreSQL is required for the integrity test suite. Set DATABASE_ENGINE=postgresql."
        )
    # Default for normal execution when no engine is explicitly supplied
    DATABASE_ENGINE_ENV = 'postgresql'

if DATABASE_ENGINE_ENV == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif 'postgres' in DATABASE_ENGINE_ENV:
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        import urllib.parse
        url = urllib.parse.urlparse(database_url)
        postgres_db = urllib.parse.unquote(url.path.lstrip('/'))
        postgres_user = urllib.parse.unquote(url.username or 'postgres')
        postgres_password = urllib.parse.unquote(url.password or '')
        postgres_host = url.hostname or '127.0.0.1'
        postgres_port = str(url.port or 5432)
    else:
        postgres_db = os.getenv('POSTGRES_DB') or os.getenv('PGDATABASE') or os.getenv('DB_NAME') or 'tribal_scholar'
        postgres_user = os.getenv('POSTGRES_USER') or os.getenv('PGUSER') or os.getenv('DB_USER') or 'postgres'
        postgres_password = os.getenv('POSTGRES_PASSWORD') or os.getenv('PGPASSWORD') or os.getenv('DB_PASSWORD') or ''
        postgres_host = os.getenv('POSTGRES_HOST') or os.getenv('PGHOST') or os.getenv('DB_HOST') or '127.0.0.1'
        postgres_port = str(os.getenv('POSTGRES_PORT') or os.getenv('PGPORT') or os.getenv('DB_PORT') or '5432')

    if not postgres_db:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            "PostgreSQL configuration is incomplete: POSTGRES_DB or DATABASE_URL is required. "
            "Do NOT silently fall back to SQLite."
        )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': postgres_db,
            'USER': postgres_user,
            'PASSWORD': postgres_password,
            'HOST': postgres_host,
            'PORT': postgres_port,
        }
    }
else:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        f"Unsupported DATABASE_ENGINE='{DATABASE_ENGINE_ENV}'. "
        "Supported modes are 'postgresql' or 'sqlite'. "
        "PostgreSQL is required for the integrity test suite. Set DATABASE_ENGINE=postgresql."
    )

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

cors_allowed_env = os.getenv('CORS_ALLOWED_ORIGINS')
if cors_allowed_env:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_allowed_env.split(',') if origin.strip()]
    CORS_ALLOW_ALL_ORIGINS = False
else:
    CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', str(DEBUG)).lower() in ('true', '1')
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
    ]

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL') or os.getenv('REDIS_PRIVATE_URL')
if not REDIS_URL:
    REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ClamAV Configuration
CLAMAV_HOST = os.getenv('CLAMAV_HOST', '127.0.0.1')
CLAMAV_PORT = int(os.getenv('CLAMAV_PORT', '3310'))
CLAMAV_TIMEOUT = float(os.getenv('CLAMAV_TIMEOUT', '5.0'))
ENABLE_CLAMAV_INTEGRATION_GATE = os.getenv('ENABLE_CLAMAV_INTEGRATION_GATE', 'true').lower() in ('true', '1')

# Quarantine Retention Configuration
QUARANTINE_RETENTION_DAYS = int(os.getenv('QUARANTINE_RETENTION_DAYS', '30'))

# Test Environment Configuration
TEST_LEVEL = os.getenv('TEST_LEVEL', '').lower()

if 'pytest' in sys.modules or os.getenv('PYTEST_CURRENT_TEST'):
    # In test mode: UNIT tests may use memory broker for speed and isolation.
    # INTEGRATION tests MUST use real Redis (REDIS_HOST, REDIS_PORT, REDIS_DB). No silent fallback!
    if TEST_LEVEL == 'unit' or any('tests/unit' in arg or 'tests\\unit' in arg for arg in sys.argv):
        CELERY_BROKER_URL = 'memory://'
        CELERY_RESULT_BACKEND = 'cache+memory://'
    else:
        CELERY_BROKER_URL = REDIS_URL
        CELERY_RESULT_BACKEND = REDIS_URL

# Object Storage Configuration (MinIO / S3 compatible)
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'local')
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'tribal-scholar-docs')
MINIO_USE_SSL = os.getenv('MINIO_USE_SSL', 'False').lower() in ('true', '1')

# Document Ingestion & Storage Architecture
STORAGE_DIR = BASE_DIR / 'storage'
MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', '10'))
MAX_PDF_PAGES = int(os.getenv('MAX_PDF_PAGES', '50'))
MAX_IMAGE_PIXELS = int(os.getenv('MAX_IMAGE_PIXELS', '25000000'))  # 25 MP decompression limit
ALLOWED_MIME_TYPES = [
    m.strip() for m in os.getenv('ALLOWED_MIME_TYPES', 'application/pdf,image/jpeg,image/png').split(',')
]
MAX_DOCUMENTS_PER_APPLICATION = int(os.getenv('MAX_DOCUMENTS_PER_APPLICATION', '20'))
MAX_UPLOADS_PER_MINUTE = int(os.getenv('MAX_UPLOADS_PER_MINUTE', '10'))
MAX_PROCESSING_ATTEMPTS = int(os.getenv('MAX_PROCESSING_ATTEMPTS', '3'))
MALWARE_SCANNER_BACKEND = os.getenv('MALWARE_SCANNER_BACKEND', 'mock')

# OCR & Document Intelligence Pipeline Configuration
OCR_PIPELINE_VERSION = '1.0.0'
OCR_ENGINE_BACKEND = os.getenv('OCR_ENGINE_BACKEND', 'paddleocr')
MAX_OCR_PAGES = int(os.getenv('MAX_OCR_PAGES', '10'))
MAX_OCR_PAGE_DIMENSION = int(os.getenv('MAX_OCR_PAGE_DIMENSION', '4000'))
MAX_OCR_TOTAL_PIXELS = int(os.getenv('MAX_OCR_TOTAL_PIXELS', '25000000'))
OCR_TIMEOUT_SECONDS = int(os.getenv('OCR_TIMEOUT_SECONDS', '120'))
MAX_OCR_RETRIES = int(os.getenv('MAX_OCR_RETRIES', '3'))
ENABLE_AUTO_OCR = os.getenv('ENABLE_AUTO_OCR', 'true').lower() in ('true', '1')

# Strict Provenance & Scheme Integrity Validation Flag
ENFORCE_STRICT_SCHEME_VALIDATION = True

# Security Logging Configuration with Sensitive Data Redaction
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sensitive_data_redactor': {
            '()': 'apps.core.logging_filters.SensitiveDataRedactingFilter',
        },
    },
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['sensitive_data_redactor'],
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
