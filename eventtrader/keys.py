import os
from dotenv import load_dotenv
from pathlib import Path

# Automatically find .env file in project root
# env_path = Path(__file__).parent / '.env'

env_path = Path(__file__).parent.parent / '.env'  # Go up two levels from keys.py to reach root
print(f"Loading .env from: {env_path}")  # Debug print
load_dotenv(env_path)

# API Keys as simple variables
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
SEC_API_KEY = os.getenv('SEC_API_KEY')
OPENFIGI_API_KEY = os.getenv('OPENFIGI_API_KEY')
BENZINGANEWS_API_KEY = os.getenv('BENZINGANEWS_API_KEY')
BENZINGACONFERENCE_API_KEY = os.getenv('BENZINGACONFERENCE_API_KEY')
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')