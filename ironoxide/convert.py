import json
import logging
import time
from multiprocessing.pool import Pool
from pathlib import Path

import pdfplumber
import pytesseract
from pdf2image import convert_from_path

from ironoxide import settings, utils

HERE = Path(__file__).parent

logging.getLogger('pdfminer').setLevel(logging.WARNING)  # for some reason it logs so much random stuff to info
logger = logging.getLogger(__file__)
logger.setLevel(settings.LOGGING_LEVEL_MODULE)


def ocr(image):
    return pytesseract.image_to_string(image, lang='eng', config=f"--oem 1")


def convert(file_path, ocr=False) -> Path:
    """ Converts a pdf to a jsonl file

    Args:
        file_path (PosixPath, str): Absolute path to the pdf file
        ocr (bool, optional): If the OCR method should be used to extract text instead of the pdfminer method. Defaults to False.

    Returns:
        Path: Absolute path to the output jsonl file
    """

    logger.info(f'Converting {file_path} to jsonl')

    MIN_WORDS = 5
    MAX_CHARS = 2000
    OCR_PROCESSES = 8

    start = time.perf_counter()
    if ocr:
        # Convert pdf to images to be OCR'd by tesseract
        pages = convert_from_path(file_path)
        logger.debug(f'Converted to images in {time.perf_counter() - start:.3f}s')

        # OCR using tesseract with multithreading
        p = Pool(processes=OCR_PROCESSES)
        pages_text = p.map(ocr, pages)
        fulltext = '\n'.join(pages_text)
        logger.debug()(f'OCR\'d in {time.perf_counter() - start:.3f}s')

    else:
        fulltext = ''
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                fulltext += page.extract_text() + '\n'

        # format and filter output and write to file
        # sentences = fulltext.split('.')
        sentences = fulltext.split('.\n') # this works best so far
        output = []
        for sentence in sentences:
            if len(sentence.replace('.', '').split(' ')) > MIN_WORDS:
                output.append({'text': utils.clean_str(sentence[:MAX_CHARS])})
        # logger.debug(f'Got PDF text in {time.perf_counter() - start:.3f}s')

    output_path = settings.DATA_PATH/'output.jsonl'
    with open(output_path, 'w') as f:
        for line in output:
            f.write(json.dumps(line) + '\n')
    logger.debug(f'Saved output in {time.perf_counter() - start:.3f}s')
    return output_path


if __name__ == '__main__':
    convert(HERE.parent/'pycoursebook.pdf')
