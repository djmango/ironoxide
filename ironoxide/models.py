from bs4 import BeautifulSoup
from django.db import models

# https://www.webforefront.com/django/modelsoutsidemodels.html


class IU_PageElement(models.Model):
    title = models.CharField(max_length=255)
    element = models.TextField()
    url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def getElement(self) -> BeautifulSoup:
        return BeautifulSoup(self.element, 'lxml')

    class Meta:
        abstract = True


class Course(IU_PageElement):

    @classmethod
    def create(cls, title: str, element: BeautifulSoup):
        course = cls(title=str(title), element=str(element))
        course.url = element['href'] if 'href' in element.attrs else None
        return course

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.title}>'


class Test(IU_PageElement):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    iu_id = models.CharField(max_length=64)
    completable = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)

    @classmethod
    def create(cls, course: Course, title: str, element: BeautifulSoup, completable: bool = False, completed: bool = False):
        test = cls(course=course, title=str(title), element=str(element), completable=completable, completed=completed)
        test.url = element['href'] if 'href' in element.attrs else None
        test.iu_id = element.attrs['id']
        return test

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.title}>'


class Question(IU_PageElement):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    text = models.TextField()
    answered = models.BooleanField(default=False)

    @classmethod
    def create(cls, test: Test, title: str, element: BeautifulSoup, text: str = '', answered: bool = False):
        question = cls(test=test, title=str(title), element=str(element), text=text, answered=answered)
        question.url = element['href'] if 'href' in element.attrs else None
        return question

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.text}>' if self.text and self.text != '' else f'<{self.__class__.__name__}: {self.title}>'


class Answer(IU_PageElement):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.TextField()
    correct = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)

    @classmethod
    def create(cls, question: Question, title: str, element: BeautifulSoup, text: str = '', correct: bool = False, verified: bool = False):
        answer = cls(question=question, title=str(title), element=str(element), text=text, correct=correct, verified=verified)
        return answer

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.text}>' if self.text and self.text != '' else f'<{self.__class__.__name__}: {self.title}>'
