# Stock Returns Calculation Flow in EventMarketDB

## Overview
The EventMarketDB system calculates stock returns (daily_stock, hourly_stock, session_stock) for news and reports, storing them as properties on INFLUENCES relationships in Neo4j.

## Complete Flow

### 1. Returns Calculation Process

#### Entry Point: `eventReturns/ReturnsProcessor.py`
- Monitors Redis for processed news/reports
- Processes items from `news:benzinga:live:processed` and historical data
- Calculates returns using Polygon API when scheduled time arrives

#### Key Methods:
- `_calculate_available_returns()` (line 479): Calculates returns based on available timestamps
- `_calculate_specific_return()` (line 860): Calculates specific return type for all symbols

### 2. Returns Calculation Logic

#### Located in: `eventReturns/polygonClass.py`
- `get_event_returns()` (line 559): Main method for calculating returns
- Calculates returns for:
  - **stock**: The actual stock's return
  - **sector**: Sector ETF return
  - **industry**: Industry ETF return  
  - **macro**: SPY (S&P 500) return

#### Return Types:
- **hourly_return**: 60-minute return from event time
- **session_return**: Return from market open to close
- **daily_return**: 1-day impact return

#### Return Calculation Formula (line 437):
```python
ret = (e_price - s_price) / s_price * 100
```

### 3. Data Structure
Returns are stored in the following structure:
```json
{
  "returns": {
    "symbols": {
      "AAPL": {
        "hourly_return": {
          "stock": 1.23,
          "sector": 0.45,
          "industry": 0.67,
          "macro": 0.12
        },
        "session_return": {...},
        "daily_return": {...}
      }
    }
  }
}
```

### 4. Integration with Neo4j

#### Extraction in: `neograph/mixins/utility.py`
- `_extract_return_metrics()` (line 103): Extracts returns from news/report data
- Maps return data to properties:
  - `hourly_stock`, `hourly_sector`, `hourly_industry`, `hourly_macro`
  - `session_stock`, `session_sector`, `session_industry`, `session_macro`
  - `daily_stock`, `daily_sector`, `daily_industry`, `daily_macro`

#### Relationship Creation in: `neograph/mixins/utility.py`
- `_prepare_entity_relationship_params()` (line 178): Prepares relationship parameters
- Lines 250-252: **ALL metrics are added to the properties**:
  ```python
  # Add ALL metrics: stock, sector, industry, macro
  for metric_key, metric_value in symbol_data_item['metrics'].items():
      props[metric_key] = metric_value
  ```

### 5. Neo4j Storage

#### Writing to Database in: `neograph/Neo4jManager.py`
- `create_relationships()` (line 1623): Generic method to create relationships
- Line 1655: **Critical line where properties are set on relationships**:
  ```cypher
  SET rel += param.properties
  ```

## Symbol Field Usage

The `symbol` field is used to:
1. **Identify the stock** for price lookups
2. **Link to universe data** to get CIK, sector, industry, and ETF mappings
3. **Store on relationships** to track which symbol the returns apply to

## Key Files Summary

1. **Returns Calculation**:
   - `/home/faisal/EventMarketDB/eventReturns/ReturnsProcessor.py`
   - `/home/faisal/EventMarketDB/eventReturns/polygonClass.py`
   - `/home/faisal/EventMarketDB/eventReturns/EventReturnsManager.py`

2. **Neo4j Integration**:
   - `/home/faisal/EventMarketDB/neograph/mixins/utility.py` (extraction and preparation)
   - `/home/faisal/EventMarketDB/neograph/mixins/news.py` (news processing)
   - `/home/faisal/EventMarketDB/neograph/mixins/report.py` (report processing)
   - `/home/faisal/EventMarketDB/neograph/Neo4jManager.py` (database operations)

## Example INFLUENCES Relationship Properties
```
{
  "symbol": "AAPL",
  "created_at": "2024-01-15T10:30:00Z",
  "hourly_stock": 1.23,
  "hourly_sector": 0.45,
  "hourly_industry": 0.67,
  "hourly_macro": 0.12,
  "session_stock": 2.34,
  "session_sector": 1.23,
  "session_industry": 1.45,
  "session_macro": 0.89,
  "daily_stock": 3.45,
  "daily_sector": 2.12,
  "daily_industry": 2.78,
  "daily_macro": 1.56
}
```

## Processing Modes
- **Live Processing**: Real-time calculation as market data becomes available
- **Historical Processing**: Batch calculation for historical data
- **Pending Returns**: Scheduled for future calculation when data becomes available