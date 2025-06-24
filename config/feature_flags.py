"""Minimal EventTrader feature flags""" 
# Don't change these here - pass Flags in command line -live or -historical - defaults are meant to be overridden via command-line arguments, not changed directly in the file
ENABLE_HISTORICAL_DATA = True
ENABLE_LIVE_DATA = True

# --- ADDED: Global Logging Configuration ---
GLOBAL_LOG_LEVEL = "INFO"  # Options: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
# --- END ADDED ---

# SEC API Form Type Constants

# VALID_FORM_TYPES = ['8-K', '8-K/A']
# FORM_TYPES_REQUIRING_XML = ['10-K', '10-Q', '10-K/A', '10-Q/A']
# FORM_TYPES_REQUIRING_SECTIONS = ['8-K', '8-K/A'] 


# SEC API Form Type Constants
VALID_FORM_TYPES = ['8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A', 
                    'SCHEDULE 13D', 'SCHEDULE 13D/A', 'SC TO-I', '425', 'SC 14D9', '6-K']

FORM_TYPES_REQUIRING_XML = ['10-K', '10-Q', '10-K/A', '10-Q/A']
FORM_TYPES_REQUIRING_SECTIONS = ['8-K', '10-K', '10-Q', '8-K/A', '10-K/A', '10-Q/A'] 



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


# --- XBRL Semaphore Implementation ---
# XBRL Thread Pool Configuration
# Number of worker threads for XBRL processing (only used when ENABLE_XBRL_PROCESSING is True)
# Higher values increase parallelism but consume more system resources
# Recommended range: 2-12 based on available CPU cores
# This setting does not interfere with event_trader.sh or other scripts
XBRL_WORKER_THREADS = 10 # Changed from 8

# Maximum number of filings that may be processed **simultaneously** (semaphore limit).
# Keep lower than or equal to XBRL_WORKER_THREADS – it throttles memory-intensive Arelle work
# without affecting the size of the thread-pool queue.
XBRL_MAX_CONCURRENT_FILINGS = 7  # (old hard-coded value was 4)


# --- Kubernetes XBRL Worker Implementation ---
# When set to True, enables Kubernetes XBRL worker implementation and stops local XBRL worker
# When set to False, skips Kubernetes XBRL worker implementation and uses local XBRL worker
ENABLE_KUBERNETES_XBRL = True



# Local on-disk cache for SEC-API XBRL-to-JSON responses. Set to None to disable.
import os, tempfile as _tmp
XBRL_JSON_CACHE_DIR = os.path.join(_tmp.gettempdir(), "xbrl_json_cache")

# Toggle bulk UNWIND node merges (used only in XBRL path for now)
ENABLE_BULK_NODE_MERGE_XBRL = True

# When True, reject news items that have more than one symbol
REJECT_MULTIPLE_SYMBOLS = True

# When True, generate embeddings using OpenAI for News nodes
# This creates vector embeddings for semantic search capabilities
ENABLE_NEWS_EMBEDDINGS = True

# OpenAI embedding model and dimensions
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_EMBEDDING_DIMENSIONS = 3072
NEWS_VECTOR_INDEX_NAME = "news_vector_index"

# OpenAI Embedding Character Limit for text-embedding-3-large is ~8192
# Maximum characters for text to be embedded (roughly 8000 tokens, using 4 chars per token estimation)
MAX_EMBEDDING_CHARS = 28000

# When True, generate embeddings using OpenAI for QAExchange nodes
# This creates vector embeddings for semantic search capabilities
### ISSUE is in QA Embeddng function, we rely on ENABLE_NEWS_EMBEDDINGS to be True - not this - correct it
ENABLE_QAEXCHANGE_EMBEDDINGS = True


QAEXCHANGE_VECTOR_INDEX_NAME = "qaexchange_vector_idx"

# --- ADDED: Model for QA Content Classification ---
# Model to use for classifying short QA exchanges as filler/substantial
QA_CLASSIFICATION_MODEL = "gpt-4.1-mini"
# --- END ADDED --- 

# --- ADDED: Word count threshold for QA substantial check ---
QA_SUBSTANTIAL_WORD_COUNT = 18
# --- END ADDED ---

# --- ADDED: Model for Speaker Classification ---
SPEAKER_CLASSIFICATION_MODEL = "gpt-4o"
# --- END ADDED ---

# When True, check ChromaDB for existing embeddings before generating new ones
USE_CHROMADB_CACHING = False

# Configuration for ChromaDB persistence
import os
_default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_db"))

# new line ↓
CHROMADB_PERSIST_DIRECTORY = os.getenv("CHROMA_DB_DIR", _default_dir)
# CHROMADB_PERSIST_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_db"))

# ChromaDB connection pool configuration
CHROMADB_MAX_WORKERS = int(os.getenv("CHROMADB_MAX_WORKERS", "4"))  # Thread pool size for ChromaDB operations
CHROMADB_TIMEOUT_SECONDS = int(os.getenv("CHROMADB_TIMEOUT_SECONDS", "30"))  # Timeout for ChromaDB operations

# --- Path Configuration ---
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
SYMBOLS_CSV_PATH = os.path.join(CONFIG_DIR, "final_symbols.csv")

# --- End Path Configuration ---

# --- Neo4j Driver Configuration ---
# Ideally : NEO4J_MAX_CONNECTION_LIFETIME ≥ CHUNK_MAX_WAIT_SECONDS
NEO4J_MAX_CONNECTION_LIFETIME = 240  # Max connection lifetime in seconds (e.g., 7200 for 2 hour)
NEO4J_KEEP_ALIVE = True               # Enable TCP keep-alive for connections
NEO4J_MAX_CONNECTION_POOL_SIZE = 250  # Maximum number of connections in the pool
# --- End Neo4j Driver Configuration ---

# When equal to or greater than this number, use OpenAI Parallel Embeddings (with rate limiting) for news items instead of Neo4j Internal function 
OPENAI_EMBED_CUTOFF = 10

# Batch sizes for embedding generation
# Number of news nodes to process in each embedding batch
NEWS_EMBEDDING_BATCH_SIZE = 50

# Number of QAExchange nodes to process in each embedding batch
# Smaller batch size due to potentially larger content in QA exchanges
QAEXCHANGE_EMBEDDING_BATCH_SIZE = 50

# Maximum sleep time (in seconds) for transcript processing thread
# Higher values reduce CPU usage but may slightly delay processing new notifications
MAX_TRANSCRIPT_SLEEP_SECONDS = 300  # 5 minutes

#  If Transcript Not Found, reschedule it after this many seconds
TRANSCRIPT_RESCHEDULE_INTERVAL = 300


# --- Historical Chunked Processing Configuration ---
HISTORICAL_CHUNK_DAYS = 5  # Default number of days per historical processing chunk
HISTORICAL_STABILITY_WAIT_SECONDS = 60 # Default seconds to wait for queue stability
# Number of monitoring cycles to wait before forcing withreturns reconciliation
# After this many checks, if items remain in withreturns namespace, force reconciliation
WITHRETURNS_MAX_RETRIES = 3
# Interval (in seconds) between monitoring checks during chunked historical processing
# Controls how frequently the system checks Redis for completion during each chunk
CHUNK_MONITOR_INTERVAL = 60


# Maximum time (in seconds) to wait for a single historical chunk to complete
CHUNK_MAX_WAIT_SECONDS = 7200 # Default: 2 hours


# Max time for processing all sections of one filing (300s)
# - Streams results via imap_unordered for immediate processing
# - Terminates pool at deadline to prevent ReportProcessor stalling
# - Long enough for reasonable processing, short enough for safety
SECTION_BATCH_EXTRACTION_TIMEOUT = 450  # seconds

# Max time for a single sec-api.get_section() call (90s)
# - Runs in ThreadPoolExecutor inside each worker (now also in _extract_section_content directly)
# - Terminates thread on timeout, marks section as failed
# - Allows sec-api retries while preventing hung HTTP requests
EXTRACTOR_CALL_TIMEOUT = 90  # seconds

# Number of threads for parallel section extraction within a single report (10-K/10-Q)
# when processed by ReportProcessor._extract_sections using ThreadPoolExecutor.
THREADS_PER_SECTION_EXTRACTION = 4 # Default number of threads

# --- End Historical Chunked Processing Configuration ---
# --- PubSub Processing Configuration ---
# Interval (in seconds) between reconciliation checks during PubSub processing
# Controls how frequently the system runs reconcile_missing_items in live mode
PUBSUB_RECONCILIATION_INTERVAL = 3600  # Default: Run once per hour
# --- End PubSub Processing Configuration ---


# TOBE REMOVED - NOT USED ANYWHERE - Threshold for BaseProcessor reconnect on consecutive timeouts
# TIMEOUT_RECONNECT_THRESHOLD = 2 # Reconnect after 10 * 60s intervals

# Add a new feature flag for report enrichment workers
ENABLE_REPORT_ENRICHER = True

# TTL for processed report keys set by the enrichment worker
PROCESSED_ITEM_KEY_TTL = 2 * 24 * 3600 # Default TTL for processed report keys (in seconds), e.g., 2 days

# --- Pending Set Configuration ---
# When True, items are automatically removed from the pending set once they reach the
# `inserted_into_neo4j_at` stage. Set to False if you prefer to keep all items in
# the pending set for post-hoc analysis.
REMOVE_FROM_PENDING_SET = True  # Default behaviour – safe for production
# --- End Pending Set Configuration ---

# Number of threads for parallel SEC historical filings ingestion (raw queue population)
SEC_HISTORICAL_INGESTION_THREADS = 4  # Used in sec_restAPI.py ThreadPoolExecutor