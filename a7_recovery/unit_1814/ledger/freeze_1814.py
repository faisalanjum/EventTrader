# -*- coding: utf-8 -*-
"""Freeze unit_1814: accounting, dependency bindings, whitelist and manifest.

The two composed views are carried as ONE directory digest each and stay out of
the publication whitelist: they are reproducible from their recipe and from
sources the tree already holds.
"""
import collections, hashlib, io, json, os

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.dirname(U)
RID = "wf_b0543d14-6c2"
ROOT = "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0"
S = "/home/faisal/EventMarketDB/.claude/settings.local.json"
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def dir_digest(d):
    rows = []
    for root, _x, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f)
            rows.append((os.path.relpath(p, d), fsha(p)))
    rows.sort()
    return hashlib.sha256(
        b"".join(("%s\0%s\n" % r).encode("utf-8") for r in rows)).hexdigest(), len(rows)


out = json.load(io.open(U + "/capture/OUTCOME_1814.json", encoding="utf-8"))
pre = json.load(io.open(U + "/evidence/PRECALL_1814.json", encoding="utf-8"))
ita = json.load(io.open(U + "/logs/INTAKE_1814.json", encoding="utf-8"))
usg = json.load(io.open(U + "/capture/RUNTIME_USAGE_1814.json", encoding="utf-8"))
own = json.load(io.open(U + "/evidence/OWNER_PERMISSION_1814.json", encoding="utf-8"))
allow = json.load(io.open(S, encoding="utf-8"))["permissions"]["allow"]
c = out["counts"]

acc = collections.OrderedDict([
    ("task", "Codex SEQ 1814: run the final segment 8 once under the owner-granted "
             "permission, preserve raw first, then intake and close the full 206-lane "
             "input/reply accounting. No prepare, no ninth receipt, no commit, push "
             "or scoring."),
    ("call", collections.OrderedDict([
        ("invoked_times", 1), ("run_id", out["run_id"]), ("task_id", out["task_id"]),
        ("tool_use_id", out["tool_use_id"]),
        ("run_id_supplied", out["actual_wire"]["run_id_supplied"]),
        ("resume_from_run_id", out["actual_wire"]["resume_from_run_id_supplied"]),
        ("input_keys", out["actual_wire"]["input_keys"]),
        ("args_wire_type", out["actual_wire"]["args_wire_type"]),
        ("args_wire_len", out["actual_wire"]["args_wire_len"]),
        ("decoded_equals_the_committed_array",
         out["actual_wire"]["decoded_equals_the_committed_array"]),
        ("decoded_compact_sha256", out["actual_wire"]["decoded_compact_sha256"]),
        ("typed_projection_sha256", out["actual_wire"]["typed_projection_sha256"]),
        ("script_sha256", pre["envelope"]["script_sha256"]),
        ("earlier_refused_workflow_not_repeated", True)])),
    ("raw_outcome", collections.OrderedDict([
        ("state_status", out["state_status"]),
        ("official_state_sha256", out["official_state_sha256"]),
        ("official_state_bytes", out["official_state_bytes"]),
        ("journal_sha256", out["journal_sha256"]),
        ("new_starts", c["actual_new_starts"]),
        ("authorized_max", c["authorized_max_new_starts"]),
        ("result_returns", c["result_returns"]),
        ("started_without_result", c["started_without_result"]),
        ("empty_results", c["empty_results"]),
        ("refusals_or_errors", c["rows_in_error"]),
        ("rows_claiming_cache", c["rows_claiming_cache"]),
        ("unexpected_extra_start", c["unexpected_extra_start"]),
        ("transcript_files", c["transcript_files"]),
        ("files_in_run_dir", c["files_in_run_dir"]),
        ("tool_uses", usg["tool_uses"]), ("subagent_tokens", usg["subagent_tokens"]),
        ("duration_ms", usg["duration_ms"]),
        ("raw_identity_gate", "clean"),
        ("parent_records_kept", out["actual_wire"]["parent_records_kept"])])),
    ("permission", collections.OrderedDict([
        ("granted_by", "the owner, through the built-in permissions command"),
        ("before", collections.OrderedDict([
            ("bytes", 8095), ("allow_entries", 139),
            ("sha256",
             "7bf06c3503d4179c2926f9cd211010e7df42f10a6a13f9ac1b09b0e9c457c750")])),
        ("after", collections.OrderedDict([
            ("bytes", os.path.getsize(S)), ("allow_entries", len(allow)),
            ("sha256", fsha(S))])),
        ("byte_delta", os.path.getsize(S) - 8095), ("entry_delta", len(allow) - 139),
        ("added_exactly_one",
         sum("seg08" in x for x in allow) == 1 and len(allow) - 139 == 1),
        ("earlier_script_rules_kept",
         sum("grade_batch" in x for x in allow) - 1),
        ("core_edited_settings", False),
        ("owner_permission_records_preserved", len(own)),
        ("native_records_preserved", len(own) + len(out["actual_wire"]
                                                    ["parent_records_kept"]))])),
    ("root_sha256", ita["root_sha256"]),
    ("root_unchanged", ita["root_sha256"] == ROOT),
    ("segment8_intake", collections.OrderedDict([
        ("receipt_supplied", ita["receipt_supplied"]), ("run_id", ita["run_id"]),
        ("logical_script_is_the_executed_file",
         ita["seg8_logical_is_the_executed_file"]),
        ("ledger", ita["ledger"]), ("retry", ita["retry"]),
        ("uncalled", ita["uncalled"]), ("problems", ita["problems"]),
        ("finalization_sha256", ita["finalization_sha256"]),
        ("accounting_sha256", ita["accounting_sha256"]),
        ("owner_counts", ita["owner_counts"]),
        ("differences_from_the_reviewer_expectation",
         ita["differences_from_the_expectation"]),
        ("earlier_intakes_rerun", False),
        ("raw_reply_files", ita["raw_reply_files_after"]),
        ("finalizations_present", ita["finalizations_present"])])),
    ("whole_root_now_complete", collections.OrderedDict([
        ("selected", ita["owner_counts"]["selected"]),
        ("required", ita["owner_counts"]["required"]),
        ("never_started", ita["owner_counts"]["never_started"]),
        ("what_this_means", "every root lane has an input-valid and reply-valid "
                            "G1 record. It is identity and schema validity ONLY."),
        ("what_this_does_not_mean", "no meaning is adjudicated, no scorer has run, "
                                    "no production replay has happened, and no grade "
                                    "or score exists.")])),
    ("no_next_packet", collections.OrderedDict([
        ("prepare_run", False), ("ninth_receipt_created", False),
        ("reason", "the root is fully accounted for; there is no remainder")])),
    ("scorer_not_run", True), ("meaning_not_reconciled", True),
    ("live_conservative_counter", 5856 + c["actual_new_starts"]),
    ("historical_frozen_baseline", 5612),
    ("not_done_deliberately", ["scoring", "meaning reconciliation", "any retry",
                               "prepare of an empty remainder", "receipt 9",
                               "staging, commit or push", "cleanup",
                               "A3-A6 reopening", "Step 14"])])
io.open(U + "/ACCOUNTING_1814.json", "w", encoding="utf-8").write(
    json.dumps(acc, indent=1) + "\n")

views = collections.OrderedDict()
for name in ("subagent_runs", "workflows"):
    d, n = dir_digest(U + "/view/" + name)
    views["view/" + name] = collections.OrderedDict([
        ("digest", d), ("files", n), ("compose_command", "compose_views_1814.sh")])
dep = collections.OrderedDict([
    ("composed_views", views),
    ("map", collections.OrderedDict([
        ("a7_map_1814.tsv", fsha(U + "/a7_map_1814.tsv"))])),
    ("derived_from", collections.OrderedDict([
        ("run", "unit_1808/out/run_1808 copied to out/run_1814"),
        ("views", "unit_1808/view/* plus this unit's captured run"),
        ("map", "unit_1808/a7_map_1808.tsv")])),
    ("note", "both views are rebuilt into NEW absent destinations from published "
             "bytes by compose_views_1814.sh and are recorded as one directory "
             "digest each instead of being republished")])
io.open(U + "/DEPENDENCIES.json", "w", encoding="utf-8").write(
    json.dumps(dep, indent=1) + "\n")

wl = []
for root, dirs, fs in os.walk(U):
    dirs[:] = [d for d in dirs if os.path.join(root, d) != U + "/view"]
    for f in fs:
        r = os.path.relpath(os.path.join(root, f), U)
        if r.startswith("view/") or r in ("WHITELIST.tsv", "MANIFEST.sha256"):
            continue
        wl.append(r)
wl.sort()
io.open(U + "/WHITELIST.tsv", "w", encoding="utf-8").write("\n".join(wl) + "\n")

man = [(fsha(os.path.join(U, r)), r) for r in wl]
man.append((fsha(U + "/WHITELIST.tsv"), "WHITELIST.tsv"))
for name in ("subagent_runs", "workflows"):
    v = views["view/" + name]
    man.append((v["digest"], "view/%s/  (%d files, one directory digest, composed "
                             "by compose_views_1814.sh)" % (name, v["files"])))
man.sort()
io.open(U + "/MANIFEST.sha256", "w", encoding="utf-8").write(
    "".join("%s  %s\n" % r for r in man))

print("  whitelist paths : %d" % len(wl))
print("  manifest rows   : %d  (whitelist + WHITELIST + 2 view digests)" % len(man))
print("  manifest        : %s" % fsha(U + "/MANIFEST.sha256"))
print("  views           : %s" % ", ".join(
    "%s %d files %s" % (k, v["files"], v["digest"][:16]) for k, v in views.items()))
print("  conservative    : %d -> %d" % (5856, acc["live_conservative_counter"]))
print("  permission      : +%d bytes, +%d entry, exactly one: %s, core edited: %s"
      % (acc["permission"]["byte_delta"], acc["permission"]["entry_delta"],
         acc["permission"]["added_exactly_one"], acc["permission"]["core_edited_settings"]))
