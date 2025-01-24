from pydantic import ValidationError
from typing import Optional, Dict, Any
from datetime import datetime
import json
import logging
import os

# Need to add WebSocket Connection Error?


class BenzingaNewsError:
    def __init__(self, error_type: str, details: str, raw_data: Optional[Any] = None):
        self.timestamp = datetime.now()
        self.error_type = error_type
        self.details = details
        self.raw_data = raw_data

class NewsErrorHandler:
    def __init__(self):
        # Setup logging
        self.logger = logging.getLogger('benzinga_news')
        self.logger.setLevel(logging.ERROR)
        
        # Get the directory where bz_news_errors.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create log file path in the same directory
        log_file_path = os.path.join(current_dir, 'benzinga_news_errors.log')
        
        # Add file handler with the correct path
        fh = logging.FileHandler(log_file_path)
        
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(fh)
        
        # Error statistics
        self.error_counts: Dict[str, int] = {
            "json_errors": 0,
            "validation_errors": 0,
            "unexpected_errors": 0
        }

    def handle_error(self, e: Exception, raw_message: str) -> BenzingaNewsError:
        """Handle different types of errors and log them"""
        if isinstance(e, json.JSONDecodeError):
            error = BenzingaNewsError(
                "JSON_DECODE_ERROR",
                str(e),
                raw_message
            )
            self.error_counts["json_errors"] += 1
            
        elif isinstance(e, ValidationError):
            error = BenzingaNewsError(
                "VALIDATION_ERROR",
                str(e),
                raw_message
            )
            self.error_counts["validation_errors"] += 1
            
        else:
            error = BenzingaNewsError(
                f"UNEXPECTED_{type(e).__name__}",
                str(e),
                raw_message
            )
            self.error_counts["unexpected_errors"] += 1

        # Log the error
        self.logger.error(
            f"Error Type: {error.error_type}\n"
            f"Details: {error.details}\n"
            f"Raw Data: {error.raw_data}\n"
        )
        
        return error

    def get_error_stats(self) -> Dict[str, int]:
        """Get current error statistics"""
        return self.error_counts