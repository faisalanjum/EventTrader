from pydantic import ValidationError
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
import json
import logging
import os
from dataclasses import dataclass, field
from collections import Counter
from benzinga.bz_news_schemas import BzRestAPINews, BzWebSocketNews, UnifiedNews
import requests
import traceback

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
            f"  - invalid_timestamp_format: {self.validation_errors['invalid_timestamp_format']}"
            f"  - missing_timestamp: {self.validation_errors['missing_timestamp']}"
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
        # Use standard logger
        self.logger = logging.getLogger(__name__)
        
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

    def print_skipped_news(self, data: Dict[str, Any], error: Exception) -> None:
        BODY_PREVIEW_LENGTH = 50
        """Print detailed info about skipped news item, handling both WebSocket and REST formats"""
        print("\nSkipped News Item:")
        
        # Handle nested WebSocket format vs flat REST format
        content = data.get('data', {}).get('content', {}) if 'data' in data else data
        
        # Basic fields (both formats)
        print(f"ID: {content.get('id') or data.get('id', 'N/A')}")
        print(f"Title: {content.get('title') or data.get('title', 'N/A')}")
        
        # Handle different author formats (list vs single)
        ws_authors = content.get('authors', [])
        rest_author = data.get('author')
        if ws_authors:
            print(f"Authors: {', '.join(ws_authors)}")
        elif rest_author:
            print(f"Author: {rest_author}")
        else:
            print("Author(s): N/A")
        
        # Handle different date field names
        created = content.get('created_at') or data.get('created', 'N/A')
        updated = content.get('updated_at') or data.get('updated', 'N/A')
        print(f"Created: {created}")
        print(f"Updated: {updated}")
        print(f"URL: {content.get('url') or data.get('url', 'N/A')}")
        
        # Handle different stock/security formats
        securities = content.get('securities', [])
        stocks = data.get('stocks', [])
        if securities:  # WebSocket format
            symbols = [sec.get('symbol', 'N/A') for sec in securities]
            print(f"Securities: {', '.join(symbols)}")
        elif stocks:    # REST format
            names = [stock.get('name', 'N/A') for stock in stocks]
            print(f"Stocks: {', '.join(names)}")
        else:
            print("Stocks: N/A")
        
        # Handle different channel formats (string list vs object list)
        ws_channels = content.get('channels', [])
        rest_channels = data.get('channels', [])
        if isinstance(rest_channels and rest_channels[0], dict):
            channel_names = [ch.get('name', 'N/A') for ch in rest_channels]
        else:
            channel_names = ws_channels or rest_channels
        print(f"Channels: {', '.join(channel_names) or 'N/A'}")
        
        # Handle different tag formats (string list vs object list)
        ws_tags = content.get('tags', [])
        rest_tags = data.get('tags', [])
        if isinstance(rest_tags and rest_tags[0], dict):
            tag_names = [tag.get('name', 'N/A') for tag in rest_tags]
        else:
            tag_names = ws_tags or rest_tags
        print(f"Tags: {', '.join(tag_names) or 'N/A'}")
        
        # Content fields (both formats)
        print(f"Teaser: {content.get('teaser') or data.get('teaser', 'N/A')}")
        # print(f"Body: {content.get('body') or data.get('body', 'N/A')}")

        # Truncated body
        body = content.get('body') or data.get('body', 'N/A')
        if len(body) > BODY_PREVIEW_LENGTH:
            print(f"Body: {body[:BODY_PREVIEW_LENGTH]}...")
        else:
            print(f"Body: {body}")        

        
        # Optional image field (both formats)
        image = content.get('image') or data.get('image')
        if image:
            print(f"Image: {image}")
        
        print(f"Error: {str(error)}")
        print("="*80)


    def handle_validation_error(self, error: Exception, data: Dict[str, Any]) -> None:
        """Handle validation errors"""
        error_type = self._classify_validation_error(error)
        self.stats.validation_errors[error_type] += 1
        
        # Always print validation errors regardless of raw mode
        # print("\nSkipped News Item:")
        # print(f"ID: {data.get('id', 'unknown')}")
        # print(f"Title: {data.get('title', 'N/A')}")
        # print(f"Error: {str(error)}")
        # print("="*80)
        # self.print_skipped_news(data, error)
        
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
    
    def handle_http_error(self, error: requests.exceptions.HTTPError) -> None:
        """Handle HTTP errors with specific messages"""
        if error.response.status_code == 400:
            print(f"\nAPI Limit Error: {error}")
            print("Try reducing date range or page count")
        elif error.response.status_code == 401:
            print("\nAuthentication Error: Please check your API key")
        elif error.response.status_code == 429:
            print("\nRate Limit Error: Too many requests")
        else:
            print(f"\nHTTP Error: {error}")
        
        self.stats.connection_errors += 1

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
        error_str = str(error).lower()
        
        # Handle both field name formats
        if any(term in error_str for term in ["stocks", "securities", "symbols"]):
            return "missing_symbols"
        elif "id" in error_str:
            return "missing_id"
        elif any(term in error_str for term in ["created", "created_at"]):
            return "invalid_created"
        elif any(term in error_str for term in ["updated", "updated_at"]):
            return "invalid_updated"
        elif "timestamp" in error_str:
            if "invalid" in error_str:
                return "invalid_timestamp_format"
            return "missing_timestamp"
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
            # Import feature flag locally
            from config.feature_flags import REJECT_MULTIPLE_SYMBOLS
            
            # Only check symbol count if feature flag is enabled
            if REJECT_MULTIPLE_SYMBOLS:
                # Count symbols based on format
                if 'data' in raw_item:  # WebSocket format
                    securities = raw_item.get('data', {}).get('content', {}).get('securities', [])
                    if len(securities) > 1:
                        return None
                else:  # REST API format
                    stocks = raw_item.get('stocks', [])
                    if len(stocks) > 1:
                        return None
            
            if 'data' in raw_item:  # WebSocket format
                news = BzWebSocketNews(**raw_item)
                # WebSocket validation - all fields required by model
                content = news.data.content
                if not content.id:
                    raise ValueError("News must have an ID")
                if not content.securities:
                    raise ValueError("News must have securities")
                if not content.created_at:
                    raise ValueError("News must have created_at timestamp")
                if not content.updated_at:
                    raise ValueError("News must have updated_at timestamp")


            else:  # REST API format
                news = BzRestAPINews(**raw_item)
                # REST API validation - all fields required by model
                if not news.id:
                    raise ValueError("News must have an ID")
                if not news.stocks:
                    raise ValueError("News must have stocks")
                if not news.created:
                    raise ValueError("News must have created timestamp")
                if not news.updated:
                    raise ValueError("News must have updated timestamp")


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