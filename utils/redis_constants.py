class RedisKeys:
    """Single source of truth for all Redis key patterns and source types"""
    
    # Source Types
    # SOURCE_NEWS = 'news:benzinga'
    SOURCE_NEWS = 'news'
    SOURCE_REPORTS = 'reports'
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
    
    # Queue Names (used consistently across codebase)
    RAW_QUEUE = 'queues:raw'
    PROCESSED_QUEUE = 'queues:processed'
    FAILED_QUEUE = 'queues:failed'
    
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