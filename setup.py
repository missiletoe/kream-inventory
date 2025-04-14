from setuptools import setup, find_packages

setup(
    name="kream-inventory",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.7.0",
        "selenium>=4.15.2",
        "requests>=2.31.0",
        "chromedriver-autoinstaller>=0.6.4",
        "webdriver-manager>=4.0.1",
    ],
) 