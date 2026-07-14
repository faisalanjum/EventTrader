# Brief: characterize Benzinga news for exact-value extraction (NO company hardcoding)

## Context
We extract a metric's EXACT verbatim value+quote from sources. News is the last weak source:
precision 100% but recall capped — our retrieval (rank ~400 article-chunks by words of a saved
FILING quote) misses 8 of 18 values that ARE in some article, because journalist wording differs.

## Facts from our census (34 test cases, ~26 companies)
- News nodes: title, teaser, body, channels (JSON list), tags, created. 348K articles.
- channels vocab seen: News, Earnings, Earnings Beats, Earnings Misses, Guidance, Price Target,
  Analyst Ratings, Trading Ideas, Markets, Movers, Options, Hot, Top Stories, After-Hours Center...
- per-channel value-hit rate: Earnings 16% (140 articles), Earnings Beats 17%, Movers 13%,
  Markets 10%, News 3% (1,027), Analyst Ratings 3%, Price Target 3%.
- value present anywhere: 18/34 cases; present in an Earnings-channel article: 13/34.
  So Earnings-first prioritization keeps 13, and 5 hide in analyst/PT articles.
- news_samples.json (same dir): 8 REAL value-carrying Earnings articles (title/teaser/body/channels).

## Your tasks (analyze the samples + reason generally; cite evidence from them)
1. TAXONOMY: what article types exist around earnings (recap, preview, movers, analyst note,
   AI-generated summaries...)? Which types state exact metric values, where (title/teaser/body,
   which paragraph), and in what phrasing patterns?
2. RETRIEVAL DESIGN: propose the simplest GENERAL fetch+rank scheme for finding a given metric's
   value in news: how to use channels (prioritize not filter), created-date windows vs earnings
   date, title/teaser vs body, chunking. No per-company/metric lists. State expected recall gain.
3. RISKS: AI-generated article disclaimers, PR-wire reposts, paywalled teasers, consensus-vs-actual
   confusion ("beat the estimate of $X" — $X is NOT the actual), stale references to prior quarters.
   How should a precision-first reader be guarded for each?
4. VERDICT: is near-100% recall-of-present achievable on news with this design, or is there a
   structural ceiling? Justify.
Write your full answer to news_analysis_gpt.md in this same directory. Be concrete and terse.
