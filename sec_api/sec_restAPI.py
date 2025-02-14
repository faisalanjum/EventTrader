from typing import List, Dict
from utils.redisClasses import RedisClient

class SECRestAPI:
    def __init__(self, api_key: str, redis_client: RedisClient, ttl: int = 3600):
        self.api_key = api_key
        self.redis_client = redis_client
        self.ttl = ttl

    def get_historical_data(self, date_from: str, date_to: str, raw: bool = False) -> List[Dict]:
        print(f"[DEBUG] SECRestAPI: Skipping historical data fetch ({date_from} to {date_to})")
        return []