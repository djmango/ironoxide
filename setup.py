from setuptools import setup

setup(
    name='ironoxide',
    version='0.0.1',
    author='djmango',
    author_email='sulaiman.ghori@outlook.com',
    description='A Question-answer automation solution for Moodle',
    long_description='file: README.md',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU GPLv3',
        'Operating System :: OS Independent'
    ],
    keywords='question answer',
    url='https://github.com/djmango/ironoxide',
    packages=['ironoxide'],
    install_requires=[
        'markdown',
    ],
    include_package_data=True,
    zip_safe=False,
    scripts=['ironoxide-cli']
)
