""" ironoxide consts and settings """
import sys

# Turn off bytecode generation
sys.dont_write_bytecode = True

import json
import logging
import os
from pathlib import Path

import django

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
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

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

# https://stackoverflow.com/questions/533048/how-to-log-source-file-name-and-line-number-in-python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(filename)s:%(lineno)d | %(message)s'
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
