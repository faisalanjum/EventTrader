# Market data sources

| Source / folder | Purpose |
|---|---|
| `lse_massive_replacement` | Tests whether LSE data can replace Massive calculations |
| `liquid_social_feed` | Live X and Truth Social research feed |
| `hyperliquid_24x7_prices` | Overnight and weekend market-price signal |
| [FinancialFilings](../.claude/plans/FinancialFilings/README.md) | Evaluated on-demand source for readable filing tables and common cross-market filing labels; not integrated |

The three local folders are isolated research tools. FinancialFilings currently
has research notes only. None of these entries changes production code or writes
to the production database.

Last live check: 2026-07-19. The LSE catalog, Liquid social feed, and Hyperliquid
price endpoints all responded successfully.
