import re
from .BaseProcessor import BaseProcessor
import html
import unicodedata
import time
from typing import Optional, Dict, List
from config.feature_flags import VALID_FORM_TYPES, FORM_TYPES_REQUIRING_SECTIONS, FORM_TYPES_REQUIRING_XML, XBRL_JSON_CACHE_DIR
from secReports.reportSections import ten_k_sections, ten_q_sections, eight_k_sections
from sec_api import ExtractorApi, XbrlApi
from eventtrader.keys import SEC_API_KEY
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import requests
from inscriptis import get_text
from config import feature_flags
import json
from redisDB.redis_constants import RedisKeys
import copy
import os
import concurrent.futures
import logging


# Notes:
# 1. The primaryDocumentUrl is XML (XBRL link) if available , else linkToTxt.
# 2. secondary_filing_content is populated only when form type is NOT in FORM_TYPES_REQUIRING_SECTIONS (so only for 'SCHEDULE 13D', 'SCHEDULE 13D/A', 'SC TO-I', '425', 'SC 14D9', '6-K') 
# 3. The items tells the system which specific sections are present in an 8-K filing (e.g., "Item 1.01: Entry into a Material Agreement"), unlike 10-K/10-Q which have standardized structures. 


def _safe_get_section(extractor_instance, url, section_id):
    """Helper function to isolate the blocking get_section call."""
    return extractor_instance.get_section(url, section_id, "text")


# Move this outside the class
def _extract_section_worker(args):
    """Standalone worker function for multiprocessing with proper retry logic"""
    url, section_id, api_key = args  # Now receiving api_key instead of creating extractor inside
    try:
        extractor = ExtractorApi(api_key)  # Create extractor with passed API key
        processing_attempts = 0
        regular_attempts = 0
        retries = 3
        processing_retries = 3
        # Use timeout from feature_flags
        call_timeout = feature_flags.EXTRACTOR_CALL_TIMEOUT
            
        while regular_attempts < retries or processing_attempts < processing_retries:
            try:
                # Use context manager for ThreadPoolExecutor to ensure it's properly closed
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_safe_get_section, extractor, url, section_id)
                    content = future.result(timeout=call_timeout)

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
                    
            except FutureTimeout:
                regular_attempts += 1 # Treat timeout as a failed attempt
                continue # Go to next retry iteration
            except Exception as e:
                regular_attempts += 1
                if regular_attempts < retries:
                    delay = 500 + (500 * regular_attempts)
                    time.sleep(delay / 1000)
                    continue
                break
                
        return section_id, None

    except Exception as e:
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
        """Extract and clean section content with retries and timeout"""
        self.logger.info(f"Attempting to extract section {section_id} from {url}")
        
        if not self.extractor:
            self.logger.warning("SEC API extractor not initialized - missing API key")
            return None
        
        processing_attempts = 0
        regular_attempts = 0
        # Use the EXTRACTOR_CALL_TIMEOUT from feature_flags, with a default if not found
        call_timeout_val = getattr(feature_flags, 'EXTRACTOR_CALL_TIMEOUT', 90) 
            
        while regular_attempts < retries or processing_attempts < processing_retries:
            try:
                # --- new block for timeout --- 
                with ThreadPoolExecutor(max_workers=1) as executor:
                    # Pass self.extractor and its method arguments to submit
                    future = executor.submit(self.extractor.get_section, url, section_id, "text")
                    content = future.result(timeout=call_timeout_val)
                # --- end new block --- 

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
                        self.logger.warning(f"Failed to get content for section {section_id} after {retries} regular attempts (empty content)")
                        return None
                    
                # Clean content if we have it
                content = html.unescape(content)
                self.logger.info(f"Successfully extracted section {section_id}")
                return unicodedata.normalize("NFKC", content)
            
            except FutureTimeout: # Handle the timeout specifically
                regular_attempts += 1
                self.logger.warning(f"Timeout extracting section {section_id} (attempt {regular_attempts}/{retries}) after {call_timeout_val}s")
                if regular_attempts < retries:
                    # Using the same delay logic as other errors for consistency
                    delay = 500 + (500 * regular_attempts) 
                    time.sleep(delay / 1000)
                    continue
                # If retries exceeded after timeout, break to return None outside loop
                self.logger.warning(f"Failed to get content for section {section_id} due to repeated timeouts.")
                break 
            except Exception as e:
                regular_attempts += 1
                self.logger.error(f"Error extracting section {section_id} (attempt {regular_attempts}/{retries}): {e}", exc_info=True)
                if regular_attempts < retries:
                    delay = 500 + (500 * regular_attempts)
                    time.sleep(delay / 1000)
                    continue
                # If retries exceeded after other exceptions, break to return None
                self.logger.warning(f"Failed to get content for section {section_id} due to repeated errors.")
                break
                    
        self.logger.warning(f"Failed to get content for section {section_id} after {regular_attempts} regular attempts and {processing_attempts} processing attempts. Returning None.")
        return None



    def _extract_sections(self, url: str, form_type: str, items: Optional[List[str]] = None) -> Dict[str, str]:
        """Extract sections based on form type with proper handling."""
        try:
            if not self.extractor:
                self.logger.warning("SEC API extractor not initialized - missing API key")
                return {}

            sections_map = self._get_sections_map(form_type)
            self.logger.info(f"Using sections map for form type {form_type}: {len(sections_map)} sections")
            extracted_sections = {}

            if form_type.startswith('8-K') and items:
                self.logger.info(f"Processing 8-K sections from items: {len(items)} items sequentially")
                for item in items:
                    if section_id := self._get_section_id_from_item(item):
                        if section_name := sections_map.get(section_id):
                            self.logger.info(f"Starting extraction for section {section_name} ({section_id})")
                            # _extract_section_content already has timeout and retries
                            if content := self._extract_section_content(url, section_id):
                                if content != "processing": # Should be handled by _extract_section_content returning None
                                    extracted_sections[section_name] = content
                                    self.logger.info(f"Successfully extracted section {section_name}")
                                    # del content # Not strictly necessary, GC will handle
            
            elif form_type.startswith(('10-K', '10-Q')):
                self.logger.info(f"Processing {form_type} sections in parallel using ThreadPoolExecutor for URL: {url}")
                
                if not SEC_API_KEY: # This check might be redundant if self.extractor check passed
                    self.logger.warning("SEC API key is missing, skipping section extraction")
                    return {}
                
                # Use a ThreadPoolExecutor for I/O-bound tasks within the worker process
                # The number of workers here can be tuned, e.g., 4-8, or based on a new feature_flag
                # os.cpu_count() might be too high for threads if many enricher processes are running.
                # Let's use a moderate fixed number or make it configurable.
                num_threads_for_sections = getattr(feature_flags, 'THREADS_PER_SECTION_EXTRACTION', 4)

                futures = {}
                with ThreadPoolExecutor(max_workers=num_threads_for_sections) as executor:
                    for section_id, section_name in sections_map.items():
                        # _extract_section_content handles its own retries and timeouts internally
                        future = executor.submit(self._extract_section_content, url, section_id)
                        futures[future] = section_name # Map future to section_name

                    # Collect results as they complete
                    # Add an overall timeout for collecting all section results for this report
                    # This is similar to the old batch_timeout but for threads.
                    overall_section_timeout = getattr(feature_flags, 'SECTION_BATCH_EXTRACTION_TIMEOUT', 450)
                    start_time = time.time()

                    for future in concurrent.futures.as_completed(futures):
                        # Check for overall timeout for this report's sections
                        if time.time() - start_time > overall_section_timeout:
                            self.logger.warning(f"Overall timeout of {overall_section_timeout}s reached for extracting sections from {url}. Aborting remaining.")
                            # Cancel remaining futures
                            for f_cancel in futures:
                                if not f_cancel.done():
                                    f_cancel.cancel()
                            break # Exit the collection loop

                        section_name_from_future = futures[future]
                        try:
                            content = future.result() # This won't block indefinitely due to internal timeout in _extract_section_content
                            if content:
                                extracted_sections[section_name_from_future] = content
                                self.logger.info(f"Successfully extracted section {section_name_from_future} for {form_type}")
                        except Exception as exc:
                            self.logger.error(f"Section {section_name_from_future} generated an exception: {exc}", exc_info=True)
            
            if extracted_sections:
                self.logger.info(f"Successfully extracted {len(extracted_sections)} sections for {url}")
            else:
                self.logger.warning(f"No sections were successfully extracted for {url}")

            return extracted_sections

        except Exception as e:
            self.logger.error(f"Error in _extract_sections for {url}: {e}", exc_info=True)
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

            # --- tiny on-disk cache for sec-api JSON to avoid repeat downloads ---
            xbrl_json = None
            cache_path = None
            if XBRL_JSON_CACHE_DIR:
                try:
                    os.makedirs(XBRL_JSON_CACHE_DIR, exist_ok=True)
                    cache_path = os.path.join(XBRL_JSON_CACHE_DIR, f"{accession_no}.json")
                    if os.path.exists(cache_path):
                        with open(cache_path, 'r', encoding='utf-8') as fh:
                            xbrl_json = json.load(fh)
                            self.logger.debug(f"Loaded cached XBRL JSON for {accession_no}")
                except Exception as cache_err:
                    self.logger.debug(f"Cache read error for {accession_no}: {cache_err}")

            if xbrl_json is None:  # Cache miss – fetch from SEC-API
                xbrl_json = self.xbrl_api.xbrl_to_json(accession_no=accession_no)
                if cache_path:
                    try:
                        with open(cache_path, 'w', encoding='utf-8') as fh:
                            json.dump(xbrl_json, fh)
                    except Exception as cache_write_err:
                        self.logger.debug(f"Cache write error for {accession_no}: {cache_write_err}")
            
            # Normalize input CIK robustly
            normalized_input_cik_str = None
            if cik and isinstance(cik, str) and cik.strip().isdigit():
                try:
                    normalized_input_cik_str = str(int(cik)).zfill(10)
                except ValueError:
                    normalized_input_cik_str = '0'.zfill(10) # Should not happen if isdigit is true
            elif cik and isinstance(cik, int):
                 normalized_input_cik_str = str(cik).zfill(10)
            else: # Handles Python None, empty string, and non-digit strings like "None"
                normalized_input_cik_str = '0'.zfill(10)
            
            input_cik_to_match = normalized_input_cik_str # Use this for comparisons
            match_found = False
            
            # First try primary CIK method
            try:
                primary_cik_from_xbrl = self._fetch_primary_cik(xbrl_json) # This method should also be robust
                if primary_cik_from_xbrl and input_cik_to_match == primary_cik_from_xbrl:
                    self.logger.info(f"Input CIK {input_cik_to_match} matches primary financial statement CIK {primary_cik_from_xbrl} for {accession_no}")
                    match_found = True
                elif primary_cik_from_xbrl: # It was found but didn't match
                    self.logger.warning(f"Input CIK {input_cik_to_match} doesn't match primary CIK {primary_cik_from_xbrl} from XBRL, trying fallback for {accession_no}")
                else: # _fetch_primary_cik returned None or couldn't find one
                    self.logger.info(f"Could not determine primary CIK from XBRL for {accession_no}, trying fallback verification.")
            except ValueError as ve_fetch_primary:
                self.logger.info(f"_fetch_primary_cik raised ValueError: {ve_fetch_primary}. Trying fallback for {accession_no}")
            
            # If primary method didn't find a match, try fallback
            if not match_found:
                xbrl_ciks_set = set()
                cover_cik_val = xbrl_json.get('CoverPage', {}).get('EntityCentralIndexKey') # Can be None, int, str, or list
                self._add_normalized_cik(cover_cik_val, xbrl_ciks_set) # This helper needs to be robust
                
                # If CoverPage CIK didn't yield a match with input_cik_to_match and it was a single valid CIK
                # Or if no CIK was on cover page, try contexts (though _fetch_primary_cik also tries contexts)
                # This fallback logic primarily focuses on EntityCentralIndexKey from CoverPage for simplicity here.
                # A more complex fallback would re-iterate contexts if _fetch_primary_cik failed to produce one.

                final_xbrl_ciks_list = list(xbrl_ciks_set)
                if not final_xbrl_ciks_list or input_cik_to_match not in final_xbrl_ciks_list:
                    self.logger.warning(f"No CIK match for {accession_no}: input CIK {input_cik_to_match} not in XBRL CIKs {final_xbrl_ciks_list} (from CoverPage). Returning None for financial statements.")
                    return None
                else:
                    self.logger.info(f"Input CIK {input_cik_to_match} matches one of the XBRL CIKs {final_xbrl_ciks_list} (from CoverPage) for {accession_no}")
                    match_found = True # Fallback match found
            
            if not match_found: # Should be redundant if above logic is correct, but as a safeguard
                self.logger.error(f"Logic error: Match not found for {accession_no} despite passing primary/fallback checks. CIK: {input_cik_to_match}")
                # Check CoverPage (the documented location for CIK)
                cover_cik = xbrl_json.get('CoverPage', {}).get('EntityCentralIndexKey', '0')
                # Ensure the same set object is reused for consistency
                self._add_normalized_cik(cover_cik, xbrl_ciks_set)
                
                # Convert back to list and check for match
                final_xbrl_ciks_list = list(xbrl_ciks_set)
                if not final_xbrl_ciks_list or input_cik_to_match not in final_xbrl_ciks_list:
                    self.logger.warning(f"No CIK match for {accession_no}: input CIK {input_cik_to_match} not in {final_xbrl_ciks_list}")
                    return None
                else:
                    self.logger.info(f"Input CIK {input_cik_to_match} matches one of the XBRL CIKs {final_xbrl_ciks_list} for {accession_no}")
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
        """Download and extract exhibit content with proper SEC rate limiting and timeout"""
        headers = {
            'User-Agent': 'EventTrader research.bot@example.com',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov' # Corrected Host back to www.sec.gov
        }
        REQUEST_TIMEOUT = 60 # seconds

        try:
            # Respect SEC's rate limit
            time.sleep(0.1)
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
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
            self.logger.error(f"Error processing exhibit {url}: {str(e)}", exc_info=True)
            return None



    # These are specifically for 6-K, 13D etc (Non FORM_TYPES_REQUIRING_SECTIONS)
    def _extract_secondary_filing_content(self, url: str) -> Optional[str]:
        """Extract clean text from any SEC filing format with minimal dependencies, with timeout"""
        headers = {
            'User-Agent': 'EventTrader research.bot@example.com',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        REQUEST_TIMEOUT = 180 # seconds
        
        try:
            # Respect SEC's rate limit
            time.sleep(0.1)
            
            # Download with proper headers
            self.logger.info(f"Downloading secondary filing from {url}")
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
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
            self.logger.error(f"Error extracting text from secondary filing {url}: {e}", exc_info=True)
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
            # Basic validation that must stay in main thread
            if not content.get('cik'):
                self.logger.info(f"Report with missing primary filer CIK: {content.get('accessionNo', 'unknown')}")
                content['cik'] = ''
            
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

            # Essential fields only
            standardized.update({
                'id': content.get('accessionNo'),
                'created': content.get('filedAt'),
                'updated': content.get('filedAt'),
                'symbols': list(symbols),
                'formType': content.get('formType'),
                # Initialize these as empty - will be populated in enrichment
                'extracted_sections': None,
                'financial_statements': None,
                'exhibit_contents': None,
                'filing_text_content': None
            })
            
            return standardized
        except Exception as e:
            self.logger.error(f"Error in _standardize_fields: {e}", exc_info=True)
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
            self.logger.error(f"Error in _clean_content: {e}", exc_info=True)
            return content  # Return original if cleaning fails

    def _process_item(self, raw_key: str) -> bool:
        """Modified to use enrichment queue for heavy processing"""
        client = None # Initialize client to None for broader scope in try-except
        try:
            # Determine client based on raw_key prefix
            client = self.hist_client if raw_key.startswith(self.hist_client.prefix) else self.live_client
            prefix_type = RedisKeys.PREFIX_HIST if raw_key.startswith(self.hist_client.prefix) else RedisKeys.PREFIX_LIVE
            identifier = raw_key.split(':')[-1]

            raw_content = client.get(raw_key)
            if not raw_content:
                if self.delete_raw:
                    client.delete(raw_key)
                self.logger.warning(f"Raw content not found: {raw_key}")
                return False

            filing = json.loads(raw_content)

            # Use the updated standardize_fields method which now contains the lightweight logic
            standardized = self._standardize_fields(filing)
            
            # Check if we have valid symbols
            if not self._has_valid_symbols(standardized):
                self.logger.debug(f"Dropping {raw_key} - no matching symbols in universe")
                if self.delete_raw:
                    client.delete(raw_key) # client is guaranteed to be assigned here or error before
                return True
            
            # Clean the content (apply lightweight cleaning)
            processed = self._clean_content(standardized)
            
            # Refined needs_enrichment check using the original 'filing' data for some conditions
            # and 'processed' for formType, as that's standardized.
            form_type = processed.get('formType') # Use standardized formType

            needs_enrichment_due_to_sections = (form_type in FORM_TYPES_REQUIRING_SECTIONS and filing.get('primaryDocumentUrl'))
            # If it's not a "sections" form but has a primary URL, it might need full text extraction by worker
            needs_enrichment_due_to_secondary_text = (form_type not in FORM_TYPES_REQUIRING_SECTIONS and filing.get('primaryDocumentUrl')) 
            needs_enrichment_due_to_xml = (form_type in FORM_TYPES_REQUIRING_XML) # Worker handles actual XML check for financials and the linkToTxt fallback if this is true
            needs_enrichment_due_to_exhibits = bool(filing.get('exhibits'))

            needs_enrichment = (
                needs_enrichment_due_to_sections or
                needs_enrichment_due_to_secondary_text or
                needs_enrichment_due_to_xml or
                needs_enrichment_due_to_exhibits
            )
            
            if needs_enrichment:
                # Queue for enrichment
                # Use deepcopy for safety, ensuring no shared mutable objects with later code paths
                payload_for_enrich_queue = copy.deepcopy(processed) 
                payload_for_enrich_queue['_original_prefix_type'] = prefix_type # Add the original prefix_type
                client.client.rpush(RedisKeys.ENRICH_QUEUE, json.dumps(payload_for_enrich_queue))
                self.logger.info(f"Queued {raw_key} (prefix type: {prefix_type}) for enrichment")
                
                # Delete raw as it's now queued for enrichment
                if self.delete_raw:
                    client.delete(raw_key)
                    
                # Return success
                return True
            else:
                # Continue with normal lightweight processing - add metadata for lightweight items
                metadata = self._add_metadata(processed)
                if metadata:
                    processed['metadata'] = metadata
                    
                # Generate processed key
                processed_key = RedisKeys.get_key(
                    source_type=self.source_type,
                    key_type=RedisKeys.SUFFIX_PROCESSED,
                    prefix_type=prefix_type,
                    identifier=identifier
                )
                
                # Store processed document
                pipe = client.client.pipeline(transaction=True)
                # Add explicit TTL if self.ttl is set (consistency with worker)
                if self.ttl:
                    pipe.set(processed_key, json.dumps(processed), ex=self.ttl)
                else:
                    pipe.set(processed_key, json.dumps(processed))
                pipe.lpush(client.PROCESSED_QUEUE, processed_key)
                pipe.publish(self.processed_channel, processed_key)
                
                if self.delete_raw:
                    pipe.delete(raw_key)
                    
                return all(pipe.execute())
                
        except Exception as e:
            self.logger.error(f"Failed to process {raw_key}: {e}", exc_info=True)
            # Fallback to queue_client if client specific to hist/live failed early or is None
            # This part needs careful handling if the initial client assignment itself fails.
            # However, _process_item is usually called with a valid raw_key from a queue
            # managed by queue_client.
            # If client is None here, it implies an error before its assignment.
            # A robust way is to try and determine the client again or use a default.
            # For now, assuming raw_key is valid enough to determine the context for FAILED_QUEUE
            # Or, more simply, use the default queue_client for pushing to FAILED_QUEUE
            # This is complex because BaseProcessor defines queue_client, hist_client, live_client.
            # Let's assume if an error happens, the raw_key can still inform which FAILED_QUEUE.
            # The original code in BaseProcessor _process_item does: 
            # client = self.hist_client if raw_key.startswith(self.hist_client.prefix) else self.live_client
            # client.push_to_queue(client.FAILED_QUEUE, raw_key)
            # So, if client assignment itself failed, this would also fail.
            # A safer bet for the except block if client might be None:
            final_client_for_fail = client if client else self.queue_client # self.queue_client is from BaseProcessor
            if final_client_for_fail:
                 # Need to ensure FAILED_QUEUE is correctly determined if using hist/live differentiation
                 # The original BaseProcessor's FAILED_QUEUE is dynamically set on the client instance.
                 # So, if client (hist/live) is determined, its FAILED_QUEUE is correct.
                 # If final_client_for_fail is self.queue_client, its FAILED_QUEUE is also correct for its context.
                target_failed_queue = final_client_for_fail.FAILED_QUEUE
                final_client_for_fail.push_to_queue(target_failed_queue, raw_key)
            
            if self.delete_raw and client: # Only delete if client was determined
                client.delete(raw_key)
            elif self.delete_raw and not client:
                 self.logger.warning(f"Could not delete raw_key {raw_key} after failure as client was not determined.")

            return False
