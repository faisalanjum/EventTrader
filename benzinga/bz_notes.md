
************************************************************************************************
**PROBLEM:**
    Need to calculate stock returns for news items at specific future times (e.g., 24h after news). Must handle thousands of items, system restarts, and work reliably on local development.
    WHY REDIS ZSET:
    - Simple but production-ready for moderate scale
    - Redis persistence means no data loss on restarts
    - ZSET (Sorted Set) provides time-based indexing
    - More reliable than Redis expiry notifications
    - Simpler than full message queue systems


{"timeforReturns": {"1h_end_time": "2025-01-02T05:00:00-05:00", "session_end_time": "2025-01-02T09:35:00-05:00", "1d_end_time": "2025-01-02T16:00:00-05:00"}, 

"metadata": {"market_session": "market_closed"}, 

"symbolsData": [{"symbol": "AMD", "sector_etf": "XLK", "industry_etf": "XSD"}, {"symbol": "NVDA", "sector_etf": "XLK", "industry_etf": "XSD"}, {"symbol": "AMZN", "sector_etf": "XLY", "industry_etf": "XRT"}]}}



**specific workflow:**
1. When news arrives:
        a. Store full news data in Redis:
        news:{id} -> {
            content: "news text",
            ticker: "AAPL",
            timestamp: "2024-01-30:10:00",
            calc_time: "2024-01-31:10:00"  # 24h later
        }

        b. Add to ZSET for time tracking:
        pending_news -> {news_id: unix_timestamp_for_calc_time}

        c. Store in Neo4j with null returns:
        CREATE (n:News {id: id, content: "...", returns: null})

2. Processing flow:
    a. Continuous script checks Redis ZSET:
    - Get current_timestamp
    - ZRANGEBYSCORE pending_news 0 current_timestamp
    
    b. For each ready news:
    - Calculate returns
    - Update Neo4j with returns
    - Remove from pending_news ZSET
    - Update news:{id} status to 'processed'

    c. Sleep 30 seconds, repeat


3. Recovery scenario:

    - System restarts
    - Script starts
    - Checks ZSET for any items <= current_time
    - Processes missed items
    - Continues normal operation

This ensures no news items are missed, efficient time-based processing, and automatic recovery after restarts.

************************************************************************************************




**Rule for News Item Symbol Validation:**
    "Any news item that doesn't contain at least one symbol matching our stocks universe is completely removed from the system. This means:

    1. Initial Validation:
    - Check if ANY valid symbols exist using _has_valid_symbols()
    - If none exist:
        - The raw content is deleted from storage (hist/live)
        - The item naturally exits the raw queue when popped
        - The item never enters the processed queue
        - No record or tracking of these invalid items is maintained

    2. Symbol Filtering (if passed initial validation):
    - After cleaning the news item
    - Keep only those symbols that exist in allowed_symbols set
    - Update processed_dict['symbols'] with filtered list
    - These filtered symbols will be used for ETF lookups and returns calculation

    This ensures we only process news items with valid symbols and maintain only the relevant symbols for each news item."


"""Redis News Storage Logic

1. preserve_processed (RedisClient.clear())
   - TRUE:  On restart → Keep processed news, delete raw
   - FALSE: On restart → Delete everything (fresh start)

2. delete_raw (NewsProcessor)
   - TRUE:  After processing → Move raw → processed
   - FALSE: After processing → Copy raw → processed (keep both)

Best Practice: preserve_processed=True, delete_raw=True
- Prevents duplicate processing
- Single source of truth
- Efficient storage
"""


Final Keys:
    - id
    - symbols
    - created (datetime)
    - updated (datetime)
    - title
    - teaser
    - body
    - authors
    - channels
    - tags
    - url


created & updated:
- example: "2024-01-01T19:33:06+00:00"
 - ISO 8601 datetime format
 - T → Separator between date and time
 - +00:00 for UTC
 - Time in 24-hour format (e.g., 19:33:06)


WebSocket/REST API -> RAW_QUEUE -> NewsProcessor -> CLEAN_QUEUE -> Neo4j

**Source → Pydantic (validation) → Redis (raw) → Processing → Neo4j**

raw_news_queue → clean_news_queue → returns_queue → neo4j_queue
    - Keep it minimal (don't over-engineer with too many queues)
    - Embedding generation happens in Neo4j

# Under the current structure:
    1.in Redis, appending ID with updated timestamp which will allow de duplicated IDs to be ingested - This means each news item is being stored with a unique updated timestamp, allowing you to keep multiple versions/updates of the same news ID. The data inside each key still maintains its original ID and structure.



Historical News - Rest API
Current News    - WebSocket
- WebSocket has Action (either Created or Updated)
- Rest API has Created and Updated fields only no Action


BzWebSocketNews -> to_unified() -> UnifiedNews
BzRestAPINews  -> to_unified() -> UnifiedNews


Classification:
  - News can be broadly classified in 2 categories:
    1. SingleStock versus MultiStock (more than 1 symbol)
    2. Unique News (Created == Updated) versus Updated News (same news id but different 'Updated')


************************************
**Step-by-Step Plan**

1. **REST API (Historical News)** - Follow the same logic as WebSocket for Action: Created & forget the 60 second filter

    - Fetch news with `created` and `updated` timestamps.
    - **Filter**: OLD - NOT USING NOW - Only store news where `updated - created <= 60 seconds` (assume it's the original). - saves History DB space
    - Link to `company` and `date` nodes in Neo4j.
    - Generate embeddings for the stored news items.

2. **WebSocket (Real-Time News)**

    **For Action: Created**
        - Store as a new node in Neo4j.
        - Generate embeddings.
        - Link to `company`'s and `date` nodes.

    **For Action: Updated**
        - **Check for Original**:
            - **Has Original**:
                - Update content & embeddings directly. (see contentIsSimilar below)
                - **Always calculate returns based on the `created` date.**
                - Retain the `created` date as a fixed property.
            - **No Original**:
                - Create a new node.
        - Link to `company` and `date` nodes.

3. **During a Trade**
    - Monitor all updates in real time.



************************************

**Problem: News Deduplication with Dynamic Symbols: Need to ensure identical news items are stored only once in Neo4j while:**

    - Handling same news (with same id) with different symbols
    - Avoiding redundant embedding generation
    - Efficiently adding new symbol relationships
    - handling out of order (Updated dates not in sequence) ingenstion

    **Solution: Hash-based MERGE pattern with automatic symbol linking:**

        MERGE (n:News {hash: f(id)})
        ON CREATE SET 
            n += $props, 
            n.created = $created,
            n.updated = $updated,
            n.embeddings = genai.vector.encode($content, 'OpenAI', {token: $token})  // Generate embeddings only for new nodes  

        ON MATCH SET 
            n.updated = CASE WHEN $updated > n.updated THEN $updated ELSE n.updated END,
            n.content = CASE WHEN $updated > n.updated THEN $content ELSE n.content END,
            n.embeddings = CASE     
                WHEN $updated > n.updated AND NOT contentIsSimilar(n.content, $content)
                THEN genai.vector.encode($content, 'OpenAI', {token: $token})
                ELSE n.embeddings END
                  
        WITH n 
        UNWIND $symbols AS symbol
        MERGE (s:Symbol {id: symbol})  // Ensure the symbol exists
        MERGE (n)-[:MENTIONS]->(s)  // Efficiently add new symbol relationships

    **Explanation:**
        1. **contentIsSimilar**: This is a custom function that checks if the new content is similar to the existing content. "Levenshtein, Jaccard, or Cosine similarity."? or simple string matching?

        In Neo4j, we could use for contentIsSimilar() with apoc.text.levenshteinSimilarity() < 0.8: 
        "WHEN $updated > n.updated AND apoc.text.levenshteinSimilarity(n.content, $content) < 0.8"
        but the issue is its only recommended for short strings like up to 200 characters (and only surface level not semantic)
        Also, simple character difference approach for contentIsSimilar() might be too basic for news - Consider using cosine similarity between embeddings themselves


        Start simple: Check if content difference is > X characters:
        def contentIsSimilar(old_content, new_content):
            # Ignore whitespace differences
            old = ' '.join(old_content.split())
            new = ' '.join(new_content.split())
            
            # If difference is less than 50 chars, consider similar
            return abs(len(new) - len(old)) < 50


        2. ***content (title, body, and teaser), updated (timestamp), and embeddings : Only these three properties are conditionally updated - ex when the news is updated. All other properties in $props should be explicitly listed if you want them updated based on timestamp.

        3. Hash = f(id): The id is enough for deduplication since you want to update existing nodes rather than create new ones for content changes.
        4. MERGE (n:News {hash: $hash}): Ensures the news node is created only once based on the hash. **Deduplication** is achieved here.
        5. ON CREATE SET n += $props, n.embeddings = generateEmbeddings($content): Attributes ($props) are added only on node creation generateEmbeddings($content) is called only when the node is new, preventing redundant embedding computations.
        6. WITH n UNWIND $symbols as symbol MERGE (s:Symbol {id: symbol}): Creates symbol nodes if they don't exist. MERGE handles node deduplication automatically.
        7. MERGE (n)-[:MENTIONS]->(s): Creates relationships between news and symbols. MERGE ensures no duplicate relationships are created, even if query runs multiple times.

        ** Use id in hash since my use case involves handling news updates (same news id with different content/symbols).**   

        ***You do not need to add symbols (securities) to the conditional update logic along with content, updated, and embeddings.
        Symbols are already handled separately and efficiently via the UNWIND and MERGE steps, which dynamically add and link them as needed.



************************************

**Discard Rules:** (to be done in redis)
    1. News with no symbol
    2. News with no 'Created' & 'Updated'
    3. News with no 'id'
    4. News can be without 'body' or 'title' or 'teaser' - so keep it


**Redis Pre-processing**
def validate_news(news):
    required = ['id', 'created', 'updated', 'symbols']
    return all(news.get(k) for k in required)

************************************


ALL AVAILABLE FIELDS (WEBSocket):
Top Level: ['api_version', 'kind', 'data']
Data Level: ['action', 'id', 'content', 'timestamp']
Content Level: ['id', 'revision_id', 'type', 'title', 'body', 'authors', 'teaser', 'url', 'tags', 'securities', 'channels', 'image', 'created_at', 'updated_at']

TOP LEVEL:
API Version: websocket/v1
Kind: News/v1

DATA LEVEL:
Action: Created
Data ID: 96927846
Timestamp: 2025-01-23T04:03:11.271Z

CONTENT LEVEL:
Content ID: 43151055
Revision ID: 51450231
Type: story


************************************
Coding Pipeline:

1. Data Standardization (Using Pydantic)
    - Define common Pydantic model for both sources:
        - id, title, content, symbols, created, updated
    - Basic field mapping to model
    - Keep timestamps in original format
    - Pydantic handles basic type validation

2. Pre-Redis Validation
    - Required fields validation (via Pydantic)
    - Remove news without symbols/id/timestamps
    - Keep raw content & symbols format
    - Keep news with missing body/title/teaser
    - Let Pydantic handle JSON serialization (ensure it's lightweight no heay load before redis)

3. Redis Queue
    - Single queue, two prefixes (historical:, websocket:)
    - Store raw standardized JSON (from Pydantic)
    - Keep original content intact
    - Store minimal metadata for source tracking

4. Pre-Neo4j Processing
    - Text cleaning/normalization
    - Token count limiting
    - Word count calculation
    - Timestamp standardization to UTC
    - Symbol format standardization
    - Final data validation

5. Neo4j Processing
    - Execute Cypher query for storage
    - Handle updates/embeddings as designed

# Benzinga News API Implementation Notes

## Error Tracking System

The system implements detailed error tracking to maintain data quality and monitor API behavior:

### Error Categories
1. **JSON Errors**
   - Failed JSON parsing
   - Malformed responses

2. **Validation Errors**
   - Missing Stocks: News items without stock symbols
   - Missing ID: Items without valid identifiers
   - Invalid Created: Malformed creation timestamps
   - Invalid Updated: Malformed update timestamps
   - Other: Unexpected schema violations

3. **Unexpected Errors**
   - Connection issues
   - API failures
   - Other runtime errors

### Purpose
- Monitor data quality
- Identify API changes
- Debug issues
- Track error patterns
- Improve reliability

### Usage
Error statistics are available through:
- Real-time logging
- Summary reports
- Error count tracking



REST API: - Raw JSON → BzRestAPINews (with nested RestAPIStock/Channel/Tag) → UnifiedNews
WebSocket: - Raw JSON → BzWebSocketNews → Content (with nested Security) → UnifiedNews