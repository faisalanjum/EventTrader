"""The final 196-item candidate and its frozen, unrun signer packet (Codex SEQ 1510 items 2-4,
corrected per SEQ 1511: no serialized key - the authoritative identity is the ordered exact raw
component shards, the bindings and the pinned loader, as F.lock defines it; strict JSON so a stray
Decimal raises; the composition owner's exact row maps in trusted data; the signer's own retry law;
the resolved-history definitions before the boundary).

Every owner is reused, none replaced: build_kfields_final_targeted.full_materialize
is the sole semantic materializer (the locked A4 owner's own materializer over the
bound base and the three bound correction rounds), build_kfields_final.counts /
key_problems validate, build_kfields_final.signer_prompt / render_signer render
the signer through the ONE signer owner with the frozen transport. A composed
event is never presented as one raw model reply: the signer sees its real
component raws (the bound base reply and the bound targeted reply) under one
composition header, and the provenance names both hashes. Nothing is repaired
here; any problem refuses before a packet exists. Write-once throughout.
"""
import collections, hashlib, io, json, os, sys
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
X = S + "/bench_1306/.claude/plans/Drivers/experiments"; H = X + "/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import a6_launch_freeze as A6, build_kfields_final as F, build_kfields_final_targeted as FT, build_kfields_key as K
import build_inventory_review as BIR, raw_transport as RT
RUNS = ("/tmp/a4_final_targeted_corr_run_1504", "/tmp/a4_final_targeted_corr2_run_1506", "/tmp/a4_final_targeted_corr3_run_1509")
DEFAULT_OUT = S + "/lock/final_key_candidate_1511"
SCHEMA = "a4-final-key-candidate/1511"
sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()
shaf = lambda p: sha(io.open(p, "rb").read())
def dumps(doc): return json.dumps(doc, indent=1, ensure_ascii=False)     # STRICT: a stray Decimal raises; no encoder, no preview
RESOLVED_HISTORY = "\n".join([
    "`record_kind_conflicts` are already-resolved differences between an item's proposed record kind and its final outcome.",
    "`phase1_ambiguities` are retained first-pass reports; an adjudicator's `ambiguity_note` records a settled judgment.",
    "Only live `open_issues`, validator or materializer problems, missing, duplicated or mis-mapped rows, group problems,",
    "or failed tag floors block the signature. Do not re-decide any meaning.",
])


def compose():
    """-> (key, sidecar, shards, raws, provenance, counts, problems) through the owners only."""
    for door, run in zip(FT.CORRECTION_DOORS, RUNS):            # every round must be the BOUND one
        if os.path.abspath(run) != FT._closed_run(door):
            raise ValueError("%s is not the bound %s run" % (run, door))
    shards, raws, prov, problems = FT.full_successor(*RUNS)
    key, sidecar, more = FT.full_materialize(*RUNS)
    problems = list(problems) + list(more) + FT.full_preservation_problems(*RUNS)
    counts = F.counts(key, sidecar)
    if counts["open_issues"]:
        problems.append("%d open issues block the candidate" % counts["open_issues"])
    if counts["tags_below_floor"]:
        problems.append("hard-class tags below the floor of %d: %s" % (BIR.CLASS_FLOOR, counts["tags_below_floor"]))
    problems += ["gold door: %s" % e for e in F.key_problems(key)]
    problems += map_problems(prov)
    return key, sidecar, shards, raws, prov, counts, problems


def map_problems(prov):
    """The composition owner's exported row maps, verified against the task
    owners' own row lists (an independent derivation): exact, complete, no
    duplicate, every replaced packet inside, nothing inferred from text."""
    b = FT._baseline()[0]
    full = {t["source_id"]: t["rows"] for t in F.event_tasks(b.evidence)}
    partial = {s: t["rows"] for s, t in FT._by_source(FT.DOOR).items()}
    bad = []
    for sid, e in prov["events"].items():
        if not e["composed"]:
            continue
        base, targeted = e.get("base_row_order"), e.get("targeted_row_order")
        if base != full.get(sid):
            bad.append("%s: composition map - base_row_order is not the full event's row order" % sid)
        if targeted != partial.get(sid):
            bad.append("%s: composition map - targeted_row_order is not the targeted task's row order" % sid)
        if base is None or targeted is None:
            continue
        if len(set(base)) != len(base) or len(set(targeted)) != len(targeted):
            bad.append("%s: composition map - a packet is duplicated" % sid)
        if not set(e["replaced"]) <= set(targeted) <= set(base):
            bad.append("%s: composition map - a replaced packet is outside the mapped rows" % sid)
    return bad


def composition_map(prov):
    return collections.OrderedDict((s, collections.OrderedDict([("replaced", e["replaced"]), ("base_origin", e["base_origin"]), ("base_raw_sha256", e["base_raw_sha256"]),
                                                                ("base_row_order", e["base_row_order"]), ("targeted_origin", e["targeted_origin"]), ("targeted_raw_sha256", e["targeted_raw_sha256"]),
                                                                ("targeted_row_order", e["targeted_row_order"])]))
                                   for s, e in prov["events"].items() if e["composed"])


def signer_head(prov):
    """Trusted text BEFORE the owner's own prompt (and so before its boundary):
    the resolved-history definitions and the exact composition map."""
    return ("[RESOLVED HISTORY]\n%s\n\n[COMPOSITION MAP]\n%s\n\n" % (RESOLVED_HISTORY, json.dumps(composition_map(prov), indent=1)))


def signer_shards(prov, raws):
    """The signer's shard list: one real raw per untouched event; for a composed
    event its two real component raws under one composition header. Hashes are
    the bindings' own; nothing is synthesized."""
    b = FT._baseline()[0]; base, braws, borigins, bad = F.v6_shards(b)
    if bad:
        raise ValueError("the signed baseline does not re-prove: %s" % bad[:2])
    targeted, traws, torigins, tbad = FT.successor_shards(*RUNS)
    if tbad:
        raise ValueError("the targeted results do not re-prove: %s" % tbad[:2])
    out, texts = [], collections.OrderedDict()
    for sid, ev in prov["events"].items():
        if not ev["composed"]:
            out.append((sid, sha(raws[sid]))); texts[sid] = raws[sid]
            continue
        for part, origin, raw in (("base", ev["base_origin"], braws[sid]), ("targeted", ev["targeted_origin"], traws[sid])):
            label = "%s [COMPOSED: %s component, origin %s, replaced %s]" % (sid, part, origin, ",".join(p.split("#")[1] for p in ev["replaced"]))
            assert sha(raw) == ev["%s_raw_sha256" % part]
            out.append((label, sha(raw))); texts[label] = raw
    return out, texts


def build(out_dir=DEFAULT_OUT):
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    key, sidecar, shards, raws, prov, counts, problems = compose()
    if problems:
        RT.write_new(out_dir + "/refusal.json", dumps({"problems": problems}))
        raise SystemExit("REFUSED before any candidate: %s" % problems[:5])
    fc = FT.full_counts(*RUNS)
    bindings = collections.OrderedDict((d, collections.OrderedDict([("path", FT._phase(d)["binding"]), ("sha256", shaf(FT._phase(d)["binding"])), ("run_dir", FT._closed_run(d))]))
                                       for d in (FT.DOOR,) + FT.CORRECTION_DOORS)
    sh, texts = signer_shards(prov, raws)
    key_shards = []
    for sid, e in prov["events"].items():
        comps = ([collections.OrderedDict([("part", "whole"), ("origin", e["origin"]), ("sha256", e["raw_sha256"])])] if not e["composed"] else
                 [collections.OrderedDict([("part", "base"), ("origin", e["base_origin"]), ("sha256", e["base_raw_sha256"]), ("row_order", e["base_row_order"])]),
                  collections.OrderedDict([("part", "targeted"), ("origin", e["targeted_origin"]), ("sha256", e["targeted_raw_sha256"]), ("row_order", e["targeted_row_order"]), ("replaced", e["replaced"])])])
        key_shards.append(collections.OrderedDict([("source_id", sid), ("composed", e["composed"]), ("components", comps)]))
    key_text = dumps(collections.OrderedDict([("schema", SCHEMA), ("authoritative", True),
                                              ("identity", "the ORDERED exact raw component shards below, the four bindings and the pinned loader - as build_kfields_final.lock defines a key; no parsed Decimal fact is serialized anywhere; a composed event is a composition of its bound base and targeted replies, never one raw model reply"),
                                              ("loader", collections.OrderedDict([("module", "build_kfields_final_targeted"), ("entry", "full_materialize"), ("sha256", shaf(FT.__file__))])),
                                              ("materializer", collections.OrderedDict([("module", "build_kfields_final"), ("entry", "materialize"), ("sha256", shaf(F.__file__))])),
                                              ("bindings", bindings), ("runs", list(RUNS)), ("counts", fc), ("key_shards", key_shards)]))
    side_text = dumps(collections.OrderedDict([("schema", SCHEMA + "/sidecar"), ("sidecar", sidecar)]))
    prov_text = dumps(collections.OrderedDict([("schema", SCHEMA + "/provenance"), ("bindings", bindings), ("runs", list(RUNS)), ("rounds", list(FT.CORRECTION_DOORS)),
                                               ("origins", collections.OrderedDict((s, o) for s, o in FT.successor_shards(*RUNS)[2].items())), ("provenance", prov)]))
    val_text = dumps(collections.OrderedDict([("schema", SCHEMA + "/validator"), ("materializer", "build_kfields_final_targeted.full_materialize -> build_kfields_final.materialize"),
                                              ("problems", []), ("full_preservation_problems", []), ("key_problems", []), ("counts", counts), ("full_counts", fc),
                                              ("class_floor", BIR.CLASS_FLOOR), ("sequential_floor", BIR.SEQUENTIAL_FLOOR)]))
    for name, text in (("key_identity.json", key_text), ("sidecar.json", side_text), ("provenance.json", prov_text), ("validator_receipt.json", val_text)):
        RT.write_new(os.path.join(out_dir, name), text)
    # the signer packet through the ONE signer owner, frozen, unrun
    ledger = A6.ledger()[0]
    block = collections.OrderedDict([("candidate", collections.OrderedDict([("key_identity_sha256", sha(key_text)), ("sidecar_sha256", sha(side_text)), ("provenance_sha256", sha(prov_text)), ("validator_receipt_sha256", sha(val_text))])),
                                     ("full_counts", fc), ("counts", counts), ("bindings", collections.OrderedDict((d, v["sha256"]) for d, v in bindings.items())),
                                     ("composition_map", composition_map(prov))])
    prompt = signer_head(prov) + F.signer_prompt(sh, block, texts)       # the owner's prompt, with the trusted head before it (the owner's own decision-prefix pattern)
    lines = F.render_signer(sh, block, texts, 1).split("\n")             # the owner's launcher, its PROMPT line swapped for the same bytes
    F._swap(lines, "const PROMPT = ", "const PROMPT = " + json.dumps(prompt), "PROMPT")
    script = "\n".join(lines)
    size = len(script.encode("utf-8"))
    if size >= K.TRANSPORT_LIMIT:
        raise SystemExit("the rendered signer is %d bytes, at or over %d" % (size, K.TRANSPORT_LIMIT))
    budget = collections.OrderedDict([("before", ledger), ("primaries", 1), ("retry_cap", F.MAX_ATTEMPTS - 1), ("after_clean", ledger + 1), ("worst", ledger + F.MAX_ATTEMPTS), ("ceiling", 6000)])
    gate = collections.OrderedDict([("success", "read_signature(text) returns an object with signed true and blocked [] (build_kfields_final.read_signature)"),
                                    ("failure", "signed false with nonempty blocked - a lawful refusal, FINAL, never retried"),
                                    ("transport_no_answer", "a genuine transport/no-answer refusal is retained and reported and is FINAL: no second call (build_kfields_final.RETRYABLE)"),
                                    ("retry", "at most one identical-bytes retry, only for a structurally invalid reply (invalid_response: build_kfields_final.read_signature refuses the shape); never for meaning")])
    retry_law = collections.OrderedDict([("owner", "build_kfields_final.RETRYABLE"), ("retryable", list(F.RETRYABLE))])
    manifest = collections.OrderedDict([("schema", SCHEMA + "/signer"), ("door", "a4_final_key_signature"), ("authority", "Codex SEQ 1510 item 4"), ("state", "frozen, unrun"),
                                        ("signer_owner", collections.OrderedDict([("module", "build_kfields_final"), ("sha256", shaf(F.__file__)), ("functions", ["signer_prompt", "render_signer", "read_signature"])])),
                                        ("materializer_owner", collections.OrderedDict([("module", "build_kfields_final_targeted"), ("sha256", shaf(FT.__file__))])),
                                        ("transport", K._transport_block()), ("label", "a4-final-signer"),
                                        ("shards", [collections.OrderedDict([("shard", s), ("sha256", h)]) for s, h in sh]),
                                        ("prompt_sha256", sha(prompt)), ("prompt_bytes", len(prompt.encode("utf-8"))), ("script_sha256", sha(script)), ("script_bytes", size), ("transport_limit_bytes", K.TRANSPORT_LIMIT),
                                        ("head_sha256", sha(signer_head(prov))), ("count_block_sha256", sha(json.dumps(block, indent=1))),
                                        ("composition_map_events", len(composition_map(prov))), ("budget", budget), ("retry_law", retry_law), ("gate", gate)])
    sd = os.path.join(out_dir, "signer"); os.path.isdir(sd) or os.makedirs(sd)
    RT.write_new(sd + "/signer_prompt.txt", prompt); RT.write_new(sd + "/final_sign.attempt1.js", script)
    RT.write_new(sd + "/signer.manifest.json", dumps(manifest))
    return collections.OrderedDict([("key_identity.json", sha(key_text)), ("sidecar.json", sha(side_text)), ("provenance.json", sha(prov_text)), ("validator_receipt.json", sha(val_text)),
                                    ("signer_prompt.txt", sha(prompt)), ("final_sign.attempt1.js", sha(script)), ("signer.manifest.json", sha(dumps(manifest)))]), fc, counts, manifest


def verify(out_dir=DEFAULT_OUT):
    """Re-derive every candidate byte from the live owners; any difference refuses."""
    fresh = os.path.join(out_dir, "_verify_tmp"); os.path.isdir(fresh) and __import__("shutil").rmtree(fresh)
    hashes, _fc, _c, _m = build(fresh)
    bad = [n for n, h in hashes.items() if shaf(os.path.join(out_dir, n) if not n.startswith(("signer_prompt", "final_sign", "signer.manifest")) else os.path.join(out_dir, "signer", n)) != h]
    __import__("shutil").rmtree(fresh)
    return bad


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    hashes, fc, counts, manifest = build(out)
    for n, h in hashes.items():
        print("%-28s %s" % (n, h))
    print("full_counts", json.dumps(fc)); print("open_issues", counts["open_issues"], "tags_below_floor", counts["tags_below_floor"], "rows_accounted", counts["rows_accounted"])
    print("signer prompt bytes", manifest["prompt_bytes"], "script bytes", manifest["script_bytes"], "shards", len(manifest["shards"]), "budget", json.dumps(manifest["budget"]))
