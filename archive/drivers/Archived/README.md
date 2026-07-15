# Stock Movement Drivers Analysis

This folder contains systematic analyses of stock price movements based on events in the EventMarketDB.

## Contents

### Framework Document
- `Stock_Movement_Driver_Analysis_Framework.md` - The complete methodology for creating driver analysis documents
  - Unambiguous step-by-step process
  - Generic queries applicable to any company
  - Confidence scoring methodology
  - XBRL integration for movement validation

### Company Analysis Files
- `AAPL_drivers.json` - Apple Inc. stock movement analysis
  - 20 events analyzed with >2% adjusted returns
  - Detailed reasoning for each movement
  - Historical patterns and sector comparisons
  - 88.7% average confidence across events

## How to Use

1. **To analyze a new company:**
   - Follow the framework document step-by-step
   - Use the parameterized queries with your target ticker
   - Apply the confidence scoring objectively
   - Validate major movements with XBRL data when available

2. **To understand a movement:**
   - Find the event by datetime
   - Review the adjusted returns vs sector/industry
   - Read the detailed reasoning
   - Check confidence score and drivers

3. **For systematic analysis:**
   - Parse JSON files programmatically
   - Filter by confidence threshold
   - Aggregate drivers for pattern recognition
   - Compare across companies for sector trends

## Key Insights from XBRL Integration

XBRL data arrives 1.5-2 hours after initial market reaction, making it valuable for:
- **Validation**: Confirming whether market reaction was justified
- **Discovery**: Finding hidden details not in press releases
- **Quality**: Assessing earnings quality (cash flow vs reported earnings)
- **Segments**: Detailed geographic/product performance

XBRL does NOT predict movements (too late) but EXPLAINS them with forensic detail.

## File Naming Convention
`[TICKER]_drivers.json` - e.g., AAPL_drivers.json, MSFT_drivers.json

## Database Requirements
- EventMarketDB with INFLUENCES and PRIMARY_FILER relationships
- Company, News, Report, and Transcript nodes
- Return data at hourly, session, and daily levels
- Sector and industry return benchmarks