"""Minimal EventTrader feature flags""" 
# Don't change these here - pass Flags in command line -live or -historical
ENABLE_HISTORICAL_DATA = True
ENABLE_LIVE_DATA = True

# SEC API Form Type Constants

VALID_FORM_TYPES = ['8-K', '8-K/A']
FORM_TYPES_REQUIRING_XML = ['10-K', '10-Q', '10-K/A', '10-Q/A']
FORM_TYPES_REQUIRING_SECTIONS = ['8-K', '8-K/A'] 


# SEC API Form Type Constants
# VALID_FORM_TYPES = ['8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A', 
#                     'SCHEDULE 13D', 'SCHEDULE 13D/A', 'SC TO-I', '425', 'SC 14D9', '6-K']

# FORM_TYPES_REQUIRING_XML = ['10-K', '10-Q', '10-K/A', '10-Q/A']
# FORM_TYPES_REQUIRING_SECTIONS = ['8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A'] 



# ✅ Earnings & Major Business Updates → 8-K, 10-K, 10-Q
# ✅ Activist Investor Stakes & Hostile Takeovers → SCHEDULE 13D, 13D/A
# ✅ Buybacks & Tender Offers → SC TO-I
# ✅ M&A & Takeover Battles → 425, SC 14D9

# TO BE REMOVED - JUST FOR DEBUGGING
# VALID_FORM_TYPES = [
#     # Existing types
#     '4', '8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A', '6-K', 
#     '13F-HR', '424B3', 'D', 'CERT', '485BXT', 'D/A', 'SCHEDULE 13G', 
#     'N-CSRS', '13F-NT', 'S-1/A', 'SCHEDULE 13G/A', 'S-8','10-D/A','10-D',
#     # Previously added types
#     'SC TO-T/A', 'DFAN14A', 'POS AM', 'S-8 POS', 'TA-2', '15-12G',
#     '425', '24F-2NT', 'TA-1/A', 'SC TO-C', '20-F', 'F-1', 'F-1/A', 
#     'S-1', 'F-3', 'F-3/A', 'F-4', 'F-4/A', 'S-3', 'S-3/A', 'S-4', 
#     'S-4/A', '40-F', '6-K/A', 'POS AM', '485BPOS', 'N-CSR',
#     # New types from latest logs
#     'SCHEDULE 13D', 'SCHEDULE 13D/A',  # Schedule 13D forms
#     'SC 13D', 'SC 13D/A',             # Alternative Schedule 13D notation
#     'SC TO-I', 'SC TO-I/A',           # Tender offer forms
#     'SC 14D9', 'SC 14D9/A',           # Solicitation/recommendation forms
#     'DEF 14A', 'DEFA14A',             # Proxy statement forms
#     'DEFM14A', 'DEFR14A',             # More proxy forms
#     '40-17G', '40-17G/A',             # Investment company forms
#     'N-1A', 'N-1A/A',                 # Registration forms
#     'N-2', 'N-2/A',                   # More registration forms
#     'N-14', 'N-14/A',                 # Investment company forms
#     'POS EX',                         # Post-effective amendments
#     'S-3ASR', 'S-8 POS',              # Automatic shelf registration
#     'CORRESP', 'UPLOAD',              # Correspondence and uploads
#     'ATS-N', 'ATS-N/MA'               # Alternative trading system forms
# ]

# XBRL Processing Feature Flag
# When set to True, enables XBRL report processing which extracts detailed financial data
# When set to False, skips XBRL processing entirely and does not initialize related resources
# This can significantly reduce memory usage and CPU load when XBRL data is not needed
ENABLE_XBRL_PROCESSING = True

# XBRL Thread Pool Configuration
# Number of worker threads for XBRL processing (only used when ENABLE_XBRL_PROCESSING is True)
# Higher values increase parallelism but consume more system resources
# Recommended range: 2-12 based on available CPU cores
# This setting does not interfere with event_trader.sh or other scripts
XBRL_WORKER_THREADS = 8

# When True, reject news items that have more than one symbol
REJECT_MULTIPLE_SYMBOLS = True

# When True, generate embeddings using OpenAI for News nodes
# This creates vector embeddings for semantic search capabilities
ENABLE_NEWS_EMBEDDINGS = True

# OpenAI embedding model and dimensions
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_EMBEDDING_DIMENSIONS = 3072
NEWS_VECTOR_INDEX_NAME = "news_vector_index"

# When True, generate embeddings using OpenAI for QAExchange nodes
# This creates vector embeddings for semantic search capabilities
ENABLE_QAEXCHANGE_EMBEDDINGS = True
QAEXCHANGE_VECTOR_INDEX_NAME = "qaexchange_vector_idx"



# When True, check ChromaDB for existing embeddings before generating new ones
# This saves API calls during development but can be disabled in production for performance
USE_CHROMADB_CACHING = True

# Configuration for ChromaDB persistence
import os
CHROMADB_PERSIST_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_db"))

# --- Path Configuration ---
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
SYMBOLS_CSV_PATH = os.path.join(CONFIG_DIR, "final_symbols.csv")

# --- End Path Configuration ---


# When equal to or greater than this number, use OpenAI Parallel Embeddings (with rate limiting) for news items instead of Neo4j Internal function 
OPENAI_EMBED_CUTOFF = 10

# Maximum sleep time (in seconds) for transcript processing thread
# Higher values reduce CPU usage but may slightly delay processing new notifications
MAX_TRANSCRIPT_SLEEP_SECONDS = 300  # 5 minutes

