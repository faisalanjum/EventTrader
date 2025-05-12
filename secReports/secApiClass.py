import asyncio
import json
import aiohttp
import backoff
import time
import logging
from typing import Optional, Dict, Any, List
from eventtrader.keys import SEC_API_KEY
from tqdm.asyncio import tqdm_asyncio

logger = logging.getLogger(__name__)

class SECApi:
    def __init__(self, api_key: Optional[str] = None, max_concurrent: int = 10):
        self.base_url = "https://api.sec-api.io"
        self.api_key = api_key or SEC_API_KEY
        self.max_concurrent = max_concurrent
        self.session = None
        self.rate_limit = asyncio.Semaphore(20)  # Max 5 requests per second
        self.last_request_time = time.time()
 
        # Separate caches for different types of data
        self._cache = { 'company_info': {}, 'filings': {}, 'statements': {}, 'ownership': {} }
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()


    @backoff.on_exception( backoff.expo, (aiohttp.ClientError, asyncio.TimeoutError), max_tries=5, max_time=30)    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make authenticated request to SEC API with rate limiting and retries."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Ensure minimum time between requests
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < 0.1:  # At least 200ms between requests
            await asyncio.sleep(0.1 - elapsed)
            
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params['token'] = self.api_key
        
        async with self.rate_limit:
            async with self.session.get(url, params=params, timeout=10) as response:
                self.last_request_time = time.time()
                
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', '5'))
                    # logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(endpoint, params)
                
                response.raise_for_status()
                await asyncio.sleep(0.1)  # Increased from 0.1
                return await response.json()
            


    
    async def get_company_info(self, cik: str) -> Optional[Dict[str, Any]]:
        """Get company information by CIK with categorized caching."""
        if cik in self._cache['company_info']:    # Changed from self.cache to self._cache
            return self._cache['company_info'][cik]
        
        
        try:
            cik_str = str(int(cik)).zfill(10)
            data = await self._make_request(f"mapping/cik/{cik_str}")
            
            if not data:
                logger.warning(f"No data returned from API for CIK {cik_str}")
                return None
                
            if not isinstance(data, list) or len(data) == 0:
                logger.warning(f"Unexpected data format for CIK {cik_str}: {data}")
                return None
                
            company = data[0]
            result = {
                'name': company.get('name'),
                'ticker': company.get('ticker'),
                'cik': company.get('cik'),
                'cusip': company.get('cusip'),
                'exchange': company.get('exchange'),
                'isDelisted': company.get('isDelisted'),
                'category': company.get('category'),
                'sector': company.get('sector'),
                'industry': company.get('industry'),
                'sic': company.get('sic'),
                'sicSector': company.get('sicSector'),
                'sicIndustry': company.get('sicIndustry'),
                'currency': company.get('currency'),
                'location': company.get('location')
            }


            # Cache in the appropriate category
            self._cache['company_info'][cik] = result 
            return result
            
        except Exception as e:
            logger.error(f"Error fetching SEC data for CIK {cik}: {str(e)}", exc_info=True)
            return None
    

    async def get_companies_info(self, ciks: List[str], show_progress: bool = True) -> Dict[str, Dict]:
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(cik: str) -> tuple:
            async with semaphore:
                result = await self.get_company_info(cik)
                return cik, result
        
        tasks = [fetch_with_semaphore(cik) for cik in ciks]
        
        # Only show progress if requested
        if show_progress:
            results = await tqdm_asyncio.gather(*tasks, desc="Fetching batch")
        else:
            results = await asyncio.gather(*tasks)
            
        return {cik: info for cik, info in results if info is not None}