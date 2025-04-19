from datetime import datetime, timedelta
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from neo4j import GraphDatabase
import pandas as pd
import json

from neograph.EventTraderNodes import MarketIndexNode, SectorNode, IndustryNode, CompanyNode, AdminReportNode, DateNode
# , AdminSectionNode, FinancialStatementNode
from utils.market_session import MarketSessionClassifier
from neograph.Neo4jManager import Neo4jManager
from XBRL.xbrl_core import RelationType, NodeType
from eventReturns.polygonClass import Polygon

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
        """Connect to Neo4j using Neo4jManager singleton"""
        try:
            # Import here to avoid circular imports
            from neograph.Neo4jConnection import get_manager
            
            # Use the singleton manager
            self.manager = get_manager()
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
    
    def initialize_all(self, start_date=None) -> bool:
        """
        Run full initialization of Neo4j database with market hierarchy.
        
        Args:
            start_date: Optional start date for date nodes in format 'YYYY-MM-DD'
        """
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
            
            # 5. Create administrative section hierarchy
            # self.create_admin_sections()
            
            # 6. Create financial statement hierarchy
            # self.create_financial_statements()
            
            # 7. Create exhibit section hierarchy
            # self.create_exhibit_sections()
            
            # 8. Create date nodes and relationships
            self.create_dates(start_date=start_date)
            
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
        
        # Create a unique list of all symbols (companies, sector ETFs, industry ETFs, and SPY)
        all_symbols_array = pd.unique([*self.universe_data, 
                                   *[v.get('sector_etf') for v in self.universe_data.values()], 
                                   *[v.get('industry_etf') for v in self.universe_data.values()], 
                                   'SPY'])
        
        # Convert numpy array to list immediately to avoid boolean context errors later
        self.all_symbols = all_symbols_array.tolist() if hasattr(all_symbols_array, 'tolist') else list(all_symbols_array)
        
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
                    'shares_out': float,
                    'fiscal_year_end_month': lambda x: int(float(x)),
                    'fiscal_year_end_day': lambda x: int(float(x))
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
            result = self.manager.execute_cypher_query_all(
                "MATCH (c:Company) RETURN c.id as cik, c.ticker as ticker",
                {}
            )
            
            if not result:
                logger.warning("No companies found for relationship creation")
                return False
                
            # Create a lookup for Company by CIK
            node_by_cik = {}
            with self.manager.driver.session() as session:
                for record in session.run("MATCH (c:Company) RETURN c.id as cik, c.ticker as ticker"):
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

    # def create_admin_sections(self) -> bool:
    #     """Create administrative section hierarchy for SEC filing sections."""
    #     try:
    #         from SEC_API_Files.reportSections import ten_k_sections, ten_q_sections, eight_k_sections
            
    #         # Define top-level section categories
    #         section_categories = {
    #             "10-K": "10-K Sections",
    #             "10-Q": "10-Q Sections",
    #             "8-K": "8-K Sections"
    #         }
            
    #         # Create parent category nodes
    #         parent_nodes = [
    #             AdminSectionNode(code=code, label=label, category=code)
    #             for code, label in section_categories.items()
    #         ]
            
    #         # Create child section nodes
    #         child_nodes = []
            
    #         # Process 10-K sections
    #         for section_code, section_label in ten_k_sections.items():
    #             child_nodes.append(
    #                 AdminSectionNode(
    #                     code=section_code,
    #                     label=section_label,
    #                     category="10-K"
    #                 )
    #             )
            
    #         # Process 10-Q sections
    #         for section_code, section_label in ten_q_sections.items():
    #             child_nodes.append(
    #                 AdminSectionNode(
    #                     code=section_code,
    #                     label=section_label,
    #                     category="10-Q"
    #                 )
    #             )
            
    #         # Process 8-K sections
    #         for section_code, section_label in eight_k_sections.items():
    #             child_nodes.append(
    #                 AdminSectionNode(
    #                     code=section_code,
    #                     label=section_label,
    #                     category="8-K"
    #                 )
    #             )
            
    #         # Combine all nodes for efficient batch creation
    #         all_nodes = parent_nodes + child_nodes
            
    #         # Create nodes in a single batch operation
    #         self.manager._export_nodes([all_nodes])
    #         logger.info(f"Created {len(all_nodes)} admin section nodes")
            
    #         # Create parent-child relationships in a single batch
    #         relationships = [
    #             (parent, child, RelationType.HAS_SUB_SECTION)
    #             for parent in parent_nodes
    #             for child in child_nodes
    #             if parent.code == child.category
    #         ]
            
    #         self.manager.merge_relationships(relationships)
    #         logger.info(f"Created {len(relationships)} admin section hierarchical relationships")
            
    #         return True
            
    #     except Exception as e:
    #         logger.error(f"Error creating admin section hierarchy: {e}")
    #         return False

    # def create_financial_statements(self) -> bool:
    #     """Create financial statement hierarchy for SEC filings."""
    #     try:
    #         # Define financial statement types
    #         financial_statements = {
    #             "FinancialStatements": "Financial Statements",
    #         }
            
    #         # Define statement subtypes
    #         statement_types = {
    #             "BalanceSheets": "Balance Sheets",
    #             "StatementsOfIncome": "Statements of Income",
    #             "StatementsOfShareholdersEquity": "Statements of Shareholders Equity",
    #             "StatementsOfCashFlows": "Statements of Cash Flows"
    #         }
            
    #         # Add descriptions for each statement type
    #         statement_descriptions = {
    #             "BalanceSheets": "Reports the company's assets, liabilities, and shareholders' equity at a specific point in time",
    #             "StatementsOfIncome": "Reports the company's financial performance over a specific accounting period",
    #             "StatementsOfShareholdersEquity": "Reports the changes in equity for a company during a specific period",
    #             "StatementsOfCashFlows": "Reports the cash generated and used during a specific period"
    #         }
            
    #         # Create parent category node
    #         parent_nodes = [
    #             FinancialStatementNode(
    #                 code=code, 
    #                 label=label, 
    #                 category=code,
    #                 description="Container for all standard financial statement types"
    #             )
    #             for code, label in financial_statements.items()
    #         ]
            
    #         # Create child statement nodes
    #         child_nodes = []
            
    #         # Process statement types
    #         for statement_code, statement_label in statement_types.items():
    #             child_nodes.append(
    #                 FinancialStatementNode(
    #                     code=statement_code,
    #                     label=statement_label,
    #                     category="FinancialStatements",
    #                     description=statement_descriptions.get(statement_code, "")
    #                 )
    #             )
            
    #         # Combine all nodes for efficient batch creation
    #         all_nodes = parent_nodes + child_nodes
            
    #         # Create nodes in a single batch operation
    #         self.manager._export_nodes([all_nodes])
    #         logger.info(f"Created {len(all_nodes)} financial statement nodes")
            
    #         # Create parent-child relationships in a single batch
    #         relationships = [
    #             (parent, child, RelationType.HAS_SUB_STATEMENT)
    #             for parent in parent_nodes
    #             for child in child_nodes
    #             if child.category == parent.code
    #         ]
            
    #         self.manager.merge_relationships(relationships)
    #         logger.info(f"Created {len(relationships)} financial statement hierarchical relationships")
            
    #         return True
            
    #     except Exception as e:
    #         logger.error(f"Error creating financial statement hierarchy: {e}")
    #         return False

    # def create_exhibit_sections(self) -> bool:
    #     """Create exhibit section hierarchy for SEC filing exhibits."""
    #     try:
    #         # Define nodes structure - parent and children
    #         parent_node = AdminSectionNode(
    #             code="ExhibitSections",
    #             label="Exhibit Sections",
    #             category="ExhibitSections"
    #         )
            
    #         # Define the two exhibit types we process
    #         child_nodes = [
    #             AdminSectionNode(code="EX-10", label="Material Contracts", category="ExhibitSections"),
    #             AdminSectionNode(code="EX-99", label="Additional Exhibits", category="ExhibitSections")
    #         ]
            
    #         # Create FilingTextContent as a separate top-level node
    #         filing_text_node = AdminSectionNode(
    #             code="FilingTextContent",
    #             label="Full Filing Text",
    #             category="FilingTextContent"
    #         )
            
    #         # Create all nodes in one batch
    #         all_nodes = [parent_node] + child_nodes + [filing_text_node]
    #         self.manager._export_nodes([all_nodes])
    #         logger.info(f"Created {len(all_nodes)} exhibit section nodes")
            
    #         # Create parent-child relationships
    #         relationships = [(parent_node, child, RelationType.HAS_SUB_SECTION) for child in child_nodes]
    #         self.manager.merge_relationships(relationships)
    #         logger.info(f"Created {len(relationships)} exhibit section hierarchical relationships")
            
    #         return True
    #     except Exception as e:
    #         logger.error(f"Error creating exhibit section hierarchy: {e}")
    #         return False



    def _prepare_date_node(self, date_str):
        """
        Prepare a date node with all required properties.
        
        Args:
            date_str: Date in format 'YYYY-MM-DD'
            
        Returns:
            DateNode: Prepared date node
        """
        market_classifier = MarketSessionClassifier()
        timestamp = pd.Timestamp(f"{date_str} 12:00:00-04:00")  # Noon used to check trading day status
        trading_hours, is_trading_day = market_classifier.get_trading_hours(timestamp)
        times = market_classifier.extract_times(trading_hours)
        
        date_node = DateNode(
            date_str=date_str,
            is_trading_day=is_trading_day
        )
        
        for key, time_val in times.items():
            if time_val is not None:
                setattr(date_node, key, time_val.strftime("%Y-%m-%d %H:%M:%S%z"))
                
        return date_node

    def create_dates(self, start_date=None, batch_size=1000, add_prices=True):
        """
        Create a batch of date nodes from start_date to today.
        Optimal for initial population or catching up after long gaps.

        Args:
            start_date: String in format 'YYYY-MM-DD' to start from
            batch_size: Number of nodes to process in a batch
            add_prices: Whether to add price relationships to created dates
            
        Returns:
            int: Number of date nodes created
        """
        try:
            # Default to a year ago if not specified
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

            # Generate date range from start_date to today
            end_date = datetime.now().strftime('%Y-%m-%d')
            date_range = pd.date_range(start=start_date, end=end_date)
            date_strings = [d.strftime('%Y-%m-%d') for d in date_range]

            if not date_strings:
                logger.warning(f"No dates to create between {start_date} and {end_date}")
                return 0

            # Process in batches to avoid memory issues
            total_created = 0
            for i in range(0, len(date_strings), batch_size):
                batch = date_strings[i:i+batch_size]
                date_nodes = [self._prepare_date_node(date_str) for date_str in batch]
                
                # Store dates by date_str for relationship creation
                dates_by_id = {node.date_str: node for node in date_nodes}
                
                # Merge nodes into Neo4j
                self.manager.merge_nodes(date_nodes)
                total_created += len(date_nodes)
                
                # Create NEXT relationships (requires the nodes to exist first)
                next_rels = []
                for j in range(len(batch) - 1):
                    curr_date = batch[j]
                    next_date = batch[j + 1]
                    next_rels.append((dates_by_id[curr_date], dates_by_id[next_date], RelationType.NEXT))
                
                if next_rels:
                    self.manager.merge_relationships(next_rels)
                    
                # Add price relationships if requested and we have multiple dates
                if add_prices and len(batch) > 1 and hasattr(self, 'all_symbols'):
                    # First check if any date nodes already have price relationships
                    date_ids = [node.id for node in date_nodes]
                    with self.manager.driver.session() as session:
                        check_query = """
                        MATCH (d:Date)-[r:HAS_PRICE]->(e)
                        WHERE d.id IN $date_ids
                        WITH d.id AS date_id, count(r) AS rel_count
                        WHERE rel_count > 0
                        RETURN collect(date_id) AS dates_with_relationships
                        """
                        result = session.run(check_query, {"date_ids": date_ids}).single()
                        dates_with_rels = result["dates_with_relationships"] if result else []
                        
                        # Filter out dates that already have relationships
                        if dates_with_rels:
                            filtered_dates = {date_str: node for date_str, node in dates_by_id.items() 
                                             if node.id not in dates_with_rels}
                            
                            if not filtered_dates:
                                logger.info(f"All {len(dates_by_id)} dates already have price relationships, skipping")
                            else:
                                logger.info(f"Found {len(dates_with_rels)} dates with existing price relationships, processing {len(filtered_dates)} remaining dates")
                                self.add_price_relationships_to_dates(filtered_dates)
                        else:
                            # No dates have relationships yet, process all
                            self.add_price_relationships_to_dates(dates_by_id)
                            logger.info(f"Added price relationships for batch of {len(batch)} dates")
                    
                logger.info(f"Created batch of {len(batch)} date nodes with relationships")
                
            return total_created
        except Exception as e:
            logger.error(f"Error creating date nodes: {e}")
            return 0

    def create_single_date(self, date_str=None):
        """
        Create a single date node and link it to the previous date.
        Optimal for daily updates.
        
        Args:
            date_str: Date in format 'YYYY-MM-DD', defaults to today
            
        Returns:
            bool: Success status
        """
        try:
            # Default to today if not specified
            if date_str is None:
                date_str = datetime.now().strftime('%Y-%m-%d')
                
            logger.info(f"Creating date node for {date_str}")
            
            # Prepare and save the node
            date_node = self._prepare_date_node(date_str)
            self.manager.merge_nodes([date_node])
            
            # Find previous date node
            prev_date = (pd.Timestamp(date_str) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            prev_query = "MATCH (d:Date {date: $prev_date}) RETURN d"
            prev_result = self.manager.execute_cypher_query(prev_query, {"prev_date": prev_date})
            
            if prev_result and hasattr(prev_result, 'get') and prev_result.get('d'):
                # Use manager.merge_relationships to create the relationship
                prev_node_props = dict(prev_result["d"].items())
                prev_date_node = DateNode.from_neo4j(prev_node_props)
                
                # Create NEXT relationship
                self.manager.merge_relationships([
                    (prev_date_node, date_node, RelationType.NEXT)
                ])
                
                logger.info(f"Linked date {date_str} to previous date")
            else:
                logger.warning(f"Could not link date {date_str} to previous date (which may not exist)")
            
            # Add price relationships if it's not today and is a trading day
            today = datetime.now().strftime('%Y-%m-%d')
            if date_str < today and hasattr(self, 'all_symbols') and date_node.is_trading_day:
                # Create a dictionary with just this date
                date_dict = {date_str: date_node}
                # Use the batch method with a dictionary containing only this date
                self.add_price_relationships_to_dates(date_dict, skip_latest=False)
                logger.info(f"Added price relationships for {date_str}")
            elif not date_node.is_trading_day:
                logger.info(f"Skipping price relationships for non-trading day {date_str}")
            
            return True
        except Exception as e:
            logger.error(f"Error creating single date node: {e}")
            return False

    def add_price_relationships_to_dates(self, dates_by_id, skip_latest=True, batch_size=500):
        """
        Add HAS_PRICE relationships from Date nodes to entity nodes with Polygon API data.
        
        Args:
            dates_by_id: Dictionary mapping date strings to DateNode objects
            skip_latest: Whether to skip the latest date (typically today)
            batch_size: Number of relationships to create in a single transaction
            
        Returns:
            int: Number of price relationships created
        """
        if not dates_by_id or not hasattr(self, 'all_symbols') or not self.all_symbols:
            return 0

        try:
            # Get API key and initialize polygon
            polygon_api_key = os.environ.get('POLYGON_API_KEY')
            if not polygon_api_key:
                logger.error("Missing POLYGON_API_KEY environment variable")
                return 0
            
            polygon = Polygon(api_key=polygon_api_key, polygon_subscription_delay=0)
            
            # Sort dates for processing
            sorted_dates = sorted(dates_by_id.keys())
            if not sorted_dates:
                return 0
            
            # Skip latest date if requested
            if skip_latest and len(sorted_dates) > 1:
                sorted_dates = sorted_dates[:-1]
            
            # Get all entity nodes with a single query using Neo4jManager
            # Use UNION to properly match different node types with correct properties
            entity_query = """
            MATCH (e:Company) 
            WHERE e.ticker IN $symbols
            RETURN e.id as id, e.ticker as ticker, 'Company' as type
            UNION
            MATCH (e:Sector) 
            WHERE e.etf IN $symbols
            RETURN e.id as id, e.etf as ticker, 'Sector' as type
            UNION
            MATCH (e:Industry) 
            WHERE e.etf IN $symbols
            RETURN e.id as id, e.etf as ticker, 'Industry' as type
            UNION
            MATCH (e:MarketIndex) 
            WHERE e.id IN $symbols
            RETURN e.id as id, e.id as ticker, 'MarketIndex' as type
            """
            
            # Use session with explicit transaction to avoid deadlocks
            entity_results = []
            with self.manager.driver.session() as session:
                def get_entities_tx(tx):
                    result = tx.run(entity_query, {"symbols": self.all_symbols})
                    return [record.data() for record in result]
                    
                entity_results = session.execute_read(get_entities_tx)
                
            if not entity_results:
                logger.warning("No entity nodes found for price relationships")
                return 0
                
            # Create simple ticker to entity ID mapping
            ticker_to_id = {}
            for r in entity_results:
                ticker = r["ticker"]
                if ticker:
                    ticker_to_id[ticker] = r["id"]
            
            today = datetime.now().strftime('%Y-%m-%d')
            total_rels = 0
            
            # Process each date
            for date_str in sorted_dates:
                # Skip future dates and non-trading days
                date_node = dates_by_id[date_str]
                if date_str > today or not date_node.is_trading_day:
                    continue
                    
                # Check for previous_trading_date property
                if not hasattr(date_node, 'previous_trading_date') or not date_node.previous_trading_date:
                    continue
                
                # First check if we already have price relationships for this date
                with self.manager.driver.session() as session:
                    check_query = """
                    MATCH (d:Date {id: $date_id})-[:HAS_PRICE]->(e)
                    RETURN count(e) as count
                    """
                    result = session.run(check_query, {"date_id": date_node.id}).single()
                    existing_count = result["count"] if result else 0
                    
                    # If we already have price relationships for this date, skip it
                    if existing_count > 0:
                        logger.info(f"Date {date_str} already has {existing_count} price relationships, skipping")
                        continue
                    
                # Get market data with one API call
                price_data = polygon.get_daily_market_summary(
                    date_str, date_node.previous_trading_date, self.all_symbols)
                
                if price_data is None or (hasattr(price_data, 'empty') and price_data.empty):
                    continue
                    
                # Prepare batch params
                batch_params = []
                
                # Process all tickers at once
                for ticker, row in price_data.iterrows():
                    if ticker not in ticker_to_id:
                        continue
                        
                    props = row.to_dict()
                    
                    # Format timestamp
                    if 'timestamp' in props and pd.notnull(props['timestamp']):
                        props['timestamp'] = props['timestamp'].strftime('%Y-%m-%d %H:%M:%S%z')
                    
                    batch_params.append({
                        "date_id": date_node.id,
                        "entity_id": ticker_to_id[ticker],
                        "properties": props
                    })
                    
                    # Execute batch when size reached
                    if len(batch_params) >= batch_size:
                        count = self.manager.create_price_relationships_batch(batch_params)
                        total_rels += len(batch_params)
                        batch_params = []
                
                # Process remaining items
                if batch_params:
                    count = self.manager.create_price_relationships_batch(batch_params)
                    total_rels += len(batch_params)
                    
                logger.info(f"Added price relationships for date {date_str}")
                
            if total_rels > 0:
                logger.info(f"Created {total_rels} HAS_PRICE relationships total")
                
            return total_rels
            
        except Exception as e:
            logger.error(f"Error adding price relationships: {e}")
            return 0


# Standalone execution support
if __name__ == "__main__":
    import argparse
    from eventtrader.keys import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
    
    parser = argparse.ArgumentParser(description="Initialize Neo4j database with market hierarchy")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--start_date", help="Start date for date nodes (YYYY-MM-DD format)", default="2023-01-01")
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
    
    success = initializer.initialize_all(start_date=args.start_date)
    if success:
        print(f"Neo4j initialization completed successfully from {args.start_date} to today")
    else:
        print("Neo4j initialization failed") 