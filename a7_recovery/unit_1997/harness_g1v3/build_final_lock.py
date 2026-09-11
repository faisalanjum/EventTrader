"""The smallest materializer seam, completed: immutable accepted raws PLUS ONE
reviewed reconciliation artifact -> final inventory, sidecar, validator receipt
and a frozen no-call sign packet (Codex SEQ 1342).

Every owner is reused, none is replaced: raw_transport parses, the reconciliation
artifact owns every semantic change, validate_benchmark_inventory validates, and
the sign input keeps the existing final_sign_input shape. Nothing is repaired
here: any mismatch refuses before a sign packet exists.

The frozen package owner build_inventory_review.py is deliberately NOT edited —
its bytes are pinned by the frozen manifest and production edits are forbidden in
this task — so the seam is completed in this candidate and proved against the
same owners.
"""
import collections, hashlib, io, json, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
     "/scratchpad")
RUN = S + "/invrev_run4"
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
H = X + "/harness"
OUT = S + "/lock/candidate"
MAILBOX = "/home/faisal/.core827-orchestrator"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_inventory_review as P                             # noqa: E402
import raw_transport as RT                                     # noqa: E402
import validate_benchmark_inventory as INV                     # noqa: E402
from driver.core.prepared_fact_v2 import verify_occurrence     # noqa: E402

sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()
RECON = RUN + "/reconciliation_final.json"
MODEL, EFFORT, AGENT, TRANSPORT = (P.REVIEW_MODEL, P.REVIEW_EFFORT,
                                   P.REVIEW_AGENT_TYPE, P.REVIEW_TRANSPORT)


def accepted():
    atts = json.load(io.open(RUN + "/attempts.json", encoding="utf-8"))
    best = {}
    for a in atts:
        if a["source_id"] not in best or a["attempt"] > best[a["source_id"]]["attempt"]:
            best[a["source_id"]] = a
    return best


def parts_of(sid):
    d = json.load(io.open(X + "/inventory_review/inputs/%s.json" % sid,
                          encoding="utf-8"))
    return {p["part"]: p["content"] for p in d["event"]["text_parts"]}


def derive(recon, best, order):
    """Accepted verdicts + the reviewed reconciliation -> rows, sidecar, problems.

    The rows are DERIVED, never copied from the artifact; the artifact's own
    proposed inventory must then equal the derivation exactly.
    """
    problems, rows, sidecar, raws = [], collections.OrderedDict(), [], {}
    for sid in order:
        a = best[sid]
        raw = io.open(os.path.join(RUN, "replies", a["raw_name"]),
                      encoding="utf-8").read()
        raws[sid] = raw
        got = RT.parse_reply(raw)
        ev = []
        for v in got["verdicts"]:
            if v.get("row") is not None:
                ev.append(dict(v["row"]))
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "proposal"),
                ("proposal_id", v["proposal_id"]), ("decision", v["decision"]),
                ("why", v["why"]), ("row", v.get("row"))]))
        for ad in got.get("additions") or []:
            ev.append(dict(ad["row"]))
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "addition"),
                ("proposal_id", None), ("decision", "add"),
                ("why", ad["why"]), ("row", ad["row"])]))
        for x in got.get("exclusions_considered") or []:
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "exclusion_considered"),
                ("proposal_id", None), ("decision", "exclude"),
                ("why", x["why"]),
                ("row", {"quote": x["quote"], "part_ref": x["part_ref"],
                         "occurrence_in_part": x["occurrence_in_part"]})]))
        rows[sid] = ev

    # ---- the ONE reviewed reconciliation, applied by its own declared changes
    declared = {c["owner"] for c in recon["changes"]}
    known = ({a["id"] for a in recon["aggregate_changes"]}
             | {c["id"] for c in recon["coverage_selections"]}
             | {"ledger#%02d" % r["ordinal"] for r in recon["resolutions"]})
    for owner in sorted(declared - known):
        problems.append("reconciliation change has no declared owner: %s" % owner)
    for r in recon["resolutions"]:
        if r["status"] == "remains_genuinely_unsettled":
            problems.append("resolution %d is unresolved" % r["ordinal"])
    for c in recon["changes"]:
        sid = c["source_id"]
        if sid not in rows:
            problems.append("change names an event outside the accepted set: %s" % sid)
            continue
        if c["op"] == "promote":
            rows[sid].append(collections.OrderedDict([
                ("source_id", sid), ("part_ref", None),
                ("occurrence_in_part", None), ("quote", c["quote"]),
                ("raw_label_or_claim", c["label"]),
                ("proposed_record_kind", c["kind"]),
                ("proposed_hard_classes", list(c["tags"]))]))
            sidecar.append(collections.OrderedDict([
                ("source_id", sid), ("origin", "reviewed_reconciliation"),
                ("proposal_id", None), ("decision", "promote"),
                ("why", c["owner"]), ("row", None)]))
            continue
        hit = [r for r in rows[sid] if r["quote"] == c["quote"]
               and r["raw_label_or_claim"] == c["label"]]
        if len(hit) != 1:
            problems.append("change targets %d rows in %s" % (len(hit), sid))
            continue
        r = hit[0]
        r["proposed_record_kind"] = c["after"]["kind"]
        r["proposed_hard_classes"] = list(c["after"]["tags"])
        sidecar.append(collections.OrderedDict([
            ("source_id", sid), ("origin", "reviewed_reconciliation"),
            ("proposal_id", None), ("decision", c["op"]),
            ("why", c["owner"]), ("row", None)]))

    # ---- the promoted rows learn their part from the source, never from prose
    for sid, rs in rows.items():
        parts = parts_of(sid)
        for r in rs:
            if r["part_ref"] is None:
                owners = [p for p, t in parts.items() if r["quote"] in t]
                if len(owners) != 1:
                    problems.append("%s: a promoted quote locates in %d parts"
                                    % (sid, len(owners)))
                    continue
                r["part_ref"] = owners[0]

    # ---- the one locator boundary: reviewer 0-based -> shared 1-based, once
    locator = []
    for sid, rs in rows.items():
        parts = parts_of(sid)
        for r in rs:
            txt = parts.get(r["part_ref"])
            if txt is None:
                problems.append("%s: part %r is not a part of the event"
                                % (sid, r["part_ref"]))
                continue
            n = txt.count(r["quote"])
            raw_ix = r["occurrence_in_part"]
            if n == 0:
                problems.append("%s: quote does not locate" % sid)
                continue
            if n == 1:
                if raw_ix is not None:
                    problems.append("%s: unique quote carries an index" % sid)
                final = None
            else:
                if type(raw_ix) is not int or not 0 <= raw_ix <= n - 1:
                    problems.append("%s: raw index %r outside 0..%d"
                                    % (sid, raw_ix, n - 1))
                    continue
                final = raw_ix + 1
                locator.append(collections.OrderedDict([
                    ("source_id", sid), ("part_ref", r["part_ref"]),
                    ("quote", r["quote"]), ("raw_0_based", raw_ix),
                    ("final_1_based", final), ("occurrences", n)]))
            why = verify_occurrence(txt, r["quote"], final)
            if why:
                problems.append("%s: %s" % (sid, why))
            r["occurrence_in_part"] = final
    return rows, sidecar, raws, locator, problems


def main():
    os.path.isdir(OUT) or os.makedirs(OUT)
    recon = json.load(io.open(RECON, encoding="utf-8"))
    best = accepted()
    order = [e["source_id"] for e in json.load(io.open(
        X + "/inventory_review/package.manifest.json", encoding="utf-8"))["events"]]
    rows, sidecar, raws, locator, problems = derive(recon, best, order)

    # the artifact's own inventory must EQUAL the derivation, ignoring the one
    # locator translation this seam owns
    for sid in order:
        want = recon["proposed_inventory"].get(sid, [])
        got = rows.get(sid, [])
        if len(want) != len(got):
            problems.append("%s: derived %d rows, the artifact claims %d"
                            % (sid, len(got), len(want)))
            continue
        for w, g in zip(want, got):
            for f in ("source_id", "quote", "raw_label_or_claim",
                      "proposed_record_kind"):
                if w[f] != g[f]:
                    problems.append("%s: %s differs from the artifact" % (sid, f))
            if list(w["proposed_hard_classes"]) != list(g["proposed_hard_classes"]):
                problems.append("%s: tags differ from the artifact" % sid)

    records = [collections.OrderedDict((f, r[f]) for f in INV.RECORD_FIELDS)
               for sid in order for r in rows[sid]]
    counted = collections.Counter(r["proposed_record_kind"] for r in records)
    frozen = json.load(io.open(INV.INV, encoding="utf-8"))
    inventory = collections.OrderedDict([
        ("base_commit", INV.BASE_COMMIT),
        ("counts", collections.OrderedDict([
            ("events_covered", len({r["source_id"] for r in records})),
            ("proposed_lawful_abstention_controls",
             counted["lawful_abstention_control"]),
            ("proposed_negative_controls", counted["negative_control"]),
            ("proposed_real_items", counted["real_item"]),
            ("records", len(records)), ("source_events", len(order))])),
        ("note", frozen["note"]), ("records", records),
        ("schema", INV.SCHEMA), ("source_manifest", frozen["source_manifest"])])
    inv_text = json.dumps(inventory, indent=1, sort_keys=True)
    problems += INV.check(json.loads(inv_text))

    tags = collections.defaultdict(set)
    for r in records:
        for t in r["proposed_hard_classes"]:
            tags[t].add((r["source_id"], r["quote"], r["raw_label_or_claim"]))
    for t in INV.HARD_CLASSES:
        if len(tags[t]) < INV.TAG_FLOOR:
            problems.append("hard class %s has %d distinct rows, below the floor %d"
                            % (t, len(tags[t]), INV.TAG_FLOOR))

    if problems:
        io.open(OUT + "/refusal.json", "w", encoding="utf-8").write(
            json.dumps({"problems": problems}, indent=1))
        print("REFUSED before any sign packet: %d problem(s)" % len(problems))
        for p in problems[:8]:
            print("   %s" % p)
        raise SystemExit(1)
    if os.path.exists(OUT + "/refusal.json"):
        os.remove(OUT + "/refusal.json")

    side_text = json.dumps(collections.OrderedDict([
        ("schema", "pre-a2-inventory-adjudication-v1"),
        ("rows", sidecar),
        ("reviewed_reconciliation", collections.OrderedDict([
            ("path", os.path.relpath(RECON, S)), ("sha256", sha(
                io.open(RECON, encoding="utf-8").read())),
            ("resolutions", len(recon["resolutions"])),
            ("changes", len(recon["changes"])),
            ("locator_translations", locator)])),
        ("raw_replies", collections.OrderedDict((s, sha(raws[s])) for s in order)),
    ]), indent=1)
    val_text = json.dumps(collections.OrderedDict([
        ("validator", os.path.relpath(INV.__file__, "/home/faisal/EventMarketDB")),
        ("problems", []), ("records_checked", len(records)),
        ("hard_class_counts", {t: len(tags[t]) for t in INV.HARD_CLASSES}),
        ("tag_floor", INV.TAG_FLOOR)]), indent=1)
    for name, text in (("final_inventory.json", inv_text),
                       ("adjudication_sidecar.json", side_text),
                       ("validator_receipt.json", val_text)):
        io.open(OUT + "/" + name, "w", encoding="utf-8").write(text)

    prompts = P.prompts()
    sign_input = collections.OrderedDict([
        ("scope", "the pre-A2 benchmark source-item and control inventory only; "
                  "not the A3 drafting run and not the A4 completed answer key"),
        ("base_commit", INV.BASE_COMMIT),
        ("event_verdicts", collections.OrderedDict(
            (sid, sha(raws[sid])) for sid in order)),
        ("reviewed_reconciliation_sha256", sha(io.open(RECON, encoding="utf-8").read())),
        ("materialized", collections.OrderedDict([
            ("final_inventory_sha256", sha(inv_text)),
            ("adjudication_sidecar_sha256", sha(side_text)),
            ("validator_receipt_sha256", sha(val_text))])),
        ("counts", inventory["counts"]),
        ("hard_class_counts", {t: len(tags[t]) for t in INV.HARD_CLASSES}),
        ("event_turns", collections.OrderedDict(
            (sid, sha(prompts[sid])) for sid in order)),
        ("source_manifest", frozen["source_manifest"])])
    si_text = json.dumps(sign_input, indent=1)
    io.open(OUT + "/final_sign_input.json", "w", encoding="utf-8").write(si_text)

    # THE TWO NUMBERS COME FROM THEIR OWNERS, never from typing: the frozen
    # event set and the validator's own tag floor.
    tmpl = io.open(S + "/lock/signer_prompt.md", encoding="utf-8").read()
    prompt = (tmpl.replace("__EVENTS__", str(len(order)))
                  .replace("__FLOOR__", str(INV.TAG_FLOOR)) + si_text)
    if "__" in prompt.split("# Evidence")[0]:
        raise SystemExit("the signer prompt still carries an unfilled placeholder")
    io.open(OUT + "/final_sign_prompt.txt", "w", encoding="utf-8").write(prompt)
    plan = collections.OrderedDict([
        ("calls", 1), ("task", "final_sign"), ("state", "unmade"),
        ("model", MODEL), ("effort", EFFORT), ("agent_type", AGENT),
        ("transport", TRANSPORT), ("disallowed_tools", list(P.REVIEW_DISALLOWED)),
        ("max_output_tokens", os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS", "128000")),
        ("parent_session_id", "5ae9b86b-f0f6-4449-beee-9cac7cfa7200"),
        ("prompt_sha256", sha(prompt)), ("prompt_chars", len(prompt)),
        ("input_sha256", sha(si_text)),
        ("instruction_sha256", sha(io.open(MAILBOX + "/archive_CODEX_1342.md",
                                           encoding="utf-8").read())),
        ("retry", "one identical-prompt retry only for an answered invalid-JSON "
                  "or invalid-schema reply"),
        ("output", "{\"signed\": true|false, \"blocked\": null|string, "
                   "\"why\": string}")])
    io.open(OUT + "/sign_call_plan.json", "w", encoding="utf-8").write(
        json.dumps(plan, indent=1))

    print("final_inventory.json        %s" % sha(inv_text))
    print("adjudication_sidecar.json   %s" % sha(side_text))
    print("validator_receipt.json      %s" % sha(val_text))
    print("final_sign_input.json       %s" % sha(si_text))
    print("final_sign_prompt.txt       %s  (%d chars)" % (sha(prompt), len(prompt)))
    print("sign_call_plan.json         %s" % sha(json.dumps(plan, indent=1)))
    print("records %d over %d events | real %d / negative %d / abstention %d"
          % (len(records), inventory["counts"]["events_covered"],
             counted["real_item"], counted["negative_control"],
             counted["lawful_abstention_control"]))
    print("locator translations %d" % len(locator))
    for l in locator:
        print("   %s %s -> %s of %d" % (l["source_id"], l["raw_0_based"],
                                        l["final_1_based"], l["occurrences"]))
    print("FROZEN VALIDATOR PASS, floors:")
    for t in INV.HARD_CLASSES:
        print("   %-34s %3d" % (t, len(tags[t])))


if __name__ == "__main__":
    main()
