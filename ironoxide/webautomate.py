import json
import logging
import pickle
from pathlib import Path

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
# https://stackoverflow.com/questions/533048/how-to-log-source-file-name-and-line-number-in-python
logging.basicConfig(level=settings.LOGGING_LEVEL, format=('%(asctime)s %(levelname)s %(module)s | %(message)s'))

creds = json.load(open(HERE.parent/'data'/'creds.json'))

class IU_PageElement():
    def __init__(self, title: str, element: BeautifulSoup):
        self.title = title
        self.element = element

class IU_Test(IU_PageElement):
    def __init__(self, title: str, element: BeautifulSoup, completable: bool = False, completed: bool = False):
        super().__init__(title, element)
        self.completable = completable
        self.completed = completed

def getValidSelection(selectables: list[str], query_string: str, default_selection_i: int = 0) -> int:
    """_summary_

    Args:
        selectables (list[str]): List of strings to be chosen from.
        query_string (str): What to ask the user in the input prompt.
        default_selection_i (int, optional): Default selection if in debug or no input given. Defaults to 0.

    Returns:
        int: Index of the selected option
    """

    # display titles to the user
    print('\n\n')
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
                print(f"Selected {selectables[selection]}!")
                return selection
        except Exception as e:
            print(e)
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

    # ensure we get a valid selection
    selection = getValidSelection(([x['title'] for x in courses]), 'Select course', 0)
    course = courses[selection]

    # -- Course --
    # go to course page
    logger.info('Going to course page..')
    driver.get(str(course['element']['href']))

    # find ONLINE TESTS AND EVALUATION
    activitiesPane = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'ctopics topics bsnewgrid row')]"))).get_attribute('innerHTML'), features='lxml')
    activities = [IU_PageElement(str(x.find('h3', {'class': 'sectionname'}).text).strip(), x) for x in list(activitiesPane.find_all('li', {'class': ['section', 'main']}))]

    for activity in activities:
        if 'online tests and evaluation' in str(activity.element.text).lower():
            test_activity = activity
            break
    else:
        selection = getValidSelection([x.title for x in activities], 'Online Tests and Evaluation not found, please select manually or exit')
        test_activity = activities[selection]

    # expand test panel if not already expanded
    the_toggle = test_activity.element.find('span', {'class': 'the_toggle'})
    if the_toggle['aria-expanded'] == 'false':
        logger.info('Expanding tests panel..')
        element = driver.find_element(By.ID, the_toggle['id'])
        element.click()

    # get list of tests and test titles from test panel
    tests = [IU_Test(str(x.find('span', {'class': 'instancename'}).text).strip(), x) for x in list(test_activity.element.find('ul', {'class': ['section', 'img-text']}).find_all('li'))]
    
    # check if any tests are completed. this could be done inline but that becomes hard to read.
    for test in tests:
        # ensure we can complete this test
        if test.element.find('div', {'class': 'availabilityinfo isrestricted'}) is None and test.element.find('span', {'class': 'autocompletion'}) is not None:
            logger.info(f'{test.title} is completable..')
            test.completable = True
            # then check if it is completed
            if test.element.find('span', {'class': 'autocompletion'}).text[:10] == 'Completed:':
                logger.info(f'{test.title} is completed!')
                test.completed = True
            else:
                logger.info(f'{test.title} is not completed..')
        else:
            logger.info(f'{test.title} is not completable..')


    # go to the first incomplete test
    for test in tests:
        if test.completable and not test.completed:
            logger.info(f'Going to test {test.title}..')
            driver.get(str(test.element.find('a')['href']))
            break

    # -- Test --

    # ensure we are in a Highest Grade test and proceed
    if 'Grading method: Highest grade' not in test.element.find('div', {'role': 'main'}).text:
        logger.error(f'Not in a Highest Grade test ({test.title}), unsafe to continue, exiting..')
        driver.quit()
    
    # proceed into the test
    driver.find_element(By.XPATH, "//button[contains(@type, 'submit')]").click()

    logger.info('Done!')
    driver.quit()


if __name__ == '__main__':
    main()
