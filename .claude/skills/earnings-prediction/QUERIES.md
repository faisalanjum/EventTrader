# Queries (PIT Filtered Mode)

## metadata
```
/filtered-data --agent neo4j-report --query "8-K {accession} metadata only (ticker, filed datetime, items)"
```

## exhibit
```
/filtered-data --agent neo4j-report --query "EX-99.1 content for {accession}"
```

## xbrl
```
/filtered-data --agent neo4j-xbrl --query "[PIT: {filing_datetime}] Last 4 quarters EPS/Revenue for {ticker}"
```

## transcript
```
/filtered-data --agent neo4j-transcript --query "[PIT: {filing_datetime}] Last 2 transcripts for {ticker}"
```

## news
```
/filtered-data --agent neo4j-news --query "[PIT: {filing_datetime}] News for {ticker} past 30 days"
```

## entity
```
/filtered-data --agent neo4j-entity --query "[PIT: {filing_datetime}] Dividends/splits for {ticker} past 90 days"
```

## consensus
```
/filtered-data --agent perplexity-search --query "[PIT: {filing_datetime}] {ticker} Q{quarter} FY{year} EPS revenue estimate consensus"
```
