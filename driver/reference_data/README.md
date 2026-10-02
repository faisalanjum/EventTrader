# Reference data: official unit and currency lists

Saved 2026-10-02 so the unit rules (3.28, 3.54, 9.1 in [the rules](../../.claude/plans/Drivers/DriversFinal/DRIVER_RULES_Categorized.md)) always point to the exact lists that were reviewed. Don't edit these files. To adopt a newer list, add it as a new dated file, review it, and update this table.

| File | Source | Version | Contents | SHA-256 |
|---|---|---|---|---|
| `utr-2024-10-22.xml` | XBRL Unit Type Registry, https://www.xbrl.org/utr/utr.xml | 1.0, lastUpdated 2024-10-22 | 324 entries: 191 currency, 8 "X per Y" templates, `pure`, `Rate`, `shares`, 122 concrete measures | `0236426fa29a1c1bca4b6088f65dc75d01df7c3fa716e5c5ae3f0702d0ba9002` |
| `iso4217-list-one-2026-09-17.xml` | ISO 4217 current currencies and funds (SIX), https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml | published 2026-09-17 | 178 distinct codes | `33139b438657d1cee116ba737807ea71d19d6de4b90f799a09c56f0cc6a1b0ff` |
| `iso4217-list-three-2026-01-01.xml` | ISO 4217 historical currencies and funds (SIX), https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-three.xml | published 2026-01-01 | 137 distinct codes | `98fde2423cdb916dd59dcf5fe96222edad8fa198d865c1c83dbc464b9cc52387` |

The registry's 122 concrete measures are the extra physical and time units allowed by 3.54; its currency entries, templates, `pure`, `Rate` and `shares` are not choices. Money uses the ISO codes under 9.1. The reasoning is in [UNITS_PLAN_2026-10-02.md](../../.claude/plans/Drivers/DriversFinal/Archive/UNITS_PLAN_2026-10-02.md) (archived).
