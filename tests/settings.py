# -*- coding: utf-8
from __future__ import unicode_literals, absolute_import

import django
import os
DEBUG = True
USE_TZ = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
        'TEST_NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    }
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 36000,
        'KEY_PREFIX': 'django_mail_admin',
    },
    'django_mail_admin': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 36000,
        'KEY_PREFIX': 'django_mail_admin',
    }
}

DJANGO_MAIL_ADMIN = {
    'BACKENDS': {
        'default': 'django.core.mail.backends.dummy.EmailBackend',
        'locmem': 'django.core.mail.backends.locmem.EmailBackend',
        'error': 'tests.test_backends.ErrorRaisingBackend',
        'smtp': 'django.core.mail.backends.smtp.EmailBackend',
        'connection_tester': 'django_mail_admin.tests.test_mail.ConnectionTestingBackend',
    }
}

ROOT_URLCONF = "tests.urls"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "django_mail_admin",
]

SITE_ID = 1

if django.VERSION >= (1, 10):
    MIDDLEWARE = ()
else:
    MIDDLEWARE_CLASSES = ()
