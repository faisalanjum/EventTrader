from pydantic import ValidationError
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
import json
import logging
import os
from dataclasses import dataclass
from collections import Counter
from benzinga.bz_news_schemas import BzRestAPINews, BzWebSocketNews, UnifiedNews

@dataclass
class ErrorStats:
    """Track error statistics"""
    validation_errors: Counter  # Counts by validation type
    skipped_items: Counter     # Track why items were skipped
    json_errors: int
    connection_errors: int
    unexpected_errors: int
    
    def __str__(self) -> str:
        return (
            f"\nError Statistics:"
            f"\nJSON Errors: {self.json_errors}"
            f"\n\nValidation Errors:"
            f"  - no_stocks: {self.validation_errors['missing_symbols']}"
            f"  - no_id: {self.validation_errors['missing_id']}"
            f"  - invalid_created: {self.validation_errors['invalid_created']}"
            f"  - invalid_updated: {self.validation_errors['invalid_updated']}"
            f"  - other: {self.validation_errors['other']}"
            f"\n\nSkipped Items:"
            f"  - No id: {self.skipped_items['no_id']}"
            f"  - No symbols: {self.skipped_items['no_symbols']}"
            f"  - No content: {self.skipped_items['no_content']}"
            f"\n\nUnexpected Errors: {self.unexpected_errors}"
        )

class NewsErrorHandler:
    """Handles and tracks different types of errors in news processing"""
    
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
        
        self.reset_stats()  # Initialize stats
        self.debug = False  # Add debug flag

    def reset_stats(self):
        """Reset all error statistics"""
        self.stats = ErrorStats(
            validation_errors=Counter(),
            skipped_items=Counter(),
            json_errors=0,
            connection_errors=0,
            unexpected_errors=0
        )

    def handle_validation_error(self, error: Exception, data: Dict[str, Any]) -> None:
        """Handle validation errors"""
        error_type = self._classify_validation_error(error)
        self.stats.validation_errors[error_type] += 1
        
        # Always print validation errors regardless of raw mode
        print("\nSkipped News Item:")
        print(f"ID: {data.get('id', 'unknown')}")
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Error: {str(error)}")
        print("="*80)
        
        # Track skipped items by type
        if "id" in str(error):
            self.stats.skipped_items['no_id'] += 1
        elif "stocks" in str(error) or "symbols" in str(error):
            self.stats.skipped_items['no_symbols'] += 1
        elif "content" in str(error):
            self.stats.skipped_items['no_content'] += 1
        
        # Track silently
        self.handle_news_item(data.get('id', 'unknown'), "skipped", {"reason": error_type})
    
    def handle_json_error(self, error: Exception, raw_data: str) -> None:
        """Single JSON error handler"""
        self.stats.json_errors += 1
        print(f"JSON Parse Error: {str(error)}")
        print(f"Raw Data Preview: {raw_data[:100]}...")
    
    def handle_connection_error(self, error: Exception) -> None:
        """Single connection error handler"""
        self.stats.connection_errors += 1
        print(f"Connection Error: {str(error)}")
    
    def handle_unexpected_error(self, error: Exception) -> None:
        """Single unexpected error handler"""
        self.stats.unexpected_errors += 1
        print(f"Unexpected Error: {str(error)}")
    
    def _classify_validation_error(self, error: Exception) -> str:
        """Classify validation error type"""
        error_str = str(error)
        if "stocks" in error_str or "symbols" in str(error):
            return "missing_symbols"
        elif "id" in error_str:
            return "missing_id"
        elif "created" in error_str:
            return "invalid_created"
        elif "updated" in error_str:
            return "invalid_updated"
        elif "image" in error_str:
            return "invalid_image"
        return "other"
    
    def handle_processing_debug(self, stage: str, item_id: str, details: Dict[str, Any]) -> None:
        """Handle debug logging for processing stages"""
        if self.debug:
            print(f"\nProcessing stage: {stage}")
            print(f"Item ID: {item_id}")
            print(f"Details: {json.dumps(details, indent=2)}")
    
    def print_summary(self, total_received: int, total_processed: int) -> None:
        """Print processing summary with error stats"""
        print("\nProcessing Summary:")
        print(f"Total items received: {total_received}")
        print(f"Items processed successfully: {total_processed}")
        print(f"Success rate: {(total_processed/total_received)*100:.1f}%")
        print(self.get_summary())
    
    def get_summary(self) -> str:
        """Get human-readable error summary"""
        total_errors = (
            sum(self.stats.validation_errors.values()) +
            self.stats.json_errors +
            self.stats.connection_errors +
            self.stats.unexpected_errors
        )
        
        return str(self.stats)  # Just use the stats string

    def handle_news_item(self, item_id: str, status: str, details: Dict[str, Any]) -> None:
        """Track news item status silently"""
        if self.debug:
            print(f"Details: {json.dumps(details, indent=2)}")

    def process_news_item(self, raw_item: Dict[str, Any], raw: bool = False) -> Optional[Union[BzRestAPINews, UnifiedNews]]:
        """Centralized processing with error handling for both REST and WebSocket"""
        try:
            # First validate the source format
            if 'data' in raw_item:  # WebSocket format
                news = BzWebSocketNews(**raw_item)
                # WebSocket validation
                if not news.data.content.id:
                    raise ValueError("News must have an ID")
                if not news.data.content.securities:
                    raise ValueError("News must have securities")

            else:  # REST API format
                news = BzRestAPINews(**raw_item)
                # REST API validation
                if not news.id:
                    raise ValueError("News must have an ID")
                if not news.stocks:
                    raise ValueError("News must have stocks")

            if raw:
                return news
            else:
                try:
                    return news.to_unified()
                except ValidationError as ve:
                    self.handle_validation_error(ve, raw_item)
                    return None

        except (ValidationError, ValueError) as ve:
            self.handle_validation_error(ve, raw_item)
            return None