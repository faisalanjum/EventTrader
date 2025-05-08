from pydantic import ValidationError
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
import json
import logging
import os
from dataclasses import dataclass
from collections import Counter
from .sec_schemas import SECFilingSchema, UnifiedReport
from config.feature_flags import FORM_TYPES_REQUIRING_XML

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
        # Use standard logger
        self.logger = logging.getLogger(__name__)
        
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
        """Log detailed info about skipped filing"""
        self.logger.info("Skipped Filing:")
        self.logger.info(f"Form Type: {data.get('formType', 'N/A')}")
        self.logger.info(f"CIK: {data.get('cik', 'N/A')}")
        self.logger.info(f"Company: {data.get('companyName', 'N/A')}")
        self.logger.info(f"Filed At: {data.get('filedAt', 'N/A')}")
        self.logger.info(f"Error: {str(error)}")

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

            self.logger.debug(f"[Filing] Processing formType:{filing.formType}, accessionNo:{filing.accessionNo}, cik:{filing.cik}, filedAt:{filing.filedAt}")

            # Quick XML check for required forms
            if filing.formType in FORM_TYPES_REQUIRING_XML and not any(f.type == 'XML' for f in filing.dataFiles):
                raise ValueError(f"No XML data found for {filing.formType}")

            # Return raw or unified
            try:
                return filing if raw else filing.to_unified()
            except Exception as e:
                self.logger.error(f"[Filing] ❌ Specific UnifiedReport creation error: {str(e)}", exc_info=True)
                raise
                    
        except Exception as e:
            self.logger.error(f"[Filing] ❌ Error: {str(e)}", exc_info=True)
            return None
        



    def handle_json_error(self, error: json.JSONDecodeError, raw_data: str):
        """Handle JSON parsing errors"""
        self.stats.json_errors += 1
        self.logger.error(f"JSON decode error: {str(error)}", exc_info=True)
        if self.debug:
            self.logger.debug(f"Raw data: {raw_data[:100]}...")

    def handle_connection_error(self, error: Exception):
        """Handle connection-related errors with more detail"""
        self.stats.connection_errors += 1
        error_msg = str(error)
        
        if "timeout" in error_msg.lower():
            self.logger.error(f"[SEC WebSocket] Connection timeout: {error_msg}", exc_info=True)
        elif "closed" in error_msg.lower():
            self.logger.error(f"[SEC WebSocket] Connection closed: {error_msg}", exc_info=True)
        else:
            self.logger.error(f"[SEC WebSocket] Connection error: {error_msg}", exc_info=True)
            
        if self.debug:
            self.logger.debug(f"[SEC WebSocket] Connection error details: {error_msg}")

    def get_summary(self) -> str:
        """Get error statistics summary"""
        return str(self.stats)

    def print_summary(self, messages_received: int, messages_processed: int):
        """Log detailed summary including processing stats"""
        self.logger.info("Processing Summary:")
        self.logger.info(f"Messages Received: {messages_received}")
        self.logger.info(f"Messages Processed: {messages_processed}")
        success_rate = (messages_processed / max(1, messages_received)) * 100
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info(str(self.stats))        


    def handle_unexpected_error(self, error: Exception):
        """Handle unexpected errors"""
        self.stats.unexpected_errors += 1
        self.logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        if self.debug:
            self.logger.debug(f"Unexpected error details: {str(error)}")        