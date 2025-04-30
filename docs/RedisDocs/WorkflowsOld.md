

### 2. Descriptions

   a) WebSocket Stream (`bz_websocket.py`):
   
   • Connects to Benzinga WebSocket API for real-time news  
   • Receives news items and validates them  
   • Stores in Redis under `news:benzinga:live:raw:{id}.{updated}`  
   • Pushes key to `news:benzinga:queues:raw`

   b) REST API (`bz_restAPI.py`):

   • Fetches historical news data in batches  
   • Validates and processes news items  
   • Stores in Redis under `news:hist:raw:{id}.{updated}`  
   • Pushes key to same `news:queues:raw`

2. News Processing (`NewsProcessor.py`):

   • Continuously monitors `news:queues:raw`  
   • For each raw news item:  
     1. Validates symbols against allowed universe  
     2. Cleans news content  
     3. Generates metadata using `EventReturnsManager`  
     4. Moves processed news to `news:benzinga:{live|hist}:processed:{id}.{updated}`  
     5. Pushes key to `news:benzinga:queues:processed`  
     6. Publishes to `news:benzinga:live:processed` channel

3. Returns Processing (`ReturnsProcessor.py`):

   • Listens for processed news on `news:live:processed` channel  
   • For each news item:  
     1. Calculates immediately available returns using `EventReturnsManager`  
     2. Schedules future returns in `news:pending_news_returns` ZSET  
   • Moves news to either:  
     • `news:withreturns:{id}` (if all returns calculated)  
     • `news:withoutreturns:{id}` (if pending returns)  
   • Continuously monitors ZSET for pending returns  
   • Updates returns as they become available

4. Event Returns Manager (`EventReturnsManager.py`):

   • Handles metadata generation and return calculations  
   • Manages market session timing  
   • Calculates three types of returns:  
     • Hourly returns (1h after event)  
     • Session returns (end of current session)  
     • Daily returns (end of next trading day)

5. Redis Management (`redisClasses.py`):

   • Manages Redis connections and operations  
   • Handles queues and data storage  
   • Maintains separate namespaces for live and historical data  
   • Manages configuration and stock universe data

Key Redis Structures:

Queues:  
- `news:queues:raw`  
- `news:queues:processed`  
- `news:queues:failed`  

Namespaces:  
- `news:live:raw:{id}.{updated}`  
- `news:hist:raw:{id}.{updated}`  
- `news:live:processed:{id}.{updated}`  
- `news:hist:processed:{id}.{updated}`  
- `news:withreturns:{id}`  
- `news:withoutreturns:{id}`
