import threading
from polygon.rest import RESTClient
import requests
import urllib3
import logging
import time

# Configure logging level for connection pools
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

class PolygonManager:
    _instance = None
    _lock = threading.Lock()
    _request_lock = threading.RLock()  # Lock for rate limiting
    _last_request_time = 0
    _min_request_interval = 0.1  # 100ms between requests
    
    @classmethod
    def get_instance(cls, api_key=None):
        with cls._lock:
            if cls._instance is None:
                if api_key is None:
                    from eventtrader.keys import POLYGON_API_KEY
                    api_key = POLYGON_API_KEY
                cls._instance = PolygonManager(api_key)
            return cls._instance
    
    def __init__(self, api_key):
        self.api_key = api_key
        
        # Create a properly configured session specific to Polygon API
        self.session = requests.Session()
        
        # Configure adapter with optimized settings for Polygon connections
        self.adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=100,
            max_retries=5,
            pool_block=True          # Critical change: block when pool is exhausted
        )
        
        # Only mount this adapter for Polygon API domain
        self.session.mount('https://api.polygon.io', self.adapter)
        
        # Create REST client for Polygon API
        self._rest_client = RESTClient(api_key=self.api_key)
        
        # Shared semaphore for all instances - extremely limited
        self.http_semaphore = threading.BoundedSemaphore(5)  # Extreme throttling
    
    @property
    def rest_client(self):
        """
        Proxy property that rate-limits access to the underlying REST client.
        This throttles ALL calls to any Polygon REST client method.
        """
        return self._RestClientProxy(self)
    
    class _RestClientProxy:
        """Proxy class to throttle all REST client calls"""
        def __init__(self, manager):
            self._manager = manager
            self._rest_client = manager._rest_client
        
        def __getattr__(self, name):
            original_method = getattr(self._rest_client, name)
            
            def throttled_method(*args, **kwargs):
                # Acquire semaphore with timeout
                acquired = False
                try:
                    acquired = self._manager.http_semaphore.acquire(timeout=10)
                    
                    # Apply rate limiting
                    with self._manager._request_lock:
                        current_time = time.time()
                        elapsed = current_time - self._manager._last_request_time
                        if elapsed < self._manager._min_request_interval:
                            sleep_time = self._manager._min_request_interval - elapsed
                            time.sleep(sleep_time)
                        
                        # Execute the original method
                        result = original_method(*args, **kwargs)
                        
                        # Update last request time
                        self._manager._last_request_time = time.time()
                        
                        return result
                        
                finally:
                    if acquired:
                        self._manager.http_semaphore.release()
            
            # Return the throttled version of the method
            return throttled_method 