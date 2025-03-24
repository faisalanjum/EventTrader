import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from neo4j import GraphDatabase
import pandas as pd

from utils.EventTraderNodes import MarketIndexNode, SectorNode, IndustryNode, CompanyNode, AdminReportNode, AdminSectionNode
from XBRL.Neo4jManager import Neo4jManager
from XBRL.xbrl_core import RelationType

# Set up logger
logger = logging.getLogger(__name__)

class Neo4jInitializer:
    """
    Initializes Neo4j database with basic structure for EventTrader.
    
    Creates a hierarchical structure with:
    MarketIndex -> Sector -> Industry -> Company
    
    Relationship structure:
    - Sectors BELONGS_TO MarketIndex (SPY)
    - Industries BELONGS_TO their Sector
    - Companies BELONGS_TO their Industry
    - Companies can be RELATED_TO other Companies
    - News INFLUENCES Companies
    """
    
    def __init__(self, uri: str, username: str, password: str, universe_data: Optional[Dict] = None):
        """
        Initialize with Neo4j connection parameters and universe data.
        
        Args:
            uri: Neo4j database URI
            username: Neo4j username
            password: Neo4j password
            universe_data: Optional pre-loaded universe data
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.universe_data = universe_data
        self.manager = None  # Will hold Neo4jManager instance
        
        # Mappings that will be populated during initialization
        self.sector_mapping = {}      # {sector_name: sector_id}
        self.industry_mapping = {}    # {industry_name: (industry_id, sector_id)}
        self.ticker_to_cik = {}       # {ticker: cik} mapping
        self.sector_etfs = {}         # {sector_name: sector_etf}
        self.industry_etfs = {}       # {industry_name: industry_etf}
        self.etf_to_sector_id = {}    # {sector_etf: sector_id}
        self.etf_to_industry_id = {}  # {industry_etf: industry_id}
        
    def connect(self) -> bool:
        """Connect to Neo4j using Neo4jManager"""
        try:
            self.manager = Neo4jManager(
                uri=self.uri,
                username=self.username,
                password=self.password
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
            
    def close(self):
        """Close Neo4j connection"""
        if self.manager:
            self.manager.close()
    
    @staticmethod
    def get_tradable_universe(cached_data=None):
        """
        Load tradable universe directly from CSV file to avoid Redis dependency.
        
        Args:
            cached_data: Optional pre-loaded universe data
            
        Returns:
            dict: Dictionary where each symbol is a key, with company data as values.
        """
        # Return cached data if available
        if cached_data is not None:
            return cached_data
            
        try:
            # Get the project root directory and file path
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(project_root, 'StocksUniverse', 'final_symbols.csv')
            
            if not os.path.exists(file_path):
                logger.error(f"Stock universe file not found: {file_path}")
                return {}
            
            # Read CSV file and perform basic validation
            try:
                df = pd.read_csv(file_path, on_bad_lines='warn')
                if 'symbol' not in df.columns or 'cik' not in df.columns:
                    logger.error("Required columns 'symbol' and 'cik' must be in CSV")
                    return {}
            except Exception as e:
                logger.error(f"Error reading CSV file: {e}")
                return {}
            
            # Clean up dataframe - remove empty symbols and duplicates
            df = df[df['symbol'].astype(str).str.strip().str.len() > 0]
            df = df.drop_duplicates(subset=['symbol'])
            
            logger.info(f"Loaded stock universe with {len(df)} companies")
            
            # Convert DataFrame to dictionary
            universe_data = {}
            for _, row in df.iterrows():
                symbol = str(row['symbol']).strip()
                company_data = {}
                
                # Process each column
                for col in df.columns:
                    if col != 'symbol' and pd.notnull(row.get(col, '')):
                        # Special handling for related field (string list conversion)
                        if col == 'related' and isinstance(row[col], str):
                            try:
                                if row[col].startswith('[') and row[col].endswith(']'):
                                    content = row[col].strip('[]').replace("'", "").replace('"', "")
                                    related_list = [item.strip() for item in content.split(',') if item.strip()]
                                    company_data[col] = related_list
                                else:
                                    company_data[col] = []
                            except Exception:
                                company_data[col] = []
                        else:
                            company_data[col] = str(row[col]).strip()
                
                universe_data[symbol] = company_data
            
            return universe_data
            
        except Exception as e:
            logger.error(f"Error loading tradable universe: {e}")
            return {}
    
    def initialize_all(self) -> bool:
        """Run full initialization of Neo4j database with market hierarchy."""
        if not self.connect():
            return False
            
        try:
            # Load universe data if not provided
            if not self.universe_data:
                self.universe_data = self.get_tradable_universe()
                if not self.universe_data:
                    logger.error("Failed to load universe data")
                    return False
            
            logger.info("Initializing Neo4j market hierarchy")
            
            # 1. Data preparation - extract all mappings once
            self.prepare_universe_data()
            
            # 2. Node creation - create all nodes in hierarchical order
            self.create_market_nodes()
            
            # 3. Relationship creation - create all relationships
            self.create_market_relationships()
            
            # 4. Create administrative entities (SEC filing report types)
            self.create_admin_reports()
            
            # 5. Create administrative section hierarchy (new)
            self.create_admin_sections()
            
            logger.info("Market hierarchy initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Error during Neo4j initialization: {e}")
            return False
        finally:
            self.close()
    
    def prepare_universe_data(self):
        """Process universe data once, creating all required mappings."""
        # Process sectors, industries, and ETFs
        self._extract_market_mappings()
        
        # Create ticker to CIK mapping for relationship creation
        self._create_ticker_to_cik_mapping()
        
        logger.info(f"Processed universe data: {len(self.sector_mapping)} sectors, {len(self.industry_mapping)} industries")
            
    def _extract_market_mappings(self):
        """Extract sector and industry mappings from universe data"""
        # Process each company's data in a single pass
        for data in self.universe_data.values():
            sector = data.get('sector', '').strip()
            sector_etf = data.get('sector_etf', '').strip()
            industry = data.get('industry', '').strip()
            industry_etf = data.get('industry_etf', '').strip()
            
            # Process sectors
            if sector and sector.lower() not in ['nan', 'none', '']:
                # Create normalized sector name (no spaces) as ID
                sector_id = sector.replace(" ", "")
                self.sector_mapping[sector] = sector_id
                
                # Store sector ETF and create ETF-to-ID mapping in one step
                if sector_etf and sector_etf.lower() not in ['nan', 'none', '']:
                    self.sector_etfs[sector] = sector_etf
                    self.etf_to_sector_id[sector_etf] = sector_id
            
            # Process industries
            if industry and industry.lower() not in ['nan', 'none', '']:
                # Create normalized industry name (no spaces) as ID
                industry_id = industry.replace(" ", "")
                
                # Store industry with its sector ID
                sector_id = self.sector_mapping.get(sector, "")
                self.industry_mapping[industry] = (industry_id, sector_id)
                
                # Store industry ETF and create ETF-to-ID mapping in one step
                if industry_etf and industry_etf.lower() not in ['nan', 'none', '']:
                    self.industry_etfs[industry] = industry_etf
                    self.etf_to_industry_id[industry_etf] = industry_id
                
        logger.info(f"Extracted {len(self.sector_mapping)} sectors, {len(self.industry_mapping)} industries")
        logger.info(f"Found {len(self.sector_etfs)} sector ETFs, {len(self.industry_etfs)} industry ETFs")
            
    def _create_ticker_to_cik_mapping(self):
        """Create a mapping from ticker symbols to CIK for relationship creation"""
        for symbol, data in self.universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                self.ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
                
        logger.info(f"Created ticker to CIK mapping for {len(self.ticker_to_cik)} companies")
    
    def create_market_nodes(self):
        """Create all market structure nodes in hierarchy order"""
        # 1. Create MarketIndex (SPY)
        self._create_market_index()
        
        # 2. Create Sectors
        self._create_sectors()
        
        # 3. Create Industries
        self._create_industries()
        
        # 4. Create Companies (basic nodes)
        self._create_companies()
        
    def create_market_relationships(self):
        """Create all market structure relationships"""
        # 1. Link Sectors to MarketIndex
        self._link_sectors_to_market_index()
        
        # 2. Link Industries to Sectors
        self._link_industries_to_sectors()
        
        # 3. Link Companies to Industries
        self._link_companies_to_industries()
        
        # 4. Create Company-to-Company relationships
        self._create_company_relationships()

    def _create_market_index(self) -> bool:
        """Create MarketIndex node (SPY)"""
        try:
            spy_node = MarketIndexNode(
                ticker="SPY",
                name="S&P 500"
            )
            
            self.manager.merge_nodes([spy_node])
            logger.info("Created MarketIndex: SPY")
            return True
        except Exception as e:
            logger.error(f"Error creating market index: {e}")
            return False

    def _create_sectors(self) -> bool:
        """Create Sector nodes using normalized names as IDs"""
        sectors = {}  # {normalized_sector_id: (sector_name, sector_etf)}
        
        # Use sector mapping from extraction
        for sector_name, sector_id in self.sector_mapping.items():
            sector_etf = self.sector_etfs.get(sector_name)
            sectors[sector_id] = (sector_name, sector_etf)
        
        # Create sector nodes
        sector_nodes = [
            SectorNode(node_id=sector_id, name=sector_name, etf=sector_etf)
            for sector_id, (sector_name, sector_etf) in sectors.items()
        ]
        
        if not sector_nodes:
            logger.warning("No sectors found")
            return False
            
        self.manager.merge_nodes(sector_nodes)
        logger.info(f"Created {len(sector_nodes)} Sector nodes")
        return True
    
    def _create_industries(self) -> bool:
        """Create Industry nodes using normalized names as IDs"""
        industries = {}  # {normalized_industry_id: (name, sector_id, industry_etf)}
        
        # Use industry mapping from extraction
        for industry_name, (industry_id, sector_id) in self.industry_mapping.items():
            industry_etf = self.industry_etfs.get(industry_name)
            industries[industry_id] = (industry_name, sector_id, industry_etf)
        
        # Create industry nodes
        industry_nodes = [
            IndustryNode(node_id=ind_id, name=name, sector_id=sector_id, etf=industry_etf)
            for ind_id, (name, sector_id, industry_etf) in industries.items()
            if sector_id  # Only include industries with a sector
        ]
        
        if not industry_nodes:
            logger.warning("No industries found")
            return False
            
        self.manager.merge_nodes(industry_nodes)
        logger.info(f"Created {len(industry_nodes)} Industry nodes")
        return True
    
    def _create_companies(self) -> bool:
        """Create basic Company nodes"""
        valid_nodes = []
        
        # Process each company
        for symbol, data in self.universe_data.items():
            cik = data.get('cik', '').strip()
            if not cik or cik.lower() in ['nan', 'none', '']:
                continue
                
            try:
                # Create company node
                company_node = CompanyNode(
                    cik=str(cik).zfill(10),
                    name=data.get('company_name', data.get('name', symbol)).strip(),
                    ticker=symbol
                )
                
                # Add basic fields
                for field in ['exchange', 'sector', 'industry', 'sector_etf', 'industry_etf']:
                    if field in data and data[field]:
                        setattr(company_node, field, data[field])
                
                # Add financial fields
                for field, converter in {
                    'mkt_cap': float,
                    'employees': lambda x: int(float(x)),
                    'shares_out': float
                }.items():
                    if field in data and data[field]:
                        try:
                            setattr(company_node, field, 
                                    converter(str(data[field]).replace(',', '')))
                        except (ValueError, TypeError):
                            pass
                
                valid_nodes.append(company_node)
            except Exception as e:
                logger.debug(f"Error creating node for {symbol}: {e}")
        
        # Create all company nodes
        if not valid_nodes:
            logger.warning("No valid company nodes to create")
            return False
            
        self.manager.merge_nodes(valid_nodes)
        logger.info(f"Created {len(valid_nodes)} Company nodes")
        return True
    
    def _link_sectors_to_market_index(self) -> bool:
        """Link sectors to the MarketIndex (SPY)"""
        try:
            # Use the new consolidated hierarchical relationship function
            count = self.manager.create_hierarchical_relationships(
                child_label="Sector",
                parent_label="MarketIndex",
                relationship_type="BELONGS_TO",
                child_condition="NOT (c)-[:BELONGS_TO]->(:MarketIndex)",
                parent_id_property="id",
                parent_id_value="SPY"  # Specify SPY as the parent MarketIndex
            )
            
            logger.info(f"Linked {count} Sectors to MarketIndex")
            return True
        except Exception as e:
            logger.error(f"Error linking sectors to market index: {e}")
            return False
        
    def _link_industries_to_sectors(self) -> bool:
        """Link industries to their sectors"""
        try:
            # Use the new consolidated hierarchical relationship function
            count = self.manager.create_hierarchical_relationships(
                child_label="Industry",
                parent_label="Sector",
                relationship_type="BELONGS_TO",
                match_property="sector_id",
                parent_id_property="id"
            )
            
            logger.info(f"Linked {count} Industries to Sectors")
            return True
        except Exception as e:
            logger.error(f"Error linking industries to sectors: {e}")
            return False
    
    def _link_companies_to_industries(self) -> bool:
        """Connect companies to their industries using normalized industry names"""
        try:
            # Use the new specialized function that implements the entire logic
            results = self.manager.link_companies_to_industries()
            
            # Log results
            direct_match = results.get("direct_match", 0)
            name_match = results.get("name_match", 0)
            created_count = results.get("created_for_orphans", 0)
            
            logger.info(f"Connected {direct_match} companies to industries using normalized industry names")
            logger.info(f"Connected additional {name_match} companies using industry name")
            logger.info(f"Created {created_count} industries for orphaned companies")
            
            total_connected = direct_match + name_match + created_count
            logger.info(f"Connected total of {total_connected} companies to industries")
            
            return True
        except Exception as e:
            logger.error(f"Error linking companies to industries: {e}")
            return False
    
    def _create_company_relationships(self) -> bool:
        """Create bidirectional RELATED_TO relationships between companies"""
        try:
            # Get all existing companies using execute_cypher_query
            result = self.manager.execute_cypher_query(
                "MATCH (c:Company) RETURN c.id as cik, c.ticker as ticker",
                {}
            )
            
            if not result:
                logger.warning("No companies found for relationship creation")
                return False
                
            # Create a lookup for Company by CIK
            node_by_cik = {}
            for record in self.manager.driver.session().run("MATCH (c:Company) RETURN c.id as cik, c.ticker as ticker"):
                cik = record["cik"]
                ticker = record["ticker"]
                if cik and ticker:
                    node_by_cik[cik] = ticker
            
            if not node_by_cik:
                logger.warning("No companies found for relationship creation")
                return False
            
            # The rest of the method remains unchanged
            relationship_pairs = set()
            relationship_batch = []
            
            # Process each company's related tickers
            for symbol, data in self.universe_data.items():
                source_cik = self.ticker_to_cik.get(symbol.upper())
                if not source_cik:
                    continue
                
                # Parse the related field
                related_tickers = data.get('related', [])
                
                # Handle string representation
                if isinstance(related_tickers, str):
                    if related_tickers.startswith('[') and related_tickers.endswith(']'):
                        try:
                            # Extract content and split
                            content = related_tickers.strip('[]')
                            if content:
                                content = content.replace("'", "").replace('"', "")
                                related_tickers = [item.strip() for item in content.split(',') if item.strip()]
                            else:
                                related_tickers = []
                        except:
                            related_tickers = []
                    else:
                        related_tickers = []
                
                if not related_tickers:
                    continue
                
                # Create relationships
                for related_ticker in related_tickers:
                    related_cik = self.ticker_to_cik.get(related_ticker.upper())
                    if not related_cik:
                        continue
                    
                    # Only process each company pair once (regardless of direction)
                    # Sort CIKs to ensure same pair is recognized regardless of order
                    company_pair = tuple(sorted([source_cik, related_cik]))
                    if company_pair in relationship_pairs:
                        continue
                    
                    relationship_pairs.add(company_pair)
                    
                    # Add to relationship batch
                    relationship_batch.append((
                        source_cik,
                        related_cik,
                        {
                            "source_ticker": symbol,
                            "target_ticker": related_ticker,
                            "relationship_type": "news_co_occurrence",
                            "bidirectional": True
                        }
                    ))
            
            # Create the relationships in Neo4j using the batch function
            if relationship_batch:
                count = self.manager.create_company_relationships_batch(relationship_batch)
                logger.info(f"Created {count} bidirectional RELATED_TO relationships between companies")
                return True
            else:
                logger.info("No company relationships to create")
                return True
                
        except Exception as e:
            logger.error(f"Error creating company relationships: {e}")
            return False

    def create_admin_reports(self) -> bool:
        """Create admin report hierarchy for SEC filings."""
        try:
            # Define report categories and subcategories
            report_categories = {
                "10-K": "10-K Reports",
                "10-Q": "10-Q Reports", 
                "8-K": "8-K Reports",
                "SCHEDULE 13D": "Schedule 13D Reports",
                "SC TO-I": "SC TO-I Reports",
                "425": "425 Reports",
                "SC 14D9": "SC 14D9 Reports",
                "6-K": "6-K Reports"
            }
            
            # Define subcategories with their parent categories
            subcategories = [
                # 10-K subcategories for fiscal year ends
                *[{"code": f"10-K_FYE-{m}31", "label": f"FYE {m}/31", "category": "10-K"} 
                 for m in ['03', '06', '09', '12']],
                
                # 10-Q subcategories for quarters
                *[{"code": f"10-Q_Q{q}", "label": f"Q{q} Filing", "category": "10-Q"} 
                 for q in range(1, 5)]
            ]
            
            # Create parent nodes
            parent_nodes = [
                AdminReportNode(code=code, label=label, category=code)
                for code, label in report_categories.items()
            ]
            
            # Create child nodes
            child_nodes = [
                AdminReportNode(
                    code=item["code"], 
                    label=item["label"], 
                    category=item["category"]
                )
                for item in subcategories
            ]
            
            # Combine all nodes for efficient batch creation
            all_nodes = parent_nodes + child_nodes
            
            # Create nodes in a single batch operation
            self.manager._export_nodes([all_nodes])
            logger.info(f"Created {len(all_nodes)} admin report nodes")
            
            # Create parent-child relationships in a single batch
            relationships = [
                (parent, child, RelationType.HAS_SUB_REPORT)
                for parent in parent_nodes
                for child in child_nodes
                if parent.code == child.category
            ]
            
            self.manager.merge_relationships(relationships)
            logger.info(f"Created {len(relationships)} admin report hierarchical relationships")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating admin report hierarchy: {e}")
            return False

    def create_admin_sections(self) -> bool:
        """Create administrative section hierarchy for SEC filing sections."""
        try:
            from SEC_API_Files.reportSections import ten_k_sections, ten_q_sections, eight_k_sections
            
            # Define top-level section categories
            section_categories = {
                "10-K": "10-K Sections",
                "10-Q": "10-Q Sections",
                "8-K": "8-K Sections"
            }
            
            # Create parent category nodes
            parent_nodes = [
                AdminSectionNode(code=code, label=label, category=code)
                for code, label in section_categories.items()
            ]
            
            # Create child section nodes
            child_nodes = []
            
            # Process 10-K sections
            for section_code, section_label in ten_k_sections.items():
                child_nodes.append(
                    AdminSectionNode(
                        code=section_code,
                        label=section_label,
                        category="10-K"
                    )
                )
            
            # Process 10-Q sections
            for section_code, section_label in ten_q_sections.items():
                child_nodes.append(
                    AdminSectionNode(
                        code=section_code,
                        label=section_label,
                        category="10-Q"
                    )
                )
            
            # Process 8-K sections
            for section_code, section_label in eight_k_sections.items():
                child_nodes.append(
                    AdminSectionNode(
                        code=section_code,
                        label=section_label,
                        category="8-K"
                    )
                )
            
            # Combine all nodes for efficient batch creation
            all_nodes = parent_nodes + child_nodes
            
            # Create nodes in a single batch operation
            self.manager._export_nodes([all_nodes])
            logger.info(f"Created {len(all_nodes)} admin section nodes")
            
            # Create parent-child relationships in a single batch
            relationships = [
                (parent, child, RelationType.HAS_SUB_SECTION)
                for parent in parent_nodes
                for child in child_nodes
                if parent.code == child.category
            ]
            
            self.manager.merge_relationships(relationships)
            logger.info(f"Created {len(relationships)} admin section hierarchical relationships")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating admin section hierarchy: {e}")
            return False


# Standalone execution support
if __name__ == "__main__":
    import argparse
    from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    
    parser = argparse.ArgumentParser(description="Initialize Neo4j database with market hierarchy")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Run initialization
    initializer = Neo4jInitializer(
        uri=NEO4J_URI,
        username=NEO4J_USERNAME, 
        password=NEO4J_PASSWORD
    )
    
    success = initializer.initialize_all()
    if success:
        print("Neo4j initialization completed successfully")
    else:
        print("Neo4j initialization failed") 