# K-fields BLIND DRAFTING instructions (one drafter, one event)

You are ONE independent drafter of a HIDDEN gold answer key. Another model
drafts the same event blind to you; a final adjudicator rules every record.
Work from the EVENT TEXT ONLY — no outside knowledge, no XBRL data, nothing
after the event date. Your draft is judged for faithfulness, not volume.

**EXACT-INPUT RULE (machine-audited):** you may read ONLY the three files
named in your prompt (this wrapper, the item contract, your one event input).
The contract defines every value you need — including the per-slot hint enums
and the per-lane matrix. Do NOT open, search, list, or grep any other file or
directory; a draft whose worker accessed anything else is DISQUALIFIED. If
something still seems undefined, choose null and explain in `ambiguity_note` —
never go looking.

## The gate (DU-03, verbatim — decides fact vs no-fact)

A gold fact exists iff the source STATES a real, non-boilerplate fact about a
driver in one of the four lanes (metric · guidance · surprise · action_event):
*"does this event carry a real fact about the driver (state/change/surprise/
guidance/action)? A bare mention → NO DriverUpdate. Generic risk boilerplate
('litigation could harm us', 'weather may affect results') → dropped."*
No materiality/significance bar; numberless/qualitative facts COUNT. Threats:
`at_risk` is STRICT — a specific, current, source-flagged adverse threat is a
fact; generic threat language is dropped. A stated expectation comparison
yields TWO facts (the actual on its home lane + a surprise; a forward
guide-vs-Street = guidance + surprise). Actual-vs-prior-period is a metric
CHANGE, never a surprise.

## How to fill each fact

Apply the attached ITEM CONTRACT (verbatim law) for every field rule: value
shapes (a point fills BOTH bands; low-only=floor; high-only=ceiling; signed
value-space), OD-11 unit basis, OD-9 measurement spans (copy exact source
qualifier spans), OD-13 favorability (doubt → unknown), OD-14 (bare guidance
movement → driver_state=unknown), OD-21 (surprise_basis_hint on surprise items
only), and the FS-15 slice ladder against the PROVIDED menu (menu match →
menu token; two-kind collision → unknown:<value>; prose-only clear kind →
coin kind:value; else unknown:<value> — never guess a kind).

## Output — STRICT

Return ONLY JSON: {"source_id": "...", "facts": [...]} where each fact is:

```jsonc
{"lane": "metric|guidance|surprise|action_event",
 "du_worthy": true,
 "gold_item": { /* ALL 34 contract fields, EVERY key present, null where
                  genuinely absent — never omit a key, never add one */ },
 "gold_extra": {"expectation_comparison_present": true|false},
 "quote": "<verbatim substring of the event text, 60-200 chars>",
 "ambiguity_note": null | "<why this case is fuzzy — the adjudicator rules>"}
```

- `quote` must be copied byte-true from the event text (it is machine-checked).
- Values: exact printed numbers (post-scale per the stated unit words); dates
  ISO. Do not compute anything the text does not state.
- If a lane boundary is genuinely unclear, still emit your best single lane and
  say why in `ambiguity_note` — never emit duplicates across lanes except the
  lawful expectation-comparison twins.
- An event may lawfully contain ZERO facts → {"source_id": "...", "facts": []}.
