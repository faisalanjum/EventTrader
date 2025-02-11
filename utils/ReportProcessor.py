
from utils.BaseProcessor import BaseProcessor


class ReportProcessor(BaseProcessor):

    
    def __init__(self, event_trader_redis, delete_raw: bool = True):
        super().__init__(event_trader_redis, delete_raw)

    def process_all_reports(self):
        """Maintain consistent naming with NewsProcessor"""
        return self.process_all_items()

    def _standardize_fields(self, content: dict) -> dict:
        """Transform SEC fields while preserving original data"""
        return {
            **content,  # Keep all original fields
            'id': content.get('accessionNo'),
            'created': content.get('filedAt'),
            'updated': content.get('filedAt'),
            'symbols': [content.get('ticker')] if content.get('ticker') else [],
            'formType': content.get('formType')
        }

    def _clean_content(self, content: dict) -> dict:
        """Convert timestamps to Eastern like NewsProcessor"""
        cleaned = content.copy()
        for field in ['created', 'updated']:
            if field in cleaned:
                cleaned[field] = self.convert_to_eastern(cleaned[field])
        return cleaned