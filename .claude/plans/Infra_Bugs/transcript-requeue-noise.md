# BUG: Live mode re-queues already-ingested transcripts every poll cycle

**Discovered**: 2026-03-04
**Status**: OPEN
**Severity**: Low — no data impact, just log noise and minor wasted work

---

## Symptom

In live mode, the transcript scheduler re-adds all of today's transcripts to the raw queue every 5 minutes, even after they've been successfully ingested into Neo4j:

```
22:36:36 - Adding transcript to live raw queue: AVGO_2026-03-04T17.00
22:36:36 - Adding transcript to live raw queue: VEEV_2026-03-04T17.00
... (7 transcripts × every 5 min)
```

## Why It's Mostly Harmless

- Downstream dedup (`_transcript_exists` Redis check) catches them early and skips processing
- EarningsCall API calendar calls are disk-cached via `requests_cache`
- OpenAI analyst extraction only runs on first pass when transcript is actually new
- No duplicate data in Neo4j

## What Could Be Better

The scheduler doesn't check whether a transcript is already ingested before adding it to the queue. A pre-check against Redis or Neo4j before queuing would eliminate the noise.

## Files

- Transcript scheduling logic in `transcripts/EarningsCallTranscripts.py`
- Live polling loop in `scripts/run_event_trader.py`
