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
    Dedicated class for initializing Neo4j database with market hierarchy:
    MarketIndex -> Sector -> Industry -> Company
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
        # Extract sector ETF mappings
        for data in self.universe_data.values():
            sector = data.get('sector', '').strip()
            sector_etf = data.get('sector_etf', '').strip()
            industry = data.get('industry', '').strip()
            industry_etf = data.get('industry_etf', '').strip()
            
            # Process sectors
            if sector and sector.lower() not in ['nan', 'none', '']:
                if sector_etf and sector_etf.lower() not in ['nan', 'none', '']:
                    # Only add if we have a valid ETF
                    self.sector_mapping[sector] = sector_etf
            
            # Process industries
            if industry and industry.lower() not in ['nan', 'none', '']:
                if industry_etf and industry_etf.lower() not in ['nan', 'none', '']:
                    # Store industry with its sector ETF
                    current_sector_etf = ''
                    if sector in self.sector_mapping:
                        current_sector_etf = self.sector_mapping[sector]
                    elif sector_etf:
                        current_sector_etf = sector_etf
                        
                    self.industry_mapping[industry] = (industry_etf, current_sector_etf)
        
        logger.info(f"Extracted {len(self.sector_mapping)} sector ETFs and {len(self.industry_mapping)} industry ETFs")
            
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
        """Create Sector nodes with ETF tickers as IDs"""
        sectors = {}  # {sector_id: sector_name}
        
        # First use mappings from CSV
        for sector_name, sector_etf in self.sector_mapping.items():
            sectors[sector_etf] = sector_name
        
        # Then process any sectors that don't have ETFs in the mapping
        for data in self.universe_data.values():
            sector_name = data.get('sector', '').strip()
            if not sector_name or sector_name.lower() in ['nan', 'none', '']:
                continue
                
            # Skip if already processed
            if sector_name in self.sector_mapping:
                continue
                
            # Generate ticker for sectors without ETFs
            sector_id = self.generate_ticker_id(sector_name)
            sectors[sector_id] = sector_name
            
            # Add to mapping for future use
            self.sector_mapping[sector_name] = sector_id
        
        # Create sector nodes
        sector_nodes = [
            SectorNode(node_id=sector_id, name=sector_name)
            for sector_id, sector_name in sectors.items()
        ]
        
        if not sector_nodes:
            logger.warning("No sectors found")
            return False
            
        self.manager.merge_nodes(sector_nodes)
        
        # Link sectors to SPY
        with self.manager.driver.session() as session:
            session.run("""
            MATCH (s:Sector)
            MATCH (m:MarketIndex {id: 'SPY'})
            MERGE (s)-[:BELONGS_TO]->(m)
            """)
            
        logger.info(f"Created {len(sector_nodes)} Sector nodes")
        return True
    
    def create_industries(self) -> bool:
        """Create Industry nodes with ETF-like IDs"""
        industries = {}  # {industry_id: (name, sector_id)}
        
        # First use mappings from CSV
        for industry_name, (industry_etf, sector_etf) in self.industry_mapping.items():
            industries[industry_etf] = (industry_name, sector_etf)
        
        # Then process any industries that don't have ETFs in the mapping
        for data in self.universe_data.values():
            industry_name = data.get('industry', '').strip()
            sector_name = data.get('sector', '').strip()
            
            if not industry_name or industry_name.lower() in ['nan', 'none', '']:
                continue
                
            # Skip if already processed
            if industry_name in self.industry_mapping:
                continue
                
            # Get sector ID from our mapping
            sector_id = self.sector_mapping.get(sector_name, '')
            
            # Generate industry ID
            industry_id = self.generate_ticker_id(industry_name)
            
            # Ensure uniqueness
            base_id = industry_id
            counter = 1
            while industry_id in industries and industries[industry_id][1] != sector_id:
                industry_id = f"{base_id}{counter}"
                counter += 1
            
            industries[industry_id] = (industry_name, sector_id)
            
            # Add to mapping for future use
            self.industry_mapping[industry_name] = (industry_id, sector_id)
        
        # Create industry nodes
        industry_nodes = [
            IndustryNode(node_id=ind_id, name=name, sector_id=sector_id)
            for ind_id, (name, sector_id) in industries.items()
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
            WHERE i.sector_id IS NOT NULL
            MATCH (s:Sector {id: i.sector_id})
            MERGE (i)-[:BELONGS_TO]->(s)
            """)
        
        logger.info(f"Created {len(industry_nodes)} Industry nodes")
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
        """Connect companies to their industries using ETF fields from CSV data"""
        with self.manager.driver.session() as session:
            # Link companies to industries directly using industry_etf
            direct_etf_result = session.run("""
            MATCH (c:Company)
            WHERE c.industry_etf IS NOT NULL AND c.industry_etf <> ''
            MATCH (i:Industry {id: c.industry_etf})
            MERGE (c)-[:BELONGS_TO]->(i)
            RETURN count(*) as connected
            """)
            etf_connected = direct_etf_result.single()["connected"]
            logger.info(f"Connected {etf_connected} companies to industries using industry_etf")
            
            # Link companies by industry name
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
                   c.sector as sector, c.industry_etf as industry_etf, c.sector_etf as sector_etf
            """).data()
            
            logger.info(f"Found {len(orphaned)} companies needing industry nodes")
            
            # Create industries for orphaned companies
            created_count = 0
            for company in orphaned:
                company_id = company["id"]
                industry_name = company["industry"]
                industry_etf = company.get("industry_etf")
                sector_etf = company.get("sector_etf")
                
                # Determine industry ID (use industry_etf if available, otherwise generate one)
                industry_id = industry_etf if industry_etf and industry_etf.strip() else self.generate_ticker_id(industry_name)
                
                # Determine sector ID (use sector_etf if available)
                sector_id = sector_etf if sector_etf and sector_etf.strip() else ""
                
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
            
            # Link industries to sectors (both existing and new)
            session.run("""
            MATCH (i:Industry)
            WHERE i.sector_id IS NOT NULL AND i.sector_id <> ''
            MATCH (s:Sector {id: i.sector_id})
            MERGE (i)-[:BELONGS_TO]->(s)
            """)
            
            # Remove any direct company->sector links (they should go through industries)
            session.run("""
            MATCH (c:Company)-[r:BELONGS_TO]->(s:Sector)
            DELETE r
            """)
            
            total_connected = etf_connected + name_connected + created_count
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