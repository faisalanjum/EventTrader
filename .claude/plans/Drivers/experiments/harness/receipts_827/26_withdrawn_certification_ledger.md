# #827 STAGE 3 — WITHDRAWN CERTIFICATION LEDGER

Reviewer ruling SEQ 140 (2026-08-02): option A — the 150-case gate certifies a law
this round WITHDREW. Its request shape carries a prefixed concept qname and an opaque
unitRef and no namespace, so it cannot state expanded identity and cannot authorize a
fact. Pinned verdicts describing that law are not evidence about the product any more.

THIS IS AN EXPLAINED REMOVAL, not a loss. Every retired artifact is identified below by
the sha256 of its exact bytes at removal, so the diff can be audited rather than trusted.

## Artifacts retired
- `scripts/driver_seed/relocate_probe/test_xbrl_gate.py`
  - sha256 abe82f030bb18f3809cb670fa925af237dd0c583806564769db13b6f0b874011
  - HEAD blob adf7381d0e2dfcd0017cf8387c0ee114c180618d
- `scripts/driver_seed/relocate_probe/xbrl_gate_expected.json`
  - sha256 d7d2f06849371a38e05d5ff781deb790c7b5250f3bae7a1c8ec85373607b2eec
  - HEAD blob cb9f694b78ed24faf88300934c4b5c6fb2e9e42c
- `scripts/driver_seed/relocate_probe/route_a_e2e_150.py`
  - sha256 d73c3f885f75aaf8f1a47ce47374f8f209372717ec293af9d632122ad7e48027
  - HEAD blob e6a625c7f241db71515524c8562ec26303c73159
- `scripts/driver_seed/relocate_probe/route_a_e2e_150_result.json`
  - sha256 d0efd32b480e3966fec555933969b6b3a6424c034e86fba9f11d202181727b37
  - HEAD blob 99f3a3b90e3dc45221bb3c323c5f7540a60f8897

## Why each
- `test_xbrl_gate.py` — the certification itself. Calls `match_facts_explain` with an
  exact `unit_ref` (it already refused the substring heuristic, correctly), but its
  concept match was by PREFIX, which is the part no repair reaches from this request.
- `xbrl_gate_expected.json` — its 150 pinned verdicts. Sole code consumer was the gate;
  the only other reader is the reporter below. Independently confirmed by grep.
- `route_a_e2e_150.py` — reads the same fixture and reports `'attempted': 0`, every case
  deferred to a Core phase that has not happened. No independent contract to preserve.
- `route_a_e2e_150_result.json` — that reporter's generated output.

## Test identities retired (2)
- test_xbrl_gate.py::test_fractional_decimal_exactness_synthetic
- test_xbrl_gate.py::test_150_case_gate_exact_rows_target_units

## What replaces them
Nothing 150-shaped, by ruling. A small public-door set proves the route now fails closed
with `insufficient_semantic_identity`, that each request-shape error stays isolated, and
that the active `locate_by_value` path is unchanged. Route A — which holds the filing and
therefore the namespaces — carries the identity proofs in
`driver/relocation/test_route_a_unit_identity.py`.

---

# COMPLETE TEST-IDENTITY ACCOUNTING (reviewer SEQ 143 item 7)

Re-derived by AST from `HEAD` vs the working tree, not from memory. My first
version of this ledger accounted only for the two gate nodes; the reviewer's own
identity diff then found a test I had deleted by accident, which is exactly what
an incomplete ledger fails to catch.

    TOTAL test identities   before 90   after 81

## A. WITHDRAWN BEHAVIOUR — the law itself is gone (22)

These asserted that a route RETURNS A VALUE when a prefixed concept string
matches, or when an opaque `unitRef` contains `usd`/`dollar`/`share`. Neither
states identity. Deleted rather than re-pinned as abstentions.

`test_match_facts.py` (9)
  test_concept_identity_matrix · test_real_corpus_collision_names_case_exact
  test_wrong_axis_swapped_pairs_and_order · test_explain_reasons
  test_float_values_rejected_raw_strings_exact
  test_exact_unit_ref_is_authoritative_over_expected_unit
  test_nonmoney_needs_positive_evidence_opaque_abstains
  test_fact_side_malformed_periods_never_candidates
  test_malformed_stored_period_containers_abstain_never_crash

`test_match_facts.py` (1 SPLIT identity — reviewer SEQ 145, and the one this
ledger previously failed to name at all)
  test_unit_case_sensitivity_strip_only_nonblank_required

  It asserted SIX things under one name, and they do not share a fate. Listing
  it only as "withdrawn" would have overstated the loss; listing it as
  "preserved" would have hidden five real removals. So it is split here:

  WITHDRAWN (5) — every one authorises or refuses by comparing RAW `unitRef`
  text, which is storage spelling and states no identity:
    · `U_USD` vs `u_usd` treated as different units -> conflict abstention
    · a request unit had to match the stored id CASE-EXACTLY
    · ` U_USD ` stripped and still MATCHED `U_USD` — matching-side repair
    · `U_USD` vs `U_EUR` conflict abstention
    · a list-valued or blank FACT-side unit was never a candidate
  The corpus fact behind the case rule (7 PSEG filings carrying `usdPerMWh`
  and `usdPerMwh` as different units) is unaffected and unrefuted; what went is
  the claim that comparing those strings decides anything.

  PRESERVED (1) — the REQUEST-shape rule, and at former strength:
    · a `unit_ref` that is blank or padded is `bad_request_unit`
  It is now pinned by `test_a_malformed_UNIT_request_says_so` (` usd ` is an
  explicit row, so the padded case is still refused rather than repaired) with
  its MUST-ALLOW twin `test_an_EXACT_unit_ref_passes_validation_and_reaches_
  the_refusal`. Both are listed in section B.

`test_exactness.py` (9 `resolve()` value expectations)
  test_resolve_returns_exact_decimal_not_rounded
  test_resolve_instant_fact_via_gp_date_date
  test_resolve_rejects_mixed_convention_dates
  test_resolve_rejects_neighboring_period_end
  test_resolve_concept_local_name_exact_only
  test_resolve_rejects_wrong_prefix_when_stored_prefixed
  test_resolve_expected_unit_class · test_resolve_unit_conflict_abstains
  test_resolve_unit_filter_when_caller_supplies_it

`test_xbrl_gate.py` (2, with the file)
  test_150_case_gate_exact_rows_target_units
  test_fractional_decimal_exactness_synthetic

`test_exactness.py` (1, deleted for VACUITY not withdrawal)
  test_xbrl_lane_shares_the_complete_parse_law — its two `is None` halves became
  true for every input; the `is not None` half was the only discriminating part.
  The rule survives in `test_unparseable_or_blank_segment_fails_closed`, which
  drives it through the ACTIVE `L.tier1`.

## B. PRESERVED VALIDATION — same law, restored at former strength (5 new)

Request-shape validation is independently meaningful and survives the matcher.

  test_a_malformed_PAIRS_request_says_so — the FULL 11-row matrix from
      `test_request_pairs_validated_never_crash_never_collapse`, including both
      repeated-axis rows that must not collapse through `frozenset`
  test_a_LAWFUL_pairs_request_reaches_the_IDENTITY_refusal — MUST-ALLOW twin,
      incl. the JSON round-trip (tuples arrive as inner LISTS)
  test_a_malformed_UNIT_request_says_so — malformed shapes pinned separately
  test_an_EXACT_unit_ref_passes_validation_and_reaches_the_refusal
  test_the_shape_errors_are_CHECKED_BEFORE_the_identity_refusal

## C. PRESERVED ADAPTER BEHAVIOUR — the seed lane's own rules (3 new)

From `test_adapter_dimensioned_member_only_always_abstains`. These are the
ADAPTER's request rules, not matcher output, so they still discriminate.

  test_the_adapter_REFUSES_a_member_only_request_outright
  test_the_adapter_REJECTS_pairs_and_members_together  (incl. `[]` counting)
  test_a_fully_specified_adapter_request_reaches_the_refusal

## D. RESTORED ACTIVE COVERAGE — accidental loss, reviewer-caught (1)

  test_tier1_unit_class_guard — `L.tier1`, the ACTIVE value-known path, never a
  `resolve()` test. It sat inside a line range I replaced wholesale and went
  with it. Restored verbatim in purpose. THE CAUSE: I replaced a block by line
  numbers and described it by what I intended it to hold, not by what it held.

## E. DELIBERATE RENAME — behaviour changed, identity re-stated (1)

  test_value_unknown_resolves_the_value
    -> test_value_unknown_ABSTAINS_because_it_cannot_state_identity
  The dict SHAPE is unchanged (still a `value` key); the value is now None.

## F. NEW FAIL-CLOSED CONTRACT (6 new)

  test_a_WELL_FORMED_request_is_refused_with_ONE_truthful_reason
  test_the_value_only_form_agrees · test_the_seed_ADAPTER_inherits_the_refusal
  test_a_DECEPTIVE_unit_id_gets_no_authority  (5 deceptive ids)
  test_NO_concept_spelling_authorizes_ANYTHING (4 spellings, incl. exact match)
  test_the_xbrl_lane_delegate_abstains_whatever_it_is_asked

## G. IMPLEMENTATION DELETED WITH THE LAW

  locator._period_ok        zero callers after the matcher went
  locator._norm_unit        it STRIPPED and returned the result as valid —
                            request-side repair, the same class of error as the
                            spelling repairs this round removed
  locator._BAD_UNIT         sentinel for the above
  locator._valid_request_unit
                            a wrapper that briefly replaced them. It went too:
                            it carried the withdrawn matching law alongside the
                            surviving shape check, and a name that says
                            "valid request unit" invites the matching meaning
                            straight back in.

  The surviving rule is asked directly at the one call site —
  `unit_ref is not None and not _nb(unit_ref)` — against the EXISTING `_nb`
  ("nonblank UNPADDED string"). One owner, no wrapper, no normalisation, and
  `unit_ref=None` stays a lawful ask.
