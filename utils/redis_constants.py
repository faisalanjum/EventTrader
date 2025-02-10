
class RedisQueues:
    """Class to hold queue names for each source type"""
    _source_queues = {}

    @classmethod
    def get_queues(cls, source_type: str):
        if source_type not in cls._source_queues:
            queue_paths = RedisKeys.get_queues(source_type)
            cls._source_queues[source_type] = {
                'RAW_QUEUE': queue_paths['raw'],
                'PROCESSED_QUEUE': queue_paths['processed'],
                'FAILED_QUEUE': queue_paths['failed']
            }
        return cls._source_queues[source_type]



class RedisKeys:
    """Single source of truth for all Redis key patterns and source types"""
    
    # Source Types
    SOURCE_NEWS = 'news:benzinga'  # Keep for reference
    # SOURCE_NEWS = 'news'  # Keep for reference
    SOURCE_REPORTS = 'reports'
    SOURCE_TRANSCRIPTS = 'transcripts'
    
    # Key Type Suffixes
    SUFFIX_RAW = 'raw'
    SUFFIX_PROCESSED = 'processed'
    SUFFIX_FAILED = 'failed'
    SUFFIX_WITHRETURNS = 'withreturns'
    SUFFIX_WITHOUTRETURNS = 'withoutreturns'
    
    # Prefix Types
    PREFIX_LIVE = 'live'
    PREFIX_HIST = 'hist'
    
    @staticmethod
    def get_queues(source_type: str) -> dict:
        """Get shared queue paths for a source type"""
        return {
            'raw': f"{source_type}:queues:{RedisKeys.SUFFIX_RAW}",
            'processed': f"{source_type}:queues:{RedisKeys.SUFFIX_PROCESSED}",
            'failed': f"{source_type}:queues:{RedisKeys.SUFFIX_FAILED}"
        }
    
    @staticmethod
    def get_prefixes(source_type: str) -> dict:
        """Get prefixes for live/hist namespaces"""
        return {
            'live': f"{source_type}:{RedisKeys.PREFIX_LIVE}:",
            'hist': f"{source_type}:{RedisKeys.PREFIX_HIST}:"
        }

    @staticmethod
    def get_returns_keys(source_type: str, prefix_type: str = PREFIX_LIVE) -> dict:
        """Get returns-related keys with proper prefix"""
        return {
            'pending': f"{source_type}:pending_returns",  # Shared at source level
            'withreturns': f"{source_type}:{RedisKeys.SUFFIX_WITHRETURNS}",  # No prefix_type!
            'withoutreturns': f"{source_type}:{RedisKeys.SUFFIX_WITHOUTRETURNS}",  # No prefix_type!
            'pubsub_channel': f"{source_type}:live:{RedisKeys.SUFFIX_PROCESSED}"  # Always live!
        }
        
    @staticmethod
    def get_key(source_type: str, key_type: str, identifier: str = '', prefix_type: str = None) -> str:
        """Generate standardized Redis key
        
        Args:
            source_type: e.g., 'news:benzinga'
            key_type: e.g., 'raw', 'processed'
            identifier: e.g., '{id}.{timestamp}'
            prefix_type: Optional 'live' or 'hist' prefix
        """
        if prefix_type:
            return f"{source_type}:{prefix_type}:{key_type}:{identifier}".rstrip(':')
        return f"{source_type}:{key_type}:{identifier}".rstrip(':')