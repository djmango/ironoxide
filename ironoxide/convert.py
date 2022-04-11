import json
import logging
from pathlib import Path
import time

import pytesseract
from pdf2image import convert_from_path
import pdfplumber
from multiprocessing.pool import Pool

from ironoxide import settings, utils

HERE = Path(__file__).parent

logging.basicConfig(level=settings.LOGGING_LEVEL, format=('%(asctime)s %(levelname)s %(name)s | %(message)s'))
logger = logging.getLogger(__file__)

def ocr(image):
    return pytesseract.image_to_string(image, lang='eng', config=f"--oem 1")

def main(file_path, ocr=False):
    logger.info(f'Converting {file_path} to json')

    MIN_WORDS = 5
    OCR_PROCESSES = 8
    
    start = time.perf_counter()
    if ocr:
        # Convert pdf to images to be OCR'd by tesseract
        pages = convert_from_path(file_path)
        logger.info(f'Converted to images in {time.perf_counter() - start:.3f}s')

        # OCR using tesseract with multithreading
        p = Pool(processes=OCR_PROCESSES)
        pages_text = p.map(ocr, pages)
        fulltext = '\n'.join(pages_text)
        logger.info(f'OCR\'d in {time.perf_counter() - start:.3f}s')

    else:
        fulltext = ''
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                fulltext += page.extract_text() + '\n'

        # format and filter output and write to file
        sentences = fulltext.split('.')
        output = []
        for sentence in sentences:
            if len(sentence.split(' ')) > MIN_WORDS:
                output.append({'text': utils.clean_str(sentence)})
        logger.info(f'Got PDF text in {time.perf_counter() - start:.3f}s')

    with open(HERE.parent/'data'/'output.jsonl', 'w') as f:
        for line in output:
            f.write(json.dumps(line) + '\n')
    logger.info(f'Saved output in {time.perf_counter() - start:.3f}s')

if __name__ == '__main__':
    main(HERE.parent/'pycoursebook.pdf')
