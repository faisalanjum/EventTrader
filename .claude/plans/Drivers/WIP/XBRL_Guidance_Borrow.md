# What the Driver catalog borrows from Guidance Extraction (XBRL linking + node identity)

**Date:** 2026-06-11 · 3-mapper read-only study `wf_0deeea7d-06e` (code + prompt-packets + live Neo4j verified; zero changes made). Companion to the future linking-pass build (post-Fable, post-GO).

## A. How guidance links XBRL concepts + members (the recipe to copy)

1. **Inline, two layers**: the LLM *proposes* a qname during extraction; a deterministic CLI *repairs/overrides* it at write time. Link failures never block the core write; edges self-heal on re-runs.
2. **The LLM never sees a taxonomy** — it sees a company-scoped MENU: numeric facts from the company's own recent 10-K/10-Qs (consolidated contexts), grouped (qname, label, usage), usage-sorted (`concept_cache_{ticker}.json`). Pattern-map first; cache fallback only when exactly one plausible candidate.
3. **Members: the LLM is forbidden entirely** ("CLI is the sole authority") — agents emit `member_u_ids: []`; the CLI matches normalized segment strings against a CIK-scoped member map (+ per-ticker alias files).
4. **Five anti-hallucination layers**: deterministic resolver override (65-entry ordered registry per label_slug; force-null lists; ambiguity → fail-closed None) · cache-membership check (qname must be one the company ACTUALLY reports) · MATCH-not-MERGE at edge time (fake qname = no edge, never a new node) · agent member claims discarded outright · unit-consistency write guards (per-share concept with m_usd ⇒ whole item rejected).
5. **Storage**: edge `MAPS_TO_CONCEPT` (0..1) + stable `xbrl_qname` property (cross-taxonomy fallback) + `concept_family_qname` rollup anchor for derived metrics (19-entry map — e.g. fcf → NetCashProvidedByOperatingActivities). Members 0..N via one UNWIND. Provenance on the node, not the edge. Coverage achieved: ~49% of GuidanceUpdates.

## B. How the same guidance node is updated over time (the DriverUpdate recipe)

1. **Two-tier identity**: durable anchor (`guidance:{label_slug}`, GLOBAL, value-free) ← per-event observation nodes whose key = `gu:{source_id}:{label_slug}:{period}:{basis}:{segment}` — built ONLY from normalized semantic dimensions, never values.
2. **The LLM never decides update-vs-new.** It names the dimensions; mandatory code builds the composite key; `MERGE` + DB uniqueness constraints decide create-vs-update mechanically. The whole dedup problem concentrates into one spot: the label.
3. **Retrieval-seeded reuse**: existing labels for the company are injected into every extraction prompt ("reuse canonical names"). Proven at scale: ALV's adjusted-operating-margin guidance = ONE anchor holding 17 updates over 22 months across 5 source types (12.0% → 10.5% → 9.5–10.0%), identity held purely by recomputed keys.
4. **Value hash (`evhash16`) is a property, never part of the key** — change detection without node-forking. Re-runs of the same document overwrite in place; new documents mint new observation nodes — the revision history IS the node set, ordered by writer-authoritative `given_date`.
5. **Shared dimension nodes reuse first-write-wins** (period lookup by ref-count before recomputing) — prevents timeline splits from slightly-different date math.
6. **U54 = READ-time collapse**, write stays lossless: canonical signatures equate extraction artifacts (point vs degenerate range; normalized qualitative text); deterministic source-priority merge (8-K > transcript > 10-Q > 10-K > news).
7. **⚠️ The proven residual: prompt-level reuse LEAKS.** CMC carries BOTH `guidance:capex` and `guidance:capital_expenditures` (cypher-verified); no merge tool exists. Lesson: advisory reuse alone is insufficient — the driver pipeline's enforced G2 reuse/admit gate + Refute + repair pass is exactly the missing enforcement layer, validated by guidance's failure mode.

## C. Driver-side facts the borrow must serve (measured)

- Readers ALREADY hint: CAKE run → 396/2,246 candidates (17.6%) carry `xbrl_or_null`, **100% well-formed us-gaap qnames, 43/44 exist as Concept nodes** — but they are NOT company-verified (readers used `us-gaap:Revenues` 23×; CAKE reports zero facts on it). Catalog: 78/573 records carry xbrl_concept; member/guidance_ref = 0 everywhere.
- Current plumbing: build_seed = first-hint-wins (silent conflicts); fold merge = identical-or-null with conflict sidecar at part-B but **part-A discards conflict rows** (asymmetry); **the validator never checks optional_links** (1 hallucinated qname shipped through VALIDATION PASSED); D5/fold splits null all links.
- §13 consumption NEVER uses optional_links — linking is an anchoring/measurement layer, not a dependency of the live reuse loop.
- The guidance method needs **no source re-reads**: label + per-company concept menu + registry. Driver linking needs only catalog records + one Neo4j inventory per company. (Run dirs keep chunks/sources on disk anyway if ever needed.)
- Open design items for the linking-pass spec: per-company resolution vs ONE optional_links dict on multi-company records (concept_family-style anchor is the guidance answer); guidance_ref format undefined (Guidance anchor id vs GuidanceUpdate id); cache scope (10-K/10-Q only — restaurant drivers coined largely from 8-Ks); validator extension for link checks; first-wins → resolver-override layer.

## C2. Deterministic test battery (2026-06-11 — run live against real code + graph; zero LLM, zero writes)

| Test | Result |
|---|---|
| T1 build CAKE's real concept menu + member map with the actual warmup queries | ✅ 272 concepts (usage-sorted), 353 members — machinery runs as-is for driver companies |
| T2 guidance-style membership check over ALL 44 reader-hinted qnames | ✅ quantified: **25 qnames (293 instances) survive; 19 qnames (103 instances = 26%) get nulled** — concepts CAKE never reports, incl. `us-gaap:Revenues` (CAKE tags none) and the one hallucinated qname. Exactly what the resolver layer fixes |
| T3 guidance's 65-entry registry vs the 573 driver names | ✅ only 11 direct hits — confirms drivers need the scalable menu+membership pattern, not the hand-registry (which is guidance-metric-specific) |
| T4 member resolution for brand drivers | ✅ **works TODAY with zero new machinery**: `north_italia` → `cake:NorthItaliaMember`, `flower_child` → `cake:FlowerChildMember`, `the cheesecake factory` → `TheCheesecakeFactoryMember` via the existing normalizer; non-segment words correctly NO MATCH (fail-closed) |
| T5 identity determinism | ✅ evhash canonicalization (1.5/2.50 == 1.50/2.5), slug determinism ('FCF (non-GAAP)' == 'fcf  non gaap' → `fcf_non_gaap`), member normalizer idempotent |
| T6 edge integrity | ✅ 0 qnames without edges; 460 member edges; **⚠️ found 2 property/edge mismatches** (Five Below `store_count`): property holds the LATEST resolution (`us-gaap:NumberOfStores`) but an older edge to the extension concept (`five:NumberOfCompanyOperatedStores`) was never deleted — edges self-heal additively, never cleaned on re-resolution. **Inherit rule for drivers: property is authoritative; on re-resolution, delete-or-reconcile stale edges; validator checks edge==property** |

## D. Sequencing verdict (owner question): AFTER Fable, decisively

1. Linking is label+menu resolution — **Opus/code work, zero Fable dependency** (guidance never re-reads source text).
2. The only Fable-time ingredient (the per-candidate qname hint) is **already captured by the readers** — no reader change needed or allowed (any reader-prompt change = gated A/B = burning irreplaceable Fable days on the recall-critical lane).
3. Nothing downstream blocks on links (§13 never references them).
⇒ Front-load Fable readers untouched; build the linking pass later as a separate deterministic-resolver + validator stage on the finished catalogs, borrowing recipe A verbatim and identity recipe B for DriverUpdate.

## E. Exact code pointers for the future linking-pass build (verified file:line)

| Piece | Where |
|---|---|
| Concept menu query (2A: company-scoped numeric facts, consolidated, usage-sorted) | `scripts/earnings/builders/warmup_cache.py` `QUERY_2A` (~line 103) |
| Member map query (CIK-scoped, authoritative) | same file, `QUERY_MEMBER_MAP` |
| Deterministic concept resolver (registry, force-null lists, membership check, fail-closed ambiguity) | `.claude/skills/earnings-orchestrator/scripts/concept_resolver.py` (`CONCEPT_CANDIDATES` :23-254, `resolve`+`apply_concept_resolution` :294-367, `CONCEPT_FAMILY` :375-402) |
| Member resolution (clear agent claims → exact normalized-label match + alias files) | `guidance_write_cli.py:393-423`; normalizer `guidance_ids.py:553` (`normalize_for_member_match`) |
| Identity: slug / slot-ID / evhash | `guidance_ids.py` (`slug` :21-26, slot ID :962-966, `compute_evhash16(low, mid, high, unit, qualitative, conditions)` :583-602) |
| Writer: anchor MERGE + alias accumulation + edge queries (MATCH-only) + Guards A–H | `guidance_writer.py:59-158, 199-296, 423-451` |
| First-write-wins period reuse (ref-count lookup) | `guidance_write_cli.py:115-152, 203-292` |
| U54 read-time collapse (canonical signatures + source priority 8-K>transcript>10-Q>10-K>news) | `scripts/earnings/builders/guidance_history.py:85-132, 367-464` |
| Retrieval queries that seed reuse (7A existing labels; 7D this-source re-run; 7E/7F enrichment) | `.claude/skills/extract/types/guidance/guidance-queries.md:13-100` |

## F. Open design questions for the linking-pass / DriverUpdate spec (from the study — owner decides at build time)

1. **Per-company links vs ONE optional_links dict on multi-company records** — guidance sidesteps this (each GuidanceUpdate is single-company); drivers need per-evidence/per-company links or a `concept_family`-style cluster anchor.
2. **`guidance_ref` format is undefined in every plan file** — Guidance anchor id vs GuidanceUpdate id vs shared label_slug key.
3. **Validator extension** — optional_links is currently never checked (a hallucinated qname shipped through VALIDATION PASSED); add Concept-exists + company-reported + edge==property checks.
4. **Concept-cache scope** — menu = 10-K/10-Q numeric consolidated facts only; restaurant drivers were coined largely from 8-K press releases → may need scope widening or a live fallback before driver coverage is useful (guidance hit 49%).
5. **Prior VALUES in the update prompt?** — guidance shows the LLM prior LABELS only; for DriverUpdate, does revised-vs-reaffirmed semantics need the latest prior state shown, or is timestamp ordering enough?
6. **Anchor-merge migration tool from day one** — guidance has no tool to merge synonym anchors (the CMC capex leak persists); DriverUpdate should budget one.
7. **Ref-count entrenchment** — first-write-wins node reuse means an early wrong node can attract all future references; needs an audit hook.
8. **Part-A fold discards optional_links conflict rows** (`fold_catalogs.py:195` drops what part-B records) — mirror part-B's sidecar when the linking pass lands.

