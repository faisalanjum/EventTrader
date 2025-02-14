from setuptools import setup, find_packages

setup(
    name="eventtrader",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pandas',
        'exchange_calendars',
        'python-dotenv',
    ],
)