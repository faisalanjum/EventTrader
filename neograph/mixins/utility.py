import logging
import json
from typing import Dict, List

from utils.date_utils import parse_news_dates, parse_date  

logger = logging.getLogger(__name__)

class UtilityMixin:
    """
    Utility methods for Neo4j processing.
    These methods handle common data extraction and transformation operations.
    """

    def _extract_symbols_from_data(self, data_item, symbols_list=None):
        """
        Extract and normalize symbols from data item (news or report).
        Handles both direct symbols list and metadata.instruments sources.
        
        Args:
            data_item (dict): News or report data dictionary
            symbols_list (list or str, optional): Explicit symbols list to process
                                                 (if None, will use data_item.get('symbols'))
        
        Returns:
            list: List of uppercase symbol strings
        """
        symbols = []
        
        # If no explicit symbols_list provided, try to get from data_item
        if symbols_list is None:
            symbols_list = data_item.get('symbols', [])
        
        # Process symbols list
        if isinstance(symbols_list, list):
            symbols = [s.upper() for s in symbols_list if s]
        elif isinstance(symbols_list, str):
            try:
                # Try JSON parsing for array-like strings
                if symbols_list.startswith('[') and symbols_list.endswith(']'):
                    content = symbols_list.replace("'", '"')  # Make JSON-compatible
                    symbols = [s.upper() for s in json.loads(content) if s]
                # Try comma-separated string
                elif ',' in symbols_list:
                    symbols = [s.strip().upper() for s in symbols_list.split(',') if s.strip()]
                else:
                    # Single symbol
                    symbols = [symbols_list.upper()]
            except:
                # Last resort parsing for malformed strings
                clean = symbols_list.strip('[]').replace("'", "").replace('"', "")
                symbols = [s.strip().upper() for s in clean.split(',') if s.strip()]
        
        # Extract additional symbols from metadata if available
        if 'metadata' in data_item and 'instruments' in data_item['metadata']:
            for instrument in data_item['metadata']['instruments']:
                symbol = instrument.get('symbol', '')
                if symbol and symbol.upper() not in symbols:
                    symbols.append(symbol.upper())
                    
        return symbols


    def _extract_market_session(self, data_item):
        """
            str: Market session value (e.g., 'pre_market', 'in_market', 'post_market') or empty string
        """
        if 'metadata' in data_item and 'event' in data_item['metadata']:
            return data_item['metadata']['event'].get('market_session', '')
        return ''
    


    def _extract_returns_schedule(self, data_item):
        """
        Extract and parse returns schedule from data item.
        
        Args:
            data_item (dict): News or report data dictionary
            
        Returns:
            dict: Dictionary with parsed return schedule dates in ISO format
        """
        returns_schedule = {}
        
        if 'metadata' in data_item and 'returns_schedule' in data_item['metadata']:
            raw_schedule = data_item['metadata']['returns_schedule']
            
            # Parse each date in the schedule
            for key, time_str in raw_schedule.items():
                if time_str:
                    try:
                        date_obj = parse_date(time_str)
                        if date_obj:
                            returns_schedule[key] = date_obj.isoformat()
                    except Exception as e:
                        logger.warning(f"Error parsing returns schedule date '{time_str}': {e}")
        
        return returns_schedule


    def _extract_return_metrics(self, news_item, symbol) -> Dict:
        """Extract return metrics for a symbol from news data"""
        metrics = {}
        symbol_upper = symbol.upper()
        
        if 'returns' not in news_item:
            return metrics
        
        # Find symbol returns data
        symbol_returns = None
        
        # Structure 1: {'returns': {'AAPL': {...}}}
        if symbol_upper in news_item['returns']:
            symbol_returns = news_item['returns'][symbol_upper]
        
        # Structure 2: {'returns': {'symbols': {'AAPL': {...}}}}
        elif 'symbols' in news_item['returns'] and symbol_upper in news_item['returns']['symbols']:
            symbol_returns = news_item['returns']['symbols'][symbol_upper]
        
        if not symbol_returns:
            return metrics
        
        # Process different return timeframes
        for timeframe in ['hourly_return', 'session_return', 'daily_return']:
            if timeframe not in symbol_returns:
                continue
                
            if not isinstance(symbol_returns[timeframe], dict):
                logger.warning(f"Expected dictionary for {timeframe} but got {type(symbol_returns[timeframe])} for symbol {symbol}")
                continue
            
            short_timeframe = timeframe.split('_')[0]  # hourly, session, daily
            
            # Extract stock metrics
            if 'stock' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_stock"] = symbol_returns[timeframe]['stock']
            
            # Extract sector metrics
            if 'sector' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_sector"] = symbol_returns[timeframe]['sector']
            
            # Extract industry metrics
            if 'industry' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_industry"] = symbol_returns[timeframe]['industry']
            
            # Extract macro metrics
            if 'macro' in symbol_returns[timeframe]:
                metrics[f"{short_timeframe}_macro"] = symbol_returns[timeframe]['macro']
        
        return metrics


    def _parse_list_field(self, field_value) -> List:
        """Parse a field that could be a list or string representation of a list"""
        if isinstance(field_value, list):
            return field_value
        
        if isinstance(field_value, str):
            try:
                if field_value.startswith('[') and field_value.endswith(']'):
                    content = field_value.replace("'", '"')  # Make JSON-compatible
                    return json.loads(content)
                return [field_value]  # Single item
            except:
                pass
            
        return []


    def _prepare_entity_relationship_params(self, data_item, symbols, universe_data, ticker_to_cik, timestamp):
        """
        Prepare relationship parameters for different entity types based on symbols.
        Common method used by both news and reports processing.
        
        Args:
            data_item (dict): The news or report data
            symbols (list): List of symbols to process
            universe_data (dict): Universe data mapping
            ticker_to_cik (dict): Mapping of tickers to CIKs
            timestamp (str): ISO-formatted timestamp for created_at field
            
        Returns:
            tuple: (valid_symbols, company_params, sector_params, industry_params, market_params)
        """
        valid_symbols = []
        symbol_data = {}
        
        # Preprocess symbols to collect metrics and filter valid ones
        for symbol in symbols:
            symbol_upper = symbol.upper()
            cik = ticker_to_cik.get(symbol_upper)
            if not cik:
                logger.warning(f"No CIK found for symbol {symbol_upper}")
                continue  # Skip symbols without CIK
            
            # Get return metrics for this symbol
            metrics = self._extract_return_metrics(data_item, symbol_upper)
            
            # Get sector and industry information
            company_data = universe_data.get(symbol_upper, {})
            sector = company_data.get('sector')
            industry = company_data.get('industry')
            
            # Skip symbol processing if missing sector or industry data
            if not sector or not industry:
                logger.warning(f"Symbol {symbol_upper} is missing sector or industry data - skipping relationship creation")
                continue
                
            # Only add to valid symbols if it passed all checks
            valid_symbols.append(symbol_upper)
            
            # Store data for later batch processing
            symbol_data[symbol_upper] = {
                'cik': cik,
                'metrics': metrics,
                'timestamp': timestamp,
                'sector': sector,
                'industry': industry
            }
        
        # Prepare parameters for each relationship type
        company_params = []
        sector_params = []
        industry_params = []
        market_params = []

        # Prepare company relationship parameters
        for symbol in valid_symbols:
            symbol_data_item = symbol_data[symbol]
            # Prepare metrics as property
            props = {
                'symbol': symbol,
                'created_at': symbol_data_item['timestamp']
            }

            # Add stock metrics
            # for timeframe in ['hourly', 'session', 'daily']:
            #     metric_key = f"{timeframe}_stock"
            #     if metric_key in symbol_data_item['metrics']:
            #         props[metric_key] = symbol_data_item['metrics'][metric_key]

            # Add ALL metrics: stock, sector, industry, macro
            for metric_key, metric_value in symbol_data_item['metrics'].items():
                props[metric_key] = metric_value
            
            company_params.append({
                'cik': symbol_data_item['cik'],
                'properties': props
            })
        
        # Prepare sector relationship parameters
        for symbol in valid_symbols:
            symbol_data_item = symbol_data[symbol]
            sector = symbol_data_item['sector']
            
            # Prepare metrics as property
            props = {
                'symbol': symbol,
                'created_at': symbol_data_item['timestamp']
            }
            
            # Add sector metrics
            for timeframe in ['hourly', 'session', 'daily']:
                metric_key = f"{timeframe}_sector"
                if metric_key in symbol_data_item['metrics']:
                    props[metric_key] = symbol_data_item['metrics'][metric_key]
            
            # Get sector_etf for property only - not for identification
            sector_etf = None
            company_data = universe_data.get(symbol, {})
            
            # Get ETF info from company data
            if 'sector_etf' in company_data and company_data['sector_etf']:
                sector_etf = company_data['sector_etf']
            
            # Check for benchmark data in data_item for ETF property (only for news items)
            if ('metadata' in data_item and 'instruments' in data_item['metadata']):
                for instrument in data_item['metadata']['instruments']:
                    if instrument.get('symbol', '').upper() == symbol and 'benchmarks' in instrument:
                        if not sector_etf and 'sector' in instrument['benchmarks']:
                            sector_etf = instrument['benchmarks']['sector']
            
            # Normalize sector ID
            sector_id = sector.replace(" ", "")
            
            # Protection against using ETF as ID - for sectors
            if sector_etf and sector_id == sector_etf:
                logger.error(f"Sector ID {sector_id} matches ETF ticker {sector_etf} - using prefixed format to prevent this")
                sector_id = f"Sector_{sector.replace(' ', '_')}"
            
            sector_params.append({
                'sector_id': sector_id,
                'sector_name': sector,
                'sector_etf': sector_etf,
                'properties': props
            })
        
        # Prepare industry relationship parameters
        for symbol in valid_symbols:
            symbol_data_item = symbol_data[symbol]
            industry = symbol_data_item['industry']
            
            # Prepare metrics as property
            props = {
                'symbol': symbol,
                'created_at': symbol_data_item['timestamp']
            }
            
            # Add industry metrics
            for timeframe in ['hourly', 'session', 'daily']:
                metric_key = f"{timeframe}_industry"
                if metric_key in symbol_data_item['metrics']:
                    props[metric_key] = symbol_data_item['metrics'][metric_key]
            
            # Get industry_etf for property only - not for identification
            industry_etf = None
            company_data = universe_data.get(symbol, {})
            
            # Get ETF info from company data
            if 'industry_etf' in company_data and company_data['industry_etf']:
                industry_etf = company_data['industry_etf']
            
            # Check for benchmark data in data_item for ETF property (only for news items)
            if ('metadata' in data_item and 'instruments' in data_item['metadata']):
                for instrument in data_item['metadata']['instruments']:
                    if instrument.get('symbol', '').upper() == symbol and 'benchmarks' in instrument:
                        if not industry_etf and 'industry' in instrument['benchmarks']:
                            industry_etf = instrument['benchmarks']['industry']
            
            # Normalize industry ID
            industry_id = industry.replace(" ", "")
            
            # Protection against using ETF as ID - for industries
            if industry_etf and industry_id == industry_etf:
                logger.error(f"Industry ID {industry_id} matches ETF ticker {industry_etf} - using prefixed format to prevent this")
                industry_id = f"Industry_{industry.replace(' ', '_')}"
            
            industry_params.append({
                'industry_id': industry_id,
                'industry_name': industry,
                'industry_etf': industry_etf,
                'properties': props
            })
        
        # Prepare market index relationship parameters
        for symbol in valid_symbols:
            symbol_data_item = symbol_data[symbol]
            has_macro_metrics = False
            
            # Prepare metrics as property
            props = {
                'symbol': symbol,
                'created_at': symbol_data_item['timestamp']
            }
            
            # Add macro metrics
            for timeframe in ['hourly', 'session', 'daily']:
                metric_key = f"{timeframe}_macro"
                if metric_key in symbol_data_item['metrics']:
                    props[metric_key] = symbol_data_item['metrics'][metric_key]
                    has_macro_metrics = True
            
            if has_macro_metrics:
                market_params.append({
                    'properties': props
                })
                
        return valid_symbols, company_params, sector_params, industry_params, market_params



    def _create_influences_relationships(self, session, source_id, source_label, entity_type, params, create_node_cypher=None):
        """
        Generic method to create INFLUENCES relationships between a source node (News or Report) and various entity types.
        Uses Neo4jManager.create_relationships for the actual implementation.
        
        Args:
            session: Neo4j session (not used directly but kept for interface compatibility)
            source_id: ID of the source node (report or news)
            source_label: Label of the source node ("News" or "Report")
            entity_type: Type of entity to connect (Company, Sector, Industry, MarketIndex)
            params: List of parameter dictionaries for the UNWIND operation
            create_node_cypher: Optional custom Cypher for node creation/update (not used)
            
        Returns:
            Number of relationships created
        """
        if not params:
            return 0
            
        # Import here to avoid circular imports
        from ..Neo4jConnection import get_manager
        
        # Get the singleton Neo4j manager
        neo4j_manager = self.manager if hasattr(self, 'manager') else get_manager()
        
        try:
            count = 0
            if entity_type == "Company":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="Company", 
                    target_match_clause="{cik: param.cik}", 
                    rel_type="INFLUENCES", 
                    params=params
                )
            elif entity_type == "Sector":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="Sector", 
                    target_match_clause="{id: param.sector_id}", 
                    rel_type="INFLUENCES", 
                    params=params,
                    target_create_properties="target.name = param.sector_name, target.etf = param.sector_etf",
                    target_set_properties="""
                        target.etf = CASE 
                            WHEN param.sector_etf IS NOT NULL AND (target.etf IS NULL OR target.etf = '') 
                            THEN param.sector_etf ELSE target.etf 
                        END
                    """
                )
            elif entity_type == "Industry":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="Industry", 
                    target_match_clause="{id: param.industry_id}", 
                    rel_type="INFLUENCES", 
                    params=params,
                    target_create_properties="target.name = param.industry_name, target.etf = param.industry_etf",
                    target_set_properties="""
                        target.etf = CASE 
                            WHEN param.industry_etf IS NOT NULL AND (target.etf IS NULL OR target.etf = '') 
                            THEN param.industry_etf ELSE target.etf 
                        END
                    """
                )
            elif entity_type == "MarketIndex":
                count = neo4j_manager.create_relationships(
                    source_label=source_label, 
                    source_id_field="id", 
                    source_id_value=source_id,
                    target_label="MarketIndex", 
                    target_match_clause="{id: 'SPY'}", 
                    rel_type="INFLUENCES", 
                    params=params,
                    target_create_properties="target.name = 'S&P 500 ETF', target.ticker = 'SPY', target.etf = 'SPY'",
                    target_set_properties="""
                        target.ticker = 'SPY', target.etf = 'SPY',
                        target.name = CASE 
                            WHEN target.name IS NULL OR target.name = '' 
                            THEN 'S&P 500 ETF' ELSE target.name 
                        END
                    """
                )
            
            if count > 0:
                logger.info(f"Created {count} INFLUENCES relationships to {entity_type.lower()}s")
                
            return count
        finally:
            # Don't close the singleton manager
            pass


    # ----------------- BEGIN PATCH -----------------
    def _coerce_record(self, rec):
        """
        Accept neo4j.Record | dict | list[Record|dict]  ➜  dict | list[dict]
        """
        from collections.abc import Iterable
        if rec is None:
            return rec
        if isinstance(rec, list):
            return [dict(r) if not isinstance(r, dict) else r for r in rec]
        return dict(rec) if not isinstance(rec, dict) else rec
    # ----------------- END PATCH -----------------