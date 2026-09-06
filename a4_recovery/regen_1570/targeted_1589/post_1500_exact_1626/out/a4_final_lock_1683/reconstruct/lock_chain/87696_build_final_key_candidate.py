import io, sys
S = sys.argv[1]; p = S + "/lock/build_final_key_candidate.py"; s = io.open(p, encoding="utf-8").read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]; s = s.replace(old, new)
rep('''"""The final 196-item candidate and its frozen, unrun signer packet (Codex SEQ 1510 items 2-4).''',
    '''"""The final 196-item candidate and its frozen, unrun signer packet (Codex SEQ 1510 items 2-4,
corrected per SEQ 1511: no serialized key - the authoritative identity is the ordered exact raw
component shards, the bindings and the pinned loader, as F.lock defines it; strict JSON so a stray
Decimal raises; the composition owner's exact row maps in trusted data; the signer's own retry law;
the resolved-history definitions before the boundary).''')
rep('''DEFAULT_OUT = S + "/lock/final_key_candidate_1510"
SCHEMA = "a4-final-key-candidate/1510"
sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()
shaf = lambda p: sha(io.open(p, "rb").read())
def dumps(doc): return json.dumps(doc, indent=1, ensure_ascii=False, default=str)''',
    '''DEFAULT_OUT = S + "/lock/final_key_candidate_1511"
SCHEMA = "a4-final-key-candidate/1511"
sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()
shaf = lambda p: sha(io.open(p, "rb").read())
def dumps(doc): return json.dumps(doc, indent=1, ensure_ascii=False)     # STRICT: a stray Decimal raises; no encoder, no preview
RESOLVED_HISTORY = "\\n".join([
    "`record_kind_conflicts` are already-resolved differences between an item's proposed record kind and its final outcome.",
    "`phase1_ambiguities` are retained first-pass reports; an adjudicator's `ambiguity_note` records a settled judgment.",
    "Only live `open_issues`, validator or materializer problems, missing, duplicated or mis-mapped rows, group problems,",
    "or failed tag floors block the signature. Do not re-decide any meaning.",
])''')
rep('''    problems += ["gold door: %s" % e for e in F.key_problems(key)]
    return key, sidecar, shards, raws, prov, counts, problems''',
    '''    problems += ["gold door: %s" % e for e in F.key_problems(key)]
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
    return bad''')
rep('''def signer_shards(prov, raws):''', '''def composition_map(prov):
    return collections.OrderedDict((s, collections.OrderedDict([("replaced", e["replaced"]), ("base_origin", e["base_origin"]), ("base_raw_sha256", e["base_raw_sha256"]),
                                                                ("base_row_order", e["base_row_order"]), ("targeted_origin", e["targeted_origin"]), ("targeted_raw_sha256", e["targeted_raw_sha256"]),
                                                                ("targeted_row_order", e["targeted_row_order"])]))
                                   for s, e in prov["events"].items() if e["composed"])


def signer_head(prov):
    """Trusted text BEFORE the owner's own prompt (and so before its boundary):
    the resolved-history definitions and the exact composition map."""
    return ("[RESOLVED HISTORY]\\n%s\\n\\n[COMPOSITION MAP]\\n%s\\n\\n" % (RESOLVED_HISTORY, json.dumps(composition_map(prov), indent=1)))


def signer_shards(prov, raws):''')
rep('''    key_text = dumps(collections.OrderedDict([("schema", SCHEMA), ("composition", "the signed V6 baseline through the locked owner with the bound targeted corrections overlaid by packet id; a composed event is a composition of its bound base and targeted replies, never one raw model reply"),
                                              ("counts", fc), ("events", len(key)), ("key", key)]))''',
    '''    sh, texts = signer_shards(prov, raws)
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
                                              ("bindings", bindings), ("runs", list(RUNS)), ("counts", fc), ("key_shards", key_shards)]))''')
rep('''    for name, text in (("final_key.json", key_text), ("sidecar.json", side_text), ("provenance.json", prov_text), ("validator_receipt.json", val_text)):
        RT.write_new(os.path.join(out_dir, name), text)
    # the signer packet through the ONE signer owner, frozen, unrun
    sh, texts = signer_shards(prov, raws)
    ledger = A6.ledger()[0]''', '''    for name, text in (("key_identity.json", key_text), ("sidecar.json", side_text), ("provenance.json", prov_text), ("validator_receipt.json", val_text)):
        RT.write_new(os.path.join(out_dir, name), text)
    # the signer packet through the ONE signer owner, frozen, unrun
    ledger = A6.ledger()[0]''')
rep('''    block = collections.OrderedDict([("candidate", collections.OrderedDict([("final_key_sha256", sha(key_text)), ("sidecar_sha256", sha(side_text)), ("provenance_sha256", sha(prov_text)), ("validator_receipt_sha256", sha(val_text))])),
                                     ("full_counts", fc), ("counts", counts), ("bindings", collections.OrderedDict((d, v["sha256"]) for d, v in bindings.items())),
                                     ("composed_events", collections.OrderedDict((s, collections.OrderedDict([("replaced", e["replaced"]), ("base_raw_sha256", e["base_raw_sha256"]), ("targeted_raw_sha256", e["targeted_raw_sha256"])]))
                                                                                for s, e in prov["events"].items() if e["composed"]))])
    prompt = F.signer_prompt(sh, block, texts); script = F.render_signer(sh, block, texts, 1)''',
    '''    block = collections.OrderedDict([("candidate", collections.OrderedDict([("key_identity_sha256", sha(key_text)), ("sidecar_sha256", sha(side_text)), ("provenance_sha256", sha(prov_text)), ("validator_receipt_sha256", sha(val_text))])),
                                     ("full_counts", fc), ("counts", counts), ("bindings", collections.OrderedDict((d, v["sha256"]) for d, v in bindings.items())),
                                     ("composition_map", composition_map(prov))])
    prompt = signer_head(prov) + F.signer_prompt(sh, block, texts)       # the owner's prompt, with the trusted head before it (the owner's own decision-prefix pattern)
    lines = F.render_signer(sh, block, texts, 1).split("\\n")             # the owner's launcher, its PROMPT line swapped for the same bytes
    F._swap(lines, "const PROMPT = ", "const PROMPT = " + json.dumps(prompt), "PROMPT")
    script = "\\n".join(lines)''')
rep('''    gate = collections.OrderedDict([("success", "read_signature(text) returns an object with signed true and blocked [] (build_kfields_final.read_signature)"),
                                    ("failure", "signed false with nonempty blocked - a lawful refusal, never retried"),
                                    ("retry", "at most one identical-bytes retry, only for transport_no_answer or a structurally invalid reply (build_kfields_final.read_signature refuses the shape); never for meaning")])''',
    '''    gate = collections.OrderedDict([("success", "read_signature(text) returns an object with signed true and blocked [] (build_kfields_final.read_signature)"),
                                    ("failure", "signed false with nonempty blocked - a lawful refusal, FINAL, never retried"),
                                    ("transport_no_answer", "a genuine transport/no-answer refusal is retained and reported and is FINAL: no second call (build_kfields_final.RETRYABLE)"),
                                    ("retry", "at most one identical-bytes retry, only for a structurally invalid reply (invalid_response: build_kfields_final.read_signature refuses the shape); never for meaning")])
    retry_law = collections.OrderedDict([("owner", "build_kfields_final.RETRYABLE"), ("retryable", list(F.RETRYABLE))])''')
rep('''                                        ("count_block_sha256", sha(json.dumps(block, indent=1))), ("budget", budget), ("gate", gate)])''',
    '''                                        ("head_sha256", sha(signer_head(prov))), ("count_block_sha256", sha(json.dumps(block, indent=1))),
                                        ("composition_map_events", len(composition_map(prov))), ("budget", budget), ("retry_law", retry_law), ("gate", gate)])''')
rep('''    return collections.OrderedDict([("final_key.json", sha(key_text)), ("sidecar.json", sha(side_text)),''', '''    return collections.OrderedDict([("key_identity.json", sha(key_text)), ("sidecar.json", sha(side_text)),''')
assert "default=str" not in s and "final_key.json" not in s
io.open(p, "w", encoding="utf-8").write(s); print("builder v2 written")
