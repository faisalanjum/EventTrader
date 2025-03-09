from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

def parse_date(date_str):
    """
    Parse a date string into a datetime object with robust error handling.
    Handles multiple date formats including:
    - ISO format (with or without timezone)
    - Unix timestamp (as string or integer)
    - Custom formats
    
    Args:
        date_str: String or integer representing a date
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
        
    # Handle already parsed datetime objects
    if isinstance(date_str, datetime):
        return date_str
    
    # Handle integer timestamps
    if isinstance(date_str, int):
        try:
            return datetime.fromtimestamp(date_str, tz=timezone.utc)
        except Exception as e:
            logger.warning(f"Could not parse timestamp integer {date_str}: {e}")
            return None
    
    # Handle string inputs
    if isinstance(date_str, str):
        # Try ISO format (most common and reliable)
        try:
            # Replace 'Z' with '+00:00' for UTC timezone
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            # Handle ISO format
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass
        
        # Try unix timestamp (as string)
        try:
            if date_str.isdigit():
                timestamp = int(date_str)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception:
            pass
        
        # Try common formats with timezone
        formats = [
            '%Y-%m-%dT%H:%M:%S%z',       # ISO-like format with timezone
            '%Y-%m-%d %H:%M:%S%z',        # Standard format with timezone
            '%Y-%m-%dT%H:%M:%S.%f%z',     # ISO with microseconds and timezone
            '%Y-%m-%d %H:%M:%S.%f%z',     # Standard with microseconds and timezone
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # Try formats without timezone (assume UTC)
        formats_no_tz = [
            '%Y-%m-%dT%H:%M:%S',          # ISO without timezone
            '%Y-%m-%d %H:%M:%S',           # Standard without timezone
            '%Y-%m-%dT%H:%M:%S.%f',        # ISO with microseconds
            '%Y-%m-%d %H:%M:%S.%f',        # Standard with microseconds
            '%Y-%m-%d',                    # Just date
        ]
        
        for fmt in formats_no_tz:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Assume UTC for dates without timezone
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    
    # Log warning if we couldn't parse the date
    logger.warning(f"Could not parse date string: {date_str}")
    return None

def parse_news_dates(news_item):
    """
    Parse created_at and updated_at fields from a news item.
    Handles different field names that might be used in different news sources.
    
    Args:
        news_item: Dictionary containing news data
        
    Returns:
        Tuple of (created_at, updated_at) as datetime objects
    """
    created_at = None
    updated_at = None
    
    # Try all possible field names for created date
    for field in ['created_at', 'created', 'creation_date', 'publish_date', 'published_at']:
        if field in news_item and news_item[field]:
            created_at = parse_date(news_item[field])
            if created_at:
                break
                
    # Check created_at in metadata if present
    if not created_at and 'metadata' in news_item and isinstance(news_item['metadata'], dict):
        if 'event' in news_item['metadata'] and isinstance(news_item['metadata']['event'], dict):
            if 'created' in news_item['metadata']['event']:
                created_at = parse_date(news_item['metadata']['event']['created'])
    
    # Try all possible field names for updated date
    for field in ['updated_at', 'updated', 'update_date', 'updated_date', 'last_modified']:
        if field in news_item and news_item[field]:
            updated_at = parse_date(news_item[field])
            if updated_at:
                break
    
    # If updated_at is still None but created_at exists, use created_at
    if updated_at is None and created_at is not None:
        updated_at = created_at
        
    return created_at, updated_at 