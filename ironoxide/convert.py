import json
import logging
from . import settings

logging.basicConfig(level=settings.LOGGING_LEVEL, format=('%(asctime)s %(levelname)s %(name)s | %(message)s'))
logger = logging.getLogger(__file__)

def main():
    pass


if __name__ == '__main__':
    main()
