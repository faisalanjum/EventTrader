# utils/TranscriptProcessor.py
from utils.BaseProcessor import BaseProcessor

class TranscriptProcessor(BaseProcessor):
    """Transcript-specific processor implementation"""
    
    def __init__(self, event_trader_redis, delete_raw=True, polygon_subscription_delay=None):
        super().__init__(event_trader_redis, delete_raw, polygon_subscription_delay)
    
    def process_all_transcripts(self):
        """Process all transcripts in queue"""
        return self.process_all_items()
    
    def _standardize_fields(self, content: dict) -> dict:
        """Transform transcript fields to standard format"""
        try:
            standardized = content.copy()
            
            # Ensure required fields are present for BaseProcessor
            standardized.update({
                'id': f"{content['symbol']}_{content['fiscal_year']}_{content['fiscal_quarter']}",
                'created': self._ensure_iso_format(content['conference_datetime']),
                'updated': self._ensure_iso_format(content['conference_datetime']),
                'symbols': [content['symbol']],
                'formType': f"TRANSCRIPT_Q{content['fiscal_quarter']}"
            })
            
            return standardized
        except Exception as e:
            self.logger.error(f"Error standardizing transcript: {e}")
            return {}
    
    def _clean_content(self, content: dict) -> dict:
        """Clean transcript content"""
        try:
            cleaned = content.copy()
            
            # Convert timestamps to Eastern
            for field in ['created', 'updated']:
                if field in cleaned:
                    cleaned[field] = self.convert_to_eastern(cleaned[field])
            
            return cleaned
        except Exception as e:
            self.logger.error(f"Error cleaning transcript: {e}")
            return content
    
    def _ensure_iso_format(self, dt) -> str:
        """Ensure datetime is in ISO format"""
        if isinstance(dt, str):
            return dt
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()
        return str(dt)