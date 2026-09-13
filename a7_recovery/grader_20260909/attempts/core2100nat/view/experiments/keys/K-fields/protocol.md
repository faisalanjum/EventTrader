# K-fields protocol — the hidden EXP-5 answer key (kf_)

> **Status: DRAFTING (v2; updated 2026-07-25 under Work Order v2.0; the final WorkOrder sha is recorded in the authoritative status-board pin list, not inlined here).**
> Authority: FableExperimentWorkOrder §3 "K-fields" (schema + the du_worthy gate,
> owner-decided 2026-07-08 closing O3) + the v1.9 drafting-route decision.
> The key is IMMUTABLE after lock; the producer arms NEVER see it.

## 1. Instrument

~150 `du_worthy:true` gold facts over the 36 O2-signed events
(`fixtures/FA_selection.json` sha `8e9556f981189a41c7764b72f7cb8ab037fa0897630c31cdfa6a990629de48db`;
packets `fixtures/events/<safe_source_id>.json`, manifest
`FIXTURES_MANIFEST.json` sha `f39f2d4b47791c3f10bb4ce090b44eed6463c5fe4cd84aaf5e1dd0a56568e073`).

Record schema (Work Order §3, verbatim shape):

```jsonc
{"key_id": "kf_0001", "source_id": "...", "ticker": "...",
 "fact_type": "metric|guidance|surprise|action_event",
 "du_worthy": true,          // false = OPTIONAL near-miss exemplar; excluded from
                             // EVERY recall denominator (adjudication context +
                             // precision spot-checks only)
 "gold_item": { /* the FULL FACT-17b item, transients included — the 37
                  model-owned fields (PreparedFact minus member_refs +
                  xbrl_concept_raw); EVERY gold_item carries ALL 37 keys
                  EXPLICITLY (null where genuinely absent) — never a subset */ },
 "gold_extra": {"expectation_comparison_present": false},   // ISS-16 ground truth
 "trap_class": "shape_point|OD-12_loss_floor|OD-11_sequential|OD-9_spans|OD-13_favorability|ISS-16_routing|slice_menu|unknown_axis|OD-17_portion|T1-05_menu_ambiguous|null"}
```

**Producer output contract (what EXP-5 scores — distinct from this gold key).** The producer emits `{"facts":[<fact_type + the 37 fields above>], "abstentions":[{"quote","reason","occurrence"}]}`. `abstentions[]` is producer-only (never in the gold key): each row = a verbatim quote + short reason for a REAL candidate the producer cannot lawfully resolve. `occurrence` is CONDITIONAL — a GLOBAL 1-based count — scan the event's `text_parts` in canonical order and count each verbatim match left-to-right within a part, continuing the SAME count across parts (never reset at a part boundary); a match never spans two parts, REQUIRED only when the quote repeats, kept OUTSIDE the 37 PreparedFact fields (abstentions are never written). Scoring: a gold-linked abstention (1:1 to an otherwise-unmatched gold fact) is a park + recall miss; a non-fact abstention is diagnostic-only.

## 2. The gate (owner 2026-07-08, closes O3 — binding verbatim)

`du_worthy` ≡ the locked DU-03 write gate ("DriverUpdate-worthy fact"),
significance-agnostic. A gold fact exists iff the source STATES a real,
non-boilerplate fact about a driver in one of the four lanes. DU-03 verbatim:
*"does this event carry a real fact about the driver (state/change/surprise/
guidance/action)? A bare mention → NO DriverUpdate. Generic risk boilerplate
('litigation could harm us', 'weather may affect results') → dropped."*

Explicitly NOT part of the gate: recurrence · "must be a change" · materiality/
significance · realized-price-move tests (read-time filters, never write gates).
Numberless/qualitative facts COUNT (DU-05). The one locked lane-level boundary:
DU-11 `at_risk` STRICT (specific, current, source-flagged adverse threat = fact;
generic = drop). Fuzzy-middle cases on other lanes have NO locked boundary —
file `ra_*` exhibits, never invent one. Stock-move attribution (`EXPLAINED_BY`)
NEVER enters this gate. Two axes never blurred: the GATE decides
fact-vs-no-fact; `trap_class` grades how an admitted fact is ENCODED.

An expectation comparison yields TWO gold facts (ISS-16/OD-21): reported ACTUAL
→ metric + surprise (`actual_vs_*`); forward GUIDE-vs-Street → guidance +
surprise (`guidance_vs_consensus`); a grounded NUMBERLESS surprise still gets
its numberless home sibling (`driver_state=unknown` + quote); an UNGROUNDED
"results beat" (no identifiable metric) is parked.

## 3. Quotas + the two drafting hooks

- ~150 `du_worthy:true` target. Trap quotas: every §12.3 planted class +
  OD-9/11/12/13/14 + ISS-16 represented **≥5× each**.
- **Hook (a):** count sequential-basis facts as drafting proceeds — if the total
  lands **<5**, fire the pinned OD-11 contingency (ULTA 10-Q
  `0001104659-25-118458` → LUV 10-Q `0000092380-26-000047`) BEFORE locking,
  recording the trigger evidence in `review_checks.od11_sequential.evidence`.
- **Hook (b):** every surprise-lane gold fact must cite a STATED expectation
  comparison from the text — never a market-implied one.

## 4. Independence (leakage law)

Gold is labeled from the event TEXT ONLY. Drafters and adjudicators must NOT
consult the filing's XBRL facts/values while labeling (EXP-6's text-vs-XBRL
twin comparison would otherwise be circular). **Fable drafting-route detail
(2026-07-24):** drafters receive EXACTLY the producer packet — event
`text_parts` + `{ticker, fye_month}` + the PIT slice menu + the verbatim ITEM
CONTRACT — because gold `slice[]` picks are graded against that same menu; the
ban covers the CURRENT filing's XBRL fact values/periods, which never enter any
prompt. The producer is never shown gold labels, realized returns, or any
> event_time context.

## 5. Drafting route (v1.9, Fable-decided per the v1.8 scope rule)

DUAL-TIER UNION: `claude-sonnet-5` AND `claude-opus-4-8` each label all 36
events independently at **effort=high**, blind to each other (72 calls,
workflow `agent()` only, billing guard, booked to WP-KEYS in BUDGET.json with
exact ids + effort). Union key = (source_id, adjudicated same-fact grouping).
Support briefs (non-graded Sonnet agents, K-reader precedent) may organize the
union; they rule NOTHING. **Fable adjudicates EVERY record** (prune / keep /
rewrite / add; du_worthy:false exemplars optional), then `key_lint` →
`sha_lock` → `K-fields.lock.json` carrying protocol+sample+key shas,
drafted_by lineage (both exact model ids + effort), and the Fable signature.
No tested producer tier authors its own gold: Haiku never drafts; Sonnet drafts
are one voice of a union that Fable fully re-judges.

## 6. Lint (key_lint kf_ checks)

Schema-exact fields · quotes verbatim in the pinned event's text under strict
UTF-8 AND a UNIQUE span (extend if the phrase repeats; else abstain — never
default to first occurrence) · fact_type enum · gold_item keys == EXACTLY the 37
model-owned fields (all 37 present on every record, null-filled; a missing OR
extra key = lint error) ·
du_worthy
booleans · trap-quota counts reported · unique key_ids · per-event coverage
table (an event MAY lawfully carry zero gold facts — recorded, not erroneous).
