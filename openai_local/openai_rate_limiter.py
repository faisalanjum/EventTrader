import time
import threading
import logging

logger = logging.getLogger(__name__)

class OpenAIRateLimiter:
    """
    A minimalistic centralized rate limiter for OpenAI API calls.
    Implements a single global instance to track API usage across different processes.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OpenAIRateLimiter, cls).__new__(cls)
                cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Default tier limits
        self.rpm_limit = 3000  # 3,000 requests per minute for embeddings
        self.tpm_limit = 250000  # 250,000 tokens per minute for embeddings
        
        # Request tracking
        self.requests = []
        self.token_counts = []  # Track token counts with timestamps
        self._request_lock = threading.Lock()
    
    def check_and_wait(self, token_count=0):
        """Thread-safe check if we're within rate limits, wait if needed"""
        with self._request_lock:
            now = time.time()
            
            # Clean up old requests (older than 60 seconds)
            self.requests = [t for t in self.requests if now - t < 60]
            self.token_counts = [t for t in self.token_counts if now - t[0] < 60]
            
            # If we're over the RPM limit, wait
            if len(self.requests) >= self.rpm_limit:
                wait_time = 60 - (now - self.requests[0]) + 0.1
                logger.info(f"Rate limit approaching, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # If we're over the TPM limit, wait
            total_tokens = sum(t[1] for t in self.token_counts) + token_count
            if total_tokens >= self.tpm_limit:
                wait_time = 60 - (now - self.token_counts[0][0]) + 0.1
                logger.info(f"Token limit approaching ({total_tokens}), waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # Record this request
            self.requests.append(time.time())
            if token_count > 0:
                self.token_counts.append((time.time(), token_count))
    
    def record_request(self, token_count=0):
        """Record a request after it's completed (useful for manual tracking)"""
        with self._request_lock:
            self.requests.append(time.time())
            if token_count > 0:
                self.token_counts.append((time.time(), token_count))
    
    @property
    def current_rpm(self):
        """Get the current requests per minute rate"""
        with self._request_lock:
            now = time.time()
            recent_requests = [t for t in self.requests if now - t < 60]
            return len(recent_requests)
    
    @property
    def current_tpm(self):
        """Get the current tokens per minute rate"""
        with self._request_lock:
            now = time.time()
            recent_tokens = [t for t in self.token_counts if now - t[0] < 60]
            return sum(t[1] for t in recent_tokens)

# Single global instance to use across the application
rate_limiter = OpenAIRateLimiter() 