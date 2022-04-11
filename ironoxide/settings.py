""" ironoxide consts and settings """
from pathlib import Path
import json
import logging

# setup
HERE = Path(__file__).parent
DASH_URL = 'https://mycampus.iubh.de/my/'
DATA_PATH = HERE.parent/'data'
LOGGING_LEVEL = logging.INFO
DEBUG = True

# creds
creds = json.load(open(HERE.parent/'data'/'creds.json', 'r'))
IU_USER = creds['iu_user']
IU_PASS = creds['iu_pass']
OPENAI_API_KEY = creds['openai_api_key']