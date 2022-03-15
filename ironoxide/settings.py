""" ironoxide consts and settings """
from pathlib import Path
import logging

# setup
HERE = Path(__file__).parent
DASH_URL = 'https://mycampus.iubh.de/my/'
DATA_PATH = HERE.parent/'data'
LOGGING_LEVEL = logging.INFO
DEBUG = True