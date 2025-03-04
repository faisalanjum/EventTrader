import logging
import os
import threading
import time
import fcntl
import atexit
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = "logs"
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

def setup_logging(log_level=logging.INFO, name=None):
    """
    Set up centralized logging configuration.
    This ensures all logs from all modules go to the same file.
    Will create exactly one log file per run, even across multiple processes.
    
    Args:
        log_level: Logging level (default: logging.INFO)
        name: Optional prefix for the log file
    
    Returns:
        str: Path to the log file
    """
    global _is_logging_initialized, _log_file_path, _lock_file
    
    # Local thread safety first
    with _setup_lock:
        # If already initialized in this process, return existing file
        if _is_logging_initialized and _log_file_path:
            return _log_file_path
        
        # Create a lock file to coordinate between processes
        lock_file_path = os.path.join(log_dir, ".logging_lock")
        
        try:
            # Acquire process-level lock
            _lock_file = open(lock_file_path, 'w')
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # We now have exclusive access across all processes
            
            # Check if a log file has already been started in the last few seconds
            recent_logs = _find_recent_logs(name, max_age_seconds=10)  # Look for logs created in the last 10 seconds
            if recent_logs:
                _log_file_path = recent_logs[0]
                _lock_file.seek(0)
                _lock_file.truncate()
                _lock_file.write(_log_file_path)
                _lock_file.flush()
                _configure_logger(_log_file_path, log_level)
                _is_logging_initialized = True
                return _log_file_path
            
            # Create a new log file with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = f"{name}_" if name else "eventtrader_"
            log_file = os.path.join(log_dir, f"{prefix}{timestamp}.log")
            _log_file_path = log_file
            
            # Write the log path to the lock file so other processes can find it
            _lock_file.seek(0)
            _lock_file.truncate()
            _lock_file.write(_log_file_path)
            _lock_file.flush()
            os.fsync(_lock_file.fileno())  # Force write to disk to ensure visibility to other processes
            
            # Configure the logger
            _configure_logger(_log_file_path, log_level)
            
            # Log the setup using a properly named logger
            setup_logger = logging.getLogger('log_config')
            setup_logger.info(f"Logging initialized. Logs will be written to: {_log_file_path}")
            
            _is_logging_initialized = True
            return _log_file_path
            
        except IOError:
            # Another process has the lock, try to use its log file
            for retry in range(3):  # Try 3 times with increasing wait
                try:
                    # Gradually increase wait time between retries
                    time.sleep(0.1 * (retry + 1))
                    
                    # Try to read from the lock file
                    with open(lock_file_path, 'r') as f:
                        path = f.read().strip()
                        if path and os.path.exists(path):
                            _log_file_path = path
                            _configure_logger(_log_file_path, log_level)
                            _is_logging_initialized = True
                            return _log_file_path
                except Exception as e:
                    # Just retry silently
                    pass
                
            # Could not read from lock file after retries, find the most recent log
            for age in [5, 15, 30]:  # Try multiple time windows
                recent_logs = _find_recent_logs(name, max_age_seconds=age)
                if recent_logs:
                    _log_file_path = recent_logs[0]
                    _configure_logger(_log_file_path, log_level)
                    _is_logging_initialized = True
                    return _log_file_path
                
            # Last resort: create a unique log file - should happen extremely rarely
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = f"{name}_" if name else "eventtrader_"
            log_file = os.path.join(log_dir, f"{prefix}{timestamp}_fallback.log")
            _log_file_path = log_file
            
            # Try one last time to get the lock - maybe it's been released
            try:
                # If lock file exists but is empty, maybe we can grab it
                _lock_file = open(lock_file_path, 'w')
                fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # We got the lock! Write our fallback path so others use it
                _lock_file.write(_log_file_path)
                _lock_file.flush()
                os.fsync(_lock_file.fileno())
            except:
                # Still can't get lock, just use the fallback
                pass
                
            _configure_logger(_log_file_path, log_level)
            _is_logging_initialized = True
            return _log_file_path

def _find_recent_logs(name=None, max_age_seconds=5):
    """Find log files created in the last few seconds"""
    now = time.time()
    prefix = f"{name}_" if name else "eventtrader_"
    recent_logs = []
    
    try:
        for file in os.listdir(log_dir):
            if file.startswith(prefix) and file.endswith('.log') and not file.endswith('_fallback.log'):
                # Prioritize non-fallback logs
                full_path = os.path.join(log_dir, file)
                if now - os.path.getctime(full_path) < max_age_seconds:
                    recent_logs.append(full_path)
        
        # If we found no non-fallback logs, try fallback logs too
        if not recent_logs:
            for file in os.listdir(log_dir):
                if file.startswith(prefix) and file.endswith('_fallback.log'):
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