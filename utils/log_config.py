import logging
import os
import threading
import time
import fcntl
import atexit
from datetime import datetime

# Create logs directory if it doesn't exist
# Use absolute path to avoid issues when running from different directories
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Global variables to track logging state
_is_logging_initialized = False
_log_file_path = None
_setup_lock = threading.RLock()  # Re-entrant lock for thread safety
_lock_file = None  # File handle for process-level locking

def _release_lock():
    """Release the file lock when the program exits"""
    global _lock_file
    if _lock_file:
        try:
            fcntl.flock(_lock_file, fcntl.LOCK_UN)
            _lock_file.close()
        except:
            pass

# Register the lock release function to run at exit
atexit.register(_release_lock)

def setup_logging(log_level=logging.INFO, name=None, force_path=None):
    """
    Set up centralized logging configuration.
    This ensures all logs from all modules go to the same file.
    Will create exactly one log file per run, even across multiple processes.
    
    Args:
        log_level: Logging level (default: logging.INFO)
        name: Optional prefix for the log file (used if force_path is None)
        force_path: Optional specific path to use for the log file
    
    Returns:
        str: Path to the log file
    """
    global _is_logging_initialized, _log_file_path, _lock_file
    
    # Local thread safety first
    with _setup_lock:
        # If already initialized in this process, return existing file
        if _is_logging_initialized and _log_file_path:
            # If a forced path was given and matches, it's fine. 
            # If a different forced path is given now, it's ambiguous, but we return the existing one.
            # If no forced path now, but was initialized before (maybe with forced), still return existing.
            return _log_file_path 
        
        # Create a lock file to coordinate between processes
        lock_file_path = os.path.join(log_dir, ".logging_lock")
        
        try:
            # Acquire process-level lock
            _lock_file = open(lock_file_path, 'w')
            # Use LOCK_NB for non-blocking lock acquisition attempt
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB) 
            
            # --- We now have exclusive access across all processes --- 
            
            log_file_to_use = None
            if force_path:
                # Use the provided path directly
                log_file_to_use = force_path
                # Ensure the directory exists if forced path is used
                os.makedirs(os.path.dirname(log_file_to_use), exist_ok=True)
            else:
                # Original logic: Check for recent logs or create new timestamped one
                recent_logs = _find_recent_logs(name, max_age_seconds=10)  
                if recent_logs:
                    log_file_to_use = recent_logs[0]
                else:
                    # Create a new log file with daily timestamp and hostname
                    timestamp = datetime.now().strftime('%Y%m%d')
                    # In Kubernetes, try to get the actual node name from NODE_NAME env var
                    # Falls back to os.uname().nodename if not in Kubernetes
                    hostname = os.environ.get('NODE_NAME', os.uname().nodename)
                    prefix = f"{name}_" if name else "eventtrader_"
                    log_file_to_use = os.path.join(log_dir, f"{prefix}{timestamp}_{hostname}.log")

            _log_file_path = log_file_to_use
            
            # Write the determined log path to the lock file so other processes can find it
            _lock_file.seek(0)
            _lock_file.truncate()
            _lock_file.write(_log_file_path)
            _lock_file.flush()
            os.fsync(_lock_file.fileno())  # Force write to disk
            
            # Configure the logger (only the process holding the lock does this)
            _configure_logger(_log_file_path, log_level)
            
            # Log the setup
            setup_logger = logging.getLogger('log_config')
            setup_logger.info(f"Logging initialized by process {os.getpid()}. Logs will be written to: {_log_file_path}")
            
            _is_logging_initialized = True
            # Keep lock until configuration is fully done, then release implicitly by exiting `try`
            # Lock will also be released by atexit handler if needed.
            return _log_file_path
            
        except (IOError, BlockingIOError): # Catch BlockingIOError for LOCK_NB
            # Another process has the lock, or we couldn't acquire it immediately.
            
            # If force_path is provided, use it directly without consulting lock file
            # This is needed for chunked historical processing where each chunk needs its own log file
            if force_path:
                _log_file_path = force_path
                # Ensure the directory exists
                os.makedirs(os.path.dirname(force_path), exist_ok=True)
                _configure_logger(_log_file_path, log_level)
                _is_logging_initialized = True
                temp_logger = logging.getLogger('log_config')
                temp_logger.info(f"Process {os.getpid()} using forced path {force_path} (bypassing lock file for chunked processing)")
                return _log_file_path
            
            # Try to read the path set by the process holding the lock.
            for retry in range(10):  # Increased retries for Kubernetes pod startup scenarios
                try:
                    time.sleep(0.1 * (retry + 1)) # Progressive backoff: 0.1s, 0.2s, 0.3s...
                    
                    # Try reading from the lock file (non-exclusive read is fine)
                    with open(lock_file_path, 'r') as f_read:
                        # Use non-blocking shared lock for reading if possible, otherwise just read
                        try:
                            fcntl.flock(f_read, fcntl.LOCK_SH | fcntl.LOCK_NB)
                            path = f_read.read().strip()
                            fcntl.flock(f_read, fcntl.LOCK_UN) # Release read lock
                        except (IOError, BlockingIOError):
                             # If shared lock fails, just try reading
                             f_read.seek(0)
                             path = f_read.read().strip()

                        if path:
                            # Check if the path exists or if it's a stale lock from a previous run
                            if os.path.exists(path):
                                # If we were given a forced path, ideally it matches.
                                # If it doesn't match, log a warning but use the path from the lock file,
                                # as that's where the handlers are configured.
                                if force_path and path != force_path:
                                    temp_logger = logging.getLogger('log_config')
                                    temp_logger.warning(f"Process {os.getpid()} requested log path {force_path} but another process initialized logging to {path}. Using {path}.")
                                
                                _log_file_path = path
                                # Ensure logger is configured even if this process didn't hold the EX lock
                                # Re-calling _configure_logger is safe as it removes old handlers.
                                _configure_logger(_log_file_path, log_level) 
                                _is_logging_initialized = True
                                return _log_file_path
                            else:
                                # Path in lock file doesn't exist - it's stale
                                # Continue to next retry or fallback
                                if retry == 9:  # Log only on last retry
                                    temp_logger = logging.getLogger('log_config')
                                    temp_logger.warning(f"Lock file contains non-existent path: {path}")
                except Exception as e:
                    # Log potential errors during retry read attempt
                    # But avoid flooding logs if lock file is just empty temporarily
                    if retry == 9: # Log only on last retry attempt
                         temp_logger = logging.getLogger('log_config')
                         temp_logger.warning(f"Could not read log path from lock file during retry {retry+1}: {e}")
                    pass # Continue retry loop
                
            # Fallback: Could not read from lock file after retries. 
            # This case is less critical now, as the primary use of --log-file (chunked) 
            # relies on force_path. This handles simultaneous starts of non-chunked runs.
            # Find most recent log as a reasonable guess.
            recent_logs = _find_recent_logs(name, max_age_seconds=30) # Wider window for Kubernetes pod starts
            if recent_logs:
                _log_file_path = recent_logs[0]
                temp_logger = logging.getLogger('log_config')
                temp_logger.warning(f"Could not get definitive log path from lock file, falling back to most recent log: {_log_file_path}")
            else:
                # Absolute last resort: Create a unique fallback file (should be very rare)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                pid = os.getpid()
                hostname = os.environ.get('NODE_NAME', os.uname().nodename)
                prefix = f"{name}_" if name else "eventtrader_"
                _log_file_path = os.path.join(log_dir, f"{prefix}{timestamp}_{hostname}_fallback_{pid}.log")
                temp_logger = logging.getLogger('log_config')
                temp_logger.error(f"Could not determine log path via lock or recent files. Creating unique fallback: {_log_file_path}")
            
            _configure_logger(_log_file_path, log_level)
            _is_logging_initialized = True
            return _log_file_path
        finally:
            # Ensure lock is released if this process held it
            if _lock_file:
                try:
                    # Check if we actually hold the lock before unlocking
                    # This might require storing the lock status or just trying unlock
                    fcntl.flock(_lock_file, fcntl.LOCK_UN)
                    _lock_file.close()
                    _lock_file = None # Reset file handle
                except Exception:
                     # If unlock fails (e.g., wasn't locked by us), ignore.
                     # Also close if open but not locked.
                     if _lock_file and not _lock_file.closed:
                          _lock_file.close()
                     _lock_file = None

def _find_recent_logs(name=None, max_age_seconds=5):
    """Find log files created in the last few seconds"""
    now = time.time()
    prefix = f"{name}_" if name else "eventtrader_"
    recent_logs = []
    
    # In Kubernetes, we need to match based on node name, not pod name
    node_name = os.environ.get('NODE_NAME', os.uname().nodename)
    
    try:
        for file in os.listdir(log_dir):
            if file.startswith(prefix) and file.endswith('.log') and not file.endswith('_fallback.log'):
                # Check if this log file is for our node (when in Kubernetes)
                # Log files have format: prefix_YYYYMMDD_nodename.log
                if f"_{node_name}.log" in file:
                    full_path = os.path.join(log_dir, file)
                    if now - os.path.getctime(full_path) < max_age_seconds:
                        recent_logs.append(full_path)
        
        # If we found no non-fallback logs, try fallback logs too
        if not recent_logs:
            for file in os.listdir(log_dir):
                if file.startswith(prefix) and '_fallback' in file and file.endswith('.log'):
                    # Check if this fallback log is for our node
                    if f"_{node_name}_fallback" in file:
                        full_path = os.path.join(log_dir, file)
                        if now - os.path.getctime(full_path) < max_age_seconds:
                            recent_logs.append(full_path)
    except:
        # If directory listing fails, return empty list
        return []
    
    return sorted(recent_logs, key=os.path.getctime, reverse=True)

def _configure_logger(log_path, log_level):
    """Configure the root logger with handlers"""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers to prevent duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create file handler for logging to file
    file_handler = logging.FileHandler(log_path)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Create console handler for logging to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(file_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def get_logger(name, level=logging.INFO):
    """
    Get a logger with the specified name and level.
    
    Args:
        name: Name for the logger, typically __name__
        level: Logging level for this specific logger (default: logging.INFO)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Ensure setup_logging has been called - thread-safely
    if not _is_logging_initialized:
        setup_logging()
    
    # Get or create logger for this module
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Ensure the logger doesn't just use 'root' as name
    if name == '__main__' or not name:
        # If called from main script, give it a more descriptive name
        try:
            import inspect
            frame = inspect.currentframe()
            caller_module = frame.f_back.f_globals.get('__name__', 'main_script')
            if caller_module != '__main__':
                logger = logging.getLogger(caller_module)
            else:
                # Last resort - use file name
                caller_file = inspect.getframeinfo(frame.f_back).filename
                module_name = os.path.basename(caller_file).replace('.py', '')
                logger = logging.getLogger(module_name)
        except:
            logger = logging.getLogger('main_script')
    
    return logger 