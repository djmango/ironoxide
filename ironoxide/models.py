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
    title = models.CharField(max_length=255, unique=True)
    iu_id = models.IntegerField(unique=True)

    def populate(self, title: str, element: BeautifulSoup):
        self.title = str(title)
        self.element = str(element)
        self.url = element['href'] if 'href' in element.attrs else None
        return self

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.title}>'


class Test(IU_PageElement):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    iu_id = models.CharField(max_length=64, unique=True)
    completable = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)

    def populate(self, course: Course, title: str, element: BeautifulSoup):
        self.course = course
        self.title = title
        self.element = str(element)
        self.url = element['href'] if 'href' in element.attrs else None
        return self

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.title}>'


class Question(IU_PageElement):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    number = models.IntegerField()
    text = models.TextField()
    answered = models.BooleanField(default=False)

    def populate(self, test: Test, element: BeautifulSoup):
        self.test = test
        self.title = str(self.number)
        self.element = str(element)
        self.url = self.test.url + f'&page={self.number}'
        return self

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.text}>' if self.text and self.text != '' else f'<{self.__class__.__name__}: {self.number}>'


class Answer(IU_PageElement):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    number = models.IntegerField()
    text = models.TextField()
    correct = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)

    def populate(self, question: Question, element: BeautifulSoup):
        self.question = question
        self.title = str(self.number)
        self.element = str(element)
        return self

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.text}>' if self.text and self.text != '' else f'<{self.__class__.__name__}: {self.title}>'
