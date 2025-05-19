class RedisKeys:
    """Single source of truth for all Redis key patterns and source types"""
    
    # Source Types
    SOURCE_NEWS = 'news'
    SOURCE_REPORTS = 'reports' # Used for SEC filings
    SOURCE_TRANSCRIPTS = 'transcripts'
    
    # Key Suffixes
    SUFFIX_RAW = 'raw'
    SUFFIX_PROCESSED = 'processed'
    SUFFIX_FAILED = 'failed'
    SUFFIX_WITHRETURNS = 'withreturns'
    SUFFIX_WITHOUTRETURNS = 'withoutreturns'
    
    # Prefix Types
    PREFIX_LIVE = 'live'
    PREFIX_HIST = 'hist'
    PREFIX_ALL = 'all'
    
    # Queue Names (used consistently across codebase)
    RAW_QUEUE = 'queues:raw'
    PROCESSED_QUEUE = 'queues:processed'
    FAILED_QUEUE = 'queues:failed'
    
    # New suffix for enrichment queue
    ENRICH_QUEUE = f"{SOURCE_REPORTS}:queues:enrich"
    # XBRL_QUEUE = f"{SOURCE_REPORTS}:queues:xbrl"
    XBRL_QUEUE_HEAVY = f"{SOURCE_REPORTS}:queues:xbrl:heavy"
    XBRL_QUEUE_MEDIUM = f"{SOURCE_REPORTS}:queues:xbrl:medium"
    XBRL_QUEUE_LIGHT = f"{SOURCE_REPORTS}:queues:xbrl:light"
    
    
    @staticmethod
    def get_prefixes(source_type: str) -> dict:
        """Get prefixes for live/hist namespaces"""
        return {
            'live': f"{source_type}:{RedisKeys.PREFIX_LIVE}:",
            'hist': f"{source_type}:{RedisKeys.PREFIX_HIST}:"
        }

    @staticmethod
    def get_returns_keys(source_type: str) -> dict:
        """Get returns-related keys"""
        return {
            'pending': f"{source_type}:pending_returns",
            'withreturns': f"{source_type}:{RedisKeys.SUFFIX_WITHRETURNS}",
            'withoutreturns': f"{source_type}:{RedisKeys.SUFFIX_WITHOUTRETURNS}",
            # 'pubsub_channel': f"{source_type}:live:{RedisKeys.SUFFIX_PROCESSED}"
        }
        
    @staticmethod
    def get_key(source_type: str, key_type: str, identifier: str = '', prefix_type: str = None) -> str:
        """Generate standardized Redis key"""
        if prefix_type:
            return f"{source_type}:{prefix_type}:{key_type}:{identifier}".rstrip(':')
        return f"{source_type}:{key_type}:{identifier}".rstrip(':')


    @staticmethod
    def get_pubsub_channel(source_type: str) -> str:
        """Get pubsub channel name for a source"""
        return f"{source_type}:{RedisKeys.PREFIX_LIVE}:{RedisKeys.SUFFIX_PROCESSED}"
    

    # Only used for transcripts
    @staticmethod
    def get_transcript_key_id(symbol: str, conference_datetime) -> str:
        """Create standardized transcript ID from symbol and datetime"""
        # Simple string conversion and replace colons with dots
        dt_str = str(conference_datetime).replace(':', '.')
        return f"{symbol}_{dt_str}"
    
    # Only used for transcripts
    @staticmethod
    def parse_transcript_key_id(key_id: str) -> dict:
        """Parse transcript key ID into symbol and whatever's after the first underscore"""
        # Split at first underscore
        parts = key_id.split('_', 1)
        if len(parts) != 2:
            return {"symbol": key_id, "conference_datetime": None}
            
        symbol = parts[0]
        dt_str = parts[1]
        
        # Replace dots back to colons in case someone needs to parse it
        dt_str_readable = dt_str.replace('.', ':')
        
        return {
            "symbol": symbol,
            "conference_datetime": dt_str_readable
        }


class RedisQueues:
    """Cached queue paths for each source type"""
    _source_queues = {}

    @classmethod
    def get_queues(cls, source_type: str) -> dict:
        """Get queue paths with caching"""
        if source_type not in cls._source_queues:
            cls._source_queues[source_type] = {
                'RAW_QUEUE': f"{source_type}:{RedisKeys.RAW_QUEUE}",
                'PROCESSED_QUEUE': f"{source_type}:{RedisKeys.PROCESSED_QUEUE}",
                'FAILED_QUEUE': f"{source_type}:{RedisKeys.FAILED_QUEUE}"
            }
        return cls._source_queues[source_type]