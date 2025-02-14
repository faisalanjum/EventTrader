import os
from dotenv import load_dotenv
from pathlib import Path

# Automatically find .env file in project root
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# API Keys as simple variables
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
SEC_API_KEY = os.getenv('SEC_API_KEY')
OPENFIGI_API_KEY = os.getenv('OPENFIGI_API_KEY')
BENZINGANEWS_API_KEY = os.getenv('BENZINGANEWS_API_KEY')
BENZINGACONFERENCE_API_KEY = os.getenv('BENZINGACONFERENCE_API_KEY')