import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from neo4j import GraphDatabase

from utils.EventTraderNodes import MarketIndexNode, SectorNode, IndustryNode, CompanyNode
from XBRL.Neo4jManager import Neo4jManager
from XBRL.XBRLClasses import RelationType

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
    
    This maintains a clean hierarchical structure:
    1. Companies only directly belong to Industries
    2. Industries only directly belong to Sectors
    3. Sectors only directly belong to the MarketIndex
    
    Note: The Neo4j schema visualization may show transitive relationships
    (e.g., it might appear companies "belong to" the MarketIndex directly).
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
        self.sector_mapping = {}  # {sector_name: sector_etf}
        self.industry_mapping = {}  # {industry_name: (industry_etf, sector_etf)}
        self.ticker_to_cik = {}  # {ticker: cik} mapping for creating relationships
        
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
    
    def initialize_all(self) -> bool:
        """Run full initialization of Neo4j database with market hierarchy."""
        if not self.connect():
            return False
            
        try:
            # Load universe data if not provided
            if not self.universe_data:
                from utils.Neo4jProcessor import Neo4jProcessor
                processor = Neo4jProcessor(uri=self.uri, username=self.username, password=self.password)
                self.universe_data = processor.get_tradable_universe()
                if not self.universe_data:
                    logger.error("Failed to load universe data")
                    return False
            
            logger.info("Initializing Neo4j market hierarchy")
            
            # Extract mappings from universe data
            self.extract_mappings()
            
            # Create company ticker to CIK mappings
            self._create_ticker_to_cik_mapping()
            
            # Build the hierarchy top-down
            self.create_market_index()      # MarketIndex (SPY)
            self.create_sectors()           # Sectors → MarketIndex
            self.create_industries()        # Industries → Sectors
            self.create_companies()         # Companies (basic nodes)
            self.link_companies()           # Companies → Industries
            
            # Create company-to-company relationships
            self.create_company_relationships()
            
            logger.info("Market hierarchy initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Error during Neo4j initialization: {e}")
            return False
        finally:
            self.close()
            
    def extract_mappings(self):
        """Extract sector and industry mappings from universe data"""
        # Extract sector ETF mappings and create normalized names
        sector_etfs = {}  # {sector_name: sector_etf}
        industry_etfs = {}  # {industry_name: industry_etf}
        
        for data in self.universe_data.values():
            sector = data.get('sector', '').strip()
            sector_etf = data.get('sector_etf', '').strip()
            industry = data.get('industry', '').strip()
            industry_etf = data.get('industry_etf', '').strip()
            
            # Process sectors - use normalized name (without spaces) as ID
            if sector and sector.lower() not in ['nan', 'none', '']:
                # Create normalized sector name (no spaces) as ID
                sector_id = sector.replace(" ", "")
                self.sector_mapping[sector] = sector_id
                
                # Store sector ETF if available
                if sector_etf and sector_etf.lower() not in ['nan', 'none', '']:
                    sector_etfs[sector] = sector_etf
            
            # Process industries - use normalized name (without spaces) as ID
            if industry and industry.lower() not in ['nan', 'none', '']:
                # Create normalized industry name (no spaces) as ID
                industry_id = industry.replace(" ", "")
                
                # Store industry with its sector ID
                sector_id = ""
                if sector in self.sector_mapping:
                    sector_id = self.sector_mapping[sector]
                        
                self.industry_mapping[industry] = (industry_id, sector_id)
                
                # Store industry ETF if available
                if industry_etf and industry_etf.lower() not in ['nan', 'none', '']:
                    industry_etfs[industry] = industry_etf
        
        # Store ETF mappings for later use
        self.sector_etfs = sector_etfs
        self.industry_etfs = industry_etfs
        
        logger.info(f"Extracted {len(self.sector_mapping)} sectors and {len(self.industry_mapping)} industries with normalized name IDs")
        logger.info(f"Found {len(sector_etfs)} sector ETFs and {len(industry_etfs)} industry ETFs")
        
        # Create a mapping from ETFs to normalized names for news processing
        self.etf_to_sector_id = {}
        self.etf_to_industry_id = {}
        
        for data in self.universe_data.values():
            sector = data.get('sector', '').strip()
            sector_etf = data.get('sector_etf', '').strip()
            industry = data.get('industry', '').strip()
            industry_etf = data.get('industry_etf', '').strip()
            
            # Map ETFs to normalized names
            if sector_etf and sector_etf.lower() not in ['nan', 'none', ''] and sector:
                self.etf_to_sector_id[sector_etf] = self.sector_mapping.get(sector, "")
                
            if industry_etf and industry_etf.lower() not in ['nan', 'none', ''] and industry:
                self.etf_to_industry_id[industry_etf] = self.industry_mapping.get(industry, ("", ""))[0]
                
        logger.info(f"Created ETF to name mappings: {len(self.etf_to_sector_id)} sectors, {len(self.etf_to_industry_id)} industries")
            
    def _create_ticker_to_cik_mapping(self):
        """Create a mapping from ticker symbols to CIK for relationship creation"""
        for symbol, data in self.universe_data.items():
            cik = data.get('cik', '').strip()
            if cik and cik.lower() not in ['nan', 'none', '']:
                self.ticker_to_cik[symbol.upper()] = str(cik).zfill(10)
            
    def create_market_index(self) -> bool:
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
    
    def generate_ticker_id(self, name: str) -> str:
        """Generate ETF-like ticker from a name"""
        # Use first letters of words + add chars to ensure 3+ chars
        ticker = ''.join(word[0] for word in name.split()[:3]).upper()
        if len(ticker) < 3:
            ticker = (ticker + name.replace(' ', '')[:3-len(ticker)]).upper()
        return ticker
    
    def create_sectors(self) -> bool:
        """Create Sector nodes using normalized names (without spaces) as IDs"""
        sectors = {}  # {normalized_sector_id: (sector_name, sector_etf)}
        
        # Use sector mapping (normalized names) from extraction
        for sector_name, sector_id in self.sector_mapping.items():
            # Get ETF for this sector if available
            sector_etf = self.sector_etfs.get(sector_name)
            sectors[sector_id] = (sector_name, sector_etf)
        
        # Then process any sectors not already in the mapping
        for data in self.universe_data.values():
            sector_name = data.get('sector', '').strip()
            sector_etf = data.get('sector_etf', '').strip()
            
            if not sector_name or sector_name.lower() in ['nan', 'none', '']:
                continue
                
            # Skip if already processed
            if sector_name in self.sector_mapping:
                continue
                
            # Generate normalized sector ID
            sector_id = sector_name.replace(" ", "")
            sectors[sector_id] = (sector_name, sector_etf if sector_etf else None)
            
            # Add to mapping for future use
            self.sector_mapping[sector_name] = sector_id
        
        # Create sector nodes
        sector_nodes = [
            SectorNode(node_id=sector_id, name=sector_name, etf=sector_etf)
            for sector_id, (sector_name, sector_etf) in sectors.items()
        ]
        
        if not sector_nodes:
            logger.warning("No sectors found")
            return False
            
        self.manager.merge_nodes(sector_nodes)
        
        # Link sectors to SPY
        # This establishes the top level of our hierarchy: Sectors belong to MarketIndex
        # We don't create direct relationships from Industry or Company to MarketIndex
        with self.manager.driver.session() as session:
            session.run("""
            MATCH (s:Sector)
            WHERE NOT (s)-[:BELONGS_TO]->(:MarketIndex)
            MATCH (m:MarketIndex {id: 'SPY'})
            MERGE (s)-[:BELONGS_TO]->(m)
            """)
            
        logger.info(f"Created {len(sector_nodes)} Sector nodes using normalized name IDs")
        return True
    
    def create_industries(self) -> bool:
        """Create Industry nodes using normalized names (without spaces) as IDs"""
        industries = {}  # {normalized_industry_id: (name, sector_id, industry_etf)}
        
        # Use industry mapping (normalized names) from extraction
        for industry_name, (industry_id, sector_id) in self.industry_mapping.items():
            # Get ETF for this industry if available
            industry_etf = self.industry_etfs.get(industry_name)
            industries[industry_id] = (industry_name, sector_id, industry_etf)
        
        # Then process any industries not already in the mapping
        for data in self.universe_data.values():
            industry_name = data.get('industry', '').strip()
            sector_name = data.get('sector', '').strip()
            industry_etf = data.get('industry_etf', '').strip()
            
            if not industry_name or industry_name.lower() in ['nan', 'none', '']:
                continue
                
            # Skip if already processed
            if industry_name in self.industry_mapping:
                continue
                
            # Get sector ID from our mapping
            sector_id = self.sector_mapping.get(sector_name, '')
            
            # Generate normalized industry ID
            industry_id = industry_name.replace(" ", "")
            
            # Ensure uniqueness
            base_id = industry_id
            counter = 1
            while industry_id in industries and industries[industry_id][1] != sector_id:
                industry_id = f"{base_id}{counter}"
                counter += 1
            
            industries[industry_id] = (industry_name, sector_id, industry_etf if industry_etf else None)
            
            # Add to mapping for future use
            self.industry_mapping[industry_name] = (industry_id, sector_id)
        
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
        
        # Link industries to sectors
        with self.manager.driver.session() as session:
            session.run("""
            MATCH (i:Industry)
            WHERE i.sector_id IS NOT NULL AND i.sector_id <> ''
            AND NOT (i)-[:BELONGS_TO]->(:Sector)
            MATCH (s:Sector {id: i.sector_id})
            MERGE (i)-[:BELONGS_TO]->(s)
            """)
        
        logger.info(f"Created {len(industry_nodes)} Industry nodes using normalized name IDs")
        return True
    
    def create_companies(self) -> bool:
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
    
    def link_companies(self) -> bool:
        """Connect companies to their industries using normalized industry names"""
        with self.manager.driver.session() as session:
            # Prepare company records with normalized industry names
            session.run("""
            MATCH (c:Company)
            WHERE c.industry IS NOT NULL AND c.industry <> ''
            SET c.industry_normalized = replace(c.industry, " ", "")
            """)
            
            # Link companies to industries using normalized industry names
            direct_result = session.run("""
            MATCH (c:Company)
            WHERE c.industry_normalized IS NOT NULL AND c.industry_normalized <> ''
            MATCH (i:Industry {id: c.industry_normalized})
            MERGE (c)-[:BELONGS_TO]->(i)
            RETURN count(*) as connected
            """)
            direct_connected = direct_result.single()["connected"]
            logger.info(f"Connected {direct_connected} companies to industries using normalized industry names")
            
            # Link companies by case-insensitive industry name for any that didn't match exactly
            name_result = session.run("""
            MATCH (c:Company)
            WHERE c.industry IS NOT NULL AND c.industry <> ''
            AND NOT (c)-[:BELONGS_TO]->(:Industry)
            MATCH (i:Industry)
            WHERE toLower(trim(i.name)) = toLower(trim(c.industry))
            MERGE (c)-[:BELONGS_TO]->(i)
            RETURN count(*) as connected
            """)
            name_connected = name_result.single()["connected"]
            logger.info(f"Connected additional {name_connected} companies using industry name")
            
            # Find remaining companies without industry links
            orphaned = session.run("""
            MATCH (c:Company)
            WHERE NOT (c)-[:BELONGS_TO]->(:Industry)
            AND c.industry IS NOT NULL AND c.industry <> ''
            RETURN c.id as id, c.ticker as ticker, c.industry as industry, 
                   c.sector as sector
            """).data()
            
            logger.info(f"Found {len(orphaned)} companies needing industry nodes")
            
            # Create industries for orphaned companies
            created_count = 0
            for company in orphaned:
                company_id = company["id"]
                industry_name = company["industry"]
                sector_name = company.get("sector", "")
                
                # Generate normalized industry ID
                industry_id = industry_name.replace(" ", "")
                
                # Determine sector ID
                sector_id = ""
                if sector_name:
                    sector_id = sector_name.replace(" ", "")
                
                # Create industry node with proper sector relationship
                session.run("""
                MERGE (i:Industry {id: $industry_id})
                ON CREATE SET i.name = $industry_name,
                             i.sector_id = $sector_id
                WITH i
                MATCH (c:Company {id: $company_id})
                MERGE (c)-[:BELONGS_TO]->(i)
                """, {
                    "industry_id": industry_id,
                    "industry_name": industry_name,
                    "sector_id": sector_id,
                    "company_id": company_id
                })
                created_count += 1
            
            # Link industries to sectors (for newly created industries)
            # Note: We only link sectors to MarketIndex and industries to sectors, not all to MarketIndex.
            # The schema visualization may show transitive relationships which is why it appears all belong to MarketIndex
            session.run("""
            MATCH (i:Industry)
            WHERE i.sector_id IS NOT NULL AND i.sector_id <> ''
            AND NOT (i)-[:BELONGS_TO]->(:Sector)
            MATCH (s:Sector {id: i.sector_id})
            MERGE (i)-[:BELONGS_TO]->(s)
            """)
            
            # Remove any direct company->sector links (they should go through industries)
            session.run("""
            MATCH (c:Company)-[r:BELONGS_TO]->(s:Sector)
            DELETE r
            """)
            
            total_connected = direct_connected + name_connected + created_count
            logger.info(f"Connected total of {total_connected} companies to industries")
            
            return True
    
    def create_company_relationships(self) -> bool:
        """Create bidirectional RELATED_TO relationships between companies"""
        try:
            # Create a lookup for Company by CIK
            node_by_cik = {}
            with self.manager.driver.session() as session:
                result = session.run("MATCH (c:Company) RETURN c.id as cik, c.ticker as ticker")
                for record in result:
                    cik = record["cik"]
                    ticker = record["ticker"]
                    if cik and ticker:
                        node_by_cik[cik] = ticker
                
            if not node_by_cik:
                logger.warning("No companies found for relationship creation")
                return False
            
            # Use a set to track unique company pairs (regardless of direction)
            relationship_pairs = set()
            relationships = []
            
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
                    
                    # Add to relationship list
                    relationships.append((
                        source_cik,
                        related_cik,
                        {
                            "source_ticker": symbol,
                            "target_ticker": related_ticker,
                            "relationship_type": "news_co_occurrence",
                            "bidirectional": True  # Flag to indicate bidirectional relationship
                        }
                    ))
            
            # Create the relationships in Neo4j
            if relationships:
                with self.manager.driver.session() as session:
                    batch_size = 100  # Process in batches for better performance
                    for i in range(0, len(relationships), batch_size):
                        batch = relationships[i:i+batch_size]
                        for source_cik, target_cik, props in batch:
                            # Use undirected relationship syntax (no directional arrow)
                            session.run("""
                            MATCH (source:Company {id: $source_cik})
                            MATCH (target:Company {id: $target_cik})
                            MERGE (source)-[r:RELATED_TO]-(target)
                            ON CREATE SET r += $props
                            """, {
                                "source_cik": source_cik,
                                "target_cik": target_cik,
                                "props": props
                            })
            
                logger.info(f"Created {len(relationships)} bidirectional RELATED_TO relationships between companies")
                return True
            else:
                logger.info("No company relationships to create")
                return True
                
        except Exception as e:
            logger.error(f"Error creating company relationships: {e}")
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