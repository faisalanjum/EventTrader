from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING, Union, Optional
from datetime import datetime, timedelta



import logging
import requests
import time
import tempfile



# Runtime imports needed for functions
# Moving DateNode import inside functions to break circular dependency
from .xbrl_core import RelationType

if TYPE_CHECKING:
    from .XBRLClasses import Neo4jNode
    # RelationType already imported above



def clean_number(value: Union[str, int, float]) -> float:
    """Convert number to float, handling string formatting"""
    if isinstance(value, (int, float)):
        return float(value)
    return float(value.replace(',', ''))
    
def resolve_primary_fact_relationships(relationships: List[Tuple]) -> List[Tuple]:
    """Pre-process relationships to handle fact duplicates"""
    # Quick check if any facts involved
    from XBRL.XBRLClasses import Fact 

    if not any(isinstance(source, Fact) or isinstance(target, Fact) 
            for source, target, *_ in relationships):
        return relationships
        
    processed = []
    for rel in relationships:
        source, target, rel_type, *props = rel

        # Convert facts to primary versions
        if isinstance(source, Fact):
            source = source.primary_fact
        if isinstance(target, Fact):
            target = target.primary_fact
        
        # Skip self-referential relationships
        if source.id == target.id: continue

        processed.append((source, target, rel_type, *props))
    
    return processed

def count_facts_in_relationships(relationships):
    """Count the number of facts in the relationships"""
    source_facts = set()
    target_facts = set()
    for rel in relationships:
        source_facts.add(rel[0])
        target_facts.add(rel[1])
    return len(source_facts), len(target_facts)






import requests
import time
import random
import os
from urllib.parse import urlparse

def download_sec_file(url, max_retries=5, base_delay=1.0):
    """Download a file from SEC with proper headers and retry logic.
    
    Args:
        url: The URL to download
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (will be increased exponentially)
        
    Returns:
        Tuple of (content, temp_file_path) or None if download fails
    """
    # Parse URL to extract filename
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    
    # Create a temporary file
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}")
    
    # Define SEC-friendly headers (required to avoid 403)
    headers = {
        'User-Agent': 'XBRL-Research-Tool/1.0 xbrl-research@example.com',  # Replace with appropriate details
        'Accept-Encoding': 'gzip, deflate',
        'Host': parsed_url.netloc
    }
    
    # Implement exponential backoff
    for attempt in range(max_retries):
        try:
            # Add jitter to delay to avoid thundering herd problem
            delay = (base_delay * (2 ** attempt)) + (random.random() * 0.5)
            
            # Wait before making request (important for rate limiting)
            if attempt > 0:
                print(f"Retry attempt {attempt} after {delay:.2f}s delay...")
                time.sleep(delay)
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            
            # Check for rate limiting or other errors
            if response.status_code == 403:
                print(f"SEC rate limit hit (403), retrying in {delay:.2f}s...")
                continue
                
            # Raise for other status codes
            response.raise_for_status()
            
            # Save content to temp file - THIS IS THE KEY CHANGE:
            # Don't return the response.content, just save it to the file
            with open(temp_file.name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            # Return None for content since we've already streamed it to file
            return None, temp_file.name
            
        except (requests.RequestException, IOError) as e:
            print(f"Download attempt {attempt+1} failed: {str(e)}")
            
            # On last attempt, cleanup and return None
            if attempt == max_retries - 1:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                return None
    
    return None


# TODO: To be replaced later by actual sec-api - This is temporary
# def get_company_info(model_xbrl):
#     # model_xbrl = get_model_xbrl(instance_url)
#     cik = next((context.entityIdentifier[1].lstrip('0') 
#                 for context in model_xbrl.contexts.values() 
#                 if context.entityIdentifier and 'cik' in context.entityIdentifier[0].lower()), None)
#     name = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'EntityRegistrantName'), None)
#     fiscal_year_end = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'CurrentFiscalYearEndDate'), None)
#     return cik, name, fiscal_year_end

# TODO: To be replaced later by actual sec-api - This is temporary
# def get_report_info(model_xbrl):
#     """
#     Extract report metadata from model_xbrl.
#     Returns a dictionary with all the fields needed for creating a ReportNode.
#     """
#     # Basic report info
#     doc_type = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentType'), 'Unknown')
#     period_end_date = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentPeriodEndDate'), 
#                           datetime.now().strftime('%Y-%m-%d'))
#     is_amendment = next((fact.value.lower() == 'true' for fact in model_xbrl.facts 
#                         if fact.qname.localName == 'AmendmentFlag'), False)
#     
#     # Additional metadata
#     period_of_report = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'PeriodOfReport'), None)
#     filed_at = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentEffectiveDate'), None)
#     accession_number = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'AccessionNumber'), None)
#     
#     # Remove '/A' from form type if present but preserve the amendment flag
#     if doc_type and '/' in doc_type:
#         doc_type = doc_type.split('/')[0]
#     
#     # Return a dictionary with all fields
#     return {
#         'form_type': doc_type,
#         'period_end': period_end_date,
#         'is_amendment': is_amendment,
#         'period_of_report': period_of_report,
#         'filed_at': filed_at,
#         'accession_number': accession_number
#     }  
