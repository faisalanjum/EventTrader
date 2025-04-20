import time
import json
from utils.log_config import get_logger

logger = get_logger("stats_tracker")

class StatsTracker:
    """Minimal tracker for data pipeline stats using Redis"""
    
    def __init__(self, redis_client, source_type):
        self.redis = redis_client
        self.source_type = source_type
        self.stats_key_prefix = f"admin:operations:{source_type}"
        self.current_operation = None
        self.init_operation("default")
    
    def init_operation(self, operation_id):
        """Initialize a new operation with its own counters"""
        self.current_operation = operation_id
        self.stats_key = f"{self.stats_key_prefix}:{operation_id}"
        self._ensure_stats_exist()
    
    def _ensure_stats_exist(self):
        """Initialize counters if they don't exist"""
        if not self.redis.client.exists(self.stats_key):
            stats = {
                "fetched": 0,
                "valid": 0, 
                "processed": 0,
                "withreturns": 0,
                "withoutreturns": 0,
                "pending_returns": 0,
                "neo4j": 0,
                "failed": 0,
                "status": "idle",
                "start_time": time.time(),
                "last_update": time.time()
            }
            self.redis.client.set(self.stats_key, json.dumps(stats))
    
    def increment(self, counter, count=1):
        """Increment a specific counter atomically"""
        try:
            stats_json = self.redis.client.get(self.stats_key)
            if not stats_json:
                self._ensure_stats_exist()
                stats_json = self.redis.client.get(self.stats_key)
            
            stats = json.loads(stats_json)
            stats[counter] += count
            stats["last_update"] = time.time()
            self.redis.client.set(self.stats_key, json.dumps(stats))
            return True
        except Exception as e:
            logger.error(f"Error incrementing {counter}: {e}")
            return False
    
    def set_status(self, status):
        """Update the current processing status"""
        try:
            stats_json = self.redis.client.get(self.stats_key)
            if not stats_json:
                self._ensure_stats_exist()
                stats_json = self.redis.client.get(self.stats_key)
                
            stats = json.loads(stats_json)
            stats["status"] = status
            stats["last_update"] = time.time()
            self.redis.client.set(self.stats_key, json.dumps(stats))
            return True
        except Exception as e:
            logger.error(f"Error setting status: {e}")
            return False
    
    def get_stats(self):
        """Get current statistics"""
        try:
            stats_json = self.redis.client.get(self.stats_key)
            return json.loads(stats_json) if stats_json else {}
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def reset(self):
        """Reset all counters but keep the start time"""
        try:
            stats = self.get_stats()
            start_time = stats.get("start_time", time.time())
            
            new_stats = {
                "fetched": 0,
                "valid": 0, 
                "processed": 0,
                "withreturns": 0,
                "withoutreturns": 0,
                "pending_returns": 0,
                "neo4j": 0,
                "failed": 0,
                "status": "reset",
                "start_time": start_time,
                "last_update": time.time()
            }
            self.redis.client.set(self.stats_key, json.dumps(new_stats))
            return True
        except Exception as e:
            logger.error(f"Error resetting stats: {e}")
            return False
            
    def list_operations(self):
        """List all operations for this source type"""
        try:
            keys = self.redis.client.keys(f"{self.stats_key_prefix}:*")
            operations = [k.split(":")[-1] for k in keys]
            return operations
        except Exception as e:
            logger.error(f"Error listing operations: {e}")
            return [] 