#!/usr/bin/env python3
"""Account for EVERY record and every replay branch (Codex SEQ 1543).

Two inventories, because "zero refusals" is not the goal and never was:

  * per owner, each route record is classified as APPLIED, NO-CHANGE, TERMINATED
    (the shell died, so history made no edit either), FAITHFULLY FAILED (my refusal
    matches a failure the transcript itself recorded) or REFUSED (I failed where
    history succeeded - the only class that is a defect);
  * per replay branch, whether a test and a mutation exercise it, so an untested
    branch is named rather than left to look like a passing one.

Faithfulness is decided by the record's OWN saved result, not by my judgement: a
result carrying a traceback or an assertion is history failing there too.
"""
import collections
import hashlib
import io
import json
import os
import re
import sys
import contextlib

R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(R, "ledger"))
import chrono_replay as CR
import replay_transcript as RT

FAILED = re.compile(r"Traceback \(most recent call last\)|AssertionError|"
                    r"^Exit code \d+$|Error:", re.M)

OWNERS = collections.OrderedDict([
    ("raw_transport.py",
     ("bench_1306/.claude/plans/Drivers/experiments/harness/raw_transport.py", 32847)),
    ("audit_worker_access.py",
     ("bench_1306/.claude/plans/Drivers/experiments/harness/audit_worker_access.py",
      33828)),
    ("test_harness_guards.py",
     ("bench_1306/.claude/plans/Drivers/experiments/harness/test_harness_guards.py",
      34187)),
])


def expected_products():
    """-> {line: (path, bytes, sha256)} - each product's INDEPENDENTLY derived identity.

    This is evidence, not a rule: every row was derived from the product's own source
    (a literal `Write`, the committed bytes served by git, or a deterministic
    reconstruction whose route lands on an already-accepted owner pin) and carries its
    provenance. Presence is not correctness, so a product is only `applied` when its
    path, byte count and digest all match the row pinned here.
    """
    out = {}
    path = os.path.join(R, "products", "EXPECTED_PRODUCTS.tsv")
    if not os.path.isfile(path):
        return out
    for row in io.open(path, encoding="utf-8"):
        if row.startswith("#") or not row.strip():
            continue
        line, ppath, nbytes, sha = row.split("\t")[:4]
        out[int(line)] = (ppath, int(nbytes), sha)
    return out


#: every state each fact can take, so a report can list them all - including zeros
PRODUCT_STATES = ("correct", "wrong", "missing", "unpinned", "not-attempted")
CALL_STATES = ("completed", "historically-failed", "faithfully-failed", "refused",
               "waiting", "missing-result", "terminated")


def product_status(now, want):
    """-> what the PRODUCT is. The sole owner of the product rule.

    Presence is not correctness: a body is `correct` only when its path, byte count and
    digest all equal the independently pinned row.
    """
    if now is None:
        return "missing"
    if want is None:
        return "unpinned"
    return "correct" if now == want else "wrong"


def call_outcome(failed, result, present, waiting, replay_error=None):
    """-> what HISTORY's call did. The sole owner of the call rule.

    Independent of the product: local replay producing bytes is not history answering,
    and a wrong product does not tell us whether the call failed, refused or never
    returned. Both facts are recorded side by side rather than one overwriting the other.

    `replay_error` is `(exception class name, message)` when the caller's replay
    failed. A replay failure is FAITHFUL only when history's saved result states THE
    SAME exception - class and full message - as the terminal text of a traceback. A
    generic failure keyword is not the historical failure: an unrelated ValueError over
    a saved AssertionError was `faithfully-failed` before (Codex SEQ 1559 item 2).
    """
    if not present:
        return "waiting" if waiting else "missing-result"
    historical_failure = result is not None and FAILED.search(result)
    if failed:
        if replay_error is not None:
            # THE WHOLE MESSAGE, AT A LINE BOUNDARY. A saved tool result carries the
            # shell's own trailer after the exception line, so the block that follows
            # the frames is `Class: message` plus unrelated tail lines. Every line of
            # the replay's message must match; what follows a complete match is not
            # part of the exception.
            cls, msg = replay_error
            # a multi-line assertion message ends in newlines the saved block does
            # not carry; trailing newlines are not part of the exception's identity
            msg = (msg or "").rstrip("\n")
            # A BARE CLASS IS A COMPLETE EXCEPTION LINE. `assert x in s` prints
            # `AssertionError` with nothing after it; asking for `AssertionError: `
            # ruled the identical historical failure `refused`.
            want = "%s: %s" % (cls, msg) if msg else cls
            blocks = historical_exceptions(result or "")
            exact = any(b == want or b.startswith(want + "\n") for b in blocks)
            return "faithfully-failed" if exact else "refused"
        # my replay failed too: faithful when history failed, otherwise MY defect
        return "faithfully-failed" if historical_failure else "refused"
    # MY REPLAY GOING THROUGH DOES NOT MAKE HISTORY'S CALL SUCCEED. The saved result is
    # the authority on what the call did; a local success over a recorded failure is
    # not `completed`, it is a failure I did not reproduce.
    return "historically-failed" if historical_failure else "completed"



def historical_exceptions(result):
    """-> every `Class: message` a saved result's tracebacks terminate in.

    A saved tool result is compound: a traceback, then pytest summaries, then the
    shell's own trailer. The exception text is what follows the last indented frame
    line of a traceback block, up to the block's end (a blank line or the next
    traceback). Multi-line messages are kept whole; nothing is truncated, and a blank
    line inside a message is not a boundary."""
    out = []
    lines = (result or "").split("\n")
    i = 0
    while i < len(lines):
        if not lines[i].startswith("Traceback (most recent call last)"):
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].startswith("  "):
            j += 1
        # the block runs to the next traceback or the end: an exception message may
        # itself contain blank lines, so a blank line is not a boundary. What follows
        # a complete message (pytest summaries, the shell trailer) is tolerated by the
        # caller's line-boundary prefix rule, never by trimming here.
        k = j
        while k < len(lines) and not lines[k].startswith("Traceback (most recent call last)"):
            k += 1
        if j < k:
            out.append("\n".join(lines[j:k]).rstrip("\n"))
        i = k
    return out

def producer_report(products):
    """-> exact producer lists for every product state and every call state.

    Built from the recorded rows rather than by re-deciding anything, and every state
    is present even when empty: a live zero is only meaningful if the bucket exists.
    """
    report = {"product_states": dict((k, []) for k in PRODUCT_STATES),
              "call_states": dict((k, []) for k in CALL_STATES),
              "finalizable": []}
    for line in sorted(products):
        row = products[line]
        report["product_states"][row["product_status"]].append(line)
        report["call_states"][row["call_outcome"]].append(line)
        if row["finalizable"]:
            report["finalizable"].append(line)
    return report


def classify(owner, upto):
    L = RT.result_ledger()
    waiting = {L.uses[t] for t in L.outstanding if t in L.uses}
    o = CR.tree_origin("bench_1306")
    base = RT._committed("/x/" + owner, commit=o[1]) or ""
    recs, producers = CR.route_records(owner, o[0], upto)
    # A PRODUCER IS NOT AN OWNER. It is in the route because a record of this
    # owner consumes what it wrote; its own failure is a fact about that
    # intermediate, not a refusal against this file - counting it as one
    # reports a defect against a file the record never wrote.
    text, side = base, {}
    rows = collections.Counter()
    detail = []
    products = {}
    pinned = expected_products()
    for n, rec in recs:
        before = text
        result = RT.saved_result(n)
        if n in producers and RT.shell_terminated(result):
            # THE SHELL DIED BEFORE THIS PRODUCER RAN. Decided first, exactly as for an
            # owner: a terminated call produced nothing, so executing it would invent a
            # product history never had.
            rows["producer-terminated"] += 1
            detail.append((n, "producer-terminated"))
            products[n] = collections.OrderedDict([
                ("path", producers[n]), ("present", False), ("bytes", None),
                ("sha256", None), ("product_status", "not-attempted"),
                ("call_outcome", "terminated"), ("finalizable", False)])
            continue
        if n in producers:
            # A PRODUCER IS JUDGED BY ITS PRODUCT, NOT BY THE OWNER'S TEXT. It is in
            # this route precisely because it writes a SIDE FILE, so a successful call
            # normally leaves the owner unchanged - measuring the owner labelled every
            # real product `no-change` and discarded the only change the record owns.
            # A call that returns WITHOUT its required product fails closed; a call that
            # raises AFTER writing one keeps both facts.
            product = producers[n]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    text, _ = RT.apply_saved_edits(text, {n: rec}, owner, side=side)
                failed = False
            except Exception:
                failed = True
            now = side.get(product)
            want = pinned.get(n)
            got = None if now is None else (
                producers[n], len(now.encode("utf-8")),
                hashlib.sha256(now.encode("utf-8")).hexdigest())
            # TWO INDEPENDENT FACTS. What the product IS, and what history's call DID.
            # Encoding either by overwriting or suffixing the other loses the one it
            # overwrites - a wrong product used to erase whether the call had faithfully
            # failed, refused, waited or never answered.
            pstatus = product_status(got, want)
            outcome = call_outcome(failed, result, RT.result_present(n), n in waiting)
            kind = "producer-%s/%s" % (pstatus, outcome)
            products[n] = collections.OrderedDict([
                ("path", producers[n]), ("present", now is not None),
                ("bytes", None if now is None else len(now.encode("utf-8"))),
                ("sha256", None if now is None
                 else hashlib.sha256(now.encode("utf-8")).hexdigest()),
                ("product_status", pstatus), ("call_outcome", outcome),
                # FINALIZATION FAILS CLOSED: only a correct product from a completed
                # call may be used.
                ("finalizable", pstatus == "correct" and outcome == "completed")])
            rows[kind] += 1
            detail.append((n, kind))
            continue
        if RT.shell_terminated(result):
            rows["terminated"] += 1
            detail.append((n, "terminated"))
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                text, _ = RT.apply_saved_edits(text, {n: rec}, owner, side=side)
            kind = "applied" if text != before else "no-change"
        except Exception:
            # PRESENCE AND TEXT ARE DIFFERENT FACTS (Codex SEQ 1544 item 4).
            #   * text carrying a failure  -> history failed here too: FAITHFUL
            #   * present but EMPTY        -> history COMPLETED with no output, so a
            #                                 refusal here is mine: a defect
            #   * absent, use still live   -> the call was WAITING at the boundary
            #   * absent, no use at all    -> the outcome is MISSING; it proves nothing
            if result is not None and FAILED.search(result):
                kind = "faithfully-failed"
            elif RT.result_present(n):
                kind = "refused-after-empty" if not result else "refused"
            elif n in waiting:
                kind = "waiting"
            else:
                kind = "missing-result"
        rows[kind] += 1
        detail.append((n, kind))
    return rows, detail, text, products


#: rows that are ordinary controls, each with the reason no mutation can prove them
CONTROL_ONLY = {
    "boundary owner": "a byte pin: these bytes are those bytes",
    "owner pins": "byte pins for the four A3 artefacts",
    "era cutoff kind": "a byte comparison against surviving era blobs",
}


def verdict(rows):
    """-> process exit status for an inventory. Nonzero if any branch is untested or
    carries no mutation (a stated byte/pin control excepted).

    The inventory used to print its counts and exit zero, so a run with an unmapped
    branch reported success and the ordered chain carried on to freeze it.
    """
    # THE ACTUAL FIELD. Generated rows carry `test`, never `tested`, so
    # `r.get("tested", True)` was always True and an untested row passed. The control
    # that "proved" this rule supplied a synthetic `tested` key, so it validated the
    # rule against a schema this module never produces.
    bad = [r for r in rows
           if not r.get("test")
           or (not r.get("mutation") and not r.get("control_only"))]
    return 1 if bad else 0


def branches():
    """-> each replay decision branch, with whether a test and a mutation cover it."""
    muts = json.load(open(os.path.join(R, "reports", "mutations.json")))
    covered = {c["case"] for c in muts["cases"] if c["killed"]}
    # EVERY test file, not one: the controls added for a new rule live in their
    # own file, and reading a single file reported them as untested.
    tdir = os.path.join(R, "tests")
    tests = "".join(io.open(os.path.join(tdir, f), encoding="utf-8").read()
                    for f in sorted(os.listdir(tdir)) if f.endswith(".py"))
    named = [
        ("tree qualification", "absolute destination names its tree",
         "test_the_owner_is_qualified_by_its_worktree"),
        # A DISTINCT BREAK OF THE SAME RULE OWNER, not a duplicate: this one judges a
        # write by its bare filename alone, which the row above does not detect.
        ("another tree's copy is not this owner", "wrong tree",
         "test_a_write_into_ANOTHER_tree_is_not_a_write_of_this_owner"),
        ("cd ordering", "wrong cwd for a relative name",
         "test_a_relative_name_belongs_to_the_cd_that_precedes_it"),
        # Codex SEQ 1559: every accepting boundary has a mutation and a named test
        ("checkpoint tuple", "checkpoint tuple binds cutoff",
         "test_it_REFUSES_a_permutation_of_cutoffs_between_two_rows"),
        ("signer full prompt", "signer prompt bound in full",
         "test_it_REFUSES_a_prompt_that_differs_by_one_byte_from_the_full_script_literal"),
        ("signer uuid chain", "signer chain bound", "test_it_REFUSES_a_broken_uuid_chain"),
        ("post-read measurement", "after-state measured after open, not after read",
         "test_the_after_state_is_measured_AFTER_the_consumer_not_after_open"),
        ("required non-null", "a null in a required field is accepted",
         "test_it_REFUSES_a_null_in_every_required_field_all"),
        ("exact historical exception", "a generic failure keyword stands in for the exact exception",
         "test_a_WRONG_exception_over_a_saved_failure_is_refused"),
        ("fixed prefix digest", "the prefix digest is not compared",
         "test_it_REFUSES_a_prefix_whose_byte_changed"),
        ("cache key identity", "the cache key ignores the input identity",
         "test_the_cache_key_binds_the_transcript_and_store_identity"),
        ("resume verdict", "a failed resume is clean",
         "test_a_run_that_raised_is_NEVER_clean_whatever_it_read"),
        ("live-only import refused", "an import only the live filesystem provides is served",
         "test_an_import_only_the_live_filesystem_provides_is_refused"),
        ("outside the package", "a path outside the package counts as inside",
         "test_outside_means_not_inside_the_package_and_not_tooling"),
        ("executed-script argv", "an executed script gets no arguments",
         "test_executed_scripts_receive_their_own_arguments"),
        ("suffix needs a directory", "a bare filename matches the repository root copy",
         "test_the_store_serves_an_empty_committed_file_as_present"),
        ("empty module is present", "an empty module source is absence",
         "test_a_repo_package_import_is_served_from_the_git_store_not_the_checkout"),
        ("bare name needs a bare owner", "a bare relative name matches any owner of that basename",
         "test_a_bare_relative_name_never_matches_a_package_marker_of_another_package"),
        ("filesystem questions from the world", "a filesystem question about the side table answers from the live box",
         "test_filesystem_questions_are_answered_by_the_world_for_outside_paths"),
        ("namespace packages served", "a namespace package is not served",
         "test_a_namespace_package_is_served_from_the_committed_tree"),
        ("directory iteration from the world", "glob walks the live box",
         "test_glob_walks_directories_through_the_world"),
        ("tree origin through a shell variable", "a tree named through a variable has no origin",
         "test_tree_origin_is_found_when_the_command_names_the_tree_through_a_variable"),
        ("import roots absolute in the world", "import roots stay relative",
         "test_relative_import_roots_are_absolute_in_the_world"),
        ("a program's cwd is its record's", "a program stands in the census directory",
         "test_a_program_stands_where_its_command_cd_ed"),
        ("shell assignments separated by semicolons", "assignments on one line are not shell variables",
         "test_assignments_separated_by_semicolons_are_shell_variables"),
        ("a replayed import is served from its world, not from a pre-loaded bench module", "a pre-loaded bench module answers a replayed import",
         "test_a_pre_imported_bench_module_never_answers_a_replayed_import"),
        ("an unmapped /tmp read is temporary, never covered", "an unmapped /tmp read is covered",
         "test_the_read_classifier_covers_only_mapped_equal_bytes_under_tmp"),
        ("a schema-invalid attempt is paid evidence, never valid", "a schema-invalid attempt is counted as valid",
         "test_the_exact_accounting_on_the_package"),
        ("the raw prefilter sees a JSON-escaped script run", "the raw prefilter misses a JSON-escaped script path",
         "test_the_script_runner_pattern_matches_a_json_escaped_quoted_path"),
        ("a cut-short program keeps a write its remainder never names", "a cut-short program always loses its write",
         "test_a_write_survives_a_later_environment_failure_when_the_rest_never_names_the_file"),
        ("a stdin program gets the arguments the shell passed", "a stdin program keeps the synthetic argv",
         "test_a_stdin_program_with_arguments_gets_them"),
        ("the pre-filter reads the scripts a command runs", "the pre-filter never reads an executed script",
         "test_the_pre_filter_admits_a_command_whose_executed_script_names_the_file"),
        ("a sed after a cd names its file from where the shell stood", "a sed after a cd names its file from the record start",
         "test_sed_after_a_same_line_cd_names_its_file_relative_to_that_directory"),
        ("an in-place sed is a route of its file", "an in-place sed is not a route",
         "test_sed_in_place_on_a_quoted_file_is_a_route_of_that_file"),
        ("the sed file token is unquoted", "the sed file token keeps its quotes",
         "test_sed_in_place_on_a_quoted_file_is_applied_at_replay"),
        ("a join-form write names its file", "a join-form write is not a write",
         "test_a_join_of_a_literal_directory_is_a_write_of_that_file"),
        ("a program's argument binds its directory", "a program's argument is not bound",
         "test_a_join_of_a_command_line_argument_is_a_write_of_that_file"),
        ("a replayed program does not sleep real time", "a replayed program sleeps real time",
         "test_a_replayed_program_does_not_sleep_real_time"),
        ("a stat miss on a mount is recorded", "a stat miss on a mount is not recorded",
         "test_an_absent_mounted_file_asked_through_isfile_is_a_recorded_miss"),
        ("the seed-tree climb stops at the root", "the seed-tree climb never stops at the root",
         "test_a_source_outside_every_seeded_tree_has_no_seed_tree"),
        ("a lookup is answered by its exact path", "a lookup is answered by a suffix match",
         "test_a_lookup_is_answered_by_its_exact_path_only"),
        ("a bare exception class is the same failure", "a bare exception class never matches",
         "test_a_bare_exception_class_in_history_matches_a_replay_error_with_no_message"),
        ("a -c program ends at its matching quote", "a -c program runs to the line's last quote",
         "test_a_dash_c_program_ends_at_its_matching_quote_not_the_lines_last_quote"),
        ("the active owner's text honours the cutoff", "the active owner text ignores the cutoff",
         "test_the_active_owners_text_is_served_only_at_or_beyond_the_record_being_applied"),
        ("a tree seeded from another tree's modified files", "a seeded tree starts from the bare commit",
         "test_a_tree_seeded_from_another_trees_modified_files_copies_each_of_them"),
        ("an append selects its process", "an append is not a write",
         "test_an_append_to_the_owner_selects_the_process"),
        ("a command starts in its record's directory", "a command without cd stood nowhere",
         "test_a_command_without_cd_stood_in_the_records_working_directory"),
        ("re-entrant reads honour their cutoff", "a re-entrant read ignores its cutoff",
         "test_a_reentrant_read_honours_its_cutoff"),
        ("a rejected tool call did nothing", "a rejected tool call is replayed",
         "test_a_rejected_tool_call_did_nothing"),
        ("a -c line inside a heredoc body is content", "a -c line inside a heredoc body is a program",
         "test_a_dash_c_line_inside_a_heredoc_body_is_content_not_a_program"),
        ("a nested program restores an outer import", "a nested program evicts an outer import",
         "test_a_nested_program_does_not_evict_an_outer_import_still_loading"),
        ("a record's own sibling write is read back", "a record's own sibling write stays stale",
         "test_a_sibling_written_by_this_record_is_read_back_as_written_even_if_marked_stale"),
        ("background record judged by what history observed", "a background record is judged by its launch notice",
         "test_a_background_record_is_judged_by_what_history_observed_not_its_launch_notice"),
        ("dot-dot paths resolve in the world", "a dot-dot path is a different directory",
         "test_a_dot_dot_path_is_the_same_directory_to_the_world"),
        ("import root is where the program stood", "an import root is where the command ended",
         "test_an_import_is_served_from_where_the_program_stood_not_where_the_command_ended"),

        ("sed line insert", "sed line insertion", "test_a_line_addressed_sed_insert_is_replayed"),
        ("grep-guarded sed", "grep-guarded sed is idempotent",
         "test_a_grep_guarded_sed_does_not_insert_a_line_that_is_already_there"),
        ("no final newline", "no final newline",
         "test_a_line_addressed_sed_insert_is_replayed"),
        ("backup/restore", "backup and restore is net zero",
         "test_a_backup_of_this_file_is_captured_so_the_restore_can_run"),
        ("multi-file program", "multi-file saved program",
         "test_a_loop_over_filenames_binds_one_variable_to_every_file"),
        ("alias cycle", "canonical-path alias cycle",
         "test_two_spellings_of_one_path_CANONICALISE_the_same"),
        ("recovered digest", "a recovered body must match its digest",
         "test_a_recovered_body_that_does_not_match_its_digest_is_REFUSED"),
        ("boundary owner", "exact-boundary owner pin",
         "test_the_a3_evidence_boundary_proves_the_run"),
        ("era cutoff kind", "delta pre-trigger vs snapshot post-trigger",
         "test_the_replay_reproduces_surviving_era_bytes"),
        ("owner pins", "every final owner pin", "test_all_four_a3_artefacts_are_reproduced_byte_exactly"),
        ("shell termination", "shell termination",
         "test_a_command_whose_shell_was_KILLED_makes_no_edit"),
        ("script closure", "executed-script closure",
         "test_a_command_that_RUNS_A_SCRIPT_owns_that_script_s_writes"),
        ("per-line substitution", "per-line substitution",
         "test_a_non_global_substitution_applies_once_PER_LINE"),
        ("command order", "sed command order",
         "test_sed_operations_run_in_COMMAND_ORDER"),
        (".bak preservation", ".bak preserved for restore",
         "test_sed_i_suffix_keeps_the_pre_edit_bytes_for_a_later_restore"),
        ("package manifest", "package manifest compares content",
         "test_the_manifest_compares_CONTENT_not_just_the_file_list"),
        ("a file's text is not a path", "a file's text is not a path",
         "test_a_whole_FILE_TEXT_is_not_mistaken_for_a_path"),
        ("out-of-range line insert", "out-of-range line insert",
         "test_a_line_address_past_the_end_inserts_nothing"),
        ("empty-file line insert", "empty-file line insert",
         "test_an_empty_file_takes_no_line_insert"),
        ("grep guard reads the named file", "guard reads the named file",
         "test_the_grep_guard_reads_the_FILE_THE_GREP_NAMES"),
        ("only owning processes EXECUTE", "only owning processes run",
         "test_an_UNRELATED_programs_missing_subprocess_cannot_erase_this_owners_write"),
        ("path built inside the open call", "path built inside the open call",
         "test_a_path_BUILT_INSIDE_THE_OPEN_CALL_still_names_this_owner"),
        ("git show producer", "git show produces its redirect target",
         "test_a_git_show_REDIRECT_produces_the_file_the_next_step_reads"),
        ("absolute destination names its tree", "absolute destination names its tree",
         "test_a_copy_INTO_ANOTHER_TREE_is_not_a_write_of_this_owner"),
        ("binary read yields bytes", "binary read yields bytes",
         "test_a_BINARY_read_of_a_replayed_file_yields_BYTES"),
        ("result found by tool_use_id", "result found by its tool_use_id",
         "test_a_RESULT_IS_FOUND_BY_ITS_TOOL_USE_ID_not_by_proximity"),
        ("a cd names the tree", "a cd names the tree",
         "test_a_cd_into_a_SIBLING_TREE_keeps_its_records_out_of_this_route"),
        ("text inside a program", "text inside a program is not a write",
         "test_a_NAME_INSIDE_A_PYTHON_STRING_does_not_classify_the_shell"),
        ("process ownership", "text inside a program is not a write",
         "test_ONE_CALL_TWO_PROCESSES_are_owned_separately"),
        ("process selection", "text inside a program is not a write",
         "test_only_the_OWNING_processes_of_a_call_are_executed"),
        ("termination order", "termination decided first",
         "test_TERMINATION_is_decided_before_any_composer_or_program_runs"),
        ("script cached per cutoff", "script cached per cutoff",
         "test_a_SCRIPT_is_cached_per_CUTOFF_not_per_path"),
        ("resume equals fresh", "resume agrees with the past route",
         "test_RESUMING_a_resolution_equals_rebuilding_it_from_scratch"),
        ("owner append", "owner append keeps its text",
         "test_an_APPEND_to_the_owner_keeps_what_was_there"),
        ("owner append cursor", "owner append keeps its text",
         "test_an_APPEND_to_the_owner_puts_the_cursor_at_the_END"),
        ("sibling append", "sibling append keeps its text",
         "test_an_APPEND_to_a_SIDE_FILE_keeps_what_was_there"),
        ("cache fence restores exactly", "the cache guard clears before refilling",
         "test_a_cleared_cache_is_restored_with_its_ORIGINAL_object"),
        ("owner write truncates", "write mode still truncates",
         "test_WRITE_to_the_OWNER_still_truncates"),
        ("sibling write truncates", "sibling write mode still truncates",
         "test_WRITE_to_a_SIDE_FILE_still_truncates"),
        ("shim self-interception", "the shim steps aside for its own reads",
         "test_the_shim_steps_aside_while_the_replay_reads_for_itself"),
        ("empty result is present", "an empty result is present",
         "test_an_EMPTY_completed_result_is_PRESENT_not_missing"),
        ("ledger accounts for every row", "ledger accounts for every row",
         "test_the_ledger_accounts_for_EVERY_row_of_the_frozen_prefix"),
        ("child audit", "child audit crosses the boundary",
         "test_a_CHILD_interpreters_reads_are_audited_too"),
        ("heredoc opening line continues", "heredoc opening line continues",
         "test_a_heredoc_whose_OPENING_LINE_CONTINUES_is_still_a_program"),
        ("a module import is served", "a module import is served",
         "test_a_replayed_program_can_IMPORT_a_sibling_it_could_open"),
        ("an unknown module still refuses", "an unknown module is not invented",
         "test_an_UNKNOWN_module_still_refuses"),
        ("a recovered artefact has an era", "a recovered artefact has an era",
         "test_each_era_is_served_at_its_own_window"),
        ("a tree sibling is not a producer", "a tree sibling is not a producer",
         "test_a_source_with_its_own_TREE_is_not_a_producer"),
        ("the producer's product is inspected", "the product check is real",
         "test_all_seven_live_products_reconcile_against_their_pins"),
        ("a missing product fails closed", "a missing product still fails closed",
         "test_a_call_that_returns_without_its_product_FAILS_CLOSED"),
        ("a wrong product fails closed", "a wrong product is rejected",
         "test_a_present_but_WRONG_product_fails_closed"),
        ("producer termination precedes execution",
         "termination precedes execution",
         "test_a_TERMINATED_call_never_executes"),
        ("a producer with no result is not credited",
         "an absent result is not completed",
         "test_a_MISSING_saved_result_is_not_credited_by_local_bytes"),
        ("a truly outstanding call is not credited",
         "an absent result is not completed",
         "test_a_truly_OUTSTANDING_call_is_not_credited_by_local_bytes"),
        ("the report lists every producer call state",
         "the report lists every call state",
         "test_the_report_lists_every_producer_call_state"),
        ("product status and call outcome do not collapse",
         "the two facts do not collapse",
         "test_a_WRONG_product_and_a_FAILED_call_both_survive"),
        ("a faithfully failed call keeps both facts",
         "the two facts do not collapse",
         "test_a_faithfully_failed_call_that_wrote_its_product_keeps_BOTH_facts"),
        ("a refused call keeps both facts", "the two facts do not collapse",
         "test_a_REFUSED_call_that_wrote_its_product_keeps_BOTH_facts"),
        ("a history failure is not completed",
         "a history failure is not completed",
         "test_correct_product_but_HISTORY_FAILED_never_finalizes"),
        ("finalization requires a completed call",
         "finalization requires a completed call",
         "test_correct_product_with_a_FAITHFUL_failure_never_finalizes"),
        ("a correct product refused never finalizes",
         "finalization requires a completed call",
         "test_correct_product_with_a_REFUSAL_never_finalizes"),
        ("a correct product outstanding never finalizes",
         "finalization requires a completed call",
         "test_correct_product_that_is_still_OUTSTANDING_never_finalizes"),
        ("a correct product with no result never finalizes",
         "finalization requires a completed call",
         "test_correct_product_with_no_saved_result_never_finalizes"),
        ("a missing pin reports unpinned", "a missing pin is not correct",
         "test_a_present_product_with_NO_PIN_reports_unpinned_and_fails_closed"),
        ("each non-completed state is listed exactly",
         "a populated call-state line is not omitted",
         "test_each_non_completed_call_state_is_listed_exactly"),
        ("owner lists exclude producer rows",
         "owner lists exclude producer rows",
         "test_the_owner_lists_hold_only_owner_rows"),
        ("the report carries every required state",
         "the report lists every call state",
         "test_the_report_carries_every_required_state"),
        ("a product before a failure keeps both facts", "the product check is real",
         "test_a_product_written_before_a_FAILURE_keeps_both_facts"),
        ("three disputed records write this owner",
         "text inside a program is not a write",
         "test_the_three_disputed_records_really_do_write_THIS_owner"),
        ("pre-series window is empty",
         "an era-less fallback may not fill a pre-series window",
         "test_before_the_first_timed_body_the_answer_is_exactly_None"),
        ("producer boundary is exact", "a recovered artefact has an era",
         "test_the_producer_boundary_is_exact"),
    ]
    out = []
    for branch, mut, test in named:
        # A ROW MAY LAWFULLY HAVE NO MUTATION, but only when it says why. A byte or pin
        # equality is an ordinary control: the "rule" is that these bytes are those
        # bytes, and the only way to "mutate" it is to corrupt the expected answer,
        # which proves nothing. Such a row carries its reason instead of a mutation,
        # and is counted separately from a row that is simply uncovered.
        reason = CONTROL_ONLY.get(branch)
        out.append(collections.OrderedDict([
            ("branch", branch),
            ("test", test if test in tests else None),
            ("mutation", None if reason else (mut if (mut and mut in covered) else None)),
            ("control_only", reason)]))
    return out


def main():
    report = collections.OrderedDict()
    for name, (owner, upto) in OWNERS.items():
        rows, detail, _text, products = classify(owner, upto)
        report[name] = collections.OrderedDict([
            ("records", sum(rows.values())), ("counts", dict(rows)),
            ("refused_lines", [n for n, k in detail if k == "refused"]),
            ("producer_lines", [n for n, k in detail if k.startswith("producer")]),
            ("producer_products", collections.OrderedDict(
                (str(n), products[n]) for n in sorted(products))),
            ("producer_report", producer_report(products)),
            ("faithfully_failed_lines", [n for n, k in detail
                                         if k == "faithfully-failed"]),
            ("refused_after_empty_lines", [n for n, k in detail
                                           if k == "refused-after-empty"]),
            ("waiting_lines", [n for n, k in detail if k == "waiting"]),
            ("missing_result_lines", [n for n, k in detail
                                      if k == "missing-result"]),
            ("terminated_lines", [n for n, k in detail if k == "terminated"])])
        print("%-26s %s" % (name, dict(rows)))
    br = branches()
    untested = [b["branch"] for b in br if not b["test"]]
    unmutated = [b["branch"] for b in br
                 if not b["mutation"] and not b.get("control_only")]
    control_only = [b["branch"] for b in br if b.get("control_only")]
    report["branches"] = br
    report["untested_branches"] = untested
    report["branches_without_a_mutation"] = unmutated
    report["control_only_branches"] = control_only
    print("branches: %d, untested %s, without a mutation %d, control-only %d"
          % (len(br), untested or "none", len(unmutated), len(control_only)))
    io.open(os.path.join(R, "reports", "branch_inventory.json"), "w",
            encoding="utf-8").write(json.dumps(report, indent=2) + "\n")
    # REFUSE on an unmapped branch rather than printing the count and exiting zero.
    return verdict(br)


if __name__ == "__main__":
    raise SystemExit(main())
