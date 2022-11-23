from .defaults import *  # noqa

DEBUG = True

SECRET_KEY = '7kao=4+@oo!1zdqme)b9!l)0%76rg5&k_-_3@ud!4w_1vpdcwd'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

ALLOWED_HOSTS = []
