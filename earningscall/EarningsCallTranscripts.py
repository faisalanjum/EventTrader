from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from earningscall import get_calendar
import pandas as pd
import pytz
import threading
import time
import logging
import json
from types import SimpleNamespace
from typing import Dict, List, Union, Set
from earningscall import get_company
from eventtrader.keys import OPENAI_API_KEY, EARNINGS_CALL_API_KEY

# Initialize OpenAI with API key using new client pattern
from openai import OpenAI
import earningscall


class EarningsCallProcessor:
    def __init__(self, api_key=None):

        #EarningsCall API Configuration
        if api_key: earningscall.api_key = api_key # Only set if provided
        earningscall.enable_requests_cache = True  # Enable caching for faster responses                
        earningscall.retry_strategy = {"strategy": "exponential",  "base_delay": 2,   "max_attempts": 10,}

        self.ny_tz = pytz.timezone('America/New_York')

        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.rate_limiter = ModelRateLimiter()
        
        self.symbols = []
        self.company_dict = {}

        self.load_companies()
        

    
    def load_companies(self):

        # This will either be loaded from Neo4j Nodes or passed in as a parameter
        self.symbols = pd.read_csv("../StocksUniverse/final_symbols.csv")['symbol'].tolist()
        
        # This fetches the company object for each symbol from the EarningsCall API 
        for ticker in self.symbols:
            company_obj = get_company(ticker)

            # IMPORTANT: Get fiscal year end month and day from Neo4j Company Nodes
            self.company_dict[ticker] = SimpleNamespace( 
                company_obj=company_obj,     # company_obj.events() requires seperate API calls for each symbol
                fiscal_year_end_month=12, 
                fiscal_year_end_day=31
            )


    # Same as inbuilt get_calendar() except conference_date is converted to America/New_York
    def get_earnings_events(self, target_date):
        calendar = get_calendar(target_date)
        events = []
        for event in calendar:
            event.conference_date = event.conference_date.astimezone(ZoneInfo("America/New_York"))
            # events.append(event.to_dict())
            events.append(event)
        return events



    # Get Transcripts for a single date - Includes many companies 
    def get_transcripts_for_single_date(self, target_date):
        """Get transcripts for a single date."""
        # Parse the date with parser function
        target_date = self._parse_dates_fn(target_date)
        
        target_date_events = self.get_earnings_events(target_date)
        final_events = []

        for calendar_event in target_date_events:
            if calendar_event.symbol.upper() in self.company_dict:
                company_obj = self.company_dict[calendar_event.symbol.upper()].company_obj
                print(f"Found company_obj for {calendar_event.symbol}")
            
            else:
                print(f"{calendar_event.symbol} Not in the database")
                company_obj = get_company(calendar_event.symbol)
                print(f"Did not find company_obj for {calendar_event.symbol}, getting from earningscall") 

            earnings_event = next((e for e in company_obj.events() if e.conference_date == calendar_event.conference_date), None)

            if calendar_event.transcript_ready:
                final_events.append(self.get_single_event(company_obj, earnings_event))

            else:
                print(f"Transcript not ready for {calendar_event.company_name} on {calendar_event.conference_date}")

       

        return final_events            




    # Pass ticker & start/end dates to fetch all transcripts
    def get_transcripts_by_date_range(self, ticker: str, start_date: Union[datetime, str], end_date: Union[datetime, str]) -> List[Dict]:

        ticker = ticker.upper() # Ensure ticker is uppercase

        # Converts a string or naive datetime to a New York timezone-aware datetime object..
        if isinstance(start_date, str):
            start_date = self.ny_tz.localize(datetime.strptime(start_date, "%Y-%m-%d"))
        elif start_date.tzinfo is None:
            start_date = self.ny_tz.localize(start_date)
        
        # set to the end of the day (23:59:59), ensuring the full day is included in any date range or filter
        if isinstance(end_date, str):
            end_date = self.ny_tz.localize(datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
        elif end_date.tzinfo is None:
            end_date = self.ny_tz.localize(end_date.replace(hour=23, minute=59, second=59))
        
        if ticker in self.company_dict:
            print(f"DEBUG: Using locally stored company object for {ticker}")
            company_obj = self.company_dict[ticker].company_obj  # Fetch locally stored company object
        else:
            print(f"DEBUG: Fetching company object from EarningsCall API for {ticker}")
            company_obj = get_company(ticker)

        results = []

        now = self.ny_tz.localize(datetime.now())
        
        # Skips events outside the start–end date range or in the future.
        for event in company_obj.events():
            event_date = event.conference_date.astimezone(self.ny_tz)
            if now < event_date or event_date < start_date or event_date > end_date:
                continue

            results.extend(self.get_single_event(company_obj, event))

        return results



    def get_single_event(self, company_obj, event):
        
        """ Retrieve and process transcript data for a single earnings call event.        
            This function can be called directly without going through get_transcripts_by_date_range.
            Make sure to call initialize_api() with your API key before using this function.            
            Returns: List containing a single transcript data dictionary if successful, empty list otherwise"""
        
        results = []
        result = None
        event_date = event.conference_date.astimezone(self.ny_tz)
        
        try:
            # Safely get the symbol upfront to avoid errors later
            symbol = None
            try:
                if hasattr(company_obj, 'company_info') and hasattr(company_obj.company_info, 'symbol'):
                    symbol = company_obj.company_info.symbol
            except:
                pass
            
            result = {
                "symbol": symbol if symbol else str(company_obj),
                "company_name": str(company_obj),
                "fiscal_quarter": event.quarter,
                "fiscal_year": event.year,
                "calendar_quarter": None,  # set later using fiscal_to_calendar()
                "calendar_year": None,     # set later using fiscal_to_calendar()
                "conference_datetime": event_date,
                "speakers": {},
                "prepared_remarks": [],
                "questions_and_answers": [],
                "qa_pairs": [],
                "full_transcript": "",
                "speaker_roles_LLM": {}      # set later using classify_speakers() LLM Calls
            }
            
            transcript_level3 = company_obj.get_transcript(event=event, level=3)
            if not transcript_level3 or not hasattr(transcript_level3, "speakers"):
                return []

            # Extract speakers and titles
            for speaker in transcript_level3.speakers:
                if hasattr(speaker, "speaker_info"):
                    name = getattr(speaker.speaker_info, "name", "Unknown")
                    title = getattr(speaker.speaker_info, "title", "")
                    result["speakers"][name] = title
            
            # Classify speakers using LLM to get analyst, executive, or operator roles
            speaker_roles = self.classify_speakers(result["speakers"])
            result["speaker_roles_LLM"] = speaker_roles
            
            # Debug: print all analysts
            analysts = [name for name, role in speaker_roles.items() if role == "ANALYST"]
            print(f"Analysts found: {analysts} for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
            
            # Create segments
            segments = []
            for speaker in transcript_level3.speakers:
                if hasattr(speaker, "start_times") and speaker.start_times and hasattr(speaker, "text"):
                    start_time = min(speaker.start_times)
                    text = speaker.text
                    speaker_name = "Unknown"
                    if hasattr(speaker, "speaker_info") and hasattr(speaker.speaker_info, "name"):
                        speaker_name = speaker.speaker_info.name
                        if not speaker_name:  # Sometimes name can be empty
                            speaker_name = "Unknown"
                    formatted_text = f"{speaker_name} [{round(start_time)}]: {text}"
                    segments.append((start_time, formatted_text, text))
            
            # Debug: print number of segments
            print(f"Number of segments: {len(segments)} for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
            
            # If no segments, handle specially
            if not segments:
                print(f"No segments found for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                result["prepared_remarks"] = []
                result["questions_and_answers"] = []
                results.append(result)
                return results
            
            # Try to get level 4 transcript
            transcript_level4 = None
            try:
                transcript_level4 = company_obj.get_transcript(event=event, level=4)
                if transcript_level4:
                    print(f"Level 4 transcript found for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                    # Validate level 4 transcript content
                    if not hasattr(transcript_level4, "prepared_remarks") or not hasattr(transcript_level4, "questions_and_answers"):
                        print(f"Level 4 transcript missing required attributes for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                        transcript_level4 = None
                    elif transcript_level4.prepared_remarks is None or transcript_level4.questions_and_answers is None:
                        print(f"Level 4 transcript has None content for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                        transcript_level4 = None
                else:
                    print(f"Level 4 transcript NOT available for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
            except Exception as e:
                print(f"Error getting level 4 transcript: {e}")
                transcript_level4 = None
            
            # Detect Q&A boundary
            qa_start_index = None
            
            if transcript_level4:
                # Method 1: Use level 4 transcript to find Q&A boundary
                prepared_remarks = transcript_level4.prepared_remarks
                qa_text = transcript_level4.questions_and_answers
                
                # Sanity check for qa_text
                if not qa_text or qa_text.strip() == "":
                    print(f"Empty Q&A text in level 4 transcript for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                    # Fall back to analyst detection method
                    for i, (_, formatted_text, _) in enumerate(segments):
                        if "[" in formatted_text:
                            parts = formatted_text.split("[", 1)
                            speaker_name = parts[0].strip()
                            role = speaker_roles.get(speaker_name)
                            if role == "ANALYST":
                                qa_start_index = i
                                break
                else:
                    # Try to match Q&A text from level 4
                    qa_match_found = False
                    for i, (_, _, text) in enumerate(segments):
                        snippet = text.strip().replace("\n", " ")[:80]  # 80 characters match
                        if snippet and snippet in qa_text:
                            qa_start_index = i
                            qa_match_found = True
                            break
                    
                    # If no match found with level 4, fall back to analyst detection
                    if not qa_match_found:
                        print(f"No Q&A match found in level 4 for {company_obj.company_info.symbol} Q{event.quarter} {event.year}, falling back to analyst detection")
                        for i, (_, formatted_text, _) in enumerate(segments):
                            if "[" in formatted_text:
                                parts = formatted_text.split("[", 1)
                                speaker_name = parts[0].strip()
                                role = speaker_roles.get(speaker_name)
                                if role == "ANALYST":
                                    qa_start_index = i
                                    break
            else:
                # Method 2: Use speaker roles to find first analyst as Q&A boundary
                for i, (_, formatted_text, _) in enumerate(segments):
                    # Extract speaker name before the opening bracket
                    if "[" in formatted_text:
                        parts = formatted_text.split("[", 1)
                        speaker_name = parts[0].strip()
                        # Look up the role in speaker_roles
                        role = speaker_roles.get(speaker_name)
                        if role == "ANALYST":
                            qa_start_index = i
                            break
            
            if qa_start_index is None:
                print(f"No Q&A boundary found for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                prepared_part = segments
                qa_part = []
                # Also store as full_transcript when boundary can't be determined for better semantic accuracy
                result["full_transcript"] = "\n".join([t[2] for t in sorted(segments, key=lambda x: x[0])])
            else:
                print(f"Q&A boundary found at position {qa_start_index} for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                prepared_part = segments[:qa_start_index]
                qa_part = segments[qa_start_index:]
            
            result["prepared_remarks"] = [t[1] for t in sorted(prepared_part, key=lambda x: x[0])]
            result["questions_and_answers"] = [t[1] for t in sorted(qa_part, key=lambda x: x[0])]

            # Form Q&A pairs using speaker roles if there are Q&A parts
            if qa_part:
                print(f"Forming {len(qa_part)} Q&A pairs for {company_obj.company_info.symbol} Q{event.quarter} {event.year}")
                try:
                    self.form_qa_pairs(qa_part, speaker_roles, result)
                except Exception as e:
                    print(f"Error in form_qa_pairs: {e}")
                    result["qa_pairs"] = []
            else:
                result["qa_pairs"] = []  # Initialize with empty list if no Q&A
                

            # Add calendar year and quarter
            # IMPORTANT: This is to be supplied from Neo4j Company Node
            
            # TO BE CHANGES once we have the fiscal_year_end_month from the Neo4j Company Node
            fiscal_month_end = 12
            # fiscal_month_end = getattr(self.company_dict[company_obj.company_info.symbol], 'fiscal_year_end_month', 12)


            cal_year, cal_quarter = self.fiscal_to_calendar(result['fiscal_year'], result['fiscal_quarter'], fiscal_month_end)
            result["calendar_year"] = cal_year
            result["calendar_quarter"] = cal_quarter


            # Ensure full_transcript is available when qa_pairs is empty
            # if not result["qa_pairs"] and not result["full_transcript"] and qa_part:
            #     result["full_transcript"] = "\n".join([t[2] for t in sorted(segments, key=lambda x: x[0])])
            
            # Final fallback: Populate full_transcript when priority conditions fail
            if (not result["prepared_remarks"] or (not result["qa_pairs"] and not result["questions_and_answers"])) and not result["full_transcript"]:
                # Use level 1 transcript for cleaner text (same as error handler)
                basic_transcript = company_obj.get_transcript(event=event, level=1)
                if basic_transcript and hasattr(basic_transcript, "text") and basic_transcript.text:
                    result["full_transcript"] = basic_transcript.text
                    
            results.append(result)
        
        except Exception as e:
            print(f"Error processing transcript for Q{event.quarter} {event.year}: {e}")
            
            try:
                # First try getting speakers if needed
                if result is not None and not result["speakers"] and transcript_level3 and hasattr(transcript_level3, "speakers"):
                    for speaker in transcript_level3.speakers:
                        if hasattr(speaker, "speaker_info"):
                            name = getattr(speaker.speaker_info, "name", "Unknown")
                            title = getattr(speaker.speaker_info, "title", "")
                            if name is not None:
                                result["speakers"][name] = title
                
                # Simple fallback - try level 1 for text
                basic_transcript = company_obj.get_transcript(event=event, level=1)
                if basic_transcript and hasattr(basic_transcript, "text") and basic_transcript.text:
                    # For problematic transcripts, store full transcript as well as in prepared remarks
                    result["full_transcript"] = basic_transcript.text
                    result["qa_pairs"] = []  # Ensure qa_pairs is always initialized
                    
                    # IMPORTANT: This is to be supplied from Neo4j Company Node

                    # TO BE CHANGES once we have the fiscal_year_end_month from the Neo4j Company Node
                    fiscal_month_end = 12
                    # fiscal_month_end = getattr(self.company_dict[company_obj.company_info.symbol], 'fiscal_year_end_month', 12)

                    cal_year, cal_quarter = self.fiscal_to_calendar(result['fiscal_year'], result['fiscal_quarter'], fiscal_month_end)
                    result["calendar_year"] = cal_year
                    result["calendar_quarter"] = cal_quarter
                    
                    results.append(result)
            except Exception as inner_e:
                print(f"Error in fallback processing: {inner_e}")
                pass
            
        return results


    def classify_speakers(self, speakers: Dict[str, str], model="gpt-4o") -> Dict[str, str]:
        """Classify speakers from earnings call as ANALYST, EXECUTIVE, or OPERATOR"""

        if not speakers:
            return {}
        
        # Check rate limits
        self.rate_limiter.wait_if_needed(model)
        
        # Prepare speaker info
        speaker_info = "\n".join([f"Name: {name}, Title: {title}" for name, title in speakers.items()])

        try:
            # Use the Responses API with structured outputs
            response = self.openai_client.responses.create(
                model=model,
                # input=f"Classify these earnings call speakers:\n{speaker_info}",
                input=[
            {"role": "system", "content": "Classify each earnings call speaker as exactly one of: ANALYST, EXECUTIVE, or OPERATOR."},
            {"role": "user", "content": f"Classify these earnings call speakers:\n{speaker_info}"}
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "speaker_classification",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "classifications": {
                                    "type": "object",
                                    "additionalProperties": {
                                        "type": "string",
                                        "enum": ["ANALYST", "EXECUTIVE", "OPERATOR"]
                                    }
                                }
                            },
                            "additionalProperties": False
                        }
                    }
                },
                temperature=0.0
            )

            # Parse the response from the Responses API format
            if response.output and len(response.output) > 0:
                # Check for refusal
                for item in response.output[0].content:
                    if item.type in ["response.refusal.delta", "response.refusal.done"]:
                        print(f"Model refused the classification request for {list(speakers.keys())}")
                        return {}
                    
                # Find the content item of type "output_text"
                for item in response.output[0].content:
                    if item.type == "output_text":
                        parsed = json.loads(item.text)
                        if "classifications" in parsed:
                            # Filter to include only valid speakers and roles
                            return {
                                name: role
                                for name, role in parsed["classifications"].items()
                                if name in speakers and role in ["ANALYST", "EXECUTIVE", "OPERATOR"]
                            }

            return {}
        
        except Exception as e:
            print(f"Error during speaker classification: {e}")
            return {}



    def form_qa_pairs(self, qa_segments, speaker_roles, result):
        """
        Form structured Q&A pairs from transcript segments, preserving chronological order
        while grouping consecutive exchanges from the same analyst.
        
        Args:
            qa_segments: List of (start_time, formatted_text, raw_text) tuples
            speaker_roles: Dictionary mapping speaker names to roles (ANALYST, EXECUTIVE, OPERATOR)
            result: Result dictionary to update with qa_pairs
        """
        try:
            if not qa_segments or not speaker_roles:
                result["qa_pairs"] = []
                return
                
            qa_pairs = []
            current_pair = None
            last_analyst = None
            
            # Sort segments by start time
            sorted_segments = sorted(qa_segments, key=lambda x: x[0])
            
            for start_time, formatted_text, raw_text in sorted_segments:
                # Skip invalid segments
                if not formatted_text or "[" not in formatted_text:
                    continue
                    
                # Extract speaker name
                parts = formatted_text.split("[", 1)
                speaker_name = parts[0].strip()
                if not speaker_name:
                    continue
                    
                # Get role and title
                role = speaker_roles.get(speaker_name, "UNKNOWN")
                title = result["speakers"].get(speaker_name, "")
                
                # Skip operators
                if role == "OPERATOR":
                    continue
                    
                # Handle analysts
                if role == "ANALYST":
                    # Create new pair if this is a different analyst than the last one
                    if speaker_name != last_analyst:
                        # Save previous pair if it exists
                        if current_pair and current_pair.get("exchanges"):
                            qa_pairs.append(current_pair)
                        
                        # Create new pair with this analyst
                        current_pair = {
                            "exchanges": [],
                            "questioner": speaker_name,
                            "questioner_title": title,
                            "responders": set(),
                            "responder_titles": {}
                        }
                        last_analyst = speaker_name
                    
                    # Add question to exchanges
                    current_pair["exchanges"].append({
                        "question": {
                            "text": formatted_text,
                            "speaker": speaker_name,
                            "title": title
                        }
                    })
                            
                # Handle executives
                elif role == "EXECUTIVE":
                    if current_pair:
                        # Add answer to exchanges
                        current_pair["exchanges"].append({
                            "answer": {
                                "text": formatted_text,
                                "speaker": speaker_name,
                                "title": title
                            }
                        })
                        current_pair["responders"].add(speaker_name)
                        current_pair["responder_titles"][speaker_name] = title
            
            # Add the last pair if it exists
            if current_pair and current_pair.get("exchanges"):
                qa_pairs.append(current_pair)
            
            # Convert responders sets to strings and format responder titles
            for pair in qa_pairs:
                if pair.get("responders"):
                    responder_names = list(pair["responders"])
                    pair["responders"] = ", ".join(responder_names)
                    
                    # Create responder_titles_str
                    responder_titles_list = []
                    for name in responder_names:
                        title = pair["responder_titles"].get(name, "")
                        if title:
                            responder_titles_list.append(title)
                    pair["responder_title"] = ", ".join(responder_titles_list)
                else:
                    pair["responders"] = ""
                    pair["responder_title"] = ""
                    
                # Clean up the temporary dict
                if "responder_titles" in pair:
                    del pair["responder_titles"]
            
            # Add to result
            result["qa_pairs"] = qa_pairs
        except Exception as e:
            print(f"Error in form_qa_pairs: {e}")
            result["qa_pairs"] = []

    # Final Functions for Mapping Calendar to Fiscal and vice versa
    def calendar_to_fiscal(self, cal_year, cal_quarter, fiscal_month_end):
        month = [3, 6, 9, 12][cal_quarter - 1]
        fiscal_year = cal_year + 1 if month > fiscal_month_end else cal_year
        fiscal_q = ((month - fiscal_month_end - 1) % 12) // 3 + 1
        return fiscal_year, fiscal_q

    def fiscal_to_calendar(self, fiscal_year, fiscal_quarter_int, fiscal_month_end):
        # Handle None values to prevent subtraction errors
        if fiscal_year is None or fiscal_quarter_int is None:
            return None, None
            
        month = (fiscal_month_end - 3 * (4 - fiscal_quarter_int)) % 12 or 12
        cal_year = fiscal_year - 1 if month > fiscal_month_end else fiscal_year
        cal_q = (month - 1) // 3 + 1
        return cal_year, cal_q



    def _parse_dates_fn(self, date_input):
        """
        Parse date input in various formats.
        
        Supports:
        - Date objects
        - Datetime objects
        - Strings in formats like "2025-01-10", "2025,1,10", etc.
        
        Returns a date object.
        """
        if isinstance(date_input, datetime):
            return date_input.date()
        elif hasattr(date_input, 'date') and callable(getattr(date_input, 'date')):
            # Handle objects with date() method
            return date_input.date()
        elif isinstance(date_input, str):
            # Handle different string formats
            date_str = date_input.replace(',', '-')  # Convert commas to hyphens
            for fmt in ['%Y-%m-%d', '%Y-%-m-%-d', '%Y-%m-%-d', '%Y-%-m-%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            # If we got here, none of the formats worked
            raise ValueError(f"Could not parse date string: {date_input}. Use format YYYY-MM-DD or YYYY,MM,DD")
        return date_input  # Assume it's already a date object



import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ModelRateLimiter:
    """Rate limiter for different LLM models"""
    
    def __init__(self):
        self.model_limits = {
            "gpt-3.5-turbo": 3500,  # RPM for GPT-3.5
            "gpt-4": 500,           # RPM for GPT-4
            # Add other models as needed
        }
        self.model_requests = {model: [] for model in self.model_limits}
        self._lock = threading.Lock()
        
    
    def wait_if_needed(self, model):
        """Wait if rate limit is approaching for specific model"""
        with self._lock:
            if model not in self.model_limits:
                return
                
            rpm_limit = self.model_limits[model]
            now = time.time()
            
            # Clean old requests
            self.model_requests[model] = [t for t in self.model_requests[model] if now - t < 60]
            
            # Wait if needed
            if len(self.model_requests[model]) >= rpm_limit:
                wait_time = 60 - (now - self.model_requests[model][0]) + 0.1
                logger.info(f"Rate limit for {model} approaching, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                
            # Record request
            self.model_requests[model].append(time.time())




