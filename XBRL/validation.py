from __future__ import annotations
from typing import Set, List, Optional, Dict, TYPE_CHECKING, Any, Union
from datetime import datetime, timedelta
import copy

if TYPE_CHECKING:
    from XBRL.XBRLClasses import Fact, AbstractConcept, PresentationNode


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
            print(*args, **kwargs)


    def validate_facts(self) -> List[Fact]:
        """Validates facts according to presentation network definition algorithm"""
        
        # Step 1: Facts -> Concepts -> PN (Presentation Network)
        facts_in_pn = self._get_facts_in_presentation_network()
        print(f"Found {len(facts_in_pn)} facts in presentation network")
        
        # Split into two paths based on hypercube presence
        facts_not_in_hc = self._get_facts_not_in_hypercubes(facts_in_pn)
        facts_in_hc = self._get_facts_in_hypercubes(facts_in_pn)
        print(f"Split facts: {len(facts_not_in_hc)} not in hypercubes, {len(facts_in_hc)} in hypercubes")

        # Process facts not in hypercubes and ignore facts without dimensions which are not in hypercubes
        filtered_non_hc_facts = self._filter_facts_without_dimensions(facts_not_in_hc)
        
        # Process facts in hypercubes
        filtered_hc_facts = self._process_hypercube_facts(facts_in_hc)
        
        # Combine and validate all facts
        all_validated_facts = self._perform_validation_checks(filtered_non_hc_facts, filtered_hc_facts)
        
        return all_validated_facts


    def _get_facts_in_presentation_network(self) -> Set[Fact]:

        """Get all facts from concepts in the presentation network"""
        print(f"\nDEBUG - Before getting facts for network: {self.name}")
        print(f"Total presentation nodes: {len(getattr(self.presentation, 'nodes', {}))}")

        from XBRL.XBRLClasses import AbstractConcept  # Use absolute import

        facts = {
            fact
            for node in getattr(self.presentation, 'nodes', {}).values()
            if node.concept and node.concept.__class__ != AbstractConcept # Exclude abstract concepts
            for fact in node.concept.facts
        }
        
        print(f"DEBUG - Presentation Network Fact collection:")
        print(f"Node concepts with facts: {len([node for node in getattr(self.presentation, 'nodes', {}).values() if node.concept and node.concept.__class__ != AbstractConcept and node.concept.facts])}")

        return facts


    def _get_facts_not_in_hypercubes(self, facts: Set[Fact]) -> Set[Fact]:
        """Filter facts whose concepts are not in any hypercubes"""
        hypercube_concepts = { concept for hypercube in self.hypercubes for concept in hypercube.concepts}    
        filtered = { fact for fact in facts if fact.concept not in hypercube_concepts }
        print(f"Facts not in hypercubes - Concepts: {[f.concept.qname for f in filtered]}")
        return filtered

    def _get_facts_in_hypercubes(self, facts: Set[Fact]) -> Set[Fact]:
        """Filter facts whose concepts are in hypercubes"""
        hypercube_concepts = { concept for hypercube in self.hypercubes for concept in hypercube.concepts}
        return { fact for fact in facts if fact.concept in hypercube_concepts }


    def _filter_facts_without_dimensions(self, facts: Set[Fact]) -> Set[Fact]:
        """Filter facts without dimensions and match periods"""
        if not facts:
            return set()
        
        # TODO: Group by Period
        # Extra filter: Match Period with Report Period (& prev)

        filtered = {fact for fact in facts if not fact.dims_members} # No dimensions
        print(f"Facts without dimensions - IDs: {[f.id for f in filtered]}")
        # return self._filter_by_period(filtered)
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
                        print(f"Warning: No default member for dimension {dimension.qname}")
                        return None
                    new_dims_members.append((dimension, default_member))
                else:
                    new_dims_members.append((dimension, member))
            
            new_fact.dims_members = new_dims_members
            return new_fact
            
        except Exception as e:
            print(f"Error processing fact {fact.u_id}: {str(e)}")
            return None


    def _check_closed_validation(self, facts: Set[Fact]) -> Set[Fact]:
        """CHECK1: Remove facts with dimensions not in hypercubes"""
        valid_facts = set()
        
        for fact in facts:
            is_valid_for_all_hypercubes = True
            
            for hypercube in self.hypercubes:
                if hypercube.closed:
                    
                    # Only for debugging
                    # fact_dims = {dim.qname for dim, _ in fact.dims_members}
                    # hc_dims = {dim.qname for dim in hypercube.dimensions}
                    # print(f"Closed validation - Fact {fact.id}:")
                    # print(f"  Fact dimensions: {fact_dims}")
                    # print(f"  Hypercube dimensions: {hc_dims}")

                    hypercube_dimensions = {dim for dim in hypercube.dimensions} # Get all dimensions in this hypercube
                    fact_dimensions = {dim for dim, _ in fact.dims_members} # Get fact's dimensions
                    
                    # If fact has any dimension not in hypercube, it's invalid for this hypercube
                    if not fact_dimensions.issubset(hypercube_dimensions):
                        # print(f"Fact ID:{fact.id} failed closed validation:")
                        # print(f"  - Fact dimensions: {[d.qname for d in fact_dimensions]}")
                        # print(f"  - Hypercube dimensions: {[d.qname for d in hypercube_dimensions]}")
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
                        print(f"Fact {fact.id} failed dimension presence check:")
                        print(f"  - Missing dimensions: {[d.qname for d in hypercube_dimensions - fact_dimensions]}")
                        is_valid = False

                        break
            
            if is_valid:
                valid_facts.add(fact)
                
        return valid_facts



    # def _perform_validation_checks(self, non_hc_facts: Set[Fact], hc_facts: Set[Fact]) -> List[Fact]:
    #         """Perform validation checks with detailed logging"""
    #         non_hc_facts = non_hc_facts or set()
    #         hc_facts = hc_facts or set()
            
    #         combined_facts = non_hc_facts.union(hc_facts)
    #         print(f"Combined facts before validation: {len(combined_facts)}")
            
    #         # CHECK1: Closed validation
    #         after_check1 = self._check_clos`ed_validation(combined_facts) or set()
    #         print(f"Facts after closed validation: {len(after_check1)}")
            
    #         # CHECK2: All dimensions present
    #         after_check2 = self._check_all_dimensions_present(after_check1) or set()
    #         print(f"Facts after dimension presence check: {len(after_check2)}")
            
    #         # CHECK3: Dimension-member match
    #         validated_facts = self._check_dimension_member_match(after_check2) or set()
    #         print(f"Facts after dimension-member match: {len(validated_facts)}")

    #         # Group and display facts by period with concepts as row labels
    #         self._filter_by_period(validated_facts)  # Just display, don't filter           
            
    #         return list(validated_facts)



    def _perform_validation_checks(self, non_hc_facts: Set[Fact], hc_facts: Set[Fact]) -> List[Fact]:
        """Perform validation checks with detailed logging"""
        non_hc_facts = non_hc_facts or set()
        hc_facts = hc_facts or set()
        
        # Split hypercube facts into with/without dimensions
        hc_facts_with_dims = {fact for fact in hc_facts if fact.dims_members}
        hc_facts_without_dims = {fact for fact in hc_facts if not fact.dims_members}
        
        print(f"Hypercube facts before validation: {len(hc_facts)}")
        print(f"  - With dimensions: {len(hc_facts_with_dims)}")
        print(f"  - Without dimensions: {len(hc_facts_without_dims)}")
    
        # CHECK1: Closed validation - Only apply validation checks to facts WITH dimensions
        after_check1 = self._check_closed_validation(hc_facts_with_dims) or set()
        print(f"Facts after closed validation: {len(after_check1)}")
        
        # CHECK2: All dimensions present
        after_check2 = self._check_all_dimensions_present(after_check1) or set()
        print(f"Facts after dimension presence check: {len(after_check2)}")
        
        # CHECK3: Dimension-member match
        validated_hc_facts = self._check_dimension_member_match(after_check2) or set()
        print(f"Facts after dimension-member match: {len(validated_hc_facts)}")

        # Combine all valid facts:
        # 1. Non-hypercube facts without dimensions (already valid)
        # 2. Hypercube facts without dimensions (valid by default)
        # 3. Validated hypercube facts with dimensions
        combined_valid_facts = non_hc_facts.union(hc_facts_without_dims).union(validated_hc_facts)

        # Group and display facts by period with concepts as row labels
        self._filter_by_period(combined_valid_facts)  # Just display, don't filter           
        
        return list(combined_valid_facts)



    def _check_dimension_member_match(self, facts: Set[Fact]) -> Set[Fact]:
        """CHECK3: Match facts' dimensions/members with hypercube"""
        valid_facts = set()
        taxonomy = self.report.taxonomy if hasattr(self, 'report') else None


        for fact in facts:
            is_valid = True
            fact_dims_members = dict(fact.dims_members)  # Convert to dict for easier lookup
            
            for hypercube in self.hypercubes:

                fact_dims_members = dict(fact.dims_members)
                # print(f"Dimension-member check - Fact {fact.id}:")
                # print(f"  Fact dim-members: {[(d.qname, m.qname if m else 'None') for d,m in fact_dims_members.items()]}")
                # print(f"  Hypercube dims: {[d.qname for d in hypercube.dimensions]}")

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
    


########################### Display Facts ###########################


    def _format_period(self, period_id: str) -> str:
        """Format period display based on period type and context"""
        if not period_id:
            return ""
            
        try:
            from datetime import datetime
            
            # Parse period components
            period_type = "instant" if "instant" in period_id.lower() else "duration"
            dates = period_id.split("_")
            
            if period_type == "duration" and len(dates) >= 3:
                start_date = datetime.strptime(dates[-2], "%Y-%m-%d")
                # end_date = datetime.strptime(dates[-1], "%Y-%m-%d")
                
                end_date = datetime.strptime(dates[-1], "%Y-%m-%d")
                months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) # Calculate duration in months
                if end_date.day == 1: # Subtract 1 day from end date if it's the first day of the month
                    end_date = end_date - timedelta(days=1)

                
                # Only show month and year for end date to make it more compact
                date_display = end_date.strftime("%d_%b'%y")  # Will show like "Sep'24"
                
                # Handle special cases
                if months == 0:
                    return end_date.strftime("%d_%b'%y")  # Just show the date for instant/very short periods
                else:
                    return f"{months}M {date_display}"
                    
            elif period_type == "instant":
                # date = datetime.strptime(dates[-1], "%Y-%m-%d")
                # # return date.strftime("%b'%y")
                # return date.strftime("%b %d, %Y")  # New format: "Oct 31, 2024"
                
                date = datetime.strptime(dates[-1], "%Y-%m-%d")

                # Subtract 1 day from date if it's the first day of the month
                if date.day == 1:
                    date = date - timedelta(days=1)
                return date.strftime("%b %d, %Y")
                
        except Exception as e:
            print(f"Error formatting period {period_id}: {str(e)}")
            return period_id


    def _format_duration_date(self, date_parts: List[str]) -> str:
        """Format duration period date"""
        try:
            from datetime import datetime
            year = date_parts[0]
            month = int(date_parts[1])
            day = int(date_parts[2])
            date = datetime(int(year), month, day)
            return date.strftime("%b. %d, %Y")
        except:
            return "-".join(date_parts)
        

    def _format_instant_date(self, date_parts: List[str]) -> str:
        """Format instant period date"""
        try:
            year = date_parts[0]
            month = int(date_parts[1])
            day = int(date_parts[2])
            from datetime import datetime
            date = datetime(int(year), month, day)
            return date.strftime("%b. %d, %Y")
        except:
            return "-".join(date_parts)

    

    def _format_display_row(self, label: str, values: list, widths: dict) -> str:
        """Format row with proper alignment and indentation"""
        # Preserve existing indentation
        indent = ''.join(' ' for c in label if c == ' ')
        label = label.lstrip()
        
        # Format the row
        row = [f"{indent}{label}".ljust(widths['concept'])]
        
        # Right-align numeric values, clean up text blocks
        for p, v in values:
            width = widths[p]
            if 'TextBlock' in label:
                # Simple text block cleanup - just normalize spaces
                v = ' '.join(v.split())
            elif v.replace(',', '').replace('.', '').replace('(', '').replace(')', '').replace('$', '').replace('-', '').isdigit():
                row.append(v.rjust(width))
                continue
            row.append(v.ljust(width))
                
        return " | ".join(row)


    
        
    # def _format_display_row(self, label: str, values: list, widths: dict) -> str:
    #     """Format row with proper alignment and indentation"""
    #     # Preserve existing indentation
    #     indent = ''.join(' ' for c in label if c == ' ')
    #     label = label.lstrip()
        
    #     # Format the row
    #     row = [f"{indent}{label}".ljust(widths['concept'])]
        
    #     # Right-align numeric values
    #     for p, v in values:
    #         width = widths[p]
    #         if v.replace(',', '').replace('.', '').replace('(', '').replace(')', '').replace('$', '').replace('-', '').isdigit():
    #             row.append(v.rjust(width))
    #         else:
    #             row.append(v.ljust(width))
                
    #     return " | ".join(row)


    def _calculate_widths(self, nodes: dict, facts: Set[Fact], periods: List[str], period_groups: dict) -> dict:
        """Calculate display widths for all columns"""
        try:
            concept_width = max(
                len(f"{node.concept.qname} [{node.concept.balance}]" if node.concept.balance else f"{node.concept.qname}")
                for node in nodes.values()
                if node.concept
            ) + 10  # Extra space for indentation

            period_widths = {
                period: max(
                    len(str(fact.value)) for fact in period_groups[period]
                ) + 5 for period in periods
            }
            
            return {'concept': concept_width, **period_widths}
        except ValueError:  # Handle empty sequences
            return {'concept': 50, **{p: 20 for p in periods}}  # Default fallback

    def _filter_by_period(self, facts: Set[Fact]) -> Set[Fact]:
        """Group and display facts by period with concepts ordered by presentation hierarchy"""
        if not facts:
            return set()

        # Group facts by period u_id
        period_groups: Dict[str, List[Fact]] = {}
        for fact in facts:
            period_id = fact.period.u_id if fact.period else "No Period"
            if period_id not in period_groups:
                period_groups[period_id] = []
            period_groups[period_id].append(fact)

        # Use new _group_periods method
        periods = self._group_periods(period_groups)
        fact_concept_ids = {fact.concept.id for fact in facts}

        # Calculate display widths
        widths = self._calculate_widths(self.presentation.nodes, facts, periods, period_groups)

        # Create header using the working version's format
        header = "Concept [Balance]".ljust(widths['concept']) + " | " + " | ".join(
            self._format_period(p).ljust(widths[p]) for p in periods)

        print("\nConcept-Period Value Matrix:")
        print("-" * len(header))
        print(header)
        print("-" * len(header))

        def traverse_hierarchy(node_id: str, visited: set):
            if node_id in visited:
                return
            visited.add(node_id)
            
            node = self.presentation.nodes[node_id]
            if node.concept and node.concept.id in fact_concept_ids:
                indent = self._get_indent_level(node)
                label = indent + self._format_concept_label(node)
                
                # Add minimal debug print
                # print(f"\nProcessing concept: {node.concept.qname}")
                
                values = [
                    (period, self._format_value(
                        next((f.value for f in period_groups[period] 
                            if f.concept.id == node.concept.id), None)))
                    for period in periods
                ]
                
                print(self._format_display_row(label, values, widths))
            
            for child_id in sorted(node.children, 
                                key=lambda cid: self.presentation.nodes[cid].order):
                traverse_hierarchy(child_id, visited)

        if hasattr(self, 'presentation'):
            root_nodes = [node_id for node_id, node in self.presentation.nodes.items() 
                        if node.level == 1]
            root_nodes.sort(key=lambda nid: self.presentation.nodes[nid].order)
            
            visited = set()
            for root_id in root_nodes:
                traverse_hierarchy(root_id, visited)

        print("-" * len(header))
        print(f"Total Facts: {len(facts)}, Unique Concepts: {len(fact_concept_ids)}, Periods: {len(periods)}")

        return facts



    def _group_periods(self, period_groups: Dict[str, List[Fact]]) -> List[str]:
        """Group periods by period ID and fact patterns"""
        # Create list of period info
        periods = []
        
        for period_id, facts in period_groups.items():
            if not facts:
                continue
                
            # Extract date from period ID
            try:
                date_parts = [part for part in period_id.split('_')[-1].split('-') if part.isdigit()]
                if len(date_parts) >= 3:
                    year, month, day = date_parts[-3:]
                    date = (int(year), int(month), int(day))
                else:
                    continue
                    
                # Create unique identifier for this period
                period_key = (
                    date,  # Date tuple (year, month, day)
                    '_'.join(period_id.split('_')[:-1]),  # Context type/scenario
                    len(facts)  # Fact count
                )
                
                periods.append({
                    'id': period_id,
                    'date': date,
                    'key': period_key,
                    'fact_count': len(facts)
                })
                    
            except Exception as e:
                continue
        
        # Sort by date and fact count
        periods.sort(key=lambda x: (x['date'], -x['fact_count']), reverse=True)
        
        # Select unique periods
        seen_keys = set()
        selected = []
        
        for period in periods:
            if period['key'] not in seen_keys:
                seen_keys.add(period['key'])
                selected.append(period['id'])
                if len(selected) >= 5:  # Limit to 5 periods
                    break
                    
        return selected


    def _format_value(self, value: Union[int, float, str, None]) -> str:
        """Format numeric values with dollar signs and parentheses for negatives"""
        if value is None:
            return "-"
            
        try:
            if isinstance(value, (int, float)):
                abs_value = abs(float(value))
                formatted = f"${abs_value:,.0f}" if abs_value.is_integer() else f"${abs_value:,.2f}"
                return f"({formatted})" if value < 0 else formatted
            return str(value)
        except:
            return str(value)

    def _get_indent_level(self, node: PresentationNode) -> str:
        """Get proper indentation based on node level"""
        base_indent = 2  # Base spaces per level
        return " " * (node.level * base_indent)        
    

    def _format_concept_label(self, node: PresentationNode) -> str:
        """Format concept label with balance type"""
        if not node.concept:
            return ""
        
        label = f"{node.concept.qname}"
        if node.concept.balance:
            label += f" [{node.concept.balance}]"
        
        return label

########################### Display Facts END ###########################