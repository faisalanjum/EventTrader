# 04 · Units

**What this is:** how a DriverUpdate's numbers get a **unit**. The per-X-in-the-name rules live in the naming section (NAME-12/13); this section is the **unit resolution** mechanics — the enum, the shared resolver, the hints, and validation.

> Every rule is **LOCKED** unless marked **⏳ OPEN** / **⏳ BUILD-PENDING**. Source = `Consolidation/UnitExtraction.md`.
> **Still open here:** UNIT-12 (add `percent_qoq`?) · UNIT-14 (wiring not done). Both tracked in `90_OpenItems.md`.

---

## A. The enum + the resolver

#### UNIT-01 — The 9-unit enum  `[LOCKED]`
- **Plain:** There are exactly 9 allowed final units. Every resolved unit must be one of them.
- **Rule:** The unit enum, borrowed **verbatim** from Guidance's `canonical_unit` (so the Guidance link + dedup line up with no translation table): `usd · m_usd · percent · percent_yoy · percent_points · basis_points · count · x · unknown`.
- **Why:** One shared, fixed vocabulary means Driver and Guidance units compare directly.
- **Source:** UnitExtraction.md (enum) · DriverGraphSchema.md (unit enum)

#### UNIT-02 — Borrow the V2 shared resolver (not V1)  `[LOCKED]`
- **Plain:** Reuse Guidance's V2 unit resolver as one shared, pure module — both Guidance and DriverUpdate call it.
- **Rule:** Use the Guidance **V2**-style resolver (NOT V1 — V1 was too weak at 54%, couldn't read `$B` / `per share` / `2.5x`). Make it ONE shared **pure module** (testable without Neo4j / Redis / LLMs / graph writes). It's a "shared unit resolver," not "Guidance unit code." Possible API: `resolve_unit_value(label, value, unit_raw, unit_kind_hint, money_mode_hint, quote=None, xbrl_qname=None)`.
- **Why:** One resolver, one source of truth — the hand-copied unit list can't rot, and both pipelines behave identically.
- **Source:** UnitExtraction.md (verdict + unification advice)

#### UNIT-03 — Producer proposes, code decides  `[LOCKED]`
- **Plain:** The producer sends the number and raw unit text exactly as written, plus hints. Code decides the final unit and scaling. The producer never converts.
- **Rule:** The producer extracts the number exactly as written + `unit_raw` (verbatim surface text, preserving denominator phrases like "cents per share") and **NEVER converts between units**. Code (the resolver) decides the final unit + all scaling.
- **Why:** Keeping conversion in code makes scaling deterministic and testable; the producer only reports what it saw.
- **Source:** UnitExtraction.md (keep-from-old · numeric value rules)

#### UNIT-04 — The two required hints  `[LOCKED]`
- **Plain:** The producer must send a "what kind of thing" hint, plus a money sub-hint when it's money.
- **Rule:** Every numeric item includes: `unit_kind_hint` (REQUIRED) ∈ {money, ratio, count, multiplier, unknown}; `money_mode_hint` (REQUIRED when `unit_kind_hint = money`) ∈ {aggregate, price_like, unknown} (null/omitted otherwise); `unit_raw` (REQUIRED, verbatim).
- **Why:** The coarse kind hint is what lifts the resolver from ~70% to 100% — it disambiguates cases the surface text alone can't.
- **Source:** UnitExtraction.md (V2 unit hint fields)

## B. How it's applied

#### UNIT-05 — Resolve level_* and change_* separately  `[LOCKED]`
- **Plain:** A fact can have two different units — one for the level, one for the change. Resolve them separately.
- **Rule:** Call the resolver SEPARATELY for `level_*` and `change_*`. Example: margin "rose 60 bps to 17.6%" → `level_unit = percent`, `change_unit = basis_points`.
- **Why:** The level and the change often carry different units; one resolution can't capture both.
- **Source:** UnitExtraction.md (DriverUpdate side)

#### UNIT-06 — Validate the final unit AND the scaled value  `[LOCKED]`
- **Plain:** Check the final resolved unit is one of the 9, and check the scaled number — not just the unit string.
- **Rule:** Validate the FINAL resolved units only (`level_unit`, `change_unit`) AND assert the scaled VALUE, not just the unit string. Reject any final unit outside the 9 (`usd_per_share`, `shares`, `dollars_per_store`, `bps_yoy` = a resolver/prompt failure).
- **Why:** A right unit string with a wrong scale is still wrong; an out-of-enum unit means something upstream failed.
- **Source:** UnitExtraction.md (validate final resolved units)

#### UNIT-07 — No unit fields on the Driver class  `[LOCKED]`
- **Plain:** Units live on the fact (DriverUpdate), never on the Driver.
- **Rule:** The Driver class has NO unit fields. Units are a per-fact, producer-time concern (on the DriverUpdate); `fact_type` is value-free.
- **Why:** The same driver can carry facts in different units over time; a unit on the class would be wrong.
- **Source:** UnitExtraction.md (Driver changes — catalog side)

#### UNIT-08 — No per-X unit (per-X lives in the name)  `[LOCKED]`
- **Plain:** There is no "per barrel" unit. The per-X sits in the driver name; the unit stays the base.
- **Rule:** There is no per-X unit. The per-X denominator lives in the driver name (NAME-13); the unit stays the base enum: `eps` / `dividend_per_share` / `sales_per_square_foot` / `oil_price_per_barrel` → `usd`; `diluted_share_count` → `count`.
- **Why:** Keeping per-X in the name (not the unit) is what lets the read-time key separate `oil_price_per_barrel` from `oil_price_per_tonne`.
- **Source:** UnitExtraction.md (Rule 4) · cross-ref NAME-13

#### UNIT-09 — No comparison_unit  `[LOCKED]`
- **Plain:** There's no separate unit for the comparison value — it shares the level's unit.
- **Rule:** There is no `comparison_unit` field. `comparison_low/high` share `level_unit`. If the source compares against a different-unit value, keep that detail in the `quote` — do not invent `comparison_unit` unless the schema later adds it.
- **Why:** Comparisons are almost always in the level's unit; a separate field would be dead weight.
- **Source:** UnitExtraction.md (comparison nuance)

#### UNIT-10 — No number → skip unit resolution  `[LOCKED]`
- **Plain:** A qualitative fact with no number skips the resolver; numeric fields stay null.
- **Rule:** For no-number DriverUpdates ("dividend suspended", "CEO resigned"), leave numeric fields null and skip unit resolution entirely.
- **Why:** There's nothing to resolve; forcing a unit would fabricate data.
- **Source:** UnitExtraction.md (no-number DriverUpdates)

#### UNIT-11 — Scaling guards  `[LOCKED]`
- **Plain:** Handle glued values ($1.5B → ×1000), reject cents-on-aggregate, keep `unit_raw` clean.
- **Rule:** The resolver applies scaling guards: a glued `$1.5B` / "billion" → ×1000 to `m_usd`; a cents value on aggregate money → error (cents guard); keep `unit_raw` clean (avoid glued `$1.5B`). Extract number + `unit_raw` exactly; the canonicalizer does all scaling.
- **Why:** These are the real failure modes the probe surfaced; guarding them keeps the scaled value correct.
- **Source:** UnitExtraction.md (keep-from-old · numeric value rules)

## C. Stability + evidence + status

#### UNIT-12 — Whether to add `percent_qoq`  `⏳ OPEN`
- **Plain:** The 9-unit enum has no "quarter-over-quarter percent". Whether to add one is left open.
- **Rule:** Keep the 9-unit enum stable. Do **NOT** add `percent_qoq` now. Revisit **only** if production evidence proves a new unit is required. *(Current lean: don't add.)*
- **Why:** Enum churn breaks the Guidance↔Driver alignment and evhash stability; add only on proven need.
- **Source:** UnitExtraction.md (decision) · also in `90_OpenItems.md`

#### UNIT-13 — Evidence  `[EVIDENCE]`
- **Plain:** The shared resolver was proven: 117/117 on the production path, 29/29 tests, naming 100%.
- **Rule:** Proven in scratch (2026-06-20): the production path (hints-on) = **117/117** units, 0 value failures, 0 lint failures (all 4 fact-types 100%); `test_unit_resolver.py` = **29/29 + 7 guard checks**; catalog naming (does the reader actually coin `oil_price_per_barrel`?) = **3 blind Opus runs, 33/33 each, no flicker**. `€M → unknown` is the only true enum gap (a safe under-merge).
- **Source:** UnitExtraction.md (post-rule re-run · next-steps status)

#### UNIT-14 — Status: proven, not yet wired  `⏳ BUILD-PENDING`
- **Plain:** The resolver design is locked and proven in scratch, but it isn't wired into the real producer yet.
- **Rule:** Steps 1–3 (resolver) + Step 4 (naming) are proven in scratch; Steps 5–7 are **NOT done**: wire the locked rules into the real reader/producer prompt; emit `unit_raw` / `unit_kind_hint` / `money_mode_hint`; call the resolver separately for `level_*` / `change_*`; block invalid output (missed per-X, invented per-X unit, invalid unit, unit fields on Driver); full real replay (0 critical failures); then move the resolver to a final shared location + add permanent validators. Wiring is deferred until real metric fact-types exist (guidance uses the resolver on only ~3% of records — per `GuidanceDriverConsolidation`).
- **Source:** UnitExtraction.md (next steps) · GuidanceDriverConsolidation.md (units) · also in `90_OpenItems.md`
