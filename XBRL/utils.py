from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING, Union
from datetime import datetime, timedelta

# Runtime imports needed for functions
# Moving DateNode import inside functions to break circular dependency
from .xbrl_core import RelationType

if TYPE_CHECKING:
    from .XBRLClasses import Neo4jNode
    from .xbrl_basic_nodes import DateNode
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



# Added utility functions for date handling
# TODO: This is temporary - later take dateNode creation outside 
def create_date_range(start: str, end: str = None) -> List:
    # Import inside function to break circular import
    from .xbrl_basic_nodes import DateNode
    
    s = datetime.strptime(start, "%Y-%m-%d").date()  # Convert to date
    e = datetime.now().date() if end is None else datetime.strptime(end, "%Y-%m-%d").date()  # Convert to date
    return [DateNode(d.year, d.month, d.day) 
            for d in (s + timedelta(days=i) for i in range((e-s).days + 1))]

# TODO: This is temporary - later take dateNode creation outside 
def create_date_relationships(dates, relationship_type=None) -> List[Tuple]:
    # Import inside function to break circular import
    if relationship_type is None:
        relationship_type = RelationType.NEXT
        
    relationships = []
    for i in range(len(dates) - 1):
        relationships.append((dates[i], dates[i + 1], relationship_type)) 
    return relationships


# TODO: To be replaced later by actual sec-api - This is temporary
def get_company_info(model_xbrl):
    # model_xbrl = get_model_xbrl(instance_url)
    cik = next((context.entityIdentifier[1].lstrip('0') 
                for context in model_xbrl.contexts.values() 
                if context.entityIdentifier and 'cik' in context.entityIdentifier[0].lower()), None)
    name = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'EntityRegistrantName'), None)
    fiscal_year_end = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'CurrentFiscalYearEndDate'), None)
    return cik, name, fiscal_year_end

# TODO: To be replaced later by actual sec-api - This is temporary
def get_report_info(model_xbrl):
    """
    Extract report metadata from model_xbrl.
    Returns a dictionary with all the fields needed for creating a ReportNode.
    """
    # Basic report info
    doc_type = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentType'), 'Unknown')
    period_end_date = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentPeriodEndDate'), 
                          datetime.now().strftime('%Y-%m-%d'))
    is_amendment = next((fact.value.lower() == 'true' for fact in model_xbrl.facts 
                        if fact.qname.localName == 'AmendmentFlag'), False)
    
    # Additional metadata
    period_of_report = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'PeriodOfReport'), None)
    filed_at = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'DocumentEffectiveDate'), None)
    accession_number = next((fact.value for fact in model_xbrl.facts if fact.qname.localName == 'AccessionNumber'), None)
    
    # Remove '/A' from form type if present but preserve the amendment flag
    if doc_type and '/' in doc_type:
        doc_type = doc_type.split('/')[0]
    
    # Return a dictionary with all fields
    return {
        'form_type': doc_type,
        'period_end': period_end_date,
        'is_amendment': is_amendment,
        'period_of_report': period_of_report,
        'filed_at': filed_at,
        'accession_number': accession_number
    }  
