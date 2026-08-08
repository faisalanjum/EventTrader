"""#827 STEP 4 — the mutation battery, each in an EXACT STAGED-TREE extract.

The live files are NEVER edited: each mutation is applied to a fresh extract of
the STAGED tree (`git write-tree` + `git archive`), and the extract is thrown
away afterwards. The COUNT is derived from the table below, never transcribed —
it said "eleven" long after there were nineteen. Every mutation must make ITS OWN NAMED DETECTOR fail — a failure
somewhere else is not proof, so the detector is run alone and its node id is
recorded with the result.

A CLEAN UNMUTATED CONTROL runs first: every detector must PASS on the
unmutated copy, or the whole run means nothing.

Explicit raises; no `assert` (python -O strips those). Read-only w.r.t. the
repository; no AI.

TWO EVIDENCE LANES, ONE OWNER:
  * ISOLATED (default) — the zero-credential battery. No graph, no network.
  * LIVE READ-ONLY (`--include-live`) — two mutations break a CYPHER predicate,
    so their only honest detector asks the real engine; a credential-free
    extract cannot run it, and a structural substitute would pin the guard's
    presence rather than its behaviour. This lane IS credentialed, reads only,
    runs one exact parameter node per mutation, and is bracketed by the graph's
    own committed-transaction counter, which must not move.

Run:  venv/bin/python receipts_827/step4_mutations.py                 # isolated
      venv/bin/python receipts_827/step4_mutations.py --include-live  # + live
Out:  receipts_827/10_step4_mutations.json
"""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
OUT = os.path.join(_HERE, "10_step4_mutations.json")

HARNESS_REL = os.path.join(".claude", "plans", "Drivers", "experiments",
                           "harness")
G = f"{HARNESS_REL}/test_g_suite.py"
R5 = "driver/relocation/test_bind_graph_fact.py"
RA = "driver/relocation/test_route_a.py"
RI = "driver/core/test_driver_ids.py"
RN = "driver/core/test_neo4j_adapter_readonly.py"
#: THE EXACT PARAMETER NODES, not the parametrized function. Naming the
#: function ran all fourteen cases, so a mutation was judged by a group rather
#: than by the one case that proves it — "run alone" means alone.
_GUARD = f"{RN}::test_the_production_cypher_guard_against_the_REAL_engine"
LIVE_ALLZERO = f"{_GUARD}[0000000000-False-all-zero non-registrant marker]"
LIVE_TOOSHORT = f"{_GUARD}[320193-False-the archive spelling, too short]"
#: What the intended assertion says when the guard is gone. `rc == 1` alone
#: would also count a connection outage or a collection error as a catch.
LIVE_INTENDED = "-> 1 row(s)"
#: The harness's own read-only transaction bracket (receipts_827/graph_census).
TX_STATEMENT = "SHOW DATABASE neo4j YIELD lastCommittedTxn, databaseID"

# (id, name, file, old, new, detector node id)
MUTATIONS = [
    (1, "direct scaleb outside its owner",
     "driver/core/fact_match.py",
     "def record_key(f):",
     "def _mutant_scaleb(x):\n    return x.scaleb(1)\n\n\ndef record_key(f):",
     "driver/core/test_round12_exact_scale.py::"
     "test_the_scaleb_scan_is_DERIVED_from_the_production_tree"),

    (2, "ASCII [0-9] changed back to \\d",
     "driver/relocation/inline_html.py",
     r"    r'[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?$|[0-9]+(?:\.[0-9]+)?$|\.[0-9]+$')",
     r"    r'\d{1,3}(?:,\d{3})*(?:\.\d+)?$|\d+(?:\.\d+)?$|\.\d+$')",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_printed_value_rejects_NON_ASCII_numerals"),

    (3, "strict dateUnion parser given a fromisoformat fallback",
     "driver/relocation/exact_numbers.py",
     '        raise ExactError(f"not a lawful xs:date or xs:dateTime: {raw!r}")',
     "        from datetime import date as _d\n"
     "        try:\n"
     "            _d.fromisoformat(text)\n"
     "            m_d, kind, tz_text = True, 'date', None\n"
     "        except ValueError:\n"
     '            raise ExactError(f"not a lawful dateUnion: {raw!r}")',
     "driver/core/test_round8_xbrl_binding.py::"
     "test_filing_boundary_REFUSES_every_malformed_form"),

    (4, "quote-occurrence check bypassed",
     "driver/core/prepared_fact_v2.py",
     "def verify_occurrence(part_text, quote, occurrence_in_part):",
     "def verify_occurrence(part_text, quote, occurrence_in_part):\n"
     "    return None",
     "driver/core/test_round13_quote_occurrence.py::"
     "test_824_a_FABRICATED_quote_is_refused_and_costs_ZERO_io"),

    (5, "source-evidence comparison removed",
     "driver/core/xbrl_attach.py",
     '    if canonical["representation_sha256"] != evidence["representation_sha256"] \\\n'
     '            or tuple(canonical["quote_span"]) != evidence["quote_span"] \\\n'
     '            or canon_label != evidence["raw_label_span"]:',
     "    if False:",
     "driver/core/test_round14_evidence_matrix.py::"
     "test_matrix_e_a_quote_span_shifted_by_one_either_way_is_refused"),

    (6, "member-check logs discarded",
     "driver/core/slice_menu.py",
     "def check_member_refs(refs, fact_tokens, menu_tokens, matched_dims):",
     "def check_member_refs(refs, fact_tokens, menu_tokens, matched_dims):\n"
     "    return ([], [], [])",
     "driver/core/test_driver_write_cli.py::"
     "test_member_ref_supporting_no_fact_slice_parks_invalid"),

    (7, "the PRIVATE ITEM BINDER imported/called by the staged adapter",
     "driver/core/prepared_fact_v2.py",
     "    from driver.core.slot_convert import SlotConversionError",
     "    from driver.core.slot_convert import SlotConversionError\n"
     "    from driver.core.xbrl_attach import _verify_and_attach  # MUTANT",
     f"{G}::test_the_v2_modules_are_a_STAGED_read_only_adapter"),

    (8, "a checked-row field dropped from the row shape",
     "driver/core/xbrl_attach.py",
     '_ROW_FIELDS = _REQUIRED_ROW_KEYS + _ROW_SHAPE_KEYS',
     '_ROW_FIELDS = _REQUIRED_ROW_KEYS  # MUTANT: shape keys dropped',
     "driver/core/test_round11_outcomes.py::"
     "test_the_checked_row_carries_ONLY_the_checked_fields"),

    (9, "one deep freeze removed",
     "driver/core/xbrl_attach.py",
     "            member_menu=_deep_freeze({\"folds\": dict(member_folds),",
     "            member_menu=({\"folds\": dict(member_folds),",
     "driver/core/test_round15_audit_evidence.py::"
     "test_825p2_an_EMPTY_event_returns_the_SAME_RESULT_RECORD"),

    (10, "the G registry changed without regenerating its artifact",
     G,
     '    "G20": ("code",',
     '    "G20": ("partial",',
     f"{G}::test_the_ledger_renderer_is_REPEATABLE_and_matches_disk"),

    (11, "a status count transcribed into the package",
     f"{HARNESS_REL}/exp5_rev4_package.md",
     "THE LEDGER IS DERIVED, NEVER TRANSCRIBED",
     "THE LEDGER IS DERIVED, NEVER TRANSCRIBED (code 20)",
     f"{G}::test_the_g_ledger_is_regenerated_not_transcribed"),

    # ---- #827 ROUND 2: every check REPAIRED this round gets its own mutation,
    # because the round's whole finding was that checks were passing while the
    # protection they claimed was broken. A repair with no mutation behind it
    # is exactly the thing being corrected.

    # 12 and 13 swap the CAUGHT exception rather than deleting the `try`, so
    # the mutant stays syntactically valid. A first version wrote `if True:`
    # above a dangling `except`, which is a SyntaxError — the module then failed
    # to import and pytest exited 4. THAT IS NOT A CAUGHT MUTATION: a mutant
    # that cannot run proves nothing about the detector, which is why `caught`
    # demands exit code 1 exactly.
    (12, "the calendar-edge guard removed from stored_period_end",
     "driver/relocation/exact_numbers.py",
     "    except OverflowError:\n"
     "        # The day after `9999-12-31` is off the representable calendar.",
     "    except ZeroDivisionError:\n"
     "        # The day after `9999-12-31` is off the representable calendar.",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_stored_period_end_REFUSES_the_calendar_edge_as_an_ExactError"),

    (13, "the calendar-edge guard removed from filing_duration_ordered",
     "driver/relocation/exact_numbers.py",
     "    except OverflowError:\n"
     "        # A date-only end means the FOLLOWING midnight; at the calendar",
     "    except ZeroDivisionError:\n"
     "        # A date-only end means the FOLLOWING midnight; at the calendar",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_duration_ordering_at_the_CALENDAR_EDGE_is_indeterminate_not_a_crash"),

    (14, "the date census timezone grammar widened back",
     f"{HARNESS_REL}/receipts_827/scan_filing_dates.py",
     r'_TZ = r"(?:Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))"',
     r'_TZ = r"(?:Z|[+-][0-9]{2}:[0-9]{2})"',
     "driver/core/test_round8_xbrl_binding.py::"
     "test_the_date_CENSUS_and_the_PRODUCTION_parser_agree_on_legality"),

    (15, "the date census year grammar widened back",
     f"{HARNESS_REL}/receipts_827/scan_filing_dates.py",
     r'_YEAR = r"-?(?:[1-9][0-9]{3,}|0[0-9]{3})"',
     r'_YEAR = r"-?[0-9]{4,}"',
     "driver/core/test_round8_xbrl_binding.py::"
     "test_the_date_CENSUS_and_the_PRODUCTION_parser_agree_on_legality"),

    (16, "a public input field that nothing validates",
     "driver/core/prepared_fact_v2.py",
     "    calendar_override: bool = False",
     "    calendar_override: bool = False\n    label: str = ''",
     "driver/core/test_v2_attacks.py::"
     "test_827_every_public_INPUT_FIELD_is_REALLY_VALIDATED"),

    (17, "a SIXTH public decision word the channel cannot read",
     "driver/core/xbrl_attach.py",
     'PUBLIC_DECISIONS = ("written", "merged", "parked", "skipped", "rejected")',
     'PUBLIC_DECISIONS = ("written", "merged", "parked", "skipped", '
     '"rejected", "deferred")',
     "driver/core/test_v2_attacks.py::"
     "test_827_the_PUBLIC_DECISION_VOCABULARY_is_the_contract_s_five_words"),

    (18, "the locator's start compared as a RAW STRING again",
     "driver/relocation/locator.py",
     "                start = (None if shape[0] == 'instant'\n"
     "                         else XN.filing_boundary_graph_start(ds))",
     "                start = (None if shape[0] == 'instant' else ds)",
     "driver/relocation/test_route_a.py::"
     "test_827_the_LOCATOR_ITSELF_binds_a_lawful_midnight_dateTime_start"),

    # NO MUTATION FOR THE LOCATOR'S FORWARD-ORDER RULE, and the absence is the
    # finding. Removing that rule changes NO result: the graph-side period is
    # validated first (`period_key` refuses a backwards window outright), so a
    # backwards filing can never reach a matching shape. Measured: 23 calls
    # across the Route-A suite, ZERO rejections. Writing a mutation row whose
    # detector cannot honestly fail would be the very thing this round exists
    # to remove — it is reported as a simplification candidate instead.

    (19, "the money guard dropped from an AI-marked test",
     "drivers_harness/tests/test_synonym_judge_live.py",
     "    _require_llm_opt_in()\n    cache: dict = {}",
     "    cache: dict = {}",
     f"{G}::test_STRUCTURE_every_ACTING_lane_guards_FIRST_and_never_skips_at_"
     "collection"),

    # ---- #827 ROUND 4 — every rule repaired this round gets its own row. The
    # round's finding was that MALFORMED XBRL bound and that proof machinery
    # overstated itself, so each repair must be shown to bite when removed.

    # 20 AND 21 ARE RETIRED, not renumbered. They disabled the round-4 counting
    # rules, and round 5 replaced that code with direct-child parsing, so their
    # anchors no longer exist and they could only ever fail to apply. Rows 28-33
    # test the same requirements against the code that now carries them.
    #
    # THEIR LESSON IS KEPT, because it shaped the replacements: a first version
    # of 21 relaxed only `divide > 1` while two other clauses of the same `if`
    # still caught every case, so the mutant disabled nothing and "escaped"
    # without ever removing the protection. A mutation that does not remove the
    # guard tests nothing — which is why each new row relaxes a rule that stands
    # alone, and why anchor uniqueness is asserted before any of them run.

    (22, "the period-KIND comparison removed",
     "driver/relocation/inline_html.py",
     "    if (not doc_start) != (period_type == 'instant'):",
     "    if False:",
     "driver/relocation/test_bind_graph_fact.py::"
     "test_827_a_lawful_DURATION_document_never_binds_an_INSTANT_row"),

    (23, "the XSD mixed-timezone order widened back to always-indeterminate",
     "driver/relocation/exact_numbers.py",
     "    if a.has_timezone == b.has_timezone:",
     "    if a.has_timezone != b.has_timezone:\n        return None\n"
     "    if a.has_timezone == b.has_timezone:",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_duration_ordering_handles_aware_naive_and_parks_when_indeterminate"),



    (26, "the read gate plans WITHOUT the caller's parameters",
     f"{HARNESS_REL}/receipts_827/graph_census.py",
     'planned = session.run("EXPLAIN " + text, **params).consume().query_type',
     'planned = session.run("EXPLAIN " + text).consume().query_type',
     f"{G}::test_827_the_read_gate_plans_and_executes_the_SAME_parameters"),

    # ---- ROUND 5: XBRL 2.1 CONTAINMENT, and the truthfulness of the reason --
    # Every rule below let malformed markup ATTACH before it was written. Each
    # row disables exactly one of them; the suite must fail (rc 1) for each.

    # THE RULE IS REMOVED, NOT LOOSENED — and the first version of this row
    # loosened it and ESCAPED. With an identifier in both entities the stray
    # guard caught the fixture anyway, so the count rule was never the one
    # being tested. The detector now carries a case only this rule can refuse
    # (a second, EMPTY entity), and the mutation deletes the rule outright.
    (28, "a context may carry two entities, two periods or two scenarios",
     "driver/relocation/inline_html.py",
     "    if len(entities) != 1 or len(periods) != 1 or len(scenarios) > 1:\n"
     "        return None",
     "    if False:\n        return None",
     f"{R5}::test_827R5_a_MISPLACED_context_element_refuses_with_ITS_OWN_reason"),

    (29, "an entity may carry two identifiers or two segments",
     "driver/relocation/inline_html.py",
     "    if len(idents) != 1 or len(segments) > 1:",
     "    if len(idents) < 1 or len(segments) > 99:",
     f"{R5}::test_827R5_a_MISPLACED_context_element_refuses_with_ITS_OWN_reason"),

    (30, "any mixture of period forms accepted (incl. two `forever`)",
     "driver/relocation/inline_html.py",
     "    if tuple(map(len, (inst, start, end, ever))) not in (\n"
     "            (1, 0, 0, 0), (0, 1, 1, 0), (0, 0, 0, 1)):",
     "    if False:",
     f"{R5}::test_827R5_a_MISPLACED_context_element_refuses_with_ITS_OWN_reason"),

    # 32 IS RETIRED AS SUPERSEDED, with the evidence. It disabled the UNIT
    # containment count (`_all` vs `placed`), and it escaped once round 7 added
    # the direct-children rules. That is not a broken fixture — the check is
    # now UNREACHABLE. Probed on a throwaway copy with containment disabled,
    # 9 stray-element placements (a measure between numerator and denominator;
    # a numerator inside a numerator; a divide inside a numerator; a
    # denominator and a measure inside a measure; a numerator beside a plain
    # measure; a measure, a divide and a numerator under `<div>` wrappers at
    # two depths): ALL still refused, none by containment.
    #
    # The argument, not just the sample: a unit's direct children must be
    # measure or divide, a divide's must be numerator or denominator, each
    # side's must be measure, and every measure must be a LEAF. That closes
    # the subtree top to bottom, so no element of ours has anywhere left to
    # hide. THE CONTEXT VERSION IS DIFFERENT and keeps its mutation: a
    # `typedMember` carries arbitrary value markup (2,112 lawful descendants
    # in the cache), so a stray CAN hide inside one there.
    #
    # OWNER RULING 2026-08-01: delete the redundant unit count, keep the
    # load-bearing context one. Done — `_parse_unit` no longer builds `placed`
    # at all, so the row has nothing left to mutate. All 11 placements behave
    # identically after the deletion (9 refused, 2 lawful still allowed).

    (33, "a unit may mix plain measures with a divide, or declare nothing",
     "driver/relocation/inline_html.py",
     "    if len(divides) > 1 or (divides and plain) or not (divides or plain):",
     "    if False:",
     f"{R5}::test_827R5_a_MISPLACED_unit_element_refuses_with_ITS_OWN_reason"),

    # Same correction as 28: a second numerator carrying MEASURES is caught by
    # the stray-measure guard, so loosening this rule changed nothing and the
    # row escaped. An EMPTY second container isolates it.
    (34, "a divide may carry two numerators or two denominators",
     "driver/relocation/inline_html.py",
     "        if len(nums) != 1 or len(dens) != 1:\n            return None",
     "        if False:\n            return None",
     f"{R5}::test_827R5_a_MISPLACED_unit_element_refuses_with_ITS_OWN_reason"),

    (35, "a divide side may carry no measure at all",
     "driver/relocation/inline_html.py",
     "        if not n_meas or not d_meas:\n            return None",
     "        if False:\n            return None",
     f"{R5}::test_827R5_a_MISPLACED_unit_element_refuses_with_ITS_OWN_reason"),

    # THE REASON IS PART OF THE CONTRACT. These three restore the exact round-4
    # lie — malformed structure reported as a repeated id — and it must be seen.
    (36, "malformed context structure renamed back to a duplicate id",
     "driver/relocation/inline_html.py",
     "        contexts[cid] = 'malformed_context_structure' if parsed is None else parsed",
     "        contexts[cid] = 'duplicate_context_id' if parsed is None else parsed",
     "driver/relocation/test_bind_graph_fact.py::"
     "test_827R5_MALFORMED_structure_is_NEVER_called_a_duplicate_id"),

    (37, "malformed unit structure renamed back to a duplicate id",
     "driver/relocation/inline_html.py",
     "        units[uid] = 'malformed_unit_structure' if parsed is None else parsed",
     "        units[uid] = 'duplicate_unit_id' if parsed is None else parsed",
     "driver/relocation/test_bind_graph_fact.py::"
     "test_827R5_MALFORMED_structure_is_NEVER_called_a_duplicate_id"),

    (38, "the consumer stops carrying the context's own reason",
     "driver/relocation/inline_html.py",
     "    ctx = prepared['contexts'].get(ctx_ref)\n"
     "    if isinstance(ctx, str):\n"
     "        return None, ctx",
     "    ctx = prepared['contexts'].get(ctx_ref)\n"
     "    if isinstance(ctx, str):\n"
     "        return None, 'duplicate_context_id'",
     "driver/relocation/test_bind_graph_fact.py::"
     "test_827R5_MALFORMED_structure_is_NEVER_called_a_duplicate_id"),

    # ---- ROUND 5b: the crash, and the schema's declared order --------------
    (40, "dimension members sorted WITHOUT being validated (the TypeError)",
     "driver/relocation/inline_html.py",
     "        if not _qname_ok(axis, ns.declared) or not _qname_ok(value, "
     "ns.declared):\n            return None",
     "        if False:\n            return None",
     f"{R5}::test_827R5_a_NAMELESS_dimension_REFUSES_and_never_crashes"),

    (41, "the context/entity/period sequence checks removed",
     "driver/relocation/inline_html.py",
     "    if not (_ordered(context, ns.i('entity'), ns.i('period'), "
     "ns.i('scenario'))\n"
     "            and _ordered(entity, ns.i('identifier'), ns.i('segment'))\n"
     "            and _ordered(period, ns.i('startdate'), ns.i('enddate'))):\n"
     "        return None",
     "    if False:\n        return None",
     f"{R5}::test_827R5_a_context_out_of_SCHEMA_ORDER_refuses"),

    (42, "the divide numerator/denominator sequence check removed",
     "driver/relocation/inline_html.py",
     "        if not _ordered(divides[0], ns.i('unitnumerator'),\n"
     "                        ns.i('unitdenominator')):\n"
     "            return None",
     "        if False:\n            return None",
     f"{R5}::test_827R5_a_divide_out_of_SCHEMA_ORDER_refuses"),

    (43, "_ordered stops looking at order at all",
     "driver/relocation/inline_html.py",
     "    return seen == sorted(seen)",
     "    return True",
     f"{R5}::test_827R5_a_context_out_of_SCHEMA_ORDER_refuses"),

    (39, "the consumer stops carrying the unit's own reason",
     "driver/relocation/inline_html.py",
     "        if isinstance(unit, str):        # refused; the string says why\n"
     "            return None, unit",
     "        if isinstance(unit, str):\n"
     "            return None, 'duplicate_unit_id'",
     "driver/relocation/test_bind_graph_fact.py::"
     "test_827R5_MALFORMED_structure_is_NEVER_called_a_duplicate_id"),

    # 24 and 25 are RETIRED: they mutated the AST coverage heuristic, which
    # round 6 DELETED for reporting coverage it could not observe. Their
    # replacement is the explicit ledger, whose own two tests (every public
    # callable named, every named node real) are mutated by rows 56-57 below.

    # 27 AND 31 ARE RETIRED AS SUPERSEDED, with the evidence. They disabled
    # direct-child READING (`recursive=False`) and the stray-element guard.
    # Round 6 item 4 added direct-child VALIDATION — unknown direct children of
    # context/entity/period/unit are refused outright — and that rule catches
    # their cases on its own: with `_kids` forced subtree-wide, the wrapped-date
    # context is STILL refused `malformed_context_structure` (verified
    # directly). A mutation that does not remove the protection tests nothing,
    # which is the same trap rows 21, 24, 28 and 34 fell into before it.
    # `recursive=False` remains correct — it is simply no longer the only guard.

    # ---- ROUND 6: identity, namespace, grammar, order ----------------------
    (44, "the SEC identifier scheme no longer checked",
     "driver/relocation/inline_html.py",
     "    if (identifier.get('scheme') or '') != SEC_CIK_SCHEME:\n        return None",
     "    if False:\n        return None",
     f"{R5}::test_827R6_a_MALFORMED_filer_identity_never_binds"),

    (45, "the ten-ASCII-digit CIK rule relaxed",
     "driver/relocation/inline_html.py",
     "    return digits if re.fullmatch(r'[0-9]{10}', digits) else None",
     "    return digits if digits else None",
     f"{R5}::test_827R6_a_MALFORMED_filer_identity_never_binds"),

    (46, "the graph CIK normalised instead of validated",
     "driver/relocation/inline_html.py",
     "    return value if isinstance(value, str) and re.fullmatch(\n"
     "        r'[0-9]{10}', value) else None",
     "    return value.zfill(10) if isinstance(value, str) and value else None",
     f"{R5}::test_827R6_a_GRAPH_cik_outside_the_stored_form_never_binds"),

    (47, "period_type falls through as duration again",
     "driver/relocation/inline_html.py",
     "    if period_type not in ('instant', 'duration'):\n"
     "        return None, 'malformed_period_type'",
     "    if False:\n        return None, 'malformed_period_type'",
     f"{R5}::test_827R6_a_period_type_outside_the_TWO_words_never_binds"),

    (48, "the year converted whole again (the >=4,300-digit crash)",
     "driver/relocation/exact_numbers.py",
     "    year_mod_400 = int(year_digits[-4:])          # bounded: four digits at most",
     "    year_mod_400 = int(year_digits)",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_827R6_an_ENORMOUS_year_parks_and_never_crashes"),

    (49, "namespace resolution replaced by the literal prefix",
     "driver/relocation/inline_html.py",
     "        self.instance = bound.get(_INSTANCE_NS, set())",
     "        self.instance = {'xbrli'}",
     f"{R5}::test_827R6_a_lawful_INSTANCE_binding_binds_whatever_its_prefix"),

    (50, "an undeclared prefix given a fallback",
     "driver/relocation/inline_html.py",
     "        self.dimension = bound.get(_DIMENSION_NS, set())",
     "        self.dimension = bound.get(_DIMENSION_NS, set()) | {'nope'}",
     f"{R5}::test_827R6_a_lawful_DIMENSION_binding_is_read_whatever_its_prefix"),

    (51, "leaf elements may carry nested markup again",
     "driver/relocation/inline_html.py",
     "    return None if node.find(True) is not None else node.get_text()",
     "    return node.get_text()",
     f"{R5}::test_827R6_item4_context_attacks"),

    (52, "unknown direct children of a unit allowed",
     "driver/relocation/inline_html.py",
     "    known = ns.i('measure') | ns.i('divide')\n"
     "    if any((t.name or '').lower() not in known\n"
     "           for t in u.find_all(recursive=False)):\n"
     "        return None",
     "    if False:\n        return None",
     f"{R5}::test_827R6_item4_an_unknown_direct_child_of_a_unit"),

    (53, "the self-ratio unit accepted again",
     "driver/relocation/inline_html.py",
     "        if set(num) & set(den):\n            return None",
     "        if False:\n            return None",
     f"{R5}::test_827R6_a_NESTED_or_SELF_RATIO_unit_never_binds"),

    (54, "the graph number grammar replaced by bare Decimal()",
     "driver/relocation/inline_html.py",
     "    if not _GRAPH_NUMBER.fullmatch(s):\n        return None",
     "    if False:\n        return None",
     f"{R5}::test_827R6_a_graph_value_outside_the_derived_grammar_is_refused"),

    (55, "the fact id stripped in the identity key again (order decides)",
     "driver/core/xbrl_attach.py",
     '            raw_id = row["fact_id"] or ""\n'
     '            out.append("" if not raw_id.strip(XML_S) else raw_id)',
     '            out.append((row["fact_id"] or "").strip())',
     "driver/core/test_round10_event_boundary.py::"
     "test_827R6_a_PADDED_fact_id_is_a_DIFFERENT_id_and_order_cannot_decide"),

    (56, "a public callable dropped from the explicit coverage ledger",
     "driver/core/test_v2_attacks.py",
     '    ("driver.core.slot_convert.validate_slot", "slot_name"):',
     '    ("driver.core.slot_convert.RETIRED_ENTRY", "slot_name"):',
     "driver/core/test_v2_attacks.py::"
     "test_827R6_every_public_callable_NAMES_the_test_that_covers_it"),

    (57, "the ledger points at a test node that does not exist",
     "driver/core/test_v2_attacks.py",
     # THE PAIR KEY IS THE ANCHOR. The bare node string now appears four
     # times — several parameters share one covering test — so it stopped
     # being an anchor at all the moment the ledger was keyed on pairs.
     '    ("driver.core.prepared_fact_v2.split_slice_part", "token"):\n'
     '        "driver/core/test_prepared_fact_v2.py::'
     'test_G33_first_colon_only_split_keeps_a_colon_in_the_value",',
     '    ("driver.core.prepared_fact_v2.split_slice_part", "token"):\n'
     '        "driver/core/test_prepared_fact_v2.py::test_no_such_node",',
     "driver/core/test_v2_attacks.py::"
     "test_827R6_every_named_test_node_really_exists"),

    # ---- #827 ROUND 7b: one mutation per rule closed this round. Each REMOVES
    # the rule outright rather than loosening it — a loosened rule proves
    # nothing when a DIFFERENT guard still catches the fixture, which is how
    # rows 21/24/27/28/31/34 escaped and had to be retired.

    (58, "the element id no longer has to be a lawful XML ID",
     "driver/relocation/inline_html.py",
     "    if _xml_id(str(element_id)) is None:\n"
     "        return None, 'malformed_id'",
     "    if False:\n        return None, 'malformed_id'",
     f"{R5}::test_827R7_an_UNLAWFUL_element_id_is_MALFORMED_under_its_own_name"),

    (59, "blankness decided by PYTHON whitespace again, at the binder door",
     "driver/relocation/inline_html.py",
     "    if (inline_element_id or '').strip(XML_S):",
     "    if (inline_element_id or '').strip():",
     f"{R5}::test_827R7_an_UNLAWFUL_element_id_is_MALFORMED_under_its_own_name"),

    (60, "the concept name no longer has to be a QName",
     "driver/relocation/inline_html.py",
     "    if not _qname_ok(el.get('name'), prepared.get('declared') "
     "or frozenset()):\n        return None, 'malformed_concept_name'",
     "    if False:\n        return None, 'malformed_concept_name'",
     f"{R5}::test_827R7_an_UNLAWFUL_concept_QName_never_binds"),

    (61, "the concept rule left guarding only the exact-id path",
     "driver/relocation/inline_html.py",
     "def evidence_for_element(doc_or_html, el):\n"
     '    """Evidence for an already-resolved element node (the fallback path)."""\n'
     "    return _evidence_from(el, _prepared(doc_or_html))",
     # THE MUTANT MUST MAKE THE FALLBACK *ACCEPT*, NOT REFUSE. My first version
     # set `declared` to None, which makes that path refuse EVERYTHING — and
     # the detector expects a refusal, so it would have stayed green while
     # proving nothing. It now seeds the element's OWN prefix as declared,
     # which disables the check on this path only.
     "def evidence_for_element(doc_or_html, el):\n"
     '    """Evidence for an already-resolved element node (the fallback path)."""\n'
     "    p = dict(_prepared(doc_or_html))\n"
     "    p['declared'] = set(p.get('declared') or ()) | {\n"
     "        (el.get('name') or '').partition(':')[0].lower()}\n"
     "    return _evidence_from(el, p)",
     f"{R5}::test_827R7_the_concept_rule_covers_the_FALLBACK_path_too"),

    (62, "XML-blank ids stop reaching the identity fallback (OVER-catching)",
     "driver/relocation/inline_html.py",
     "    if (inline_element_id or '').strip(XML_S):",
     "    if inline_element_id is not None:",
     f"{R5}::"
     "test_827R7_MUST_ALLOW_an_XML_blank_id_still_uses_the_identity_fallback"),

    (63, "the public id door calls U+00A0 blank again",
     "driver/relocation/inline_html.py",
     "    if not element_id or not str(element_id).strip(XML_S):",
     "    if not element_id or not str(element_id).strip():",
     f"{R5}::"
     "test_827R7_the_PUBLIC_id_door_refuses_an_unlawful_id_for_EVERY_caller"),

    # ---- Packet 17: the SEC CIK contract. The two mutations that need a real
    # Cypher engine live in LIVE_MUTATIONS below, not here — a credential-free
    # extract cannot run their detector, and listing them here would report a
    # result for something that never executed.
    (64, "the locator repairs a non-string CIK back into a lawful spelling",
     "driver/relocation/locator.py",
     "        want_cik = graph_cik(source.get('company_cik'))",
     "        want_cik = graph_cik(str(source.get('company_cik') or ''))",
     f"{RA}::test_a_NON_STRING_expected_CIK_abstains_through_the_public_door"),

    (65, "the query inlines the guard instead of naming its one owner",
     "driver/core/driver_neo4j_adapter.py",
     '"WHERE " + _CIK_GUARD + " "',
     '"WHERE co.cik =~ $cik_pattern AND co.cik <> $non_registrant "',
     f"{RN}::test_the_query_references_the_ONE_guard_BY_NAME"),

    (66, "graph_cik stops refusing the non-registrant marker",
     "driver/core/driver_ids.py",
     "    return None if value == NON_REGISTRANT_CIK else value",
     "    return value",
     f"{RI}::test_graph_cik_refuses_the_non_registrant_marker"),

    (67, "_norm_uid stops requiring the matched company's exact prefix",
     "driver/core/driver_neo4j_adapter.py",
     "    if not u_id.startswith(prefix):\n        return None",
     "    if False:\n        return None",
     f"{RN}::test_norm_uid_refuses_a_reference_that_is_not_this_company"),

    (68, "the parser module re-publishes the owner as a second import path",
     "driver/relocation/inline_html.py",
     "from driver.core.driver_ids import (SEC_CIK_10_PATTERN as "
     "_SEC_CIK_10_PATTERN,\n"
     "                                    graph_cik as _graph_cik)",
     "from driver.core.driver_ids import SEC_CIK_10_PATTERN, graph_cik\n"
     "_SEC_CIK_10_PATTERN = SEC_CIK_10_PATTERN\n_graph_cik = graph_cik",
     f"{RN}::test_the_owner_has_exactly_ONE_public_import_path"),

    (69, "the CIK rule stops being ASCII (Python's \\d admits other digits)",
     "driver/core/driver_ids.py",
     'SEC_CIK_10_PATTERN = r"^[0-9]{10}$"',
     'SEC_CIK_10_PATTERN = r"^[\\d]{10}$"',
     f"{RI}::test_graph_cik_refuses_every_malformed_twin"),

    (72, "O1: the _lawful_fye gate removed (fye_month flows unvalidated)",
     "driver/core/driver_period_resolver.py",
     '    if v is not None and not (type(v) is int and 1 <= v <= 12):\n'
     '        raise PeriodResolutionError(f"fye_month out of range: {v!r} — park")\n'
     '    return v',
     '    return v',
     "driver/core/test_driver_period_resolver.py::"
     "test_fye_month_thirteen_parks"),

    (73, "O10: time_type dropped from the 11-key vocabulary owner",
     "driver/core/driver_period_resolver.py",
     '                    "long_range_end_year", "sentinel_class", "time_type",\n'
     '                    "period_scope")',
     '                    "long_range_end_year", "sentinel_class",\n'
     '                    "period_scope")',
     "driver/core/test_driver_period_resolver.py::"
     "test_time_type_only_parks_not_periodless"),

    (74, "C1 m1: percent_sequential removed from the one unit-vocabulary owner",
     "driver/core/slot_convert.py",
     'CANONICAL_UNITS = ("usd", "m_usd", "percent", "percent_yoy", "percent_sequential",\n'
     '                   "percent_points", "basis_points", "count", "x", "unknown")',
     'CANONICAL_UNITS = ("usd", "m_usd", "percent", "percent_yoy",\n'
     '                   "percent_points", "basis_points", "count", "x", "unknown")',
     "driver/core/test_driver_units.py::test_enum_is_the_ten_units"),

    (75, "C1 m2: percent_qoq invented in the one unit-vocabulary owner",
     "driver/core/slot_convert.py",
     'CANONICAL_UNITS = ("usd", "m_usd", "percent", "percent_yoy", "percent_sequential",\n'
     '                   "percent_points", "basis_points", "count", "x", "unknown")',
     'CANONICAL_UNITS = ("usd", "m_usd", "percent", "percent_yoy", "percent_sequential",\n'
     '                   "percent_points", "basis_points", "count", "x", "unknown",\n'
     '                   "percent_qoq")',
     "driver/core/test_driver_units.py::test_enum_is_the_ten_units"),

    (76, "C3 o1: the multiplier owner stops answering for x",
     "driver/core/slot_convert.py",
     "    if unit in MULTIPLIER_ONE_UNITS:\n        return Decimal(1)\n    return None",
     '    if unit in MULTIPLIER_ONE_UNITS and unit != "x":\n        return Decimal(1)\n    return None',
     "driver/core/test_prepared_fact_v2.py::"
     "test_G3_multiplier_not_one_on_a_ratio_slot_parks[x]"),

    (77, "C3 o2: the multiplier owner answers Decimal(10)",
     "driver/core/slot_convert.py",
     "    if unit in MULTIPLIER_ONE_UNITS:\n        return Decimal(1)\n    return None",
     "    if unit in MULTIPLIER_ONE_UNITS:\n        return Decimal(10)\n    return None",
     "driver/core/test_prepared_fact_v2.py::"
     "test_G3_multiplier_not_one_on_a_ratio_slot_parks[percent]"),

    (78, "C3 s1: the validate door reverts to a drifted inline mult>1 copy",
     "driver/core/slot_convert.py",
     "    _required = family_required_multiplier(stated_unit)\n"
     "    if _required is not None and mult != _required:",
     "    if stated_unit in MULTIPLIER_ONE_UNITS and mult > 1:",
     "driver/core/test_prepared_fact_v2.py::"
     "test_G3_multiplier_not_one_on_a_ratio_slot_parks[percent]"),

    (79, "C2 p1: percent_sequential deleted from the numberless-growth pair",
     "driver/core/driver_validators.py",
     '    elif level_unit is not None and level_unit not in ("percent_yoy",\n'
     '                                                       "percent_sequential"):',
     '    elif level_unit is not None and level_unit not in ("percent_yoy",):',
     "driver/core/test_driver_validators.py::"
     "test_numberless_fact_with_unit_rules"),

    (80, "C2 p2: the annual percent_sequential rule goes dead",
     "driver/core/driver_validators.py",
     '    if fact.get("period_scope") == "annual" and "percent_sequential" in (',
     '    if fact.get("period_scope") == "never" and "percent_sequential" in (',
     "driver/core/test_driver_validators.py::"
     "test_units_required_with_numbers"),

    (81, "C2 p3: the numberless-growth pair widened with percent",
     "driver/core/driver_validators.py",
     '    elif level_unit is not None and level_unit not in ("percent_yoy",\n'
     '                                                       "percent_sequential"):',
     '    elif level_unit is not None and level_unit not in ("percent_yoy",\n'
     '                                                       "percent_sequential", "percent"):',
     "driver/core/test_driver_validators.py::"
     "test_numberless_fact_with_unit_rules"),

    (82, "T1: a rogue outcome token minted outside the one vocabulary",
     "driver/core/driver_validators.py",
     "    add = lambda code, action, msg: v.append(   # T1: every minted token passes",
     '    v.append(Violation("ROGUE_TOKEN", "REJECT", "mutant"))\n'
     "    add = lambda code, action, msg: v.append(   # T1: every minted token passes",
     "driver/core/test_driver_validators.py::"
     "test_the_one_outcome_code_module_owns_every_minted_token"),

    (83, "T2: the numeric-prose heuristic resurrected",
     "driver/core/driver_validators.py",
     '        elif len(vt) > 200:\n'
     '            add("VALUE_TEXT", "REJECT", "value_text over 200 chars")',
     '        elif len(vt) > 200:\n'
     '            add("VALUE_TEXT", "REJECT", "value_text over 200 chars")\n'
     '        elif __import__("re").search(r"\\b(?!(?:19|20)\\d\\d\\b)\\d+\\b", vt):\n'
     '            add("VALUE_TEXT", "REJECT", "mutant heuristic")',
     "driver/core/test_driver_validators.py::"
     "test_T2_timeframe_prose_is_lawful_value_text"),

    (84, "P-O2 a: the invariant call removed from _result",
     "driver/core/driver_period_resolver.py",
     "    verdicts = period_invariant(u_id, scope, time_type, start, end)\n"
     "    if verdicts:",
     "    verdicts = ()\n"
     "    if verdicts:",
     "driver/core/test_driver_period_resolver.py::"
     "test_preserved_multiday_instant_parks"),

    (85, "P-O2 b: the invariant call removed from the validators' period door",
     "driver/core/driver_validators.py",
     "    for code, msg in period_invariant(u_id, fact.get(\"period_scope\"),",
     "    for code, msg in (lambda *a, **k: ())(u_id, fact.get(\"period_scope\"),",
     "driver/core/test_driver_validators.py::"
     "test_stray_period_metadata_without_id_rejected"),

    (86, "P-O3 a: the existing-hit checker unwrapped (hits trusted verbatim)",
     "driver/core/driver_period_resolver.py",
     '            found = _lawful_hit("existing", found, want_scope, time_type)',
     '            pass  # MUTANT: hit trusted verbatim',
     "driver/core/test_driver_period_resolver.py::"
     "test_existing_hit_scope_mismatch_with_request_parks"),

    (87, "P-O3 b: the exact-allowed-keys law ignores extras",
     "driver/core/driver_period_resolver.py",
     "    extra = keys - required - optional\n"
     "    if extra:",
     "    extra = frozenset()  # MUTANT: extras ignored\n"
     "    if extra:",
     "driver/core/test_driver_period_resolver.py::"
     "test_lookup_result_extra_key_parks"),

    (88, "P-O8: the quiet Q4 default restored",
     "driver/core/driver_period_resolver.py",
     "    q = item.get(\"fiscal_quarter\")\n"
     "    if q is None:",
     "    q = item.get(\"fiscal_quarter\") or 4\n"
     "    if False:",
     "driver/core/test_driver_period_resolver.py::"
     "test_ytd_missing_quarter_parks"),

    (89, "P-O12 a: the keyword bool type law removed",
     "driver/core/driver_period_resolver.py",
     "    if type(calendar_override) is not bool:",
     "    if False:",
     "driver/core/test_driver_period_resolver.py::"
     "test_calendar_keyword_type_law_parks_on_all_paths"),

    (90, "P-O12 b: the superseded item route resurrected",
     "driver/core/driver_period_resolver.py",
     "    cal = calendar_override              # P-O12: keyword route ONLY, no coercion",
     '    cal = bool(calendar_override or item.get("calendar_override"))',
     "driver/core/test_driver_period_resolver.py::"
     "test_calendar_keyword_type_law_parks_on_all_paths"),

    (91, "T4: a chosen year endpoint re-invented",
     "driver/core/driver_period_resolver.py",
     '                         ("fiscal_year", MINYEAR, MAXYEAR),',
     '                         ("fiscal_year", 1900, 2200),',
     "driver/core/test_driver_period_resolver.py::"
     "test_strict_shape_check_rejects_mixed_and_incomplete_framing"),

    (92, "T7: the alias re-authored as a second tuple",
     "driver/core/prepared_fact_v2.py",
     "from driver.core.driver_validators import NUMERIC_FIELDS\n"
     "NUMERIC_SLOTS = NUMERIC_FIELDS",
     'NUMERIC_SLOTS = ("level_low", "level_high", "change_value",\n'
     '                 "comparison_low")  # MUTANT: drifted copy',
     "driver/core/test_prepared_fact_v2.py::"
     "test_G34_value_text_and_numeric_slots_are_mutually_exclusive"),

    (93, "C6 r1: the routing author answers level_unit for change_value",
     "driver/core/prepared_fact_v2.py",
     '    return change_unit if name == "change_value" else level_unit',
     '    return level_unit',
     # detector REPOINTED (2026-08-08, C6 close): the G4 node only exercised
     # level slots and never caught this (the recorded coverage gap); the C6
     # card's five-field/two-door node is the honest detector.
     "driver/core/test_prepared_fact_v2.py::"
     "test_slot_unit_routing_matches_the_FROZEN_contract"),

    (95, "C6 s2: the conversion door bypasses the helper with a flipped inline copy",
     "driver/core/prepared_fact_v2.py",
     "            unit = _unit_for_slot(name, it.level_unit, it.change_unit)",
     "            unit = it.level_unit",
     "driver/core/test_prepared_fact_v2.py::"
     "test_slot_unit_routing_matches_the_FROZEN_contract"),

    (94, "T1/P-O2: a resolver emit site bypasses the mint gate with a rogue token",
     "driver/core/driver_period_resolver.py",
     '        out.append((require_known("SCOPE_PAIR"), f"period_scope {scope!r} not in the enum"))',
     '        out.append(("SCOPE_PAIRX", f"period_scope {scope!r} not in the enum"))',
     "driver/core/test_driver_period_resolver.py::"
     "test_T1_the_resolver_mints_every_period_code_through_the_one_owner"),

    (96, "P-D5: the band table quietly widens the ytd cap",
     "driver/core/driver_period_resolver.py",
     '    "ytd": (None, 390),',
     '    "ytd": (None, 400),',
     "driver/core/test_driver_period_resolver.py::"
     "test_band_boundary_rejects[ytd-391]"),

    (97, "P-D6: the repository-pin check is neutered",
     "driver/core/driver_period_resolver.py",
     "    if actual is None or Path(actual).resolve() != expected:",
     "    if False:",
     "driver/core/test_driver_period_resolver.py::"
     "test_substrate_binding_one_authorized_path_both_orders"),

    (98, "T8: the pf2 lane gate is neutered",
     "driver/core/prepared_fact_v2.py",
     "        if self.fact_type not in LANE_STATES:   # T8: the ONE lane vocabulary",
     "        if False:   # MUTANT",
     "driver/core/test_prepared_fact_v2.py::"
     "test_T8_one_lane_vocabulary_owner"),

    (99, "T3: the producerless field sneaks back into the stored contract",
     "driver/core/driver_validators.py",
     '    "slice_parts", "measurement_tokens", "surprise",',
     '    "slice_parts", "measurement_tokens", "surprise", "fact_scope_period_token",',
     "driver/core/test_driver_validators.py::"
     "test_the_producerless_period_token_field_is_gone"),

    (100, "T6: a local id split grows back in the validators",
     "driver/core/driver_validators.py",
     "        src = fact_source_id(fact.get(\"id\"))",
     "        src = (fact.get(\"id\") or \"\").split(\":\", 3)[1]",
     "driver/core/test_driver_ids.py::"
     "test_T6_the_minimal_fact_id_reader_lives_at_the_owner"),

    (101, "T9: the bool guard falls out of the exactness core",
     "driver/core/slot_convert.py",
     '    if isinstance(v, bool):\n        raise SlotConversionError(f"{name}: bool is not a number")',
     "    # bool guard gone",
     "driver/core/test_prepared_fact_v2.py::"
     "test_T9_one_public_exact_number_predicate"),

    (102, "T10: the dead member_refs emission grows back",
     "driver/core/prepared_fact_v2.py",
     '        "id": fact_id, "fact_scope": fact_scope,',
     '        "id": fact_id, "fact_scope": fact_scope,\n        "member_refs": it.member_refs,',
     "driver/core/test_prepared_fact_v2.py::"
     "test_T10_the_clean_path_emits_no_member_refs"),

    (103, "SLICE-GRAMMAR D1: member_token regrows a local KIND:VALUE f-string",
     "driver/core/driver_member_fold.py",
     "    return slice_token(kind, member_label)   # D1: the owner's ONE spelling",
     '    value = norm(member_label)\n    return f"{kind}:{value}"',
     "driver/core/test_driver_ids.py::"
     "test_SLICE_GRAMMAR_one_owner_for_token_and_reader"),

    (104, "SLICE-GRAMMAR D2: slice_menu regrows a local scope reader",
     "driver/core/slice_menu.py",
     "from driver.core.driver_ids import slice_tokens_from_scope  # noqa: F401",
     "def slice_tokens_from_scope(fact_scope):\n"
     "    for slot in (fact_scope or \"\").split(\"|\"):\n"
     "        if slot.startswith(\"slice=\"):\n"
     "            return set(slot[len(\"slice=\"):].split(\";\"))\n"
     "    return set()",
     "driver/core/test_driver_ids.py::"
     "test_SLICE_GRAMMAR_one_owner_for_token_and_reader"),

    (105, "XMLNAME-MIN: the unused prefix slot grows back",
     "driver/xml_names.py",
     "    return local",
     "    return (prefix, local)",
     "driver/core/test_graph_qname_shape.py::"
     "test_a_LAWFUL_graph_qname_splits[ex:Revenue-Revenue-prefixed \\u2014 the alias is dropped, not returned]"),

    (106, "EU-039: the parse security policy silently expands hidden content",
     "driver/relocation/inline_html.py",
     "_PARSER_OPTIONS = dict(recover=False, resolve_entities=False, load_dtd=False,",
     "_PARSER_OPTIONS = dict(recover=False, resolve_entities=True, load_dtd=True,",
     "driver/relocation/test_parser_encoding_ownership.py::"
     "test_EU039_the_parser_policy_never_expands_hidden_content"),

    (107, "EU-070: the template prune is mistargeted",
     "driver/relocation/inline_html.py",
     "    if name == 'template':",
     "    if name == 'templatex':",
     "driver/relocation/test_two_view_bridge.py::"
     "test_EU070_template_contents_are_never_rendered"),

    (108, "EU-071: content-visibility:hidden stops pruning",
     "driver/relocation/inline_html.py",
     "    prune = (st['display'] == 'none' or st['cv'] == 'hidden'",
     "    prune = (st['display'] == 'none' or st['cv'] == 'hiddenx'",
     "driver/relocation/test_two_view_bridge.py::"
     "test_EU071_content_visibility_hidden_prunes"),

    (109, "EU-072: the element-name API token is misspelled",
     "driver/relocation/inline_html.py",
     "    name = (getattr(el, 'name', '') or '').lower()",
     "    name = (getattr(el, 'nome', '') or '').lower()",
     "driver/relocation/test_two_view_bridge.py::"
     "test_EU072_ua_hidden_elements_stay_hidden_by_the_named_api"),

    (110, "EU-078: the Clark universal-name template drifts",
     "driver/relocation/inline_html.py",
     "    return '{%s}%s' % (uri, local)",
     "    return '{%s}-%s' % (uri, local)",
     "driver/relocation/test_two_view_bridge.py::"
     "test_ANY_lawful_prefix_for_the_fact_element_still_binds[ix]"),

    (111, "EU-121: the nsmap API token is misspelled",
     "driver/relocation/inline_html.py",
     "    if not isinstance(value, str) or not hasattr(el, 'nsmap'):",
     "    if not isinstance(value, str) or not hasattr(el, 'nsmapx'):",
     "driver/relocation/test_two_view_bridge.py::"
     "test_ANY_lawful_prefix_for_the_fact_element_still_binds[ix]"),

    (112, "EU-122: the QName separator drifts off the REC grammar",
     "driver/relocation/inline_html.py",
     "    prefix, sep, local = value.partition(':')",
     "    prefix, sep, local = value.partition('.')",
     "driver/relocation/test_two_view_bridge.py::"
     "test_ANY_lawful_prefix_for_the_fact_element_still_binds[ix]"),

    (113, "EU-122: an empty prefix stops refusing",
     "driver/relocation/inline_html.py",
     "    if sep and not prefix:\n        return None",
     "    if False:\n        return None",
     "driver/relocation/test_two_view_bridge.py::"
     "test_the_reserved_xml_prefix_resolves_without_being_declared"),

    (114, "EU-122: the reserved xml binding is mistargeted",
     "driver/relocation/inline_html.py",
     "        uri = el.nsmap.get(prefix) or (_XML_PREFIX_NS if prefix == 'xml'",
     "        uri = el.nsmap.get(prefix) or (_XML_PREFIX_NS if prefix == 'xmlx'",
     "driver/relocation/test_two_view_bridge.py::"
     "test_the_reserved_xml_prefix_resolves_without_being_declared"),

    (115, "EU-131: foreign renderer-parse warnings go silent again",
     "driver/relocation/inline_html.py",
     "        warnings.simplefilter('error')\n        warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)",
     "        warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)",
     "driver/relocation/test_parser_encoding_ownership.py::"
     "test_EU131_a_foreign_renderer_parse_warning_refuses_typed"),

    (116, "EU-132: the renderer view swaps tree builders",
     "driver/relocation/inline_html.py",
     "            return BeautifulSoup(html_text, 'lxml')",
     "            return BeautifulSoup(html_text, 'html.parser')",
     "driver/relocation/test_parser_encoding_ownership.py::"
     "test_EU132_the_renderer_view_is_built_by_the_pinned_lxml_builder"),

    (117, "EU-137: 'display' drops out of the style-state vocabulary",
     "driver/relocation/inline_html.py",
     "        if nm not in ('display', 'visibility', 'content-visibility', 'all'):",
     "        if nm not in ('visibility', 'content-visibility', 'all'):",
     "driver/relocation/test_two_view_bridge.py::"
     "test_a_lawful_document_is_NOT_refused"),

    (118, "EU-138: the important-ordering key flips",
     "driver/relocation/inline_html.py",
     "        key = (bool(d.important), i)",
     "        key = (not d.important, i)",
     "driver/relocation/test_two_view_bridge.py::"
     "test_EU138_an_important_earlier_winner_beats_a_later_plain_value"),

    (119, "EU-139: hidden=until-found stops refusing",
     "driver/relocation/inline_html.py",
     "            and hv.lower() == 'until-found':",
     "            and hv.lower() == 'until-foundx':",
     "driver/relocation/test_two_view_bridge.py::"
     "test_EU139_hidden_until_found_refuses_as_unsupported"),

    (120, "EU-140: the empty style default silently styles",
     "driver/relocation/inline_html.py",
     # first draft used str(None) -> 'None', observationally EQUIVALENT (no
     # declarations either way) and lawfully uncaught; the real attack is a
     # NON-empty default, which must redden any visible-text node.
     "            tinycss2.parse_declaration_list(str(el.get('style') or ''))):",
     "            tinycss2.parse_declaration_list(str(el.get('style') or 'display:none'))):",
     "driver/relocation/test_two_view_bridge.py::"
     "test_a_lawful_document_is_NOT_refused"),

    (121, "EU-141: the all shorthand goes dead",
     "driver/relocation/inline_html.py",
     "        if nm == 'all':",
     "        if nm == 'allx':",
     "driver/relocation/test_two_view_bridge.py::"
     "test_EU141_the_all_shorthand_resets_an_earlier_display_none"),

    (122, "EU-142: the declaration node-type token drifts",
     "driver/relocation/inline_html.py",
     "        if getattr(d, 'type', None) != 'declaration' or d.name.startswith('--'):",
     "        if getattr(d, 'type', None) != 'declarationx' or d.name.startswith('--'):",
     "driver/relocation/test_two_view_bridge.py::"
     "test_a_lawful_document_is_NOT_refused"),

    (123, "GRADE-DOMAIN/W9c: the item key-set widens to admit source-owned",
     "driver/core/prepared_fact_v2.py",
     # original anchors (the SOURCE-OWNED precheck raise) were DELETED by W9c
     # (proof-by-construction); the surviving boundary is the derived
     # ITEM_FIELDS exclusion, so the mutant re-admits the pair there.
     'ITEM_FIELDS = tuple(k for k in PreparedItemV2.__dataclass_fields__\n'
     '                    if k not in SOURCE_OWNED_FIELDS and not k.startswith("_"))',
     'ITEM_FIELDS = tuple(k for k in PreparedItemV2.__dataclass_fields__\n'
     '                    if not k.startswith("_"))',
     "driver/core/test_prepared_fact_v2.py::"
     "test_GRADE_DOMAIN_source_owned_evidence_cannot_alter_selection"),

    (124, "W1: the polarity basis enum stops refusing",
     "driver/core/prepared_fact_v2.py",
     '        if proof["basis"] not in ("source_framing", "metric_meaning"):',
     '        if False:',
     "driver/core/test_prepared_fact_v2.py::"
     "test_W1_an_invented_polarity_basis_is_refused"),

    (125, "W2: the retired-name special case grows back",
     "driver/core/prepared_fact_v2.py",
     '        _check_keys(raw, ITEM_FIELDS,',
     '        if "level_unit_raw" in raw:\n'
     '            raise SchemaError("retired v1 field(s) — this payload predates v2")\n'
     '        _check_keys(raw, ITEM_FIELDS,',
     "driver/core/test_prepared_fact_v2.py::"
     "test_W2_a_retired_key_refuses_at_the_exact_key_owner"),

    (126, "W3: the deferral escape hatch grows back",
     "driver/core/prepared_fact_v2.py",
     "# W3 (#827): the deferral mechanism is DELETED — no deferred helper",
     'DEFERRED_HELPERS = ()\n# W3 (#827): the deferral mechanism is DELETED — no deferred helper',
     "driver/core/test_round9_corrections.py::"
     "test_no_contract_helper_is_left_unreachable_from_production"),

    (127, "W4: a second 64-hex regex grows back in pf2",
     "driver/core/prepared_fact_v2.py",
     "    from driver.core.driver_ids import sha256_hex_ok   # W4: the ONE owner\n    if not sha256_hex_ok(value):",
     '    import re as _re\n    if not isinstance(value, str) or not _re.fullmatch(r"[0-9a-f]{64}", value):',
     "driver/core/test_round8_xbrl_binding.py::"
     "test_W4_the_representation_sha_grammar_has_one_owner"),

    (128, "W16: the xbrl_backed switch flips its default",
     "driver/core/slot_convert.py",
     "def validate_slot(slot_name, slot, *, stated_unit, quote, xbrl_backed=False):",
     "def validate_slot(slot_name, slot, *, stated_unit, quote, xbrl_backed=True):",
     # first detector (G5 structure) ran BEFORE the switch and lawfully missed
     # the flip; the honest detector is a node that RELIES on the default
     # applying the TEXT evidence law.
     "driver/core/test_prepared_fact_v2.py::"
     "test_G6_evidence_must_sit_inside_the_quote"),

    (129, "W15: a removed name sneaks back into the export surface",
     "driver/core/prepared_fact_v2.py",
     '__all__ = ["SchemaError", "ProductionValidationError", "SourceUnavailable",',
     '__all__ = ["SchemaError", "ProductionValidationError", "SourceUnavailable", "PreparedItemV2",',
     "driver/core/test_round10_event_boundary.py::"
     "test_W15_the_declared_export_surface_is_exactly_the_retained_set"),

    (130, "W9: a second production constructor site appears",
     "driver/core/xbrl_attach.py",
     '            fact = PreparedFactV2._build(i["fact"], {   # the fact schema law\n'
     '                "xbrl_concept_raw": concept, "member_refs": i["member_refs"]})',
     '            from driver.core.prepared_fact_v2 import PreparedItemV2 as _It\n'
     '            _It(**{})  # MUTANT: a second aliased constructor site\n'
     '            fact = PreparedFactV2._build(i["fact"], {   # the fact schema law\n'
     '                "xbrl_concept_raw": concept, "member_refs": i["member_refs"]})',
     "driver/core/test_v2_attacks.py::"
     "test_W9_the_verified_bundle_boundary_is_static_and_singular"),

    (131, "W6: a surplus stored key sneaks into the emission",
     "driver/core/prepared_fact_v2.py",
     '        "id": fact_id, "fact_scope": fact_scope,',
     '        "id": fact_id, "fact_scope": fact_scope, "rogue_key": None,',
     "driver/core/test_prepared_fact_v2.py::"
     "test_W6_every_emitted_stored_key_traces_to_a_named_owner"),

    (132, "W7: the instant start-exclusion law goes quiet",
     "driver/core/prepared_fact_v2.py",
     '        if self.time_type == "instant" and self.period_start_date is not None:',
     '        if False:',
     "driver/core/test_round8_xbrl_binding.py::"
     "test_W7_an_instant_bundle_carries_ONLY_its_end_date[instant_with_start]"),

    (133, "W11: the owner's closed polarity pair stops refusing",
     "driver/core/prepared_fact_v2.py",
     '        if proof["polarity"] not in ("favorable", "unfavorable"):',
     '        if False:',
     "driver/core/test_prepared_fact_v2.py::"
     "test_W11_an_invented_polarity_token_is_refused"),

    (134, "F2: the permanent provider errors go back to retry-forever",
     "driver/core/xbrl_attach.py",
     "    except NON_RETRYABLE_SOURCE_ERRORS:\n        raise                                # F2: permanent — never retried",
     "    except ():\n        raise",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F2_only_genuinely_transient_provider_errors_park[permission-fails-loud]"),

    (135, "F3: the unreadable document goes back to fact-blame rejection",
     "driver/core/xbrl_attach.py",
     "        if refused(prepared_doc):\n            raise SourceUnavailable(",
     "        if refused(prepared_doc):\n            raise SchemaError(",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F3_an_unreadable_served_document_parks_with_document_blame"),

    (136, "F5: the adapter's stored-null alias translation is neutered",
     "driver/core/driver_neo4j_adapter.py",
     '                            "end_date": (None if r["end_date"] == "null"\n'
     '                                         else r["end_date"]), "dims": dims,',
     '                            "end_date": r["end_date"], "dims": dims,',
     "driver/core/test_dimension_expanded_identity.py::"
     "test_the_ADAPTER_owns_the_stored_null_alias_and_emits_None"),

    (137, "F9: the attach alias drifts back to a private restatement",
     "driver/core/xbrl_attach.py",
     "_PERIOD_TYPES = PERIOD_TIME_TYPES",
     '_PERIOD_TYPES = ("duration", "instant")',
     "driver/core/test_driver_period_resolver.py::"
     "test_F9_the_period_kind_vocabulary_has_ONE_owner"),

    (138, "F8: the concept QName contract gate is neutered",
     "driver/core/xbrl_attach.py",
     "            if graph_qname_parts(concept) is None:\n                raise SchemaError(",
     "            if False:\n                raise SchemaError(",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F8_a_malformed_concept_QName_is_refused_as_contract_input[a:b:c]"),

    (139, "F7: the adapter's emission drifts from the interface statement",
     "driver/core/driver_neo4j_adapter.py",
     '                            "value": r.get("value"),',
     '                            "value": r.get("value"),\n                            "decimals": r.get("decimals"),',
     "driver/core/test_dimension_expanded_identity.py::"
     "test_F7_the_adapter_and_consumer_share_ONE_interface_statement"),

    (140, "F11: the empty-set park regresses to a channel rejection",
     "driver/core/xbrl_attach.py",
     "    if not lawful:\n        raise ProductionValidationError(",
     "    if False:\n        raise ProductionValidationError(",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F11_an_EMPTY_candidate_set_parks_as_route_limitation"),

    (141, "F12: the owner's level-pair requirement is neutered",
     "driver/core/prepared_fact_v2.py",
     '            if name in (\"level_low\", \"level_high\"):\n                if slot_v is None:',
     '            if name in (\"level_low\", \"level_high\"):\n                if False:',
     "driver/core/test_prepared_fact_v2.py::"
     "test_F12_the_OWNER_requires_the_level_pair_on_an_xbrl_backed_fact"),

    (142, "F12: the owner's null-evidence rule on the xbrl lane is neutered",
     "driver/core/slot_convert.py",
     "        if ev is not None:\n            raise SlotConversionError(",
     "        if False:\n            raise SlotConversionError(",
     "driver/core/test_prepared_fact_v2.py::"
     "test_F12_the_OWNER_refuses_scale_evidence_on_an_xbrl_backed_slot"),

    (143, "F13: the company precheck falls back to the sloppy str test",
     "driver/core/xbrl_attach.py",
     "        if graph_cik(entity_cik) is None:",
     '        if not str(entity_cik or \"\").strip():',
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F13_a_non_canonical_graph_company_parks_at_the_PRECHECK[int]"),

    (144, "F13: the all-excluded read collapses back into carries-NO-fact",
     "driver/core/xbrl_attach.py",
     "                if read.exclusions:",
     "                if False:",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F13_an_all_excluded_read_states_the_TRUTHFUL_availability"),

    (145, "F10: the one-representation graph guard is neutered",
     "driver/core/xbrl_attach.py",
     "        if type(count) is not int or count != 1:",
     "        if False:",
     "driver/core/test_round10_event_boundary.py::"
     "test_more_than_one_xbrl_representation_PARKS"),

    (146, "F14: SchemaError's authorized decision flips to parked",
     "driver/core/prepared_fact_v2.py",
     '    return {SchemaError: "rejected",',
     '    return {SchemaError: "parked",',
     "driver/core/test_round11_outcomes.py::"
     "test_F14_the_authorized_class_outcome_table_at_its_owner"),

    (147, "F14: SchemaError's authorized default code drifts",
     "driver/core/xbrl_attach.py",
     '(SchemaError, "XBRL_CONTRACT_INVALID"),',
     '(SchemaError, "XBRL_SCHEMA_BAD"),',
     "driver/core/test_round11_outcomes.py::"
     "test_F14_the_authorized_class_outcome_table_at_its_owner"),

    (148, "F14: the event-wide fan-out reaches only the first item",
     "driver/core/xbrl_attach.py",
     "        for idx, _f, _c, _e in checked:\n            outcomes.append(_outcome_row(idx, exc, code=code))",
     "        for idx, _f, _c, _e in checked[:1]:\n            outcomes.append(_outcome_row(idx, exc, code=code))",
     "driver/core/test_round10_event_boundary.py::"
     "test_F14_an_event_wide_failure_reaches_EVERY_item"),

    (149, "F14: concept-local failures stop routing to their claimants",
     "driver/core/xbrl_attach.py",
     "        exc = concept_failure.get(concept)",
     "        exc = None",
     "driver/core/test_round10_event_boundary.py::"
     "test_the_guard_asks_the_GRAPH_not_only_the_channels_hashes"),

    (150, "F4: a published token escapes the T1 mint gate",
     "driver/core/xbrl_attach.py",
     '        return _fan_out(exc, code=require_known(\"SOURCE_COMPANY_AMBIGUOUS\"))',
     '        return _fan_out(exc, code=\"SOURCE_COMPANY_AMBIGUOUS\")',
     "driver/core/test_round11_outcomes.py::"
     "test_F4_every_attach_token_is_minted_through_the_T1_owner"),

    (151, "F6: the item gate's unlisted-vocabulary park is neutered",
     "driver/core/xbrl_attach.py",
     "                if type(i) is dict and set(_EVENT_ITEM_KEYS) <= set(i):",
     "                if False:",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F6_an_UNLISTED_item_field_parks_and_a_missing_one_rejects"),

    (152, "F6: the evidence gate's unlisted-vocabulary park is neutered",
     "driver/core/xbrl_attach.py",
     "        if type(value) is dict and set(SOURCE_EVIDENCE_KEYS) <= set(value):",
     "        if False:",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F6_an_UNLISTED_evidence_field_parks_never_rejects"),

    (153, "F6: the piece gate's unlisted-vocabulary park is neutered",
     "driver/core/xbrl_attach.py",
     "            if type(piece) is dict and set(PIECE_KEYS) <= set(piece):",
     "            if False:",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F6_an_UNLISTED_piece_field_parks_and_a_missing_one_rejects"),

    (154, "F6: the unlisted piece kind regresses to a rejection",
     "driver/core/xbrl_attach.py",
     "        if piece[\"kind\"] not in PIECE_KINDS:\n            raise ProductionValidationError(           # F6: unlisted -> park",
     "        if piece[\"kind\"] not in PIECE_KINDS:\n            raise SchemaError(",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F6_an_UNKNOWN_piece_kind_parks_never_rejects"),

    (155, "S2: the slot guard renders the caller's keys again",
     "driver/core/slot_convert.py",
     '        raise SlotConversionError(f"slot carries exactly {SLOT_KEYS}")',
     '        raise SlotConversionError(f"slot carries exactly {SLOT_KEYS}; got {sorted(slot)}")',
     "driver/core/test_prepared_fact_v2.py::"
     "test_S2_a_mixed_key_slot_is_refused_without_rendering_caller_keys"),

    (156, "S8: a fixed precision cap replaces the operand-derived bound",
     "driver/core/slot_convert.py",
     "            ctx.prec = need",
     "            ctx.prec = 60",
     "driver/core/test_v2_attacks.py::"
     "test_ATTACK_a_65_digit_value_is_not_rounded"),

    # 157's first draft neutered the FLOAT branch — NOT CAUGHT rc=0: the
    # later int/Decimal type gate still refuses a float (different message,
    # same outcome), so that mutant is observationally shadowed. Replaced
    # (the entry-120 precedent) with the LOAD-BEARING bool guard, whose
    # removal silently ACCEPTS True as the number 1.
    (157, "S9: the load-bearing bool guard at the shared numeric core is neutered",
     "driver/core/slot_convert.py",
     "    if isinstance(v, bool):\n        raise SlotConversionError(",
     "    if False:\n        raise SlotConversionError(",
     "driver/core/test_prepared_fact_v2.py::"
     "test_S9_slot_numeric_types_at_the_public_door[value-bool]"),

    (158, "S7: the owner bound drifts one character NARROW (4095)",
     "driver/core/slot_convert.py",
     "_MAX_STORED_CHARS = 4096",
     "_MAX_STORED_CHARS = 4095",
     "driver/core/test_round12_exact_scale.py::"
     "test_the_storable_bound_matches_the_owner_contract"),

    (159, "S7: the owner bound drifts one character WIDE (4097)",
     "driver/core/slot_convert.py",
     "_MAX_STORED_CHARS = 4096",
     "_MAX_STORED_CHARS = 4097",
     "driver/core/test_round12_exact_scale.py::"
     "test_the_storable_bound_matches_the_owner_contract"),

    (160, "S11: the canonicalizer stops stripping trailing zeros",
     "driver/core/driver_ids.py",
     '    if "." in out:\n        out = out.rstrip("0").rstrip(".")',
     '    if False:\n        out = out.rstrip("0").rstrip(".")',
     "driver/core/test_v2_attacks.py::"
     "test_ATTACK_the_canonical_length_matches_the_real_canonicalizer"),

    (161, "EU-054: a Core-facing evidence key spelling drifts off the sheet",
     "driver/relocation/inline_html.py",
     "SOURCE_EVIDENCE_KEYS = ('representation_sha256', 'quote_span',\n                        'raw_label_span', 'pieces')",
     "SOURCE_EVIDENCE_KEYS = ('representation_sha256', 'quote_span',\n                        'raw_label_span', 'piecez')",
     "driver/relocation/test_packet_items_through_the_door.py::"
     "test_EU054_the_core_facing_evidence_vocabulary_is_the_sheets"),

    (162, "EU-160: the binder's four-key result contract drifts",
     "driver/relocation/inline_html.py",
     "            'printed_value': printed_value(evidence.get('value_input'),",
     "            'printed_valu': printed_value(evidence.get('value_input'),",
     "driver/relocation/test_bind_graph_fact.py::"
     "test_RED_the_expected_numeric_object_is_returned_for_field_wise_binding"),

    (163, "EU-180: a prepared-record key spelling drifts at the writer",
     "driver/relocation/inline_html.py",
     "                'fact_nodes': fact_nodes,",
     "                'fact_nodez': fact_nodes,",
     "driver/relocation/test_two_view_bridge.py::"
     "test_a_prior_row_carrying_an_ALTERNATE_PREFIX_fact_is_not_taken_as_a_section"),

    (164, "EU-185: the refusal-record reader's spelling drifts",
     "driver/relocation/inline_html.py",
     "    return prepared.get('refused') if isinstance(prepared, dict) else None",
     "    return prepared.get('refuzed') if isinstance(prepared, dict) else None",
     "driver/core/test_round8_xbrl_binding.py::"
     "test_F3_an_unreadable_served_document_parks_with_document_blame"),

    (165, "EU-187: the evidence writer's result key drifts off the sheet",
     "driver/relocation/inline_html.py",
     "            'quote_span': [span[0], span[1]],",
     "            'quote_spam': [span[0], span[1]],",
     "driver/relocation/test_evidence_writer_contract.py::"
     "test_EU187_the_evidence_writer_emits_exactly_the_sheets_four_keys"),
    (166, "EU-001: a canonical key drifts out of the Route-A compat table",
     "driver/relocation/exact_numbers.py",
     "    'usd':   frozenset({'usd', 'usd_per_share'}),",
     "    'us_d':   frozenset({'usd', 'usd_per_share'}),",
     "driver/relocation/test_unit_handoff_census.py::"
     "test_EU001_the_route_a_unit_maps_are_pinned_and_C1_membered"),

    (167, "EU-033: the divide branch key drifts and every per-share abstains",
     "driver/relocation/exact_numbers.py",
     "    if declared.get('is_divide'):",
     "    if declared.get('is_divid'):",
     "driver/relocation/test_unit_handoff_census.py::"
     "test_EU033_the_semantic_reader_is_fail_closed_on_its_branch_keys"),
]


#: THE LIVE READ-ONLY LANE — the same tuple schema, the same staged-tree
#: extraction and mutation helpers, one extra opt-in. It exists because these
#: two mutations break a CYPHER predicate, so their only honest detector asks
#: the real engine; the zero-credential extract cannot run it, and a structural
#: substitute would pin the guard's presence rather than its behaviour.
#: NOT zero-credential, and the receipt says so.
LIVE_MUTATIONS = [
    (70, "the Cypher guard stops refusing the non-registrant marker",
     "driver/core/driver_neo4j_adapter.py",
     '_CIK_GUARD = "co.cik =~ $cik_pattern AND co.cik <> $non_registrant"',
     '_CIK_GUARD = "co.cik =~ $cik_pattern"',
     LIVE_ALLZERO),

    (71, "the Cypher guard stops enforcing the ten-ASCII-digit contract",
     "driver/core/driver_neo4j_adapter.py",
     '_CIK_GUARD = "co.cik =~ $cik_pattern AND co.cik <> $non_registrant"',
     '_CIK_GUARD = "co.cik <> $non_registrant"',
     LIVE_TOOSHORT),
]


#: The paths a detector can need. `driver_period_resolver` imports the ONE
#: calendar canon `fiscal_math` from the skills tree, and `drivers_harness`
#: carries the paid-OpenAI acting lane — without either, a detector cannot be
#: collected at all, and a collection error (rc 4) is NOT a mutation proof.
#: The 4.3 GiB filing cache is deliberately excluded: no detector here reads it.
TREE_PATHS = ("driver", HARNESS_REL, "drivers_harness", "conftest.py",
              "pytest.ini",
              os.path.join(".claude", "skills", "earnings-orchestrator",
                           "scripts"))


def build_tree(base):
    """The EXACT STAGED TREE, extracted with git — never the working tree.

    This used to `shutil.copytree` the live checkout, so every mutation proof
    described whatever happened to be on disk rather than the tree that will be
    committed. With zero drift the two coincide, which is exactly why the
    difference goes unnoticed until the one time it matters. `git write-tree`
    is the same object `git commit` records and the same one the isolated gate
    proves, so the mutation battery and the gate now describe ONE tree.
    """
    root = os.path.join(base, "tree")
    os.makedirs(root)
    tree = subprocess.run(["git", "write-tree"], cwd=_REPO, check=True,
                          capture_output=True, text=True).stdout.strip()
    tar = subprocess.run(["git", "archive", tree, "--"] + list(TREE_PATHS),
                         cwd=_REPO, check=True, capture_output=True)
    if subprocess.run(["tar", "-x", "-C", root], input=tar.stdout).returncode:
        raise RuntimeError("could not extract the staged tree")
    return root


def run_detector(root, node_id):
    # THE APPROVED ALLOWLIST, from the gate itself — never a blocklist of
    # credential-ish words, which admits the next name nobody enumerated.
    import tempfile as _tf
    sys.path.insert(0, os.path.join(_REPO, ".claude", "plans", "Drivers",
                                    "experiments", "harness"))
    from isolated_manifest_check import sanitized_env
    home = _tf.mkdtemp(prefix="step4_home_")
    env = sanitized_env(root, home)
    env["PYTHONPATH"] = os.pathsep.join(
        [root, os.path.join(root, "driver", "relocation"),
         os.path.join(root, ".claude", "skills", "earnings-orchestrator",
                      "scripts")])
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p",
                        "no:randomly", "-p", "no:cacheprovider", "--no-header",
                        "--tb=no", node_id],
                       cwd=root, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "")[-400:]


def run_live_detector(root, node_id):
    """The SAME invocation as `run_detector`, with two deliberate differences:
    `-m live` selects the engine test, and the environment is the REAL one —
    `sanitized_env` strips the credentials this detector exists to use. Every
    other guard is unchanged (one exact parameter node, run alone), except that
    here a catch requires exit 1 PLUS the intended assertion marker — exit 1
    alone would also count a connection, credential or collection failure as
    proof, which is not a catch.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [root, os.path.join(root, "driver", "relocation"),
         os.path.join(root, ".claude", "skills", "earnings-orchestrator",
                      "scripts")])
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p",
                        "no:randomly", "-p", "no:cacheprovider", "--no-header",
                        "--tb=no", "-m", "live", node_id],
                       cwd=root, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "")[-400:]


def read_tx_marker():
    """The graph's own committed-transaction counter, read read-only. The live
    section is bracketed by it: if these mutations caused any write, the number
    moves. Returns (lastCommittedTxn, databaseID)."""
    sys.path.insert(0, _REPO)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO, ".env"))
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ["NEO4J_URI"],
                               auth=(os.environ["NEO4J_USERNAME"],
                                     os.environ["NEO4J_PASSWORD"]))
    try:
        with drv.session(default_access_mode="READ") as s:
            r = s.run(TX_STATEMENT).single()
            return r["lastCommittedTxn"], r["databaseID"]
    finally:
        drv.close()


def apply_mutation(root, rel, old, new):
    path = os.path.join(root, rel)
    text = open(path, encoding="utf-8").read()
    if text.count(old) != 1:
        raise RuntimeError(
            f"mutation anchor is not unique in {rel}: {text.count(old)} "
            f"occurrence(s) of {old[:60]!r}")
    open(path, "w", encoding="utf-8").write(text.replace(old, new))


def main():
    results, problems = [], []
    base = tempfile.mkdtemp(prefix="step4_control_")
    try:
        clean = build_tree(base)
        for mid, name, _f, _o, _n, node in MUTATIONS:
            rc, tail = run_detector(clean, node)
            results.append({"phase": "clean control", "id": mid,
                            "detector": node, "rc": rc,
                            "passed": rc == 0, "tail": tail.strip()[-160:]})
            if rc != 0:
                problems.append(f"control FAILED for detector {node} (rc {rc})")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    for mid, name, rel, old, new, node in MUTATIONS:
        base = tempfile.mkdtemp(prefix=f"step4_m{mid}_")
        try:
            root = build_tree(base)
            apply_mutation(root, rel, old, new)
            rc, tail = run_detector(root, node)
            caught = rc == 1      # EXACTLY 'tests failed'
            results.append({"phase": "mutation", "id": mid, "name": name,
                            "file": rel, "detector": node, "rc": rc,
                            "caught": caught, "tail": tail.strip()[-200:],
                            "note": ("caught requires pytest exit 1 exactly; "
                                     "2-5 mean the suite did not run")})
            print(f"[{mid:2d}] {'CAUGHT ' if caught else 'ESCAPED'} "
                  f"{name} -> {node.split('::')[-1]}", flush=True)
            if not caught:
                problems.append(
                    f"mutation {mid} ({name}) did not FAIL its detector "
                    f"(pytest exit {rc}; only exit 1 counts as caught)")
        finally:
            shutil.rmtree(base, ignore_errors=True)

    # ---- THE LIVE READ-ONLY LANE, only when explicitly asked for ----------
    live_results, tx_before, tx_after = [], None, None
    include_live = "--include-live" in sys.argv
    if include_live:
        tx_before = read_tx_marker()
        base = tempfile.mkdtemp(prefix="step4_live_control_")
        try:            # EACH exact node is its OWN control, run alone
            clean = build_tree(base)
            for _m, _n, _f, _o, _w, node in LIVE_MUTATIONS:
                rc, tail = run_live_detector(clean, node)
                live_results.append({"phase": "clean control", "id": _m,
                                     "detector": node, "rc": rc,
                                     "passed": rc == 0,
                                     "tail": tail.strip()[-160:]})
                if rc != 0:
                    problems.append(
                        f"LIVE control FAILED for {node} (rc {rc})")
        finally:
            shutil.rmtree(base, ignore_errors=True)

        for mid, name, rel, old, new, node in LIVE_MUTATIONS:
            base = tempfile.mkdtemp(prefix=f"step4_live_m{mid}_")
            try:
                root = build_tree(base)
                apply_mutation(root, rel, old, new)
                rc, tail = run_live_detector(root, node)
                # EXIT 1 IS NOT ENOUGH HERE. A dropped connection, a missing
                # credential or a collection error also exits non-zero, and
                # would have been recorded as a caught mutation. The captured
                # result must additionally show THE INTENDED ANSWER: with the
                # guard gone the refused value returns a row instead of none.
                intended = LIVE_INTENDED in tail
                caught = rc == 1 and intended
                live_results.append({"phase": "mutation", "id": mid,
                                     "name": name, "file": rel,
                                     "detector": node, "rc": rc,
                                     "intended_assertion": intended,
                                     "expected_marker": LIVE_INTENDED,
                                     "caught": caught,
                                     "tail": tail.strip()[-200:]})
                print(f"[{mid:2d}] {'CAUGHT ' if caught else 'ESCAPED'} "
                      f"(live) {name}", flush=True)
                if not caught:
                    problems.append(
                        f"LIVE mutation {mid} ({name}) not caught: pytest exit "
                        f"{rc} (need exactly 1) and intended assertion "
                        f"{'present' if intended else 'ABSENT'} "
                        f"({LIVE_INTENDED!r}) — a setup, connection or "
                        f"collection failure is not a catch")
            finally:
                shutil.rmtree(base, ignore_errors=True)

        tx_after = read_tx_marker()
        if tx_before != tx_after:
            problems.append(
                f"LIVE lane moved the graph: {tx_before} -> {tx_after}")

    n_iso, n_live = len(MUTATIONS), len(LIVE_MUTATIONS)

    def _group(rows, phase, key):
        """The rows that PASSED/CAUGHT in one group. Counting them, rather than
        asking `all(...)`, is what stops the flag being vacuous: `all()` over an
        empty list is True, so a group that never ran would have looked clean."""
        return [r for r in rows if r["phase"] == phase and r.get(key)]

    counts = {
        "isolated_controls_passed": len(_group(results, "clean control", "passed")),
        "isolated_mutants_caught": len(_group(results, "mutation", "caught")),
        "live_controls_passed": len(_group(live_results, "clean control", "passed")),
        "live_mutants_caught": len(_group(live_results, "mutation", "caught")),
    }
    expected = {"isolated_controls_passed": n_iso,
                "isolated_mutants_caught": n_iso,
                "live_controls_passed": n_live,
                "live_mutants_caught": n_live}
    proof_complete = bool(
        include_live
        and not problems
        and tx_before is not None and tx_before == tx_after
        and counts == expected)

    doc = {"receipt": f"#827 step 4 — {n_iso} isolated + {n_live} "
                      f"read-only-live staged-tree mutations",
           "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
           "method": f"each mutation applied to a FRESH EXTRACT of the "
                     f"STAGED tree (git write-tree + git archive), never the "
                     f"working tree; the live tree is never edited; each "
                     f"mutation must fail its OWN named detector, run alone; "
                     f"a clean unmutated control must pass first. "
                     f"{n_iso} isolated mutations run zero-credential; "
                     f"{n_live} run in the CREDENTIALED read-only live lane "
                     f"(--include-live), each against one exact parameter "
                     f"node, requiring the intended assertion and not merely "
                     f"a non-zero exit, bracketed by "
                     f"lastCommittedTxn which must not move",
           #: TRUE only when BOTH lanes actually ran and every gate held. The
           #: final #827 proof requires it; a default (isolated-only) run
           #: leaves it false rather than looking complete.
           "proof_complete": proof_complete,
           "proof_counts": counts, "proof_counts_expected": expected,
           "script_sha256": hashlib.sha256(
               open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "isolated": {"zero_credential": True,
                        "count": len(MUTATIONS), "results": results},
           "live_read_only": {
               "zero_credential": False,
               "note": "NOT the zero-credential lane: these two mutations "
                       "break a Cypher predicate, so their detector must ask "
                       "the real engine. Read-only, one named node, bracketed "
                       "by the graph's own committed-transaction counter.",
               "ran": include_live,
               "opt_in": "--include-live",
               "count": len(LIVE_MUTATIONS),
               "detectors": [r[5] for r in LIVE_MUTATIONS],
               "intended_assertion_marker": LIVE_INTENDED,
               "tx_statement": TX_STATEMENT,
               "tx_before": tx_before, "tx_after": tx_after,
               "tx_unchanged": (tx_before == tx_after) if include_live else None,
               "results": live_results},
           # the legacy top-level `results` duplicated `isolated.results`
           # verbatim; repository search found no reader, so the two-section
           # shape is the only copy.
           "problems": problems}
    body = json.dumps(doc, indent=1, sort_keys=True)
    open(OUT, "w").write(body + "\n")
    print(f"\nproblems: {len(problems)}")
    for p in problems:
        print("   ", p)
    print(f"wrote {os.path.basename(OUT)}")
    if include_live and not proof_complete:
        # WRITING A FALSE FIELD IS NOT ENOUGH: a caller that only checks the
        # exit status would read an incomplete proof as a successful run.
        print(f"PROOF INCOMPLETE — counts {counts} expected {expected}, "
              f"tx {tx_before} -> {tx_after}")
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
