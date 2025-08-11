import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env but don't override existing environment variables (K8s values)
load_dotenv(override=False)  # Prevents overriding K8s values

# API Keys as simple variables
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
SEC_API_KEY = os.getenv('SEC_API_KEY')
OPENFIGI_API_KEY = os.getenv('OPENFIGI_API_KEY')
BENZINGANEWS_API_KEY = os.getenv('BENZINGANEWS_API_KEY')
BENZINGACONFERENCE_API_KEY = os.getenv('BENZINGACONFERENCE_API_KEY')
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
VOYAGE_API_KEY = os.getenv('VOYAGE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
LANGEXTRACT_API_KEY = os.getenv('LANGEXTRACT_API_KEY', os.getenv('GEMINI_API_KEY'))
GROK_API_KEY = os.getenv('GROK_API_KEY')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2')
LANGSMITH_TRACING = os.getenv('LANGSMITH_TRACING')
LANGCHAIN_PROJECT = os.getenv('LANGCHAIN_PROJECT')
LANGCHAIN_CALLBACKS_BACKGROUND = os.getenv('LANGCHAIN_CALLBACKS_BACKGROUND')
EARNINGS_CALL_API_KEY = os.getenv('EARNINGS_CALL_API_KEY')

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))





