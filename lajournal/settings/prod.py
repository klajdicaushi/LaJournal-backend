import os
from datetime import timedelta

import dj_database_url
from django.core.management.utils import get_random_secret_key

from .defaults import *  # noqa

SECRET_KEY = os.getenv('SECRET_KEY', get_random_secret_key())

DEBUG = False
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

NINJA_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

NINJA_EXTRA = {
    'PAGINATION_PER_PAGE': 100,
    'NUM_PROXIES': None
}
