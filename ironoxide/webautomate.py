import logging
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

class IU_PageElement():
    def __init__(self, title: str, element: BeautifulSoup):
        self.title = str(title)
        self.element = element
        self.url = element['href'] if 'href' in element.attrs else None

class Course(IU_PageElement):
    def __init__(self, title: str, element: BeautifulSoup):
        super().__init__(title, element)
    
    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.title}>'

    # -- Course Subclasses --
    class Test(IU_PageElement):
        def __init__(self, course, title: str, element: BeautifulSoup, completable: bool = False, completed: bool = False):
            super().__init__(title, element)
            self.course: Course = course
            self.id = self.element.attrs['id']
            self.completable = completable
            self.completed = completed
            self.questions: list[Course.Test.Question]
        
        def __repr__(self) -> str:
            return f'<{self.__class__.__name__} {self.title}>'

        class Question(IU_PageElement):
            def __init__(self, test, title: str, element: BeautifulSoup):
                super().__init__(title, element)
                self.test: Course.Test = test
                self.text: str
                self.answered = False
                self.answers: list[Course.Test.Question.Answer]

            def __repr__(self) -> str:
                    return str(self.text)

            class Answer(IU_PageElement):
                def __init__(self, question, title: str, element: BeautifulSoup):
                    super().__init__(title, element)
                    self.question: Course.Test.Question = question
                    self.text = element.text
                    self.correct = False
                    self.verified = False

                def __repr__(self) -> str:
                    return f'<{self.__class__.__name__} {self.text}>'

        def do_test(self, driver: uc.Chrome):
            # wait for load
            test_main_page = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//div[contains(@role, 'main')]"))).get_attribute('innerHTML'), features='lxml')

            # ensure we are in a Highest Grade test and proceed
            if  'Grading method: Highest grade' not in test_main_page.find('div', {'class': 'quizinfo'}).text:
                logger.error(f'Not in a Highest Grade test ({self.title}), unsafe to continue, exiting..')
                driver.quit()
            
            # proceed into the test
            driver.find_element(By.XPATH, "//button[contains(@type, 'submit')]").click()

            # populate questions
            question_navigation_block = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//div[contains(@class, 'qn_buttons clearfix multipages')]"))).get_attribute('innerHTML'), features='lxml')
            self.questions = [Course.Test.Question(self, i, x) for i, x in enumerate(list(question_navigation_block.find_all('a')))]

            # make sure all the question urls are fully qualified
            for i, question in enumerate(self.questions):
                if not question.url.startswith('https://'):
                    question.url = self.questions[i-1].url.rsplit('&')[0] + f'&page={i}'

            # go to each question page and populate answers
            for i, question in enumerate(self.questions):
                logger.info(f'Question {i+1}/{len(self.questions)}')
                driver.get(question.url)
                question_block = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//div[contains(@class, 'formulation clearfix')]"))).get_attribute('innerHTML'), features='lxml')
                question.text = question_block.find('div', {'class': 'qtext'}).text
                answer_block = question_block.find('div', {'class': 'answer'})
                self.answers = [Course.Test.Question.Answer(question, i, x) for i, x in enumerate(list(answer_block.find_all('div')))]

                # now its time to get the answer from our answering machine
                logger.info(f'Getting answer for question {i+1}/{len(self.questions)}')

            # NOTE for next time to pick up on, so we now need to populate the questions and answers, and create a method to select them. after that we need to store the selected answers in a csv file. or somethign. data storage is two sessions down the line.
            # one more thing, id like to add colour to the logging

    # -- Course Methods --
    def populate_tests(self, driver: uc.Chrome):
        """ Populates the tests for this course by searching the activity pane. Assumes driver is on the course page """
        
        # Find ONLINE TESTS AND EVALUATION
        activitiesPane = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'ctopics topics bsnewgrid row')]"))).get_attribute('innerHTML'), features='lxml')
        activities = [IU_PageElement(str(x.find('h3', {'class': 'sectionname'}).text).strip(), x) for x in list(activitiesPane.find_all('li', {'class': ['section', 'main']}))]

        for activity in activities:
            if 'online tests and evaluation' in str(activity.element.text).lower():
                test_activity = activity
                break
        else:
            selection = getValidSelection([x.title for x in activities], 'Online Tests and Evaluation not found, please select manually or exit')
            test_activity = activities[selection]

        # Expand test panel if not already expanded
        the_toggle = test_activity.element.find('span', {'class': 'the_toggle'})
        if the_toggle['aria-expanded'] == 'false':
            logger.info('Expanding tests panel..')
            element = driver.find_element(By.ID, the_toggle['id'])
            element.click()

        # Get list of tests and test titles from test panel
        self.tests = [Course.Test(self, str(x.find('span', {'class': 'instancename'}).text).strip(), x) for x in list(test_activity.element.find('ul', {'class': ['section', 'img-text']}).find_all('li'))]
        
        # Check if any tests are completed. If so, mark them as such
        for test in self.tests:
            # ensure we can complete this test
            if test.element.find('div', {'class': 'availabilityinfo isrestricted'}) is None and test.element.find('span', {'class': 'autocompletion'}) is not None:
                logger.info(f'{test.title} is completable..')
                test.completable = True
                # then check if it is completed
                completion = next(test.element.find('span', {'class': 'autocompletion'}).children).attrs['alt']
                if next(test.element.find('span', {'class': 'autocompletion'}).children).attrs['alt'][:10] == 'Completed:':
                    logger.info(f'{test.title} is completed!')
                    test.completed = True
                else:
                    logger.info(f'{test.title} is not completed..')
            else:
                logger.info(f'{test.title} is not completable..')

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
    # We must login, i didnt get cookies working yet
    if driver.current_url != settings.DASH_URL:
        # Wait for page load
        logger.info('Logging in..')
        try:
            element = WebDriverWait(driver, 3).until(ec.presence_of_element_located((By.ID, 'username')))
        except TimeoutException:
            logger.error("Loading took too much time!")
        # Fill in user & pass fields
        for fieldname in ['username', 'password']:  # fill in user and password
            keys = settings.USERNAME if fieldname == 'username' else settings.PASSWORD
            field = driver.find_element(By.ID, fieldname)
            field.clear()
            field.send_keys(keys)
        # hit login
        driver.find_element(By.ID, 'loginbtn').click()
        logger.info('Logged in!')

    # -- Dashboard --
    # Ensure dashboard load - this commonly fails
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

    # Get list of active courses
    coursesPane = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.ID, 'courses-active'))).get_attribute('innerHTML'), features='lxml')
    courses = [Course(str(x.text).strip().split('\n')[1], x) for x in list(coursesPane.find_all('a', {'class': 'courseitem'}))]

    # Ensure we get a valid selection
    selection = getValidSelection(([x.title for x in courses]), 'Select course', 0)
    course = courses[selection]

    # -- Course --
    # Go to course page
    logger.info(f'Navigating to {course.title}..')
    driver.get(str(course.url))
    
    # get tests
    course.populate_tests(driver)

    # go to the first incomplete test
    for test in course.tests:
        if test.completable and not test.completed:
            logger.info(f'Going to test {test.title}..')
            driver.get(str(test.element.find('a')['href']))
            break

    # -- Test --

    test.do_test(driver)
    
    logger.info('Done!')
    driver.quit()


if __name__ == '__main__':
    main()
