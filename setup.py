from setuptools import setup, find_packages

setup(
    name="eventtrader",
    version="0.1.0",
    packages=find_packages(include=[
        'utils',
        'benzinga',
        'secReports',
        'transcripts',
        'eventtrader',
        'neograph',
        'openai_local',
        'redisDB',
        'eventReturns',
        'scripts',
        'XBRL',
        'config',
        
    ]),
    package_dir={'': '.'},
    install_requires=[
        'pandas',
        'exchange_calendars',
        'python-dotenv',
        'pydantic',  
        'redis',     
    ],
)