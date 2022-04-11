import json
import logging
import time
from pathlib import Path

import requests

from ironoxide import settings

HERE = Path(__file__).parent

logging.basicConfig(level=settings.LOGGING_LEVEL, format=('%(asctime)s %(levelname)s %(name)s | %(message)s'))
logger = logging.getLogger(__file__)

def upload(file_path):
    headers = {'Authorization': f'Bearer {settings.OPENAI_API_KEY}'}
    files = {'file': open(file_path, 'rb')}
    r = requests.post('https://api.openai.com/v1/files', headers=headers, data={'purpose': 'answers'}, files=files)
    e = r.json()
    print(e)

if __name__ == '__main__':
    upload(HERE.parent/'data'/'output.jsonl')