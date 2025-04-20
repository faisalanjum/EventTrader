import re
from .BaseProcessor import BaseProcessor
from datetime import datetime
import html
import unicodedata
import time
from typing import Optional, Dict, List
from SEC_API_Files.sec_schemas import UnifiedReport
from config.feature_flags import VALID_FORM_TYPES, FORM_TYPES_REQUIRING_SECTIONS, FORM_TYPES_REQUIRING_XML
from SEC_API_Files.reportSections import ten_k_sections, ten_q_sections, eight_k_sections
from sec_api import ExtractorApi, XbrlApi
from eventtrader.keys import SEC_API_KEY
from multiprocessing import Pool
import requests
from inscriptis import get_text


# Notes:
# 1. The primaryDocumentUrl is XML (XBRL link) if available , else linkToTxt.
# 2. secondary_filing_content is populated only when form type is NOT in FORM_TYPES_REQUIRING_SECTIONS (so only for 'SCHEDULE 13D', 'SCHEDULE 13D/A', 'SC TO-I', '425', 'SC 14D9', '6-K') 
# 3. The items tells the system which specific sections are present in an 8-K filing (e.g., "Item 1.01: Entry into a Material Agreement"), unlike 10-K/10-Q which have standardized structures. 



# Move this outside the class
def _extract_section_worker(args):
    """Standalone worker function for multiprocessing with proper retry logic"""
    url, section_id = args
    try:
        extractor = ExtractorApi(SEC_API_KEY)
        processing_attempts = 0
        regular_attempts = 0
        retries = 3
        processing_retries = 3
            
        while regular_attempts < retries or processing_attempts < processing_retries:
            try:
                content = extractor.get_section(url, section_id, "text")

                # Handle processing status
                if content == "processing":
                    processing_attempts += 1
                    if processing_attempts <= processing_retries:
                        delay = 500 + (500 * processing_attempts)  # 500ms, 1000ms, 1500ms
                        time.sleep(delay / 1000)  # Convert to seconds
                        continue
                    return section_id, None

                # Handle empty content
                if not content or not content.strip():
                    regular_attempts += 1
                    if regular_attempts < retries:
                        delay = 500 + (500 * regular_attempts)
                        time.sleep(delay / 1000)
                        continue
                    return section_id, None
                    
                # Clean content if we have it
                content = html.unescape(content)
                return section_id, unicodedata.normalize("NFKC", content)
                        
            except Exception:
                regular_attempts += 1
                if regular_attempts < retries:
                    delay = 500 + (500 * regular_attempts)
                    time.sleep(delay / 1000)
                    continue
                break
                    
        return section_id, None

    except Exception:
        return section_id, None


class ReportProcessor(BaseProcessor):
    """Report-specific processor implementation"""
    
    def __init__(self, event_trader_redis, delete_raw: bool = True, polygon_subscription_delay: int = None, ttl=None):
        # Pass all parameters to parent class
        super().__init__(event_trader_redis, delete_raw, polygon_subscription_delay)
        self.ttl = ttl
        self.extractor = ExtractorApi(SEC_API_KEY) if SEC_API_KEY else None
        self.xbrl_api = XbrlApi(SEC_API_KEY) if SEC_API_KEY else None



    def _extract_section_content(self, url: str, section_id: str, retries: int = 3, processing_retries: int = 3) -> Optional[str]:
        """Extract and clean section content with retries"""
        self.logger.info(f"Attempting to extract section {section_id} from {url}")
        
        if not self.extractor:
            self.logger.warning("SEC API extractor not initialized - missing API key")
            return None
        
        processing_attempts = 0
        regular_attempts = 0
            
        while regular_attempts < retries or processing_attempts < processing_retries:
            try:
                content = self.extractor.get_section(url, section_id, "text")

                # Handle processing status - retry with SEC recommended delay
                if content == "processing":
                    processing_attempts += 1
                    if processing_attempts <= processing_retries:
                        delay = 500 + (500 * processing_attempts)  # 500ms, 1000ms, 1500ms
                        self.logger.debug(f"Section {section_id} processing, attempt {processing_attempts}/{processing_retries}, waiting {delay}ms")
                        time.sleep(delay / 1000)  # Convert to seconds
                        continue
                    else:
                        self.logger.warning(f"Section {section_id} still processing after {processing_retries} attempts")
                        return None

                # Only retry if content is empty/None
                if not content or not content.strip():
                    regular_attempts += 1
                    if regular_attempts < retries:
                        delay = 500 + (500 * regular_attempts)  # Match SEC recommended delays
                        self.logger.debug(f"Empty content received for section {section_id}, attempt {regular_attempts}/{retries}")
                        time.sleep(delay / 1000)
                        continue
                    else:
                        self.logger.warning(f"Failed to get content for section {section_id} after {retries} regular attempts")
                        return None
                    
                # Clean content if we have it
                content = html.unescape(content)
                self.logger.info(f"Successfully extracted section {section_id}")
                return unicodedata.normalize("NFKC", content)
                        
            except Exception as e:
                regular_attempts += 1
                self.logger.error(f"Error extracting section {section_id} (attempt {regular_attempts}/{retries}): {e}")
                if regular_attempts < retries:
                    delay = 500 + (500 * regular_attempts)
                    time.sleep(delay / 1000)
                    continue
                break
                    
        self.logger.warning(f"Failed to get content for section {section_id} after {regular_attempts} regular attempts and {processing_attempts} processing attempts")
        return None



    def _extract_sections(self, url: str, form_type: str, items: Optional[List[str]] = None) -> Dict[str, str]:
        """Extract sections based on form type with proper handling"""
        try:
            if not self.extractor:
                self.logger.warning("SEC API extractor not initialized - missing API key")
                return {}

            sections_map = self._get_sections_map(form_type)
            self.logger.info(f"Using sections map for form type {form_type}: {len(sections_map)} sections")
            extracted_sections = {}

            # Handle 8-K forms using items (sequential processing)
            if form_type.startswith('8-K') and items:
                self.logger.info(f"Processing 8-K sections from items: {len(items)} items")
                for item in items:
                    if section_id := self._get_section_id_from_item(item):
                        if section_name := sections_map.get(section_id):
                            self.logger.info(f"Starting extraction for section {section_name} ({section_id})")
                            if content := self._extract_section_content(url, section_id):
                                if content != "processing":
                                    extracted_sections[section_name] = content
                                    self.logger.info(f"Successfully extracted section {section_name}")
                                    del content  # Help garbage collection


            # Inside _extract_sections method, update the parallel processing part:
            elif form_type.startswith(('10-K', '10-Q')):
                self.logger.info(f"Processing {form_type} sections in parallel")
                try:
                    args = [(url, section_id) for section_id in sections_map.keys()]
                    with Pool(processes=4) as pool:
                        results = pool.map(_extract_section_worker, args)
                        
                        # Process results and free memory as we go
                        for section_id, content in zip(sections_map.keys(), results):
                            if content and content != "processing":
                                section_name = sections_map[section_id]
                                extracted_sections[section_name] = content  # Content already cleaned in worker
                                self.logger.info(f"Successfully extracted section {section_name}")
                            del content  # Help garbage collection
                finally:
                    pool.close()  # Ensure proper cleanup
                    pool.join()

            if extracted_sections:
                self.logger.info(f"Total sections extracted: {len(extracted_sections)}")
            else:
                self.logger.warning("No sections were successfully extracted")

            return extracted_sections

        except Exception as e:
            self.logger.error(f"Error in _extract_sections: {e}")
            return {}

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
        # print(f"[Processor Debug] Starting ReportProcessor")
        # print(f"[Processor Debug] Queue to watch: {self.queue_client.RAW_QUEUE}")
        return self.process_all_items()


    def _get_section_id_from_item(self, item: str) -> Optional[str]:
        """Convert item format to section ID format
        Examples:
        - "Item 1.01: Entry..." -> "1-1"
        - "Item 2.02: Results..." -> "2-2"
        - "Item 6.10: Alternative..." -> "6-10"
        - "Signature" -> "signature"
        """
        try:
            # Handle signature case
            if item == "Signature":
                return "signature"
                
            # Handle regular item format
            if match := re.search(r'Item (\d+)\.(\d+)', item):
                major, minor = match.groups()
                # Special case for 6.10
                if major == "6" and minor == "10":
                    return "6-10"
                # Regular case: strip leading zeros
                return f"{major}-{int(minor)}"
            return None
        except Exception as e:
            self.logger.error(f"Error parsing item: {item}")
            return None



    def _fetch_primary_cik(self, xbrl_json):
        """
        Returns the primary CIK for the financial statements.
        It first attempts to use the CoverPage field (as per sec-api.io docs).
        If that fails, it scans for a default context (without dimensions).
        """
        # Preferred method: use CoverPage's EntityCentralIndexKey
        cover = xbrl_json.get("CoverPage", {})
        cik = cover.get("EntityCentralIndexKey")
        
        # Handle list values (as we've seen in some filings)
        if isinstance(cik, list):
            cik = cik[0] if cik else None
        
        if cik:
            try:
                # Ensure it is numeric and return as a 10-digit string
                return str(int(cik)).zfill(10)
            except (ValueError, TypeError):
                pass  # fall through to secondary method

        # Secondary method: if the JSON includes contexts, pick the one without dimensions
        contexts = xbrl_json.get("Contexts", [])
        default_contexts = [ctx for ctx in contexts if not ctx.get("Dimensions")]
        if len(default_contexts) == 1:
            candidate = default_contexts[0].get("EntityCentralIndexKey")
            if candidate:
                try:
                    return str(int(candidate)).zfill(10)
                except (ValueError, TypeError):
                    pass

        # If ambiguity remains or no candidate is found, raise an error so you can handle it explicitly
        raise ValueError("Unable to determine a unique primary CIK from the filing data.")



    def _add_normalized_cik(self, cik_value, cik_set):
        """Helper to add normalized CIKs to a set, handling both single values and lists"""
        if isinstance(cik_value, list):
            for cik in cik_value:
                if cik:
                    try:
                        cik_set.add(str(int(cik)).zfill(10))
                    except (ValueError, TypeError):
                        pass
        elif cik_value:
            try:
                cik_set.add(str(int(cik_value)).zfill(10))
            except (ValueError, TypeError):
                pass


    def _get_financial_statements(self, accession_no: str, cik: str) -> Optional[Dict]:
        """Extract financial statements from XBRL data"""
        try:
            if not self.xbrl_api:
                self.logger.warning("SEC XBRL API not initialized - missing API key")
                return None

            xbrl_json = self.xbrl_api.xbrl_to_json(accession_no=accession_no)
            
            # Normalize input CIK
            input_cik = str(int(cik)).zfill(10) if cik else '0'.zfill(10)
            match_found = False
            
            # First try primary CIK method
            try:
                primary_cik = self._fetch_primary_cik(xbrl_json)
                if input_cik == primary_cik:
                    self.logger.info(f"Input CIK {input_cik} matches primary financial statement CIK for {accession_no}")
                    match_found = True
                else:
                    self.logger.warning(f"Input CIK {input_cik} doesn't match primary CIK {primary_cik}, trying fallback")
            except ValueError:
                self.logger.info(f"Couldn't determine primary CIK, trying fallback verification for {accession_no}")
            
            # If primary method didn't find a match, try fallback
            if not match_found:
                xbrl_ciks = set()  # Use set to avoid duplicates
                
                # Check CoverPage (the documented location for CIK)
                cover_cik = xbrl_json.get('CoverPage', {}).get('EntityCentralIndexKey', '0')
                self._add_normalized_cik(cover_cik, xbrl_ciks)
                
                # Convert back to list and check for match
                xbrl_ciks = list(xbrl_ciks)
                if not xbrl_ciks or input_cik not in xbrl_ciks:
                    self.logger.warning(f"No CIK match for {accession_no}: input CIK {input_cik} not in {xbrl_ciks}")
                    return None
                else:
                    self.logger.info(f"Input CIK {input_cik} matches one of the XBRL CIKs {xbrl_ciks} for {accession_no}")
                    match_found = True
            
            # Only continue if we found a match
            if not match_found:
                return None
                
            # Initialize all expected statements with None
            financial_statements = {
                'BalanceSheets': None,
                'StatementsOfIncome': None,
                'StatementsOfShareholdersEquity': None,
                'StatementsOfCashFlows': None
            }
            
            # Update with available data
            for statement in financial_statements.keys():
                if statement_data := xbrl_json.get(statement):
                    financial_statements[statement] = statement_data
                    self.logger.debug(f"Found data for {statement}")
                else:
                    self.logger.debug(f"No data found for {statement}")
                    
            # Only return if at least one statement has data
            return financial_statements if any(v is not None for v in financial_statements.values()) else None
                    
        except Exception as e:
            self.logger.error(f"Error extracting XBRL data for accession {accession_no}: {e}")
            return None


    def _download_exhibit(self, url: str) -> Optional[str]:
        """Download and extract exhibit content with proper SEC rate limiting"""
        headers = {
            'User-Agent': 'EventTrader research.bot@example.com',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }

        try:
            # Respect SEC's rate limit
            time.sleep(0.1)
            
            # Download with proper headers
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            content = response.text
            
            # Format detection and appropriate text extraction
            raw_text = ""
            
            # SGML format with TEXT tags
            if "<TEXT>" in content:
                text_blocks = re.findall(r'<TEXT>(.*?)</TEXT>', content, re.DOTALL)
                for block in text_blocks:
                    # HTML content inside TEXT tags
                    if re.search(r'<(html|body|div|p|table)', block, re.I):
                        raw_text += get_text(block) + "\n\n"
                    elif block.strip().startswith("<?xml") or block.strip().startswith("<XML>"):
                        raw_text += block + "\n\n"
                    else:
                        # Plain text inside TEXT tags
                        raw_text += block + "\n\n"
            # Pure HTML format
            elif re.search(r'<(html|body)', content, re.I):
                raw_text = get_text(content)
            # Unknown format - use as is
            else:
                raw_text = content
            
            if not raw_text.strip():
                return None
            
            # Apply cleaning just like in _extract_secondary_filing_content
            clean_text = re.sub(r'<[^>]*>', ' ', raw_text)
            clean_text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
            
            return clean_text.strip()
            
        except Exception as e:
            self.logger.error(f"Error processing exhibit {url}: {str(e)}")
            return None

    # These are specifically for 6-K, 13D etc (Non FORM_TYPES_REQUIRING_SECTIONS)
    def _extract_secondary_filing_content(self, url: str) -> Optional[str]:
        """Extract clean text from any SEC filing format with minimal dependencies"""
        headers = {
            'User-Agent': 'EventTrader research.bot@example.com',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        
        try:
            # Respect SEC's rate limit
            time.sleep(0.1)
            
            # Download with proper headers
            self.logger.info(f"Downloading secondary filing from {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            content = response.text
            
            # PHASE 1: Format-specific extraction
            raw_text = ""
            
            # SGML format with TEXT tags
            if "<TEXT>" in content:
                self.logger.info(f"Detected SGML format with <TEXT> tags")
                text_blocks = re.findall(r'<TEXT>(.*?)</TEXT>', content, re.DOTALL)
                for block in text_blocks:
                    # HTML content inside TEXT tags
                    if re.search(r'<(html|body|div|p|table)', block, re.I):
                        self.logger.info(f"HTML content detected inside TEXT tags")
                        raw_text += get_text(block) + "\n\n"
                    elif block.strip().startswith("<?xml") or block.strip().startswith("<XML>"):
                        self.logger.info(f"XML content detected in document")
                        raw_text += block + "\n\n"
                    else:
                        # Plain text inside TEXT tags
                        raw_text += block + "\n\n"
            # Pure HTML format
            elif re.search(r'<(html|body)', content, re.I):
                self.logger.info(f"Detected HTML format, extracting text")
                raw_text = get_text(content)
            # Unknown format - use as-is
            else:
                self.logger.info(f"Unknown document format, using raw content")
                raw_text = content
            
            if not raw_text.strip():
                self.logger.warning(f"No text extracted from {url}")
                return None
            
            # PHASE 2: Universal text cleaning pipeline
            self.logger.info(f"Cleaning and normalizing extracted text ({len(raw_text)} chars)")
            
            # Remove remaining tags, clean entities, normalize whitespace
            clean_text = re.sub(r'<[^>]*>', ' ', raw_text)
            clean_text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
            
            self.logger.info(f"Successfully extracted clean text from secondary filing ({len(clean_text)} chars)")
            return clean_text.strip()
            
        except Exception as e:
            self.logger.error(f"Error extracting text from secondary filing {url}: {e}")
            return None

    def _process_exhibits(self, exhibits: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Process all exhibits in a filing"""
        exhibit_content = {}
        
        for exhibit_id, url in exhibits.items():
            if content := self._download_exhibit(url):
                exhibit_content[exhibit_id] = {
                    'text': content,
                    'url': url
                }
            
        return exhibit_content

    def _standardize_fields(self, content: dict) -> dict:
        """Transform SEC fields while preserving original data.
        Note: If primary ticker (from cik) not in allowed_symbols, it's set to None but filing 
        will still process if other valid tickers exist in entities."""
        try:
            # Flag reports with missing CIKs but still process them
            # Reports with missing CIKs will be marked as ineligible for XBRL processing later
            # but their content can still be used for other purposes
            if not content.get('cik') or content.get('cik') == '':
                self.logger.info(f"Report with missing primary filer CIK: {content.get('accessionNo', 'unknown')}")
                content['cik'] = ''  # Ensure CIK is an empty string not None

                # Inorder to skip it return empty dict to signal skip
                # return {}
            

            if content['formType'] not in VALID_FORM_TYPES:
                self.logger.info(f"Invalid form type so Skipping: {content['formType']}")
                return {}

            standardized = content.copy()
            symbols = set()  # Use set for unique symbols

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
                'extracted_sections': None,  # Initialize with None by default
                'financial_statements': None,  # Initialize with None by default
                'exhibit_contents': None,  # Initialize exhibits with None by default
                'filing_text_content': None  # Full document text content
            })

            # Extract sections if URL available and form type requires it
            # Extract content from document URL if available
            if url := content.get('primaryDocumentUrl'):
                if content['formType'] in FORM_TYPES_REQUIRING_SECTIONS:
                    # For forms like 8-K, 10-K, 10-Q: extract specific sections
                    self.logger.info(f"Found primaryDocumentUrl: {url}, attempting to extract sections")
                    if extracted_sections := self._extract_sections(
                        url=url,
                        form_type=content['formType'],
                        items=content.get('items')
                    ):
                        standardized['extracted_sections'] = extracted_sections
                        self.logger.info(f"Successfully extracted sections for {content['formType']}")
                else:
                    # For forms like SCHEDULE 13D/A: extract full document content
                    self.logger.info(f"Form type {content['formType']} doesn't require sections, extracting document text")
                    if text_content := self._extract_secondary_filing_content(url):
                        standardized['filing_text_content'] = text_content
                        self.logger.info(f"Successfully extracted document text from primaryDocumentUrl")

            # Logically since we are not saving xbrl content when cik is nul, we do below fallback to capture text content instead
            # If text content is still empty and we have a null CIK with XML filing, try extracting from linkToTxt
            if standardized['filing_text_content'] is None and standardized['cik'] is None and content.get('is_xml') is True and content.get('linkToTxt'):
                self.logger.info(f"Document text not available, CIK is null with XML filing, attempting to extract from text link")
                if fallback_content := self._extract_secondary_filing_content(content['linkToTxt']):
                    standardized['filing_text_content'] = fallback_content
                    self.logger.info(f"Successfully extracted document text from linkToTxt (fallback)")

            # Extract financial statements for forms requiring XML
            if content['formType'] in FORM_TYPES_REQUIRING_XML:
                self.logger.info(f"Form type {content['formType']} requires XBRL processing")
                if financial_statements := self._get_financial_statements(
                    accession_no=content.get('accessionNo'),
                    cik=str(content.get('cik'))
                ):
                    standardized['financial_statements'] = financial_statements
                    self.logger.info(f"Successfully extracted financial statements")

            # Process exhibits if available
            if exhibits := content.get('exhibits'):
                self.logger.info(f"Found {len(exhibits)} exhibits, attempting to extract content")
                if exhibit_contents := self._process_exhibits(exhibits):
                    standardized['exhibit_contents'] = exhibit_contents
                    self.logger.info(f"Successfully extracted {len(exhibit_contents)} exhibits")

            return standardized

        except Exception as e:
            self.logger.error(f"Error in _standardize_fields: {e}")
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
