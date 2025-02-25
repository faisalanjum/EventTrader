from utils.BaseProcessor import BaseProcessor
from datetime import datetime
import html
import unicodedata
import time
from typing import Optional, Dict
from SEC_API_Files.sec_schemas import UnifiedReport, VALID_FORM_TYPES
from SEC_API_Files.reportSections import ten_k_sections, ten_q_sections, eight_k_sections
from sec_api import ExtractorApi
from eventtrader.keys import SEC_API_KEY

class ReportProcessor(BaseProcessor):
    """Report-specific processor implementation"""
    
    def __init__(self, event_trader_redis, delete_raw: bool = True):
        # Pass all parameters to parent class
        super().__init__(event_trader_redis, delete_raw)
        self.extractor = ExtractorApi(SEC_API_KEY) if SEC_API_KEY else None


    def _extract_section_content(self, url: str, section_id: str, retries: int = 3) -> Optional[str]:
        """Extract and clean section content with retries"""
        if not self.extractor:
            self.logger.warning("SEC API extractor not initialized - missing API key")
            return None
            
        for attempt in range(retries):
            try:
                content = self.extractor.get_section(url, section_id, "text")
                
                # Only retry if content is empty/None
                if not content or not content.strip():
                    if attempt < retries - 1:  # Don't sleep on last attempt
                        time.sleep(1)
                    continue
                    
                # Clean content if we have it
                content = html.unescape(content)
                return unicodedata.normalize("NFKC", content)
                
            except Exception as e:
                self.logger.error(f"Error extracting section {section_id} (attempt {attempt+1}/{retries}): {e}")
                return None  # Don't retry on API errors
                
        self.logger.warning(f"Failed to get content for section {section_id} after {retries} attempts")
        return None

    def _get_sections_map(self, form_type: str) -> dict:
        """Get appropriate sections map based on form type"""
        if form_type.startswith('10-K'):
            return ten_k_sections
        elif form_type.startswith('10-Q'):
            return ten_q_sections
        elif form_type.startswith('8-K'):
            return eight_k_sections
        return {}


    def process_all_reports(self):
        """Maintain consistent naming with NewsProcessor"""
        print(f"[Processor Debug] Starting ReportProcessor")
        print(f"[Processor Debug] Queue to watch: {self.queue_client.RAW_QUEUE}")
        return self.process_all_items()


    def _standardize_fields(self, content: dict) -> dict:
        """Transform SEC fields while preserving original data.
        Note: If primary ticker (from cik - standardized['ticker']) not in allowed_symbols, it's set to None but filing 
        will still process if other valid tickers exist in entities. If no valid tickers at all, 
        BaseProcessor will delete raw_key."""

        # print(f"[^Processor Debug] Standardizing fields for content-1: {content}")
        try:
            if content['formType'] not in VALID_FORM_TYPES:
                self.logger.info(f"Invalid form type so Skipping: {content['formType']}")
                return {}

            standardized = content.copy()
            symbols = set()  # Use set for unique symbols

            # print(f"[^Processor Debug] Standardizing fields for content-2: {content}")

            # Map primary CIK to ticker
            try:
                primary_cik = int(content.get('cik'))
                primary_matches = self.stock_universe[self.stock_universe.cik == primary_cik]
                
                if not primary_matches.empty:
                    primary_ticker = primary_matches.iloc[0]['symbol'].strip().upper()
                    if primary_ticker in self.allowed_symbols:
                        standardized['ticker'] = primary_ticker
                        symbols.add(primary_ticker)
                    else:
                        standardized['ticker'] = None
                else:
                    standardized['ticker'] = standardized['cik'] = None

            except (ValueError, TypeError):
                standardized['ticker'] = standardized['cik'] = None

            # Add entity symbols
            if entities := content.get('entities', []):
                for entity in entities:
                    try:
                        if entity_cik := int(entity.get('cik')):
                            matches = self.stock_universe[self.stock_universe.cik == entity_cik]
                            if not matches.empty:
                                ticker = matches.iloc[0]['symbol'].strip().upper()
                                if ticker in self.allowed_symbols:
                                    symbols.add(ticker)
                    except (ValueError, TypeError):
                        continue

            standardized.update({
                'id': content.get('accessionNo'),
                'created': content.get('filedAt'),
                'updated': content.get('filedAt'),
                'symbols': list(symbols),  # Convert set to list
                'formType': content.get('formType'),
            })

            # Extract sections if URL available
            if url := content.get('primaryDocumentUrl'):
                sections_map = self._get_sections_map(content['formType'])
                extracted_sections = {}
                
                for section_id, section_name in sections_map.items():
                    # print(f"[^Processor Debug] Extracting section {section_name} from {url}")
                    if section_content := self._extract_section_content(url, section_id):
                        extracted_sections[section_name] = section_content
                
                if extracted_sections:
                    standardized['extracted_sections'] = extracted_sections
            
            # print(f"[^Processor Debug] Standardizing fields for content-3: {standardized}")
            return standardized
            
        except Exception as e:
            self.logger.error(f"Error in _standardize_fields: {e}")
            # print(f"[^Processor Debug] Error in _standardize_fields: {e}")
            return {}

    def _clean_content(self, content: dict) -> dict:
        """Clean report content and convert timestamps
        This is called after standardization
        """
        try:
            cleaned = content.copy()
            
            # Convert timestamps to Eastern # 'created', 'updated' is filedAt
            for field in ['created', 'updated']:
                if field in cleaned:
                    cleaned[field] = self.convert_to_eastern(cleaned[field])
            
            # Add any other report-specific cleaning here
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error in _clean_content: {e}")
            return content  # Return original if cleaning fails

    # Looks like its not used anywhere?
    # def standardize_report(self, report: UnifiedReport) -> Optional[UnifiedReport]:
    #     """Public method to standardize a single report
    #     This is used by SECWebSocket for immediate processing
    #     """
    #     try:
    #         # Convert to dict for processing
    #         content = report.model_dump()
            
    #         # Apply standardization
    #         standardized = self._standardize_fields(content)
            
    #         # Clean content
    #         cleaned = self._clean_content(standardized)
            
    #         # Convert back to UnifiedReport
    #         return UnifiedReport(**cleaned)
            
    #     except Exception as e:
    #         self.logger.error(f"Error standardizing report: {e}")
    #         return None