from __future__ import annotations
from collections import defaultdict
from typing import Set, List, Optional, Dict, TYPE_CHECKING, Any, Union, Tuple
from datetime import datetime, timedelta
import copy
import logging

if TYPE_CHECKING:
    from XBRL.XBRLClasses import Fact, AbstractConcept, PresentationNode

logger = logging.getLogger(__name__)

# Based on the algorithm in the presentation network definition (See schema)
class ValidationMixin:
    """Mixin providing validation methods for Network class"""

    def __init__(self):
        self.debug = False

    def set_debug(self, enabled: bool = True):
        self.debug = enabled

    def _debug_print(self, *args, **kwargs):
        """Print only if debug mode is enabled"""
        if getattr(self, 'debug', False):
            logger.debug(*args, **kwargs)

    def validate_facts(self, network_type: str = 'presentation') -> Tuple[List[Fact], List[Tuple[Fact, Dict]]]:
        """Validates facts according to network type"""
        # Step 1: Get initial facts based on network type
        if network_type == 'presentation':
            initial_facts = self._get_facts_in_presentation_network()
        else:  # calculation
            initial_facts = self._get_facts_from_calculation()

        # Split into two paths based on hypercube presence
        facts_not_in_hc = self._get_facts_not_in_hypercubes(initial_facts)
        facts_in_hc = self._get_facts_in_hypercubes(initial_facts)
        # print(f"Split facts: {len(facts_not_in_hc)} not in hypercubes, {len(facts_in_hc)} in hypercubes")

        # Process facts not in hypercubes and ignore facts without dimensions which are not in hypercubes
        filtered_non_hc_facts = self._filter_facts_without_dimensions(facts_not_in_hc)
        
        # Process facts in hypercubes
        filtered_hc_facts = self._process_hypercube_facts(facts_in_hc)
        
        # Combine and validate all facts
        all_validated_facts = self._perform_validation_checks(filtered_non_hc_facts, filtered_hc_facts)
        
        return all_validated_facts
        

    def _get_facts_in_presentation_network(self) -> Set[Fact]:

        from XBRL.XBRLClasses import AbstractConcept  # Use absolute import

        facts = {
            fact
            for node in getattr(self.presentation, 'nodes', {}).values()
            if node.concept and node.concept.__class__ != AbstractConcept # Exclude abstract concepts
            for fact in node.concept.facts
        }
        
        return facts

    def _get_facts_from_calculation(self) -> Set[Fact]:
        facts = {
            fact
            for node in getattr(self.calculation, 'nodes', {}).values()
            if node.concept  # No need to check for AbstractConcept
            for fact in node.concept.facts
        }

        return facts



    def _get_facts_not_in_hypercubes(self, facts: Set[Fact]) -> Set[Fact]:
        """Filter facts whose concepts are not in any hypercubes"""
        hypercube_concepts = { concept for hypercube in self.hypercubes for concept in hypercube.concepts}    
        filtered = { fact for fact in facts if fact.concept not in hypercube_concepts }
        # print(f"Facts not in hypercubes - Concepts: {[f.concept.qname for f in filtered]}")
        return filtered

    def _get_facts_in_hypercubes(self, facts: Set[Fact]) -> Set[Fact]:
        """Filter facts whose concepts are in hypercubes"""
        hypercube_concepts = { concept for hypercube in self.hypercubes for concept in hypercube.concepts}
        return { fact for fact in facts if fact.concept in hypercube_concepts }


    def _filter_facts_without_dimensions(self, facts: Set[Fact]) -> Set[Fact]:
        """Filter facts without dimensions and match periods"""
        if not facts:
            return set()
        
        filtered = {fact for fact in facts if not fact.dims_members} # No dimensions
        return filtered



    def _process_hypercube_facts(self, facts: Set[Fact]) -> Set[Fact]:
        """Process facts in hypercubes according to algorithm"""
        if not facts:
            return set()
            
        # Facts without dimensions are valid with implicit default members
        facts_without_dims = {fact for fact in facts if not fact.dims_members}
        
        # Facts with dimensions need processing for each hypercube
        facts_with_dims = {fact for fact in facts if fact.dims_members}
        valid_facts = set()
        
        # Process each fact
        for fact in facts_with_dims:
            is_valid_for_all_hypercubes = True
            
            # Must be valid for every hypercube
            for hypercube in self.hypercubes:

                # only adding default members to dimensions where members are missing
                processed_fact = self._process_fact_for_hypercube(fact, hypercube)
                if not processed_fact:
                    is_valid_for_all_hypercubes = False
                    break
                    
            if is_valid_for_all_hypercubes:
                valid_facts.add(fact)
        
        # Combine with facts without dimensions
        return facts_without_dims.union(valid_facts)

    def _process_fact_for_hypercube(self, fact: Fact, hypercube) -> Optional[Fact]:  
        """Process a single fact for a specific hypercube"""
        try:
            if any(member is None for _, member in fact.dims_members):
                return self._add_default_members_to_fact(fact)
            return fact
        except Exception as e:
            self._debug_print(f"Error processing fact {fact.id}: {str(e)}")
            return None

    # Uses copy of fact to avoid modifying original fact
    def _add_default_members_to_fact(self, fact: Fact) -> Optional[Fact]:
        """Create a copy of fact and add default members where missing"""
        try:
            # Create shallow copy of fact
            new_fact = copy.copy(fact)
            new_dims_members = []
            
            for dimension, member in fact.dims_members:
                if member is None:
                    default_member = dimension.default_member
                    if default_member is None:
                        # print(f"Warning: No default member for dimension {dimension.qname}")
                        return None
                    new_dims_members.append((dimension, default_member))
                else:
                    new_dims_members.append((dimension, member))
            
            new_fact.dims_members = new_dims_members
            return new_fact
            
        except Exception as e:
            logger.error(f"Error processing fact {fact.u_id}: {str(e)}")
            return None


    def _check_closed_validation(self, facts: Set[Fact]) -> Set[Fact]:
        """CHECK1: Remove facts with dimensions not in hypercubes"""
        valid_facts = set()
        
        for fact in facts:
            is_valid_for_all_hypercubes = True
            
            for hypercube in self.hypercubes:
                if hypercube.closed:
                    
                    hypercube_dimensions = {dim for dim in hypercube.dimensions} # Get all dimensions in this hypercube
                    fact_dimensions = {dim for dim, _ in fact.dims_members} # Get fact's dimensions
                    
                    # If fact has any dimension not in hypercube, it's invalid for this hypercube
                    if not fact_dimensions.issubset(hypercube_dimensions):
                        is_valid_for_all_hypercubes = False
                        break
            
            if is_valid_for_all_hypercubes:
                valid_facts.add(fact)
                
        return valid_facts

    def _check_all_dimensions_present(self, facts: Set[Fact]) -> Set[Fact]:
        """CHECK2: Remove facts that don't include all dimensions in hypercube"""
        valid_facts = set()
        
        for fact in facts:
            is_valid = True
            for hypercube in self.hypercubes:
                if hypercube.is_all:
                    # Get all dimensions in this hypercube
                    hypercube_dimensions = {dim for dim in hypercube.dimensions}
                    
                    # Get fact's dimensions
                    fact_dimensions = {dim for dim, _ in fact.dims_members}
                    
                    # If fact doesn't have all hypercube dimensions, it's invalid
                    if not hypercube_dimensions.issubset(fact_dimensions):
                        is_valid = False

                        break
            
            if is_valid:
                valid_facts.add(fact)
                
        return valid_facts


    def _perform_validation_checks(self, non_hc_facts: Set[Fact], hc_facts: Set[Fact]) -> List[Fact]:
        """Perform validation checks with detailed logging"""
        non_hc_facts = non_hc_facts or set()
        hc_facts = hc_facts or set()
        
        # Split hypercube facts into with/without dimensions
        hc_facts_with_dims = {fact for fact in hc_facts if fact.dims_members}
        hc_facts_without_dims = {fact for fact in hc_facts if not fact.dims_members}
        
    
        # CHECK1: Closed validation - Only apply validation checks to facts WITH dimensions
        after_check1 = self._check_closed_validation(hc_facts_with_dims) or set()
        
        # CHECK2: All dimensions present
        after_check2 = self._check_all_dimensions_present(after_check1) or set()
        
        # CHECK3: Dimension-member match
        validated_hc_facts = self._check_dimension_member_match(after_check2) or set()

        # Combine all valid facts from:
        # 1. Non-hypercube facts without dimensions (already valid)
        # 2. Hypercube facts without dimensions (valid by default)
        # 3. Validated hypercube facts with dimensions
        combined_valid_facts = non_hc_facts.union(hc_facts_without_dims).union(validated_hc_facts)

        return combined_valid_facts


    def _check_dimension_member_match(self, facts: Set[Fact]) -> Set[Fact]:
        """CHECK3: Match facts' dimensions/members with hypercube"""
        valid_facts = set()
        taxonomy = self.report.taxonomy if hasattr(self, 'report') else None


        for fact in facts:
            is_valid = True
            fact_dims_members = dict(fact.dims_members)  # Convert to dict for easier lookup
            
            for hypercube in self.hypercubes:

                fact_dims_members = dict(fact.dims_members)

                # Get hypercube dimensions and their members
                hypercube_dims_members = {
                    dim: dim.members_dict
                    for dim in hypercube.dimensions
                }
                
                # Check each fact dimension-member pair
                for fact_dim, fact_member in fact_dims_members.items():
                    if fact_dim in hypercube_dims_members:
                        # Case 1: Dimension exists in hypercube
                        # Validate member against hypercube's dimension members
                        if fact_member not in hypercube_dims_members[fact_dim].values():
                            is_valid = False
                            break
                    else:
                        # Case 2: Extra dimension in fact
                        # Validate member against taxonomy-wide dimension members
                        taxonomy_dim = next(
                            (dim for dim in self.taxonomy.dimensions 
                            if dim.qname == fact_dim.qname),
                            None
                        )
                        
                        if not taxonomy_dim or fact_member not in taxonomy_dim.members_dict.values():
                            is_valid = False
                            break
                
                if not is_valid:
                    break
                    
            if is_valid:
                valid_facts.add(fact)
        
        return valid_facts