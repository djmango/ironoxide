import json
import logging
import pickle
from pathlib import Path
import re
from select import select

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from ironoxide import settings

# setup
HERE = Path(__file__).parent
COOKIEPATH = settings.DATA_PATH/'cookies.pkl'
logger = logging.getLogger(__file__)
logging.basicConfig(level=settings.LOGGING_LEVEL, format=('%(asctime)s %(levelname)s %(name)s | %(message)s'))

creds = json.load(open(HERE.parent/'data'/'creds.json'))

def main():
    driver = uc.Chrome(use_subprocess=True)

    # -- Login --

    driver.get(settings.DASH_URL)
    # load cookies if we have them
    # if COOKIEPATH.is_file():
    #     cookies = pickle.load(open(COOKIEPATH, 'rb'))
    #     for cookie in cookies:
    #         cookie['domain'] = '.iubh.de'
    #         driver.add_cookie(cookie)
    #     driver.get(settings.DASH_URL)

    # cookies should allow is to go straight to the dashboard but if not then we must login
    if driver.current_url != settings.DASH_URL:
        # wait for page load
        try:
            element = WebDriverWait(driver, 3).until(ec.presence_of_element_located((By.ID, 'username')))
        except TimeoutException:
            logger.error("Loading took too much time!")
        # fill in user & pass fields
        for fieldName in ['username', 'password']:  # fill in user and password
            field = driver.find_element(By.ID, fieldName)
            field.clear()
            field.send_keys(creds[fieldName])
        # hit login
        driver.find_element(By.ID, 'loginbtn').click()
        logger.info('Logged in..')

    # -- Dashboard --
    # ensure dashboard load - this commonly fails
    for attempt in range(5):
        try:
            # deny cookies
            element = WebDriverWait(driver, timeout=10).until(ec.presence_of_element_located((By.ID, 'uc-a-deny-banner')))
            element.click()
            logger.info('Denied cookies..')
        except Exception as e:
            logger.error(e)
            driver.refresh()
        else:
            break

    # save login cookies
    # cookies = driver.get_cookies()
    # for cookie in cookies:
    #     cookie['domain'] = '.iubh.de'
    # pickle.dump(cookies, open(COOKIEPATH, 'wb'))

    # get list of active courses
    coursesPane = BeautifulSoup(WebDriverWait(driver, 3).until(ec.presence_of_element_located((By.ID, 'courses-active'))).get_attribute('innerHTML'), features='lxml')
    courses = list(coursesPane.find_all('a', {'class': 'courseitem'}))

    for i, course in enumerate(courses):
        clean = re.sub(r'[^a-zA-Z]', '', course.text)
        print(f'{i}: {clean}')

    selection = input('Select course: ')
    if selection == '':
        selection = 0
    
    try:
        selection = int(selection)
    except:
        print('oh no bad')
    
    
    logger.info('Done!')
    driver.quit()


if __name__ == '__main__':
    main()
