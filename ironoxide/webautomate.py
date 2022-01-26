import json
import logging
import pickle
from pathlib import Path

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from . import settings

# setup
HERE = Path(__file__).parent
COOKIEPATH = settings.DATA_PATH/'cookies.pkl'
logger = logging.getLogger(__name__)
# driver = uc.Chrome(use_subprocess=True, user_data_dir=str(HERE/'data'/'user_data_dir'))
driver = uc.Chrome(use_subprocess=True)
creds = json.load(open(HERE.parent/'data'/'creds.json'))

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

# -- Dashboard --
# ensure dashboard load - this commonly fails
for attempt in range(5):
    try:
        # deny cookies
        element = WebDriverWait(driver, timeout=10).until(ec.presence_of_element_located((By.ID, 'uc-a-deny-banner')))
        element.click()
    except Exception as e:
        logger.debug(e)
        driver.refresh()
    else:
        break

# save login cookies
# cookies = driver.get_cookies()
# for cookie in cookies:
#     cookie['domain'] = '.iubh.de'
# pickle.dump(cookies, open(COOKIEPATH, 'wb'))

print('done!')
driver.quit()
