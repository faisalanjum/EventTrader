from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .XBRLClasses import Neo4jNode


    
def process_fact_relationships(relationships: List[Tuple]) -> List[Tuple]:
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