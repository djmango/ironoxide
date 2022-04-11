""" ironoxide consts and settings """
from pathlib import Path
import json
import logging
import os

# setup
HERE = Path(__file__).parent
DATA_PATH = HERE/'data'
LOGGING_LEVEL_ROOT = logging.INFO
LOGGING_LEVEL_MODULE = logging.DEBUG
DEBUG = True
DASH_URL = 'https://mycampus.iubh.de/my/'
# os.environ['PYTHONPATH'] = '..'

# creds
creds = json.load(open(DATA_PATH/'creds.json', 'r'))
IU_USER = creds['iu_user']
IU_PASS = creds['iu_pass']
OPENAI_API_KEY = creds['openai_api_key']

# django
SECRET_KEY = creds['django_secret_key']

DEFAULT_AUTO_FIELD='django.db.models.AutoField'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_PATH/'db.sqlite3',
    }
}

INSTALLED_APPS = ['ironoxide']
