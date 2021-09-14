from setuptools import setup, find_packages
from serpens.settings import APPNAME, VERSION

setup(
    name="serpens",
    version="1.12.0",
    description="A set of Python utilities, recipes and snippets",
    author="Everaldo Canuto",
    author_email="everaldo.canuto@gmail.com",
    license="MIT",
    platforms="any",
    packages=find_packages(),
    install_requires=[],
)
