"""
Django settings for tribel_scholar project.
MoTA SIH Problem Statement 26239 - Foundation Architecture
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps to sys.path
sys.path.insert(0, str(BASE_DIR / 'apps'))

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-mota-sih-26239-foundation-secret-key-tribal-scholar')

DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

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
# Uses PostgreSQL if DATABASE_ENGINE or DB_ENGINE or DB_NAME or POSTGRES_DB is set, falls back to SQLite for local development
DATABASE_ENGINE_ENV = os.getenv('DATABASE_ENGINE', os.getenv('DB_ENGINE', '')).lower()
if 'postgres' in DATABASE_ENGINE_ENV or os.getenv('POSTGRES_DB') or os.getenv('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', os.getenv('DB_NAME', 'tribal_scholar')),
            'USER': os.getenv('POSTGRES_USER', os.getenv('DB_USER', 'postgres')),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', '')),
            'HOST': os.getenv('POSTGRES_HOST', os.getenv('DB_HOST', '127.0.0.1')),
            'PORT': os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', '5432')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

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

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# Celery Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Object Storage Configuration (MinIO / S3 compatible)
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'local')
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'tribal-scholar-docs')
MINIO_USE_SSL = os.getenv('MINIO_USE_SSL', 'False').lower() in ('true', '1')

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
