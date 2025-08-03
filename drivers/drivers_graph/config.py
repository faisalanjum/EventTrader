"""Configuration for drivers_graph - loads environment variables following EventMarketDB pattern"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Find the EventMarketDB root directory (two levels up)
ROOT_DIR = Path(__file__).parent.parent.parent
ENV_FILE = ROOT_DIR / '.env'

# Load .env but don't override existing environment variables (K8s values)
load_dotenv(ENV_FILE, override=False)

# Neo4j Connection
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Redis Connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
LANGSMITH_API_KEY = os.getenv('LANGSMITH_API_KEY')
LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2')

# Optional API Keys that might be used
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
VOYAGE_API_KEY = os.getenv('VOYAGE_API_KEY')

# Logging configuration
import sys
sys.path.append(str(ROOT_DIR))