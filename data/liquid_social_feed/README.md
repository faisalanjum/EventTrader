# Liquid social feed

Free, live posts from a curated list of X and Truth Social accounts. The source is
Liquid Co-Invest's public, no-key endpoint.

Live check on 2026-07-19: 39 configured accounts, 32 active, and fresh Sunday posts
arriving in the 100-event rolling feed.

## Run

From the repository root:

```bash
python3 data/liquid_social_feed/poll_feed.py --roster
python3 data/liquid_social_feed/poll_feed.py --once
python3 data/liquid_social_feed/poll_feed.py --loop --interval 25
```

The rolling event log and last-seen state always stay in this folder. They are
ignored by Git because they are runtime files.

## Test

```bash
python3 -m unittest discover -s data/liquid_social_feed -p 'test_*.py' -v
```

## Limits

- The endpoint is undocumented and may change or disappear.
- It keeps only about 100 recent posts, so continuous use requires polling.
- The simple ticker finder is only a hint. It is not reliable company matching.
- Use this as a research signal, not as production infrastructure.
