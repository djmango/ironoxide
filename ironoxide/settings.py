""" ironoxide consts and settings """
import django
from pathlib import Path
import json
import logging
import os
import sys

# setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ironoxide.settings')
HERE = Path(__file__).parent
DATA_PATH = HERE/'data'
LOGGING_LEVEL_ROOT = logging.INFO
LOGGING_LEVEL_MODULE = logging.DEBUG
DEBUG = True
DASH_URL = 'https://mycampus.iubh.de/my/'

# creds
creds = json.load(open(DATA_PATH/'creds.json', 'r'))
IU_USER = creds['iu_user']
IU_PASS = creds['iu_pass']
OPENAI_API_KEY = creds['openai_api_key']

# django
SECRET_KEY = creds['django_secret_key']

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_PATH/'db.sqlite3',
    }
}

INSTALLED_APPS = ['ironoxide']

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# logging config
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s | %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL_ROOT
        }
    },
}

django.setup()
