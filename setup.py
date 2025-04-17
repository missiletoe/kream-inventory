from setuptools import setup, find_packages

setup(
    name="kream-inventory",
    version="0.1",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[
        "PyQt6>=6.7.0",
        "selenium>=4.15.2",
        "requests>=2.31.0",
        "chromedriver-autoinstaller>=0.6.4",
        "webdriver-manager>=4.0.1",
    ],
    entry_points={
        'console_scripts': [
            'kream_inventory = kream_inventory:main',
        ],
    },
)