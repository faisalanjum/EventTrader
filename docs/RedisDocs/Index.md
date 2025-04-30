---
geometry: margin=1in
fontsize: 11pt
monofont: "Courier New"
---


Complete Data Ingestion workflow:

### 1. Data Sources

#### Primary Sources for fetching data

**1.1 Benzinga News**  
- **1.1.a Historical**: REST API [`bz_restAPI.py`](../benzinga/bz_restAPI.py)  
- **1.1.b Live**: WebSocket [`bz_websocket.py`](../benzinga/bz_websocket.py)  
  - common:  
    [`bz_news_schemas.py`](../benzinga/bz_news_schemas.py)  
    [`bz_news_errors.py`](../benzinga/bz_news_errors.py)  

**1.2 SEC Reports**  
- **1.2.a Historical**: REST API [`sec_restAPI.py`](../secReports/sec_restAPI.py)  
- **1.2.b Live**: WebSocket [`sec_websocket.py`](../secReports/sec_websocket.py)  
  - common:  
    [`sec_schemas.py`](../secReports/sec_schemas.py)  
    [`sec_errors.py`](../secReports/sec_errors.py)  
    [`reportSections.py`](../secReports/reportSections.py)    

**1.3 Transcripts**  
- **1.3.a Historical**: REST API [`EarningsCallTranscripts.py`](../transcripts/EarningsCallTranscripts.py)  
- **1.3.b Live**: REST API [`transcript_schemas.py`](../transcripts/transcript_schemas.py)  

#### Supplementary Source (Market Pricing/Returns)

**1.4 Polygon Data**  
- **1.4.a**  [`polygonClass.py`](../eventReturns/polygonClass.py)  
- **1.4.b**  [`polygon_manager.py`](../eventReturns/polygon_manager.py)   
- **1.4.c** Dividends [`...py`](../path/to/polygon_dividends.py)  
- **1.4.d** Splits [`...py`](../path/to/polygon_splits.py)  


#### Returns Calculations

**1.5 Returns Calculations**  
- **1.5.a**  [`EventReturnsManager.py`](../eventReturns/EventReturnsManager.py)  
- **1.5.b**  [`ReturnsProcessor.py`](../eventReturns/ReturnsProcessor.py)   


### 2. Redis Ingestion

#### Redis Ingestion Components (`redisDB/`)

**2.1 Base Components**  
- **2.1.a** Base Processor Logic [`BaseProcessor.py`](../redisDB/BaseProcessor.py)  
- **2.1.b** Redis Constants and Keys [`redis_constants.py`](../redisDB/redis_constants.py)  
- **2.1.c** Redis Connection and Helpers [`redisClasses.py`](../redisDB/redisClasses.py)  

**2.2 Ingestion Pipelines**  
- **2.2.a** News Processing Pipeline [`NewsProcessor.py`](../redisDB/NewsProcessor.py)  
- **2.2.b** SEC Reports Processing Pipeline [`ReportProcessor.py`](../redisDB/ReportProcessor.py)  
- **2.2.c** Transcript Processing Pipeline [`TranscriptProcessor.py`](../redisDB/TranscriptProcessor.py)  

### 3. Neo4j Ingestion

#### Core Components (`neograph/`)

**3.1 Initialization and Connection**  
- **3.1.a** Neo4j Initialization [`Neo4jInitializer.py`](../neograph/Neo4jInitializer.py)  
- **3.1.b** Neo4j Connection Handling [`Neo4jConnection.py`](../neograph/Neo4jConnection.py)  
- **3.1.c** Graph Management Utilities [`Neo4jManager.py`](../neograph/Neo4jManager.py)  

**3.2 Graph Processing**  
- **3.2.a** Graph Processor Core [`Neo4jProcessor.py`](../neograph/Neo4jProcessor.py)  
- **3.2.b** Node Definitions and Structures [`EventTraderNodes.py`](../neograph/EventTraderNodes.py)  

#### Mixins (`neograph/mixins/`)

**3.3 Ingestion Logic by Data Type**  
- **3.3.a** News Ingestion [`news.py`](../neograph/mixins/news.py)  
- **3.3.b** Report Ingestion [`report.py`](../neograph/mixins/report.py)  
- **3.3.c** Transcript Ingestion [`transcript.py`](../neograph/mixins/transcript.py)  
- **3.3.d** XBRL Ingestion [`xbrl.py`](../neograph/mixins/xbrl.py)  

**3.4 Shared Functionalities**  
- **3.4.a** Embedding Support [`embedding.py`](../neograph/mixins/embedding.py)  
- **3.4.b** Initialization Helpers [`initialization.py`](../neograph/mixins/initialization.py)  
- **3.4.c** Pub/Sub Integration [`pubsub.py`](../neograph/mixins/pubsub.py)  
- **3.4.d** Reconciliation Logic [`reconcile.py`](../neograph/mixins/reconcile.py)  
- **3.4.e** Utility Functions [`utility.py`](../neograph/mixins/utility.py)  


### 4. Utility Modules

#### Core Utility Scripts (`utils/`)

**4.1 General Utilities**  
- **4.1.a** Date Helpers [`date_utils.py`](../utils/date_utils.py)  
- **4.1.b** Miscellaneous Helpers [`misc.py`](../utils/misc.py)  
- **4.1.c** Graceful Shutdown Handling [`graceful_shutdown.py`](../utils/graceful_shutdown.py)  
- **4.1.d** Logging Configuration [`log_config.py`](../utils/log_config.py)  
- **4.1.e** Market Session Management [`market_session.py`](../utils/market_session.py)  

**4.2 Data and Metadata**  
- **4.2.a** ETF Mapping Logic [`ETF_mappings.py`](../utils/ETF_mappings.py)  
- **4.2.b** Local CSV Reader [`fetchLocalcsv.py`](../utils/fetchLocalcsv.py)  
- **4.2.c** Metadata Field Management [`metadata_fields.py`](../utils/metadata_fields.py)  

**4.3 Monitoring**  
- **4.3.a** Stats Tracker [`stats_tracker.py`](../utils/stats_tracker.py)  


### 5. Configuration

#### Central Configuration Management (`config/`)

**5.1 Core Configuration Files**  
- **5.1.a** Central Data Coordination Logic [`DataManagerCentral.py`](../config/DataManagerCentral.py)  
- **5.1.b** Feature Flags and Toggles [`feature_flags.py`](../config/feature_flags.py)  

