"""
This module contains the main process_report class for XBRL processing.
This is the entry point for XBRL processing functionality.
"""

# Import common dependencies
from .common_imports import *
from datetime import datetime, timedelta

# Import core module
from .xbrl_core import Neo4jNode, NodeType, RelationType, ReportElementClassifier, XBRLNode

# Import utility functions
from .utils import clean_number, resolve_primary_fact_relationships

# Import basic and concept nodes
from .xbrl_basic_nodes import Context, Period, Unit, CompanyNode, ReportNode
from .xbrl_concept_nodes import Concept, GuidanceConcept, AbstractConcept

# Import specialized modules
from .xbrl_taxonomy import Taxonomy
from .xbrl_dimensions import Dimension, Domain, Member, Hypercube
from .xbrl_networks import Network, Presentation, Calculation
from .xbrl_reporting import Fact

# Type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .Neo4jManager import Neo4jManager

# Arelle imports
from arelle import Cntlr, ModelDocument, FileSource, XbrlConst
from arelle.ModelFormulaObject import FormulaOptions
from arelle.ModelValue import QName
from arelle.ModelDtsObject import ModelConcept
from arelle.ModelInstanceObject import ModelFact, ModelContext, ModelUnit
from arelle.ModelXbrl import ModelXbrl
from enum import Enum


def get_company_by_cik(neo4j: 'Neo4jManager', cik: str) -> Optional[CompanyNode]:
    """Get CompanyNode from Neo4j by CIK."""
    try:
        with neo4j.driver.session() as session:
            result = session.run(
                "MATCH (c:Company {cik: $cik}) RETURN c",
                {"cik": cik}
            ).single()
            if result:
                return CompanyNode.from_neo4j(dict(result["c"].items()))
            return None
    except Exception as e:
        print(f"Error retrieving company with CIK {cik}: {e}")
        return None


def get_report_by_accessionNo(neo4j: 'Neo4jManager', accessionNo: str) -> Optional[ReportNode]:
    """Get ReportNode from Neo4j by accession number."""
    try:
        with neo4j.driver.session() as session:
            result = session.run(
                "MATCH (r:Report {accessionNo: $accessionNo}) RETURN r",
                {"accessionNo": accessionNo}
            ).single()
            if result:
                return ReportNode.from_neo4j(dict(result["r"].items()))
            return None
    except Exception as e:
        print(f"Error retrieving report with accession number {accessionNo}: {e}")
        return None


@dataclass
class process_report:

    # Required parameters
    neo4j: 'Neo4jManager'  # Neo4j connection manager
    cik: str              # Company CIK
    accessionNo: str      # Report accession number
    
    # Defaults
    log_file: str = field(default='ErrorLog.txt', repr=False)
    testing: bool = field(default=True)  # Add testing flag as configurable (set to False in later calls for now)

    # These will be loaded in post_init
    report_node: ReportNode = field(init=False)
    external_company: CompanyNode = field(init=False)
    
    # XBRL processing node
    xbrl_node: XBRLNode = field(init=False)  # The XBRL processing node
    
    # Initialized in post_init
    model_xbrl: ModelXbrl = field(init=False, repr=False)

    # Common Nodes
    concepts: List[Concept] = field(init=False, default_factory=list, repr=False)
    abstracts: List[AbstractConcept] = field(init=False, default_factory=list, repr=False) # Used in Presentation Class (Abstracts, LineItems, Table (Hypercube), Axis (Dimensions), Members, Domain)
    pure_abstracts: List[AbstractConcept] = field(init=False, default_factory=list, repr=False) # Used in Presentation Class (only Abstracts, LineItems)    
    periods: List[Period] = field(init=False, default_factory=list, repr=False)
    units: List[Unit] = field(init=False, default_factory=list, repr=False)
    
    # Company Nodes
    company: CompanyNode = field(init=False)
    contexts: List[Context] = field(init=False, default_factory=list, repr=False)
    dimensions: List[Dimension] = field(init=False, default_factory=list, repr=False)        
    # members are inside dimensions but are also company-specific

    # Report-specific Nodes
    facts: List[Fact] = field(init=False, default_factory=list, repr=False)    
    taxonomy: Taxonomy = field(init=False) # Although this is company-specific, we load it for each report

    # Lookup Tables

    # Populated in populate_common_nodes, used for linking concept to fact (in _build_facts -> concept.add_fact), 
    # used in (get_concept) in both Presentation & Calculation Class
    _concept_lookup: Dict[str, Concept] = field(init=False, default_factory=dict, repr=False) # Used in Linking Fact to Concept (concept.id: concept)
    
    # Populated in Presentation Class (_build_abstracts), used in Presentation Class (get_concept)
    _abstract_lookup: Dict[str, AbstractConcept] = field(init=False, default_factory=dict, repr=False) # Used in Presentation (abstract.id: abstract)
    
    # Add new field for guidance concepts
    guidance_concepts: List[GuidanceConcept] = field(init=False, default_factory=list)
    
    def __post_init__(self):
        # Get company node and report node
        self.external_company = get_company_by_cik(self.neo4j, self.cik)
        if not self.external_company:
            raise ValueError(f"No company found with CIK {self.cik}")
            
        self.report_node = get_report_by_accessionNo(self.neo4j, self.accessionNo)
        if not self.report_node:
            raise ValueError(f"No report found with accession number {self.accessionNo}")
            
        # Verify the report_node has primaryDocumentUrl
        if not hasattr(self.report_node, 'primaryDocumentUrl') or not self.report_node.primaryDocumentUrl:
            raise ValueError("Report node must have primaryDocumentUrl attribute")
        
        # Create constraints directly like in ground truth
        with self.neo4j.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT FOR ()-[r:PRESENTATION_EDGE]->() REQUIRE r.order IS NOT NULL")
                print("Created constraint for PRESENTATION_EDGE relationships")
                session.run("CREATE CONSTRAINT FOR ()-[r:CALCULATION_EDGE]->() REQUIRE r.weight IS NOT NULL")
                print("Created constraint for CALCULATION_EDGE relationships")
            except Exception as e:
                # Continue even if constraint creation fails (might already exist)
                print(f"Note: Constraint creation message: {e}")
        
        self._primary_facts: Dict[str, Fact] = {}  # canonical_key -> primary fact
        self._duplicate_map: Dict[str, str] = {}   # duplicate_uid -> primary_uid
        
        self.initialize_xbrl_node()
        self.load_xbrl()
        self.initialize_company_node()
        
        self.populate_common_nodes()
        self.populate_company_nodes()
        self.populate_report_nodes()

        self._validate_and_link_networks()
        self._link_guidance_concepts()

    def _link_guidance_concepts(self):
        """Create relationships between guidance concepts and their targets"""
        relationships = []
        
        for guidance in self.guidance_concepts:
            print(f"\nProcessing guidance: {guidance.qname}")
            print(f"Guidance text: {guidance.guidance_text}")
            
            for target_qname in guidance.target_concepts:
                target_concept = next(
                    (c for c in self.concepts if str(c.qname) == target_qname), 
                    None
                )
                if target_concept:
                    relationships.append((
                        guidance,
                        target_concept,
                        RelationType.PROVIDES_GUIDANCE,
                        {
                            'guidance_text': guidance.guidance_text,
                            'concept_type': guidance.concept_type,
                            'namespace': guidance.namespace
                        }
                    ))
                    print(f"Created guidance relationship to: {target_concept.qname}")
        
        if relationships:
            self.neo4j.merge_relationships(relationships)
            print(f"\nCreated {len(relationships)} guidance relationships")



    def _validate_and_link_networks(self) -> None:
        """Validate facts and create relationships for all networks"""
        print("\nStarting network validation and linking...")
        
        for network in self.networks:
            network.report = self
            network.taxonomy = self.taxonomy

            # print(f"IsPresentation: {network.isPresentation}, IsCalculation: {network.isCalculation}, Network: {network.name}")
            
            # Always validate presentation first if available
            if network.isPresentation and hasattr(network, 'presentation'):
                validated_facts = network.validate_facts(network_type='presentation')
                network.presentation.validated_facts = validated_facts
                network.presentation.fact_lookup = defaultdict(list)
                for fact in validated_facts:
                    network.presentation.fact_lookup[fact.concept.u_id].append(fact)
                    
            # Only validate calculation if it exists and no presentation facts
            elif (network.isCalculation and 
                hasattr(network, 'calculation') and 
                not (hasattr(network, 'presentation') and 
                    getattr(network.presentation, 'fact_lookup', None))):
                
                validated_facts = network.validate_facts(network_type='calculation')
                network.calculation.validated_facts = validated_facts
                network.calculation.fact_lookup = defaultdict(list)
                for fact in validated_facts:
                    network.calculation.fact_lookup[fact.concept.u_id].append(fact)
        
        # Create relationships
        self.link_presentation_facts()
        self.link_calculation_facts()

    def get_network_fact_lookup(self, network) -> Optional[Dict[str, List[Fact]]]:
        
        # """Get fact lookup for a network, preferring presentation over calculation"""
        if (hasattr(network, 'presentation') and 
            getattr(network.presentation, 'fact_lookup', None)):
            return network.presentation.fact_lookup
        
        if (hasattr(network, 'calculation') and 
            getattr(network.calculation, 'fact_lookup', None)):
            return network.calculation.fact_lookup
        
        # Fallback: Create lookup from all facts
        fact_lookup = defaultdict(list)
        for fact in self.facts:
            fact_lookup[fact.concept.u_id].append(fact)
        return fact_lookup if fact_lookup else None


    def link_presentation_facts(self) -> None:
        """Create presentation relationships using stored validated facts"""
        print("\nCreating presentation relationships...")
        relationships = []
        debug_counts = defaultdict(int)
        
        for network in self.networks:
            if not network.isPresentation:
                continue
                
            if not hasattr(network, 'presentation') or not hasattr(network.presentation, 'fact_lookup'):
                print(f"Warning: Missing presentation or fact_lookup for network {network.name}")
                continue
                
            fact_lookup = network.presentation.fact_lookup
            abstract_lookup = {abstract.u_id: abstract for abstract in self.pure_abstracts}
            
            for node in network.presentation.nodes.values():
                parent_node = node.concept
                parent_u_id = parent_node.u_id if parent_node else None
                if not parent_u_id:
                    continue
                    
                for child_id in node.children:
                    child_node = network.presentation.nodes[child_id]
                    child_u_id = child_node.concept.u_id if child_node.concept else None
                    
                    if not child_u_id:
                        continue
                        
                    rel_props = {
                        'network_uri': network.network_uri,
                        'network_name': network.name,
                        'company_cik': self.company.cik,
                        'report_id': self.xbrl_node.id,  # Use XBRLNode id
                        'parent_level': node.level,
                        'parent_order': node.order,
                        'child_level': child_node.level,
                        'child_order': child_node.order
                    }
                    
                    # Create relationships...
                    if parent_u_id in abstract_lookup and child_u_id in abstract_lookup:
                        relationships.append((
                            abstract_lookup[parent_u_id],
                            abstract_lookup[child_u_id],
                            RelationType.PRESENTATION_EDGE,
                            rel_props
                        ))
                        debug_counts['abstract_to_abstract'] += 1
                    
                    if parent_u_id in abstract_lookup and child_u_id in fact_lookup:
                        for fact in fact_lookup[child_u_id]:
                            relationships.append((
                                abstract_lookup[parent_u_id],
                                fact,
                                RelationType.PRESENTATION_EDGE,
                                rel_props
                            ))
                            debug_counts['abstract_to_fact'] += 1
        
        print("\nPresentation Relationship Summary:")
        print(f"Total relationships: {len(relationships)}")
        for rel_type, count in debug_counts.items():
            print(f"{rel_type}: {count}")
            
        if relationships:
            print("Creating relationships in Neo4j...")
            self.neo4j.merge_relationships(relationships)
            
        print("\nPresentation Relationship Creation Summary:")
        print(f"Total relationships created: {len(relationships)}")
        for rel_type, count in debug_counts.items():
            print(f"{rel_type}: {count}")




    def link_calculation_facts(self) -> None:
        """Creates calculation relationships in Neo4j.
        Facts are grouped by context (period, entity, dimensions) and unit
        as per XBRL 2.1 and Dimensions 1.0 specifications.
        """
        
        relationships = []
        context_lookup = {ctx.context_id: ctx for ctx in self.contexts}
        debug_counts = defaultdict(int)
        
        for network in self.networks:
            if not network.isCalculation: continue
                
            # Get validated facts from presentation network if available
            fact_lookup = self.get_network_fact_lookup(network)
            if not fact_lookup:
                print(f"No valid fact lookup available for network: {network.name}")
                debug_counts['missing_fact_lookup'] += 1
                continue
                
            calc_rel_set = network.model_xbrl.relationshipSet(XbrlConst.summationItem, network.network_uri)
            if not calc_rel_set:
                print(f"No calculation relationships in network: {network.name}")
                debug_counts['no_calc_relationships'] += 1
                continue
            
            # Group facts by context and unit
            for rel in calc_rel_set.modelRelationships:
                try:
                    parent_id = f"{rel.fromModelObject.qname.namespaceURI}:{rel.fromModelObject.qname}"
                    child_id = f"{rel.toModelObject.qname.namespaceURI}:{rel.toModelObject.qname}"
                except AttributeError:
                    debug_counts['invalid_relationships'] += 1
                    continue
                
                parent_facts = fact_lookup.get(parent_id, [])
                child_facts = fact_lookup.get(child_id, [])
                
                if not parent_facts or not child_facts:
                    debug_counts['missing_facts'] += 1
                    continue
                
                # Group parent facts by context and unit
                parent_groups = defaultdict(list)
                for p_fact in parent_facts:
                    if p_fact.value is None: 
                        debug_counts['null_parent_values'] += 1
                        continue
                        
                    p_context = context_lookup.get(p_fact.context_id)
                    if not p_context:
                        debug_counts['missing_parent_context'] += 1
                        continue
                    
                    # Context inherently includes period, entity, and dimensions
                    group_key = (p_context.context_id, p_fact.unit)
                    parent_groups[group_key].append(p_fact)
                
                # Match child facts to parent groups
                for group_key, group_parents in parent_groups.items():
                    context_id, unit = group_key
                    parent_context = context_lookup[context_id]
                    
                    matching_children = [
                        c_fact for c_fact in child_facts
                        if (c_fact.value is not None and
                            c_fact.unit == unit and
                            context_lookup.get(c_fact.context_id) and
                            context_lookup[c_fact.context_id].context_id == context_id 
                            
                            # Not useful
                            # or any(c_fact.concept.qname == rel.toModelObject.qname 
                            #     for rel in calc_rel_set.fromModelObject(group_parents[0].concept))

                        ) 
                    ]
                    
                    # Create relationships for matching facts
                    for parent_fact in group_parents:
                        for child_fact in matching_children:
                            relationships.append((
                                parent_fact,
                                child_fact,
                                RelationType.CALCULATION_EDGE,
                                {
                                    'network_uri': network.network_uri,
                                    'network_name': network.name,
                                    'context_id': context_id,
                                    'weight': rel.weight,
                                    'order': rel.order,
                                    'company_cik': self.company.cik,
                                    'report_id': self.xbrl_node.id,  # Use XBRLNode id
                                    'report_instance': self.xbrl_node.id  # Use XBRLNode id
                                }
                            ))
                            debug_counts['relationships_created'] += 1


        # Print debug summary
        print("\nCalculation Relationship Summary:")
        print(f"Total relationships created: {len(relationships)}")
        for count_type, count in debug_counts.items():
            print(f"{count_type}: {count}")
        
        if relationships:
            print("Checking calculation steps...")
            # Get valid relationships from check_calculation_steps
            valid_relationships = []
            self.check_calculation_steps(relationships, context_lookup, valid_relationships) 

            if valid_relationships:  # Only create valid relationships
                # print("Creating relationships in Neo4j...")
                self.neo4j.merge_relationships(valid_relationships)

                # print("\nValidating Neo4j calculations...")
                self.neo4j.validate_neo4j_calculations()


    def check_calculation_steps(self, relationships, context_lookup, valid_relationships=None) -> None:
        """Validates summation consistency of pre-grouped calculation relationships.
        Processes relationships the same way as Neo4j storage to ensure exact matching."""
        
        print("\nStarting calculation validation...")
        debug_counts = defaultdict(int)
        
        relationships = resolve_primary_fact_relationships(relationships)
        matches = 0
        non_matches = 0
        
        # Group by network just for organized output
        network_groups = defaultdict(list)
        for rel in relationships:
            attrs = rel[3]
            required_props = {'company_cik', 'report_id', 'network_uri', 'context_id'}
            missing_props = required_props - set(attrs.keys())
            if missing_props:
                raise ValueError(f"Missing required properties: {missing_props}")
                
            network_uri = attrs['network_uri']
            network_groups[network_uri].append(rel)
            debug_counts['total_relationships'] += 1
        
        for network_uri, network_rels in network_groups.items():
            # print(f"\nNetwork: {network_rels[0][3]['network_name']}")
            debug_counts['networks_processed'] += 1
            
            # Group by parent fact for summation checking
            parent_groups = {} 
            for parent_fact, child_fact, _, attrs in network_rels:
                if parent_fact not in parent_groups:
                    parent_groups[parent_fact] = {}
                    debug_counts['unique_parents'] += 1

                network_name = attrs['network_uri'].split('/')[-1]
                # Deduplicate using same keys as Neo4j MERGE
                child_key = (
                    attrs.get('company_cik'),
                    attrs.get('report_id'),
                    network_name,
                    parent_fact.id,
                    child_fact.id,
                    attrs.get('context_id')
                )

                parent_groups[parent_fact][child_key] = (child_fact, attrs['weight'])
                debug_counts['child_facts_processed'] += 1
            
            # Check summations for each parent
            for parent_fact, unique_children in parent_groups.items():
                parent_context = context_lookup.get(parent_fact.context_id)
                debug_counts['calculations_checked'] += 1
                
                # Calculate total sum
                total_sum = 0
                for child_fact, weight in unique_children.values():
                    weighted_value = float(child_fact.value) * weight
                    total_sum += weighted_value
                    debug_counts['children_processed'] += 1
                
                # Validate summation
                parent_value = clean_number(parent_fact.value)
                percent_diff = abs(parent_value - total_sum) if parent_value == 0 else abs(parent_value - total_sum) / abs(parent_value)
                # is_match = percent_diff < 0.01 # 1% tolerance
                is_match = percent_diff < 0.001  # 0.1% tolerance
                
                matches += 1 if is_match else 0
                non_matches += 1 if not is_match else 0
                debug_counts['matches'] = matches
                debug_counts['non_matches'] = non_matches
                
                # Handle valid/invalid cases
                if is_match and valid_relationships is not None:
                    valid_relationships.extend([rel for rel in network_rels if rel[0] == parent_fact])
                else:
                    # Print details for invalid summations
                    print(f"\nInvalid Calculation Group:")
                    print(f"net: {network_rels[0][3]['network_name']}, {network_rels[0][3]['network_uri']}")
                    print(f"Parent: {parent_fact.concept.qname} ({parent_fact.concept.balance}) = {parent_fact.value}, "
                        f"{parent_context.period_u_id}, "
                        f"{parent_context.cik}, "
                        f"{parent_fact.unit.id.split('/')[-1]}, "
                        f"{parent_fact.context_id}")
                    
                    print("\nChildren:")
                    for child_fact, weight in unique_children.values():
                        weighted_value = float(child_fact.value) * weight
                        balance_type = "Credit" if child_fact.concept.balance == 'credit' else "Debit"
                        child_context = context_lookup.get(child_fact.context_id)
                        
                        print(f"{balance_type}: {child_fact.concept.qname} = {child_fact.value} × {weight} = {weighted_value}, "
                            f"{child_context.period_u_id}, "
                            f"{child_context.cik}, "
                            f"{child_fact.unit.id.split('/')[-1]}, "
                            f"{child_fact.context_id}")
                        
                        if hasattr(child_context, 'dimensions'):
                            print(f"    Dimensions: {child_context.dimensions}")



                    print(f"\nTotal Sum: {total_sum}")
                    print(f"Calculated Value: {total_sum}")
                    print(f"Parent Value: {parent_value}")
                    print(f"Match: No")
                    print("="*80)
        
        # Print summaries
        print("\nCalculation Validation Summary:")
        for count_type, count in debug_counts.items():
            print(f"{count_type}: {count}")
        
        print(f"\nSummary:")
        print(f"Total Matches: {matches}")
        print(f"Total Non-Matches: {non_matches}")
        if matches + non_matches > 0:
            print(f"Match Rate: {matches/(matches+non_matches)*100:.1f}%")


    def initialize_company_node(self):
        """Set the company node from the externally provided company (minimal version)"""
        if not self.external_company:
            raise ValueError("External company node is required but none was provided")
        
        # Simply set the company reference - no Neo4j operations
        self.company = self.external_company
        print(f"Using company node: {self.company.name} (CIK: {self.company.cik})")

    
    def link_fact_footnotes(self) -> None:
        """Debug version to understand fact-footnote relationships"""
        print("\n" + "="*80)
        print("DEBUGGING FACT-FOOTNOTE RELATIONSHIPS")
        print("="*80)
        
        # Try both standard arcroles
        fact_footnote_arcrole = "http://www.xbrl.org/2003/arcrole/fact-footnote"
        fact_explanatory_arcrole = "http://www.xbrl.org/2009/arcrole/fact-explanatoryFact"
        
        # Get relationship sets
        footnote_rel_set = self.model_xbrl.relationshipSet(fact_footnote_arcrole)
        explanatory_rel_set = self.model_xbrl.relationshipSet(fact_explanatory_arcrole)
        
        # Check for footnotes in the instance document
        print("\nChecking Instance Document:")
        print(f"Instance URL: {self.xbrl_node.primaryDocumentUrl}")
        print(f"Has Footnote Links: {'Yes' if footnote_rel_set else 'No'}")
        print(f"Has Explanatory Facts: {'Yes' if explanatory_rel_set else 'No'}")
        
        # If no relationships found, check for inline XBRL footnotes
        if not (footnote_rel_set or explanatory_rel_set):
            print("\nChecking for iXBRL footnotes:")
            for fact in self.facts:
                if hasattr(fact, 'footnoteRefs') and fact.footnoteRefs:
                    print(f"Found iXBRL footnote reference in fact: {fact.concept.qname}")
        
        print("\n" + "="*80)



    def load_xbrl(self):
        # Initialize the controller
        controller = Cntlr.Cntlr(logFileName=self.log_file, logFileMode='w', logFileEncoding='utf-8')
        controller.modelManager.formulaOptions = FormulaOptions()

        # Load the model_xbrl directly from the XBRLNode's primaryDocumentUrl
        try:
            self.model_xbrl = controller.modelManager.load(
                filesource=FileSource.FileSource(self.xbrl_node.primaryDocumentUrl), 
                discover=True
            )
        except Exception as e: 
            raise RuntimeError(f"Error loading XBRL model: {e}")


    def populate_common_nodes(self):
        """Populate common nodes in Neo4j."""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        # Build common nodes from XBRL
        self._build_concepts() # 1. Build concepts first (includes guidance concepts)
        self._build_periods()  # 2. Build periods
        self._build_units()    # 3. Build units

        # contexts are company-specific 
        self._build_contexts()  # 4. Build contexts - but only nodes, not relationships
        

        # Upload to Neo4j only common nodes first
        self.neo4j._export_nodes([
            self.concepts,
            self.guidance_concepts,  # Add guidance concepts here
            self.periods, 
            self.units, 
            self.contexts
        ], testing=False)

        self._concept_lookup = {concept.id: concept for concept in [*self.concepts, *self.guidance_concepts]}


    def populate_company_nodes(self):
        """Build and sync company-specific nodes (Dimensions, Members) with Neo4j"""        
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")

        # Build taxonomy-wide dimensions
        self.taxonomy = Taxonomy(self.model_xbrl)
        self.taxonomy.build_dimensions()

        # Here we should load_nodes_as_instances from both self.taxonomy.dimensions, self.taxonomy.members, domains as well as member hierarchies

        # Collect all nodes
        all_domains = [dim.domain for dim in self.taxonomy.dimensions if dim.domain is not None]
        all_members = [member for dim in self.taxonomy.dimensions 
                    if dim.members_dict 
                    for member in dim.members_dict.values()]
        

        # Export nodes to Neo4j
        self.neo4j._export_nodes([
            self.taxonomy.dimensions,  # Dimensions
            all_domains,               # Domains
            all_members                # Members
        ], testing=False)

        # Export relationships
        relationships = []
        relationships.extend(self.taxonomy.get_dimension_domain_relationships())
        relationships.extend(self.taxonomy.get_dimension_member_relationships())
        relationships.extend(self.taxonomy.get_member_hierarchy_relationships())
        
        if relationships:
            self.neo4j.merge_relationships(relationships)
        
        self._build_networks()

        # populate_company_nodes calls _build_hierarchy which inturn calls _build_abstracts (which are common nodes & not company-specific) & fills self.abstracts
        abstracts_lineItems = [abs for abs in self.abstracts if abs.category in ['Abstract', 'LineItems']]

        self.neo4j._export_nodes([abstracts_lineItems], testing=False) # Only export Abstracts & LineItems 
        # self.neo4j._export_nodes([self.abstracts], testing=False) # Only export Abstracts & LineItems 

        self.pure_abstracts = abstracts_lineItems
        # self.pure_abstracts = self.neo4j.load_nodes_as_instances(NodeType.ABSTRACT, AbstractConcept)



    def populate_report_nodes(self):
        """Build and export report-specific nodes (Facts, Dimensions)"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")

        self._build_facts()       # 5. Build facts
        
        # Upload to Neo4j report-specific nodes - # Testing=False since otherwise it will clear the db
        self.neo4j._export_nodes([self.facts], testing=False) 

        #  Get relationships from mapping Fact to its corresponding target instances (Concept, Unit, Period)
        fact_relationships = self._map_fact_relationships([
            (Fact, Concept, RelationType.HAS_CONCEPT),
            (Fact, Unit, RelationType.HAS_UNIT),
            (Fact, Period, RelationType.HAS_PERIOD)
        ])
        
        # Create relationships in Neo4j
        if fact_relationships: 
            self.neo4j.merge_relationships(fact_relationships)

        # Build report-fact relationships
        report_fact_relationships = self._build_report_fact_relationships()
        
        # Merge fact relationships
        if report_fact_relationships:
            self.neo4j.merge_relationships(report_fact_relationships)

        # Export fact-dimension relationships
        fact_dim_relationships = self._build_fact_dimension_relationships()
        if fact_dim_relationships:
            self.neo4j.merge_relationships(fact_dim_relationships)

        # Export context relationships
        context_relationships = self._build_context_relationships()
        if context_relationships:
            self.neo4j.merge_relationships(context_relationships)

        # Export fact-context relationships
        fact_context_relationships = self._build_fact_context_relationships()
        if fact_context_relationships:
            self.neo4j.merge_relationships(fact_context_relationships)

        print(f"Built report nodes: {len(self.facts)} facts")


    def _build_concepts(self):
        """Build concept objects from the model."""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        self.concepts = []
        self.guidance_concepts = []
        type_counts = defaultdict(int)
        
        # Get all concepts from the model, not just those with facts
        all_concepts = set(self.model_xbrl.qnameConcepts.values())
        
        # Also get concepts with facts
        fact_concepts = {fact.concept for fact in self.model_xbrl.factsInInstance 
                        if fact.concept.qname in self.model_xbrl.factsByQname.keys()}
        
        # Process all concepts
        for concept in all_concepts:
            node_type = ReportElementClassifier.classify(concept)
            type_counts[node_type] += 1
            
            if node_type == NodeType.GUIDANCE:
                guidance = GuidanceConcept(concept)
                self.guidance_concepts.append(guidance)
            elif concept in fact_concepts:  # Only create Concept nodes for those with facts
                self.concepts.append(Concept(concept))
        
        print("\nConcept types:")
        for node_type, count in type_counts.items():
            print(f"{node_type.value}: {count}")
        


    def _build_units(self):
        """Build unique unit objects from the model."""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
                
        units_dict = {}  # Use dict for uniqueness
        for fact in self.model_xbrl.factsInInstance:
            if hasattr(fact, 'unitID') and fact.unitID:  # Only check for unitID
                try:
                    unit = Unit(model_fact=fact)
                    if unit.string_value or unit.unit_reference:  # Only add if we have some identifying info
                        units_dict[unit.id] = unit
                except Exception as e:
                    print(f"Error processing unit for fact {fact.id}: {e}")
        
        self.units = list(units_dict.values())
        print(f"Built {len(self.units)} unique units") 


    def _build_periods(self) -> None:
        """Build unique period objects from contexts"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        periods_dict = {}  # Use dict for uniqueness
        
        for ctxt_id, context in self.model_xbrl.contexts.items():
            try:
                # Determine period type
                period_type = ("instant" if getattr(context, "isInstantPeriod", False)
                            else "duration" if getattr(context, "isStartEndPeriod", False)
                            else "forever")
                
                # Extract dates
                start_date = None
                end_date = None
                
                if period_type == "instant":
                    start_date = context.instantDatetime.strftime('%Y-%m-%d')
                elif period_type == "duration":
                    start_date = context.startDatetime.strftime('%Y-%m-%d')
                    end_date = context.endDatetime.strftime('%Y-%m-%d')
                    
                # Create period
                period = Period(
                    period_type=period_type,
                    start_date=start_date,
                    end_date=end_date,
                    context_ids=[ctxt_id]
                )
                
                # Add to dict using _id as key for uniqueness
                if period.u_id in periods_dict:
                    # periods_dict[period.u_id].merge_context(ctxt_id)
                    # print(f"Merged context {ctxt_id} into existing period {period.u_id}")
                    pass        
                else:
                    periods_dict[period.u_id] = period
                    
            except Exception as e:
                print(f"Error processing context {ctxt_id}: {e}")
        
        self.periods = list(periods_dict.values())
        print(f"Built {len(self.periods)} unique periods")


    def _build_facts(self):
        """Build facts with two-way concept relationships"""

         # Filter out hidden facts right at the source
        valid_facts = [fact for fact in self.model_xbrl.factsInInstance 
                    if not (fact.id and fact.id.startswith('hidden-fact'))
                    and fact.context.id]
                    
        for model_fact in valid_facts:
            fact = Fact(model_fact=model_fact, _report=self)  # Pass self as report reference

            model_concept = model_fact.concept
            concept_id = f"{model_concept.qname.namespaceURI}:{model_concept.qname}"
            concept = self._concept_lookup.get(concept_id)
            
            if not concept: 
                print(f"Warning: No concept found for fact {fact.fact_id}")
                continue
                
            # Create canonical key using model_concept - sort of makes the key unique (concept, context, unit)
            canonical_key = f"{model_concept.qname}:{fact.context_id}:{fact.unit}"
            
            # Check for duplicates & picks primary fact based on precision & significant digits:
            if canonical_key in self._primary_facts:
                primary = self._primary_facts[canonical_key]
                fact_decimals = fact.decimals if fact.decimals is not None else float('-inf')
                primary_decimals = primary.decimals if primary.decimals is not None else float('-inf')
                if fact_decimals > primary_decimals or (
                    # Selects higher precision or, if equal, the fact with more significant digits (ex 339 vs 340 or 341 vs 340).
                        fact_decimals == primary_decimals and 
                        len(str(fact.value).lstrip('0').replace('.', '').replace('-', '')) > 
                        len(str(primary.value).lstrip('0').replace('.', '').replace('-', ''))
                    ):

                    self._duplicate_map[primary.u_id] = fact.u_id
                    self._primary_facts[canonical_key] = fact
                else:
                    self._duplicate_map[fact.u_id] = primary.u_id
            else:
                self._primary_facts[canonical_key] = fact
            
            # Only linking concept.facts since fact.concept = concept done in export_            
            # Also this is not done for Neo4j nodes but for internal classes only  
            concept.add_fact(fact)
            self.facts.append(fact)
            
        print(f"Built {len(self.facts)} facts ({len(self._primary_facts)} unique)")


    def _build_contexts(self):
        """Build context objects from the model"""
        if not self.model_xbrl:
            raise RuntimeError("XBRL model not loaded.")
            
        contexts_dict = {}
        
        for model_context in self.model_xbrl.contexts.values():
            try:
                # Period handling
                if model_context.isInstantPeriod:
                    period_type = "instant"
                    start_date = model_context.instantDatetime.strftime('%Y-%m-%d')
                    end_date = None
                elif model_context.isStartEndPeriod:
                    period_type = "duration"
                    start_date = model_context.startDatetime.strftime('%Y-%m-%d')
                    end_date = model_context.endDatetime.strftime('%Y-%m-%d')
                else:
                    period_type = "forever"
                    start_date = None
                    end_date = None
                
                period = Period(
                    period_type=period_type,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Get CIK from entity identifier
                _, identifier = model_context.entityIdentifier
                cik = identifier.lstrip('0')  # Remove leading zeros as per CompanyNode
                
                # Get dimensions and members
                dimension_u_ids = []
                member_u_ids = []
                if model_context.qnameDims:
                    for dim_qname, member in model_context.qnameDims.items():
                        try:
                            # Get company_id from the same source as Dimension class
                            company_id = self.model_xbrl.modelDocument.uri.split('/')[-3]
                            
                            # Create dimension u_id matching Dimension class format
                            dim_u_id = f"{company_id}:{dim_qname.namespaceURI}:{dim_qname}"
                            dimension_u_ids.append(dim_u_id)
                        except AttributeError:
                            continue

                        try:
                            if hasattr(member, 'memberQname'):
                                # Create member u_id matching Member class format
                                mem_u_id = f"{company_id}:{member.memberQname.namespaceURI}:{member.memberQname}"
                                member_u_ids.append(mem_u_id)
                        except AttributeError:
                            continue


                context = Context(
                    context_id=model_context.id,
                    cik=cik,
                    period_u_id=period.u_id,
                    dimension_u_ids=dimension_u_ids,
                    member_u_ids=member_u_ids
                )
                
                contexts_dict[context.u_id] = context
                    
            except Exception as e:
                print(f"Error processing context {model_context.id}: {e}")
        
        self.contexts = list(contexts_dict.values())
        print(f"Built {len(self.contexts)} unique contexts")



    def _build_context_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Build relationships between contexts and their related nodes"""
        context_relationships = []
        
        for context in self.contexts:
            # Context -> Period
            period = next((p for p in self.periods if p.u_id == context.period_u_id), None)
            if period:
                context_relationships.append((context, period, RelationType.HAS_PERIOD))
            
            # Context -> Company
            context_relationships.append((context, self.company, RelationType.FOR_COMPANY))
            
            # Context -> Dimensions
            for dim_id in context.dimension_u_ids:
                dim = next((d for d in self.taxonomy.dimensions if d.u_id == dim_id), None)
                if dim:
                    context_relationships.append((context, dim, RelationType.HAS_DIMENSION))
            
            # Context -> Members
            for mem_id in context.member_u_ids:
                for dim in self.taxonomy.dimensions:
                    member = next((m for m in dim.members_dict.values() if m.u_id == mem_id), None)
                    if member:
                        context_relationships.append((context, member, RelationType.HAS_MEMBER))
                        break
                        
        return context_relationships


    def _build_fact_dimension_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Build relationships between facts and their dimensions/members"""
        relationships = []

        # Create lookup dictionaries using QName objects
        dim_lookup = {dim.u_id: dim for dim in self.taxonomy.dimensions}
        member_lookup = {}

        for dim in self.taxonomy.dimensions:
            for member_qname_str, member in dim.members_dict.items():
                member_lookup[member.u_id] = member 

        # Process each fact's dimensions
        for fact in self.facts:
            if not fact.dims_members:
                continue

            for dim_concept, member_concept in fact.dims_members:
                if not dim_concept:
                    continue

                taxonomy_dim = dim_lookup.get(dim_concept.u_id)
                if not taxonomy_dim:
                    continue

                # If we have a member, try to link through it
                if member_concept:
                    member = member_lookup.get(member_concept.u_id)
                    if member:
                        relationships.append((fact, member, RelationType.FACT_MEMBER))
                        continue  # Proceed to next dimension-member pair

                # If no member or member not found, link directly to dimension
                relationships.append((fact, taxonomy_dim, RelationType.FACT_DIMENSION))
                
        return relationships

    # Need to check if we can remove this?
    def _build_fact_context_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Build relationships between facts and their contexts"""
        fact_context_relationships = []
        
        # Create a lookup dictionary for faster access
        context_lookup = {ctx.context_id: ctx for ctx in self.contexts}
        missing_contexts = set()  # For debugging

        for fact in self.facts:
            # Find matching context using context_id
            # context = next((ctx for ctx in self.contexts 
            #             if ctx.context_id == fact.context_id), None)

            context = context_lookup.get(fact.context_id)
            if context:
                fact_context_relationships.append((fact, context, RelationType.IN_CONTEXT))
            else:
                missing_contexts.add(fact.context_id)
            
            
        if missing_contexts:
            print(f"Warning: {len(missing_contexts)} facts have missing contexts: {missing_contexts}")
        print(f"Built {len(fact_context_relationships)} fact-context relationships")
        return fact_context_relationships


    # 1. Build networks - Also builds hypercubes in networks with isDefinition = True
    def _build_networks(self):
        """Builds networks specific to this filing instance. Networks are report-specific sections."""
        
        # Define relationship types to check
        relationship_sets = [
            XbrlConst.parentChild,       # parent-child relationships - presentation
            XbrlConst.summationItem,     # calculation relationships  - calculation
            XbrlConst.all,               # all relationships (primary item requires dimension members) - definition
            XbrlConst.notAll,            # notAll relationships (primary item excludes dimension members) - definition
            XbrlConst.dimensionDefault,  # dimension-default relationships - definition
            XbrlConst.dimensionDomain,   # dimension-domain relationships - definition
            XbrlConst.domainMember,      # domain-member relationships - definition
            XbrlConst.hypercubeDimension # hypercube-dimension relationships - definition
        ]
        
        # linkrole: 'http://strongholddigitalmining.com/role/CONSOLIDATEDBALANCESHEETS'
        # role_name: (0000003 - Statement - CONSOLIDATED BALANCE SHEETS)
    
        # Create networks for each section of this specific report (e.g., Balance Sheet, Income Statement, Notes)
        self.networks = [
            Network(
                model_xbrl = self.model_xbrl,
                name =' - '.join(parts[2:]), 
                network_uri=uri,
                id=parts[0],
                category=parts[1],
                relationship_sets=[rel_set]
            )
            for rel_set in relationship_sets
            for rel in self.model_xbrl.relationshipSet(rel_set).modelRelationships

            # Skip if  is missing
            if (role_name := self.model_xbrl.roleTypeName(roleURI=(uri := rel.linkrole))) 
            and len(parts := [p.strip() for p in role_name.split(' - ')]) >= 3 ] # Need at least ID, Category, and Description
        

        # 1. Network deduplication with relationship set merging
        unique_networks = {}
        for network in self.networks:
            key = (network.network_uri, network.name, network.id, network.category)
            if key in unique_networks:
                # Add any new relationship sets that aren't already present
                unique_networks[key].relationship_sets.extend(
                    rs for rs in network.relationship_sets 
                    if rs not in unique_networks[key].relationship_sets)
            else:
                unique_networks[key] = network
        
        self.networks = list(unique_networks.values())

        # 2. Link presentation concepts first - also _build_abstracts in build_hierarchy, also initialize Calculation Class
        for network in self.networks:
            # Create Presentation Class
            if network.isPresentation:
                # Pass report reference to access/create concepts and abstracts
                network.presentation = Presentation(network_uri=network.network_uri, model_xbrl=self.model_xbrl, process_report=self)


            # Create Calculation Class
            if network.isCalculation:
                network.calculation = Calculation( network_uri=network.network_uri, 
                                                  name=network.name, model_xbrl=self.model_xbrl, process_report=self)
                            
        # 3. Adding hypercubes after networks are complete which in turn builds dimensions
        for network in self.networks:
            network.add_hypercubes(self.model_xbrl)
            for hypercube in network.hypercubes:                
                hypercube._link_hypercube_concepts(self.concepts, self.abstracts)


    def _map_fact_relationships(self, rel_types: List[Tuple[Type[Neo4jNode], Type[Neo4jNode], RelationType]]) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Maps Facts to their corresponding target instances (Concept, Unit, Period) and returns relationships"""
        relationships = []
        
        # Here source is always assumed to be a Fact instance
        def create_temp_target(source, target_type):
            """Create a temporary target instance based on the source instance and target type."""
            if target_type == Concept:
                return Concept(model_concept=source.model_fact.concept)
            elif target_type == Unit:
                return Unit(model_fact=source.model_fact)
            elif target_type == Period:
                context = source.model_fact.context
                # Uses exact same logic as _build_periods
                period_type = ("instant" if getattr(context, "isInstantPeriod", False)
                            else "duration" if getattr(context, "isStartEndPeriod", False)
                            else "forever")
                return Period(
                    period_type=period_type,
                    start_date=context.instantDatetime.strftime('%Y-%m-%d') if context.isInstantPeriod 
                        else context.startDatetime.strftime('%Y-%m-%d'),
                    end_date=context.endDatetime.strftime('%Y-%m-%d') 
                        if context.isStartEndPeriod else None
                )
            return None

        for source_type, target_type, rel_type in rel_types:
            try:
                collection = getattr(self, f"{target_type.__name__.lower()}s") # such as self.concepts, self.units etc - note lower()
                target_lookup = {node.id: node for node in collection} # Mapping of actual class instances
                
                for source in getattr(self, f"{source_type.__name__.lower()}s"):
                    if temp_target := create_temp_target(source, target_type):
                        
                        # target is the actual class instances
                        if target := target_lookup.get(temp_target.id):
                            relationships.append((source, target, rel_type))
                            # Sets Fact instance to point to the corresponding target instance ((e.g., concept, unit, period))
                            setattr(source, target_type.__name__.lower(), target) # Like fact.concept etc
                            
            except (AttributeError, KeyError) as e:
                print(f"Skipping {source_type.__name__} -> {target_type.__name__}: {e}")
        
        return relationships
            

    def _build_report_fact_relationships(self) -> List[Tuple[Neo4jNode, Neo4jNode, RelationType]]:
        """Build relationships between facts and their dimensions/members"""
        report_fact_relationships = []
        
        for fact in self.facts:
            # Add relationship between fact and report
            report_fact_relationships.append((
                fact, 
                self.xbrl_node,  # Use XBRLNode instead of ReportNode
                RelationType.REPORTS,
                {
                    'report_id': self.xbrl_node.id,  # Use XBRLNode id
                    'company_cik': self.company.cik
                }
            ))

        print(f"Built {len(report_fact_relationships)} report-fact relationships")    
        
        return report_fact_relationships

    def initialize_xbrl_node(self):
        """Create XBRLNode and link it with ReportNode"""
        # Create XBRLNode
        self.xbrl_node = XBRLNode(
            primaryDocumentUrl=self.report_node.primaryDocumentUrl,
            cik=self.report_node.cik,
            report_id=self.report_node.id
        )
        
        # Export XBRLNode to Neo4j
        self.neo4j._export_nodes([self.xbrl_node], testing=False)
        
        # Create relationship between ReportNode and XBRLNode
        self.neo4j.merge_relationships([
            (self.report_node, self.xbrl_node, RelationType.HAS_XBRL)
        ])
        
        print(f"Created XBRL processing node for report: {self.report_node.id}")


