"""
Singleton connection manager for Neo4j.
CRITICAL: This module must be imported before any Neo4j operations.
"""
from neograph.Neo4jManager import Neo4jManager
from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
import os

# Single global instance - initialized at module load time
_manager = None

def get_manager():
    """Get the singleton Neo4jManager instance"""
    global _manager
    if _manager is None:
        # Use environment variables or defaults
        uri = os.getenv("NEO4J_URI", NEO4J_URI)
        username = os.getenv("NEO4J_USERNAME", NEO4J_USERNAME) 
        password = os.getenv("NEO4J_PASSWORD", NEO4J_PASSWORD)
        
        _manager = Neo4jManager(uri=uri, username=username, password=password)
        
    return _manager

def reset():
    """Close and reset the singleton (for testing)"""
    global _manager
    if _manager is not None:
        try:
            _manager.close()
        except:
            pass
        _manager = None

def release_resources():
    """
    Release resources in the singleton Neo4jManager without closing it.
    This helps manage file handles without disrupting the singleton pattern.
    """
    global _manager
    if _manager is not None:
        # Only force garbage collection when file descriptor usage is high
        try:
            # Check how many file descriptors we're using
            import resource
            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            
            # Count current open file descriptors (more efficient than getting list)
            try:
                # Try using /proc/self/fd if available (Linux)
                if os.path.exists('/proc/self/fd'):
                    current_fds = len(os.listdir('/proc/self/fd'))
                else:
                    # Fallback for macOS
                    import subprocess
                    result = subprocess.run(['lsof', '-p', str(os.getpid())], 
                                           capture_output=True, text=True)
                    current_fds = len(result.stdout.splitlines()) - 1  # Subtract header
                
                # Only run GC if we're using more than 70% of our file descriptor limit
                if current_fds > (soft_limit * 0.7):
                    import gc
                    gc.collect()
                    
            except (FileNotFoundError, PermissionError, subprocess.SubprocessError):
                # If we can't check, be conservative and run GC
                import gc
                gc.collect()
                
        except ImportError:
            # If resource module not available, fall back to conservative approach
            import gc
            gc.collect()