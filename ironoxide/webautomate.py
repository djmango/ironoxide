from distutils.log import debug
import json
import logging
import pickle
from pathlib import Path
import re
from select import select
from typing import Iterable

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from ironoxide import settings

# setup
HERE = Path(__file__).parent
TIMEOUT = 3  # in seconds
logger = logging.getLogger(__file__)
logging.basicConfig(level=settings.LOGGING_LEVEL, format=('%(asctime)s %(levelname)s %(name)s | %(message)s'))

creds = json.load(open(HERE.parent/'data'/'creds.json'))

def getValidSelection(selectables: list[str], query_string: str, default_selection_i: int = 0) -> int:
    """_summary_

    Args:
        selectables (list[str]): List of strings to be chosen from.
        query_string (str): What to ask the user in the input prompt.
        default_selection_i (int, optional): Default selection if in debug or no input given. Defaults to 0.

    Returns:
        int: Index of the selected option
    """

    for i, selectable in enumerate(selectables):
        print(f'{i}: {selectable}')

    # ensure we get a valid selection
    while True:
        # dont wanna input when im debugging
        if settings.DEBUG:
            selection = default_selection_i
        else:
            selection = input(f"{query_string} [{default_selection_i}]: ")

        # default
        if selection == '':
            selection = default_selection_i

        try:
            selection = int(selection)
            if selection in range(0, len(selectables)):
                break
            print(f"Chose {selectables[selection]}")
            return selection
        except:
            print(f'ERROR: selection must be an integer from 0 to {len(selectables)-1}')

def main():
    driver = uc.Chrome(use_subprocess=True)

    # -- Login --

    driver.get(settings.DASH_URL)
    # we must login, i didnt get cookies working yet
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

    # get list of active courses
    coursesPane = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.ID, 'courses-active'))).get_attribute('innerHTML'), features='lxml')
    courses = [{'title': str(x.text).strip().split('\n')[1], 'element': x} for x in list(coursesPane.find_all('a', {'class': 'courseitem'}))]

    # display titles to the user
    print('\n\n')
    for i, course in enumerate(courses):
        print(f'{i}: {course["title"]}')

    # ensure we get a valid selection
    selection = getValidSelection([x['title'] for x in courses], 'Select course', 0)
    course = courses[selection]
    print(f'\nSelected {course["title"]}!')

    # -- Course --
    # go to course page
    logger.info('Going to course page..')
    driver.get(str(course['element']['href']))

    # find ONLINE TESTS AND EVALUATION
    activitiesPane = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'ctopics topics bsnewgrid row')]"))).get_attribute('innerHTML'), features='lxml')
    activities = [{'title': str(x.find('h3', {'class': 'sectionname'}).text).strip(), 'element': x} for x in list(activitiesPane.find_all('li', {'class': ['section', 'main']}))]

    for activity in activities:
        if 'online tests and evaluation' in str(activity['element'].text).lower():
            test_activity = activity
            break
    else:
        selection = getValidSelection([x['title'] for x in activities], 'Online Tests and Evaluation not found, please select manually or exit')
        test_activity = activities[selection]

    # expand test panel if not already expanded
    the_toggle = test_activity['element'].find('span', {'class': 'the_toggle'})
    if the_toggle['aria-expanded'] == 'false':
        logger.info('Expanding tests panel..')
        element = driver.find_element(By.ID, the_toggle['id'])
        element.click()

    # get list of tests and test titles from test panel
    tests = [{'title': str(x.find('span', {'class': 'instancename'}).text).strip(), 'element': x} for x in list(test_activity['element'].find('ul', {'class': ['section', 'img-text']}).find_all('li'))]
    
    # okay so NOTE s to pick up on next time, we need to figure out which courses have been completed and which havent, can use the image alt text and look for Passing grade
    logger.info('Done!')
    driver.quit()


if __name__ == '__main__':
    main()
