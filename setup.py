from setuptools import setup, find_packages

setup(
    name="eventtrader",
    version="0.1.0",
    packages=find_packages(include=[
        'utils',
        'benzinga',
        'SEC_API_Files',
        'IBKR',
        'News',
        'dataBento',
        'earningscall',
        'eventtrader',
        'sec_api',
    ]),
    package_dir={'': '.'},
    install_requires=[
        'pandas',
        'exchange_calendars',
        'python-dotenv',
        'pydantic',  # Added
        'redis',     # Added
    ],
)