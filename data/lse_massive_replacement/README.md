# Massive Replacement Audit

This folder is an isolated, read-only audit of whether London Strategic Edge can replace Massive in EventMarketDB.

Permanent project location:
`data/lse_massive_replacement/`

## Decision

LSE cannot replace Massive as the only EventMarketDB source today. Its
regular-hours stock candles are promising, but required ETFs, daily values,
ATR, macro history, stored fields, feed rules, and data rights do not meet the
current system's needs.

The historical, code, and database work is complete. A U.S. live-stock delay
test remains for the next market session, but it cannot remove the confirmed
replacement blockers.

## Safety boundary

- No EventMarketDB production source file is changed.
- No production database is written.
- Production code and databases may be read to document current behavior.
- All new scripts, downloaded samples, comparisons, and reports stay in this folder.
- No live API key or other secret is present in the final folder.

## Main report

See [`docs/FINDINGS.md`](docs/FINDINGS.md).
