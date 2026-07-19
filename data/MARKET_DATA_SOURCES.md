# Market data sources

| Folder | Purpose |
|---|---|
| `lse_massive_replacement` | Tests whether LSE data can replace Massive calculations |
| `liquid_social_feed` | Live X and Truth Social research feed |
| `hyperliquid_24x7_prices` | Overnight and weekend market-price signal |

These folders are isolated research tools. They do not change production code or
write to the production database.

Last live check: 2026-07-19. The LSE catalog, Liquid social feed, and Hyperliquid
price endpoints all responded successfully.
