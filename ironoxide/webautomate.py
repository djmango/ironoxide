import logging
from pathlib import Path
import time
from urllib import parse

import openai
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from thefuzz import process

from ironoxide import settings
from ironoxide.models import Answer, Course, Question, Test

# TODO: id like to add colour to the logging
# setup
HERE = Path(__file__).parent
TIMEOUT = 3  # in seconds
logger = logging.getLogger(__file__)
logger.setLevel(settings.LOGGING_LEVEL_MODULE)
openai.api_key = settings.OPENAI_API_KEY


def populate_tests(course: Course, driver: uc.Chrome):
    """ Populates the tests for this course by searching the activity pane. Assumes driver is on the course page """

    # Find ONLINE TESTS AND EVALUATION
    activitiesPane = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'ctopics topics bsnewgrid row')]"))).get_attribute('innerHTML'), features='lxml')
    activities = [{'title': str(x.find('h3', {'class': 'sectionname'}).text).strip(), 'element': x} for x in list(activitiesPane.find_all('li', {'class': ['section', 'main']}))]

    for activity in activities:
        if 'online tests and evaluation' in str(activity['element'].text).lower():
            test_activity = activity
            break
    else:
        selection = getValidSelection([x['title'] for x in activities], 'Online Tests and Evaluation not found, please select manually or exit')
        test_activity = activities[selection]

    # Expand test panel if not already expanded
    test_panel_toggle = test_activity['element'].find('span', {'class': 'the_toggle'})
    if test_panel_toggle['aria-expanded'] == 'false':
        logger.debug('Expanding tests panel..')
        element = driver.find_element(By.ID, test_panel_toggle['id'])
        element.click()

    # Get list of tests and test titles from test panel
    test_elements = list(test_activity['element'].find('ul', {'class': ['section', 'img-text']}).find_all('li'))

    # Check if any tests are completed. If so, mark them as such
    tests: list[Test] = []
    for test_element in test_elements:
        iu_id = test_element.attrs['id']
        test: Test
        test, created = Test.objects.get_or_create(course=course, iu_id=iu_id)
        test.populate(course, str(test_element.find('span', {'class': 'instancename'}).text).strip(), test_element)

        if created:
            logger.debug(f'Created test {test.title}')
        else:
            logger.debug(f'Found test {test.title}')

        # Ensure we can complete this test
        if test.getElement().find('div', {'class': 'availabilityinfo isrestricted'}) is None and test.getElement().find('span', {'class': 'autocompletion'}) is not None:
            logger.debug(f'{test.title} is completable..')
            test.completable = True
            # then check if it is completed
            if next(test.getElement().find('span', {'class': 'autocompletion'}).children).attrs['alt'][:10] == 'Completed:':
                logger.debug(f'{test.title} is completed!')
                test.completed = True
            else:
                logger.debug(f'{test.title} is not completed..')
        else:
            logger.debug(f'{test.title} is not completable..')

        test.save()
        tests.append(test)
    return tests


def do_test(test: Test, driver: uc.Chrome):
    # wait for load
    test_main_page = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//div[contains(@role, 'main')]"))).get_attribute('innerHTML'), features='lxml')

    # ensure we are in a Highest Grade test and proceed
    if 'Grading method: Highest grade' not in test_main_page.find('div', {'class': 'quizinfo'}).text:
        logger.error(f'Not in a Highest Grade test ({test.title}), unsafe to continue, exiting..')
        driver.quit()

    # proceed into the test
    driver.find_element(By.XPATH, "//button[contains(@type, 'submit')]").click()

    # populate questions
    question_navigation_block = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//div[contains(@class, 'qn_buttons clearfix multipages')]"))).get_attribute('innerHTML'), features='lxml')
    test.url = driver.current_url
    test.save()
    question_elements: list[BeautifulSoup] = list(question_navigation_block.find_all('a'))

    questions: list[Question] = []
    for i, question_element in enumerate(question_elements):
        logger.debug(f'Question {i+1}/{len(question_elements)}')

        question: Question
        question, created = Question.objects.get_or_create(test=test, number=i)
        question.populate(test, question_element)

        if created:
            logger.debug(f'Created question {question.title}')
        else:
            logger.debug(f'Found question {question.title}')

        # populate question text
        while True: # sometimes we get an alert asking if we want to save changes, so close and wait for that
            time.sleep(1)
            try:
                alert = driver.switch_to_alert()
                alert.dismiss()
            except:
                driver.get(question.url)
                break
        question_block = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//div[contains(@class, 'formulation clearfix')]"))).get_attribute('innerHTML'), features='lxml')
        question.text = question_block.find('div', {'class': 'qtext'}).text
        question.save()

        # populate answers
        answer_block = question_block.find('div', {'class': 'answer'})
        answer_elements: list[BeautifulSoup] = list(answer_block.find_all('div', {'class': 'flex-fill ml-1'}))
        answers: list[Answer] = []
        for k, answer_element in enumerate(answer_elements):
            answer: Answer
            answer, created = Answer.objects.get_or_create(question=question, number=k)
            answer.populate(question, answer_element)
            answer.save()

            if created:
                logger.debug(f'Created answer {answer.title}')
            else:
                logger.debug(f'Found answer {answer.title}')

            answers.append(answer)

        # now its time to get the answer from our answering machine
        logger.debug(f'Getting answer for question {i+1}/{len(question_elements)}')

        all_verified = True if all([x.verified for x in answers]) else False
        for answer in answers:
            if answer.correct:
                break
        
        # if we dont have a saved answer then we need to get one
        if not answer.correct:
            response = openai.Answer.create(
                search_model='ada', 
                model='davinci', 
                question=question.text, 
                file=test.course.textbook_id,
                examples_context="In 2017, U.S. life expectancy was 78.6 years.", 
                examples=[["What is human life expectancy in the United States?", "78 years."]], 
                max_rerank=200,
                max_tokens=max([len(x.text) for x in answers])/3, # tokens are usually 3 ish chars
                stop=["\n", "<|endoftext|>"]
            )

            # levenshtein distance to match the openai answer to our answer
            answer, score = process.extractOne(response['answers'][0], [x.text for x in answers])
            # get our object back since we were selecting  by text
            answer = answers[[x.text for x in answers].index(answer)]
            answer.correct = True
        
        # click it!
        answer_i = answers.index(answer)
        answer_sel_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'flex-fill ml-1')]")
        answer_sel_elements[answer_i].click()
        logger.info(f'Selected answer {answer.text}')

        answer.save()
        questions.append(question)

    # cool so now weve answered all the questions, lets submit the test
    test_submit_1 = driver.find_element(By.XPATH, "//input[contains(@class, 'mod_quiz-next-nav btn btn-primary')]")
    test_submit_1.click()


    test_submit_2 = WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn btn-secondary') and text() = 'Submit all and finish']")))
    test_submit_2.click()

    test_submit_3 = WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn btn-primary') and text() = 'Submit all and finish']")))
    test_submit_3.click()
    logger.info('Submitted test!')
    

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
            keys = settings.IU_USER if fieldname == 'username' else settings.IU_PASS
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
            deny_cookies = WebDriverWait(driver, timeout=10).until(ec.presence_of_element_located((By.ID, 'uc-a-deny-banner')))
            deny_cookies.click()
            logger.info('Denied cookies..')
        except Exception as e:
            logger.error(e)
            driver.refresh()
        else:
            break

    # Get list of active courses elements
    coursesPane = BeautifulSoup(WebDriverWait(driver, TIMEOUT).until(ec.presence_of_element_located((By.ID, 'courses-active'))).get_attribute('innerHTML'), features='lxml')
    course_elements = list(coursesPane.find_all('a', {'class': 'courseitem'}))

    # Get or create Course objects
    courses: list[Course] = []
    for course_element in course_elements:
        iu_id = int(parse.parse_qs(parse.urlparse(course_element['href']).query)['id'][0])
        course: Course
        course, created = Course.objects.get_or_create(iu_id=iu_id)
        course.populate(str(course_element.text).strip().split('\n')[1], course_element)
        course.save()

        if created:
            logger.debug(f'Created course {course.title}')
        else:
            logger.debug(f'Found course {course.title}')

        courses.append(course)

    # Ensure we get a valid selection
    selection = getValidSelection(([x.title for x in courses]), 'Select course', 0)
    course = courses[selection]

    # -- Course --
    # Go to course page
    logger.info(f'Navigating to {course.title}..')
    driver.get(str(course.url))

    # get tests
    tests = populate_tests(course, driver)

    # go to the first incomplete test
    for test in tests:
        if test.completable and not test.completed:
            logger.info(f'Going to test {test.title}..')
            driver.get(str(test.getElement().find('a')['href']))
            break

    # -- Test --

    do_test(test, driver)

    logger.info('Done!')
    driver.quit()


if __name__ == '__main__':
    main()
