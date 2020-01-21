from setuptools import setup, find_packages
from os import path

HERE = path.abspath(path.dirname(__file__))

with open(path.join(HERE, 'README.md')) as f:
    long_description = f.read()

setup(
    name='recleagueparser',
    version='0.0.1',
    description='Recreational league sports schedule/stat webpage scrapers',
    long_description=long_description,
    url='https://github.com/gmfrasca/recleagueparser',
    author='Giulio Frasca',
    packages=find_packages(),
    python_requires='>=3.6, <4',
    install_requires=[
        'bs4',
        'parsedatetime',
        'requests',
        'google-api-python-client',
    ]
)
