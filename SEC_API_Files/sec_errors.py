from pydantic import ValidationError
from typing import Optional, Dict, Any, Union
from datetime import datetime
import json
import logging
import os
from dataclasses import dataclass
from collections import Counter
from SEC_API_Files.sec_schemas import SECFilingSchema, UnifiedReport
from SEC_API_Files.sec_schemas import FORM_TYPES_REQUIRING_XML

@dataclass
class FilingErrorStats:
    """Track error statistics"""
    validation_errors: Counter
    skipped_items: Counter
    json_errors: int
    connection_errors: int
    unexpected_errors: int
    
    def __str__(self) -> str:
        return (
            f"\nError Statistics:"
            f"\nJSON Errors: {self.json_errors}"
            f"\n\nValidation Errors:"
            f"  - invalid_form_type: {self.validation_errors['invalid_form_type']}"
            f"  - missing_xml: {self.validation_errors['missing_xml']}"
            f"  - missing_cik: {self.validation_errors['missing_cik']}"
            f"  - invalid_filed_at: {self.validation_errors['invalid_filed_at']}"
            f"  - other: {self.validation_errors['other']}"
            f"\n\nSkipped Items:"
            f"  - No XML data: {self.skipped_items['no_xml']}"
            f"  - Invalid form type: {self.skipped_items['invalid_form']}"
            f"  - Missing required data: {self.skipped_items['missing_required']}"
            f"\n\nUnexpected Errors: {self.unexpected_errors}"        
        )

class FilingErrorHandler:
    """Handles and tracks different types of errors in SEC filing processing"""
    
    def __init__(self):
        self.logger = logging.getLogger('sec_filings')
        self.logger.setLevel(logging.ERROR)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(current_dir, 'sec_filing_errors.log')
        
        fh = logging.FileHandler(log_file_path)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(fh)
        
        self.stats = FilingErrorStats(
            validation_errors=Counter(),
            skipped_items=Counter(),
            json_errors=0,
            connection_errors=0,
            unexpected_errors=0
        )
        self.debug = False

    def reset_stats(self):
        """Reset all error statistics"""
        self.stats = FilingErrorStats(
            validation_errors=Counter(),
            skipped_items=Counter(),
            json_errors=0,
            connection_errors=0,
            unexpected_errors=0
        )

    def print_skipped_filing(self, data: Dict[str, Any], error: Exception) -> None:
        """Print detailed info about skipped filing"""
        print("\nSkipped Filing:")
        print(f"Form Type: {data.get('formType', 'N/A')}")
        print(f"CIK: {data.get('cik', 'N/A')}")
        print(f"Company: {data.get('companyName', 'N/A')}")
        print(f"Filed At: {data.get('filedAt', 'N/A')}")
        print(f"Error: {str(error)}")

    def handle_validation_error(self, error: Exception, raw_item: Dict[str, Any]) -> None:
        """Handle validation errors"""
        error_type = self._classify_validation_error(error)
        self.stats.validation_errors[error_type] += 1
        
        if self.debug:
            self.print_skipped_filing(raw_item, error)
        self.logger.error(f"Validation error ({error_type}): {str(error)}")


    def _classify_validation_error(self, error: Exception) -> str:
        """Classify validation error type"""
        error_str = str(error).lower()
        
        if "form type" in error_str:
            return "invalid_form_type"
        elif "xml" in error_str:
            return "missing_xml"
        elif "cik" in error_str:
            return "missing_cik"
        elif "filed" in error_str:
            return "invalid_filed_at"
        return "other"


    def process_filing(self, raw_item: dict, raw: bool = False) -> Optional[Union[SECFilingSchema, UnifiedReport]]:
        try:
            # Create and validate basic filing
            filing = SECFilingSchema(**raw_item)

            print(f"[Filing] Processing formType:{filing.formType}, accessionNo:{filing.accessionNo}, cik:{filing.cik}, filedAt:{filing.filedAt}")

            # Quick XML check for required forms
            if filing.formType in FORM_TYPES_REQUIRING_XML and not any(f.type == 'XML' for f in filing.dataFiles):
                raise ValueError(f"No XML data found for {filing.formType}")

            # Return raw or unified
            try:
                return filing if raw else filing.to_unified()
            except Exception as e:
                print(f"[Filing] ❌ Specific UnifiedReport creation error: {str(e)}") 
                raise
                    
        except Exception as e:
            print(f"[Filing] ❌ Error: {str(e)}")
            return None
        



    def handle_json_error(self, error: json.JSONDecodeError, raw_data: str):
        """Handle JSON parsing errors"""
        self.stats.json_errors += 1
        self.logger.error(f"JSON decode error: {str(error)}")
        if self.debug:
            print(f"JSON decode error: {str(error)}")
            print(f"Raw data: {raw_data[:100]}...")

    def handle_connection_error(self, error: Exception):
        """Handle connection-related errors with more detail"""
        self.stats.connection_errors += 1
        error_msg = str(error)
        
        if "timeout" in error_msg.lower():
            self.logger.error(f"[SEC WebSocket] Connection timeout: {error_msg}")
        elif "closed" in error_msg.lower():
            self.logger.error(f"[SEC WebSocket] Connection closed: {error_msg}")
        else:
            self.logger.error(f"[SEC WebSocket] Connection error: {error_msg}")
            
        if self.debug:
            print(f"[SEC WebSocket] Connection error: {error_msg}")

    def get_summary(self) -> str:
        """Get error statistics summary"""
        return str(self.stats)

    def print_summary(self, messages_received: int, messages_processed: int):
        """Print detailed summary including processing stats"""
        print("\nProcessing Summary:")
        print(f"Messages Received: {messages_received}")
        print(f"Messages Processed: {messages_processed}")
        success_rate = (messages_processed / max(1, messages_received)) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        print(str(self.stats))        


    def handle_unexpected_error(self, error: Exception):
        """Handle unexpected errors"""
        self.stats.unexpected_errors += 1
        self.logger.error(f"Unexpected error: {str(error)}")
        if self.debug:
            print(f"Unexpected error: {str(error)}")        