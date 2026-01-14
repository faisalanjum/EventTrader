# Queries (Direct Mode - No PIT Filtering)

## metadata
```
Task(subagent_type=neo4j-report, prompt="8-K {accession} metadata only (ticker, filed datetime, items)")
```

## exhibit
```
Task(subagent_type=neo4j-report, prompt="EX-99.1 content for {accession}")
```

## xbrl
```
Task(subagent_type=neo4j-xbrl, prompt="Last 4 quarters EPS/Revenue for {ticker}")
```

## transcript
```
Task(subagent_type=neo4j-transcript, prompt="Last 2 transcripts for {ticker}")
```

## news
```
Task(subagent_type=neo4j-news, prompt="News for {ticker} past 30 days")
```

## entity
```
Task(subagent_type=neo4j-entity, prompt="Dividends/splits for {ticker} past 90 days")
```

## consensus
```
Task(subagent_type=perplexity-search, prompt="{ticker} Q{quarter} FY{year} EPS revenue estimate consensus")
```
