import io, sys
H = sys.argv[1]
p = H + "/build_kfields_final_targeted.py"
s = io.open(p, encoding="utf-8").read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:80])
    s = s.replace(old, new)

# ---- constants: the second round
rep('''CORR_LEAD_KEYS = ("lead_id", "origin", "sha256", "reply")
''', '''CORR_LEAD_KEYS = ("lead_id", "origin", "sha256", "reply")

# Codex SEQ 1505: the second correction round over exactly the events whose
# accepted shard still carries an open issue. Its own package, budget receipt
# and review receipt; everything else is the correction phase's.
CORR2_DOOR = "a4_final_targeted_correction_2"
CORR2_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr2_1505")
CORR2_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1505.json"
CORR2_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1505.json")
''')

# ---- operation cache
rep('''            _primary_cached.cache_clear()
''', '''            _bound_cached.cache_clear()
''')

# ---- phase table: binding + payload per door; the rounds from the table
rep('''    """THE two phases this wrapper serves, resolved from module globals at
    call time. The same lifecycle serves both; only what a phase genuinely
    owns differs - its door, package, budget receipt, population, prompt,
    launcher, leads, payload shape and sentence."""
    if door in (None, DOOR):
        return {"door": DOOR, "pkg_dir": PKG_DIR, "manifest": MANIFEST_NAME,
                "prefix_name": PREFIX_NAME, "budget_receipt": BUDGET_RECEIPT,
                "tasks": event_tasks, "prompt": final_prompt,
                "launcher": render_launcher, "leads": event_leads,
                "prefix": prompt_prefix, "control": truthful_control,
                "sentence": input_sentence, "marks": PREFIX_MARKS,
                "payload_keys": PAYLOAD_KEYS, "lead_origins": LEAD_ORIGINS,
                "lead_keys": ("lead_id", "row_index", "origin", "sha256", "reply"),
                "derived_from": _derived_from}
    if door == CORR_DOOR:
        return {"door": CORR_DOOR, "pkg_dir": CORR_PKG_DIR,
                "manifest": CORR_MANIFEST_NAME, "prefix_name": CORR_PREFIX_NAME,
                "budget_receipt": CORR_BUDGET_RECEIPT,
                "tasks": correction_tasks, "prompt": correction_prompt,
                "launcher": render_correction_launcher, "leads": correction_leads,
                "prefix": correction_prefix, "control": correction_control,
                "sentence": correction_input_sentence, "marks": CORR_PREFIX_MARKS,
                "payload_keys": CORR_PAYLOAD_KEYS,
                "lead_origins": (CORR_LEAD_ORIGIN,), "lead_keys": CORR_LEAD_KEYS,
                "derived_from": _correction_derived_from}
    raise ValueError("%r is not a door of this wrapper" % (door,))
''', '''    """THE phases this wrapper serves - the primary and each correction round
    - resolved from module globals at call time. The same lifecycle serves
    all of them; only what a phase genuinely owns differs - its door,
    package, budget receipt, binding, population, prompt, launcher, leads,
    payload shape and sentence."""
    if door in (None, DOOR):
        return {"door": DOOR, "pkg_dir": PKG_DIR, "manifest": MANIFEST_NAME,
                "prefix_name": PREFIX_NAME, "budget_receipt": BUDGET_RECEIPT,
                "binding": BINDING,
                "tasks": event_tasks, "prompt": final_prompt,
                "launcher": render_launcher, "leads": event_leads,
                "payload": _payload,
                "prefix": prompt_prefix, "control": truthful_control,
                "sentence": input_sentence, "marks": PREFIX_MARKS,
                "payload_keys": PAYLOAD_KEYS, "lead_origins": LEAD_ORIGINS,
                "lead_keys": ("lead_id", "row_index", "origin", "sha256", "reply"),
                "derived_from": _derived_from}
    if door in _ROUNDS:
        r, P = _ROUNDS[door], functools.partial
        earlier = CORRECTION_DOORS[:CORRECTION_DOORS.index(door)]
        return {"door": door, "pkg_dir": r["pkg_dir"],
                "manifest": CORR_MANIFEST_NAME, "prefix_name": CORR_PREFIX_NAME,
                "budget_receipt": r["budget_receipt"], "binding": r["binding"],
                "tasks": P(correction_tasks, door),
                "prompt": P(correction_prompt, door=door),
                "launcher": P(render_correction_launcher, door=door),
                "leads": P(correction_leads, door=door),
                "payload": P(correction_payload, door=door),
                "prefix": correction_prefix, "control": correction_control,
                "sentence": correction_input_sentence, "marks": CORR_PREFIX_MARKS,
                "payload_keys": CORR_PAYLOAD_KEYS,
                "lead_origins": (CORR_LEAD_ORIGIN,) + tuple(_ROUNDS[d]["origin"] for d in earlier),
                "lead_keys": CORR_LEAD_KEYS,
                "derived_from": P(_correction_derived_from, door)}
    raise ValueError("%r is not a door of this wrapper" % (door,))
''')

# ---- manifest dispatch
rep('''    if door not in (None, DOOR):
        return _correction_manifest()
''', '''    if door not in (None, DOOR):
        return _correction_manifest(door)
''')

# ---- prepare
rep('''def prepare_correction_run(out_dir):
    return prepare_run(out_dir, CORR_DOOR)
''', '''def prepare_correction_run(out_dir, door=CORR_DOOR):
    return prepare_run(out_dir, door)
''')

# ---- cross-phase freshness
rep('''    if ph["door"] == CORR_DOOR and _closed_run():   # freshness is across PHASES (the locked
        r, a, m, q = F._spent_identities_uncached(_closed_run())   # owner's law): no primary identity
        runs |= r; agents |= a; responses |= m; requests |= q       # may serve a correction call
''', '''    for other in _DOORS:                         # freshness is across PHASES (the locked owner's
        if other != ph["door"] and _closed_run(other):   # law): no identity of another phase's
            r, a, m, q = F._spent_identities_uncached(_closed_run(other))   # bound run may serve this call
            runs |= r; agents |= a; responses |= m; requests |= q
''')

# ---- accepted_shards over every door, closed history per door
rep('''        if not isinstance(fin, dict) or fin.get("door") not in (DOOR, CORR_DOOR) \\
                or fin.get("version") != VERSION:''',
    '''        if not isinstance(fin, dict) or fin.get("door") not in _DOORS \\
                or fin.get("version") != VERSION:''')
rep('''            # THE BOUND PRIMARY IS CLOSED HISTORY: proved against its pinned package
            closed = _closed_run()
            if os.path.abspath(run_dir) == closed:
                pinned = _closed_pins(base)
                bad += _closed_receipt_problems(base, receipt, 1, pinned)
                prompt_of = lambda task, _p=pinned: _pinned_prompt(_p["package_dir"], task)   # noqa: E731
''', '''            # A BOUND RUN IS CLOSED HISTORY: proved against its pinned package
            closed = _closed_run(ph["door"])
            if os.path.abspath(run_dir) == closed:
                pinned = _closed_pins(base, ph["door"])
                bad += _closed_receipt_problems(base, receipt, 1, pinned, ph["door"])
                prompt_of = lambda task, _p=pinned, _d=ph["door"]: _pinned_prompt(_p["package_dir"], task, _d)   # noqa: E731
''')

# ---- the binding section, keyed by door
rep('''# ------------------------------------ the completed primary, bound and counted --
# Codex SEQ 1501 item 1: the targeted-run binding/pointer pattern over THIS
# lifecycle. The immutable binding decides which attempts exist, what their
# receipt, finalization, every raw/proved file and canonical raw tree ARE, and
# which package they ran under; a6_launch_freeze.ledger() only records the
# proved row. A FINALIZED run whose package has since moved on (this wrapper
# binds its own bytes, so every later change moves it) is CLOSED HISTORY: it
# is proved against the pinned package, never the live derivation - the
# locked owner's own law (build_kfields_final._receipt_still_the_proved_one).
''', '''# ---------------------------------- the completed runs, bound and counted --
# Codex SEQ 1501 item 1 / SEQ 1505 item 1: the targeted-run binding/pointer
# pattern over THIS lifecycle, one binding per door. The immutable binding
# decides which attempts exist, what their receipt, finalization, every
# raw/proved file and canonical raw tree ARE, and which package they ran
# under; a6_launch_freeze.ledger() only records the proved row. A FINALIZED
# run whose package has since moved on (this wrapper binds its own bytes, so
# every later change moves it) is CLOSED HISTORY: it is proved against the
# pinned package, never the live derivation - the locked owner's own law
# (build_kfields_final._receipt_still_the_proved_one).
''')
rep('''def write_binding(run_dir, pkg_dir):
    """Freeze the accepted primary ONCE, with the package its receipt names by
    hash. Write-once through the transport's owner; never rewritten."""
    run_dir = os.path.abspath(run_dir)
    rec = _load(os.path.join(run_dir, K.RECEIPT_NAME))
    man = os.path.join(pkg_dir, MANIFEST_NAME)
''', '''def write_binding(run_dir, pkg_dir, door=None):
    """Freeze one door's finalized run ONCE, with the package its receipt
    names by hash. Write-once through the transport's owner; never rewritten."""
    ph = _phase(door)
    run_dir = os.path.abspath(run_dir)
    rec = _load(os.path.join(run_dir, K.RECEIPT_NAME))
    man = os.path.join(pkg_dir, ph["manifest"])
''')
rep('''            ("prefix_sha256", INV.sha_file(os.path.join(pkg_dir, PREFIX_NAME)))])),
        ("attempts", attempts)])
    RT.write_new(BINDING, json.dumps(doc, indent=1))
    return doc


def _closed_run():
    """The bound primary run's directory, or None before any binding."""
    if not os.path.isfile(BINDING):
        return None
    return os.path.abspath(_load(BINDING)["run_dir"])


def _closed_pins(base):
    """The pinned package of the bound run, re-measured: dir, manifest doc."""
    pkg = _load(BINDING)["package"]
    man = os.path.join(pkg["dir"], MANIFEST_NAME)
    if not os.path.isfile(man) or INV.sha_file(man) != pkg["manifest_sha256"]:
        raise ValueError("the pinned package %s is not the bound one" % pkg["dir"])
    if INV.sha_file(os.path.join(pkg["dir"], PREFIX_NAME)) != pkg["prefix_sha256"]:
        raise ValueError("the pinned prefix is not the bound one")
    return {"package_dir": pkg["dir"], "manifest": _load(man),
            "manifest_sha256": pkg["manifest_sha256"]}


def _pinned_prompt(package_dir, task):
    """The prompt a CLOSED run received: the package's shipped prefix bytes
    plus the payload derived from the immutable bound evidence."""
    return K._read(os.path.join(package_dir, PREFIX_NAME)) \\
        + json.dumps(_payload(task), indent=1)
''', '''            ("prefix_sha256", INV.sha_file(os.path.join(pkg_dir, ph["prefix_name"])))])),
        ("attempts", attempts)])
    RT.write_new(ph["binding"], json.dumps(doc, indent=1))
    return doc


def _closed_run(door=None):
    """One door's bound run directory, or None before its binding."""
    binding = _phase(door)["binding"]
    if not os.path.isfile(binding):
        return None
    return os.path.abspath(_load(binding)["run_dir"])


def _closed_pins(base, door=None):
    """The pinned package of one door's bound run, re-measured: dir, manifest doc."""
    ph = _phase(door)
    pkg = _load(ph["binding"])["package"]
    man = os.path.join(pkg["dir"], ph["manifest"])
    if not os.path.isfile(man) or INV.sha_file(man) != pkg["manifest_sha256"]:
        raise ValueError("the pinned package %s is not the bound one" % pkg["dir"])
    if INV.sha_file(os.path.join(pkg["dir"], ph["prefix_name"])) != pkg["prefix_sha256"]:
        raise ValueError("the pinned prefix is not the bound one")
    return {"package_dir": pkg["dir"], "manifest": _load(man),
            "manifest_sha256": pkg["manifest_sha256"]}


def _pinned_prompt(package_dir, task, door=None):
    """The prompt a CLOSED run received: the package's shipped prefix bytes
    plus the payload derived from the immutable bound evidence."""
    ph = _phase(door)
    return K._read(os.path.join(package_dir, ph["prefix_name"])) \\
        + json.dumps(ph["payload"](task), indent=1)
''')
rep('''def _closed_receipt_problems(base, rec, attempt, pinned):
    """The receipt of closed history must be exactly what the PINNED package
    derived; every prompt must be the pinned prefix plus the bound payload;
    every stored script must be the pinned launcher."""
    man, bad = pinned["manifest"], []
    by_task = {r["source_id"]: r for r in man["tasks"]}
    tasks = _by_source(DOOR)
''', '''def _closed_receipt_problems(base, rec, attempt, pinned, door=None):
    """The receipt of closed history must be exactly what the PINNED package
    derived; every prompt must be the pinned prefix plus the bound payload;
    every stored script must be the pinned launcher."""
    ph = _phase(door)
    man, bad = pinned["manifest"], []
    by_task = {r["source_id"]: r for r in man["tasks"]}
    tasks = _by_source(ph["door"])
''')
rep('''        ("run_id", os.path.basename(os.path.abspath(base))),
        ("door", DOOR), ("version", VERSION), ("attempt", attempt),
        ("allowed", allowed), ("parent", parent),
        ("transport", K._transport_block()),
        ("manifest_sha256", pinned["manifest_sha256"]),''',
    '''        ("run_id", os.path.basename(os.path.abspath(base))),
        ("door", ph["door"]), ("version", VERSION), ("attempt", attempt),
        ("allowed", allowed), ("parent", parent),
        ("transport", K._transport_block()),
        ("manifest_sha256", pinned["manifest_sha256"]),''')
rep('''        if _sha(_pinned_prompt(pinned["package_dir"], tasks[sid])) != want["prompts"][sid]:''',
    '''        if _sha(_pinned_prompt(pinned["package_dir"], tasks[sid], ph["door"])) != want["prompts"][sid]:''')
rep('''def proved_spend(run_dir):
    """READ-ONLY. The calls the FINALIZED primary actually spent, re-proved:''',
    '''def proved_spend(run_dir, door=None):
    """READ-ONLY. The calls one door's FINALIZED bound run actually spent, re-proved:''')
rep('''    binding = _load(BINDING)
    if binding.get("schema") != BINDING_SCHEMA or \\
            binding.get("run_dir") != os.path.abspath(run_dir):
        raise ValueError("%s is not the bound final-targeted run %s"
                         % (run_dir, binding.get("run_dir")))
''', '''    ph = _phase(door)
    binding = _load(ph["binding"])
    if binding.get("schema") != BINDING_SCHEMA or \\
            binding.get("run_dir") != os.path.abspath(run_dir):
        raise ValueError("%s is not the bound %s run %s"
                         % (run_dir, ph["door"], binding.get("run_dir")))
''')
rep('''    pinned = _closed_pins(run_dir)
    tasks = _by_source(DOOR)
    rows = []
''', '''    pinned = _closed_pins(run_dir, ph["door"])
    tasks = _by_source(ph["door"])
    rows = []
''')
rep('''        bad = _closed_receipt_problems(base, rec, attempt, pinned)
        allowed = list(rec.get("allowed") or [])''',
    '''        bad = _closed_receipt_problems(base, rec, attempt, pinned, ph["door"])
        allowed = list(rec.get("allowed") or [])''')
rep('''                ("door", fin.get("door"), DOOR),
                ("version", fin.get("version"), VERSION),
                ("run_id", fin.get("run_id"), rec.get("run_id")),''',
    '''                ("door", fin.get("door"), ph["door"]),
                ("version", fin.get("version"), VERSION),
                ("run_id", fin.get("run_id"), rec.get("run_id")),''')
rep('''        proved, problems = run_evidence(
            base, rec, lambda t, _p=pinned: _pinned_prompt(_p["package_dir"], t),
            lambda t, a, _b=base: _pinned_script(_b, t, a))''',
    '''        proved, problems = run_evidence(
            base, rec, lambda t, _p=pinned, _d=ph["door"]: _pinned_prompt(_p["package_dir"], t, _d),
            lambda t, a, _b=base: _pinned_script(_b, t, a))''')
rep('''                _obj, why = read_shard(text, tasks[label], event_leads(tasks[label]))
                derived[label] = "valid" if not why else "invalid_response"''',
    '''                _obj, why = read_shard(text, tasks[label], ph["leads"](tasks[label]))
                derived[label] = "valid" if not why else "invalid_response"''')

# ---- the correction phase: rounds
rep('''# --------------------------------------------------- the correction phase --
# Codex SEQ 1501 items 2-7: the locked owner's decision-correction PATTERN
# through this one wrapper - the same rules first, the complete event, the
# affected rows, the exact primary settlement as an untrusted lead and the
# reviewer's findings LAST; the same reader, materializer and raw lifecycle.
# The population is DERIVED from one bound review receipt: every event whose
# receipt entry is nonempty, where the receipt must carry the primary's own
# open issues verbatim and may add reviewer findings that point at existing
# rules. No semantic string decides anything here.
@functools.lru_cache(maxsize=None)
def _primary_cached(binding_sha):
    """The accepted primary shards and raw texts, proved once per operation:
    the binding identity through proved_spend, the parse through the shared
    accepted_shards over the pinned prefix. Keyed by the immutable binding."""
    del binding_sha
    run = _closed_run()
    if run is None:
        raise ValueError("no primary run is bound")
    proved_spend(run)
    shards, raws, bad = accepted_shards(run)
    if bad:
        raise ValueError("the bound primary does not re-prove: %s" % bad[:2])
    return shards, raws


def primary_shards():
    """Callers get COPIES; nothing they mutate reaches the cache."""
    shards, raws = _primary_cached(INV.sha_file(BINDING))
    return (collections.OrderedDict((k, copy.deepcopy(v)) for k, v in shards.items()),
            collections.OrderedDict(raws))


def _review_receipt():
    doc = _load(REVIEW_RECEIPT)
    if doc.get("schema") != REVIEW_SCHEMA:
        raise ValueError("the review receipt is not of this schema")
    pb = doc.get("primary_binding") or {}
    if pb.get("binding_path") != BINDING or pb.get("binding_sha256") != INV.sha_file(BINDING) \\
            or pb.get("run_dir") != _closed_run():
        raise ValueError("the review receipt is not bound to the accepted primary")
    return doc


def correction_events():
    """THE population, derived: every primary event whose bound review entry
    is nonempty, in primary order. The receipt must carry each event's own
    open issues verbatim and completely; a reviewer finding must be a
    nonempty text naming at least one existing rule."""
    rec = _review_receipt()
    shards, _raws = primary_shards()
    findings = rec.get("findings") or {}
    order = [t["source_id"] for t in event_tasks()]
    for sid in findings:
''', '''# --------------------------------------------------- the correction phase --
# Codex SEQ 1501 items 2-7 / SEQ 1505 items 2-3: the locked owner's
# decision-correction PATTERN through this one wrapper - the same rules first,
# the complete event, the affected rows, the exact prior settlement as an
# untrusted lead and the reviewer's findings LAST; the same reader,
# materializer and raw lifecycle. Each ROUND corrects the accepted key before
# it (the bound primary with every earlier round's bound overlay). The
# population is DERIVED, never listed: from the bound review receipt (round
# one) or from the open issues the accepted key still carries (round two);
# either way the receipt must carry each event's own open issues verbatim and
# may add reviewer findings that point at existing rules. No semantic string
# decides anything here.
def _review_population(shards, findings, order):
    """Round one (Codex SEQ 1501): every event whose bound review entry is nonempty."""
    del shards
    return [sid for sid in order if findings.get(sid)]


def _open_issue_population(shards, findings, order):
    """Round two (Codex SEQ 1505 item 2): exactly the events whose accepted
    shard still carries an open issue; the receipt must cover exactly them."""
    pop = [sid for sid in order if shards[sid]["open_issues"]]
    if [sid for sid in order if findings.get(sid)] != pop:
        raise ValueError("the review receipt does not cover exactly the events "
                         "with an open issue")
    return pop


#: THE correction rounds, in the order their overlays apply. What a round
#: genuinely owns is listed here; nothing else differs between rounds.
_ROUNDS = collections.OrderedDict([
    (CORR_DOOR, {
        "pkg_dir": CORR_PKG_DIR, "budget_receipt": CORR_BUDGET_RECEIPT,
        "review_receipt": REVIEW_RECEIPT,
        "binding": os.path.join(K.EVIDENCE, "final_targeted_corr_binding.json"),
        "launcher_name": CORR_LAUNCHER_NAME, "authority": "Codex SEQ 1501",
        "origin": "final_targeted_correction", "receipt_key": "primary_binding",
        "population": _review_population}),
    (CORR2_DOOR, {
        "pkg_dir": CORR2_PKG_DIR, "budget_receipt": CORR2_BUDGET_RECEIPT,
        "review_receipt": CORR2_REVIEW_RECEIPT,
        "binding": os.path.join(K.EVIDENCE, "final_targeted_corr2_binding.json"),
        "launcher_name": CORR_LAUNCHER_NAME + "-2", "authority": "Codex SEQ 1505",
        "origin": "final_targeted_correction_2", "receipt_key": "lead_binding",
        "population": _open_issue_population})])
CORRECTION_DOORS = tuple(_ROUNDS)
_DOORS = (DOOR,) + CORRECTION_DOORS


def _lead_door(door):
    """The door whose bound run a round reviews: the round before it, or the primary."""
    earlier = CORRECTION_DOORS[:CORRECTION_DOORS.index(door)]
    return earlier[-1] if earlier else DOOR


@functools.lru_cache(maxsize=None)
def _bound_cached(door, binding_sha):
    """One door's bound shards and raw texts, proved once per operation: the
    binding identity through proved_spend, the parse through the shared
    accepted_shards over the pinned prefix. Keyed by the immutable binding."""
    del binding_sha
    run = _closed_run(door)
    if run is None:
        raise ValueError("no %s run is bound" % door)
    proved_spend(run, door)
    shards, raws, bad = accepted_shards(run)
    if bad:
        raise ValueError("the bound %s run does not re-prove: %s" % (door, bad[:2]))
    return shards, raws


def bound_shards(door):
    """Callers get COPIES; nothing they mutate reaches the cache."""
    shards, raws = _bound_cached(door, INV.sha_file(_phase(door)["binding"]))
    return (collections.OrderedDict((k, copy.deepcopy(v)) for k, v in shards.items()),
            collections.OrderedDict(raws))


def primary_shards():
    return bound_shards(DOOR)


def _lead(door):
    """What a round corrects: the accepted key before it - the bound primary
    with every earlier round's BOUND overlay. -> (shards, raws, origins)"""
    earlier = CORRECTION_DOORS[:CORRECTION_DOORS.index(door)]
    runs = [_closed_run(d) for d in earlier]
    if None in runs:
        raise ValueError("the %s run is not bound" % earlier[runs.index(None)])
    shards, raws, origins, bad = successor_shards(*runs)
    if bad:
        raise ValueError("the accepted key before %s does not re-prove: %s" % (door, bad[:2]))
    return shards, raws, origins


def _review_receipt(door=CORR_DOOR):
    r, lead = _ROUNDS[door], _lead_door(door)
    doc = _load(r["review_receipt"])
    if doc.get("schema") != REVIEW_SCHEMA:
        raise ValueError("the review receipt is not of this schema")
    binding = _phase(lead)["binding"]
    pb = doc.get(r["receipt_key"]) or {}
    if pb.get("binding_path") != binding or pb.get("binding_sha256") != INV.sha_file(binding) \\
            or pb.get("run_dir") != _closed_run(lead):
        raise ValueError("the review receipt is not bound to the accepted %s run" % lead)
    return doc


def correction_events(door=CORR_DOOR):
    """THE population of one round, derived through the round's own rule, in
    primary order. The receipt must carry each event's own open issues
    verbatim and completely; a reviewer finding must be a nonempty text
    naming at least one existing rule."""
    rec = _review_receipt(door)
    shards, _raws, _origins = _lead(door)
    findings = rec.get("findings") or {}
    order = list(shards)
    for sid in findings:
''')
rep('''            raise ValueError("%s: the review receipt does not carry the primary's "
                             "open issues verbatim and completely" % sid)''',
    '''            raise ValueError("%s: the review receipt does not carry the accepted "
                             "shard's open issues verbatim and completely" % sid)''')
rep('''                raise ValueError("%s: a reviewer finding has no text or names no rule" % sid)
    return [sid for sid in order if findings.get(sid)]


def correction_tasks():
    by = {t["source_id"]: t for t in event_tasks()}
    return [collections.OrderedDict([
        ("task_id", "ftc-%03d" % n), ("event_index", by[sid]["event_index"]),
        ("source_id", sid), ("rows", list(by[sid]["rows"])),
        ("groups", collections.OrderedDict(by[sid]["groups"]))])
        for n, sid in enumerate(correction_events())]


def correction_leads(task):
    """The exact primary settlement, as its RAW bytes, hash-bound, untrusted."""
    _shards, raws = primary_shards()
    raw = raws[task["source_id"]]
    return [collections.OrderedDict([
        ("lead_id", "primary/%s" % task["source_id"]), ("origin", CORR_LEAD_ORIGIN),
        ("sha256", _sha(raw)), ("reply", raw)])]


def correction_findings(task):
    """The bound review entries for this event, verbatim, last in the data."""
    return [collections.OrderedDict(f) for f in _review_receipt()["findings"][task["source_id"]]]
''', '''                raise ValueError("%s: a reviewer finding has no text or names no rule" % sid)
    return _ROUNDS[door]["population"](shards, findings, order)


def correction_tasks(door=CORR_DOOR):
    by = {t["source_id"]: t for t in event_tasks()}
    return [collections.OrderedDict([
        ("task_id", "ftc-%03d" % n), ("event_index", by[sid]["event_index"]),
        ("source_id", sid), ("rows", list(by[sid]["rows"])),
        ("groups", collections.OrderedDict(by[sid]["groups"]))])
        for n, sid in enumerate(correction_events(door))]


def correction_leads(task, door=CORR_DOOR):
    """The exact prior settlement of this event - the accepted key before the
    round - as its RAW bytes, hash-bound, untrusted."""
    _shards, raws, origins = _lead(door)
    sid = task["source_id"]
    raw, origin = raws[sid], origins[sid]
    return [collections.OrderedDict([
        ("lead_id", "%s/%s" % (origin.rsplit("_", 1)[-1], sid)), ("origin", origin),
        ("sha256", _sha(raw)), ("reply", raw)])]


def correction_findings(task, door=CORR_DOOR):
    """The bound review entries for this event, verbatim, last in the data."""
    return [collections.OrderedDict(f) for f in _review_receipt(door)["findings"][task["source_id"]]]
''')
rep('''def correction_payload(task):
    body = _payload(task)
    del body["leads"]
    body["leads"] = correction_leads(task)
    body["reviewer_findings"] = correction_findings(task)
    return body


def correction_prompt(task):
    return correction_prefix() + json.dumps(correction_payload(task), indent=1)


def render_correction_launcher(task, attempt=1):
    """The primary launcher again, transformed. Transport bytes untouched."""
    lines = render_launcher(task, attempt).split("\\n")
    F._swap(lines, "  name:", "  name: '%s'," % CORR_LAUNCHER_NAME, "meta name")
''', '''def correction_payload(task, door=CORR_DOOR):
    body = _payload(task)
    del body["leads"]
    body["leads"] = correction_leads(task, door)
    body["reviewer_findings"] = correction_findings(task, door)
    return body


def correction_prompt(task, door=CORR_DOOR):
    return correction_prefix() + json.dumps(correction_payload(task, door), indent=1)


def render_correction_launcher(task, attempt=1, door=CORR_DOOR):
    """The primary launcher again, transformed. Transport bytes untouched."""
    lines = render_launcher(task, attempt).split("\\n")
    F._swap(lines, "  name:", "  name: '%s'," % _ROUNDS[door]["launcher_name"], "meta name")
''')
rep('''    F._swap(lines, "const PROMPT = ", "const PROMPT = "
            + json.dumps(correction_prompt(task)), "PROMPT")
    return "\\n".join(lines)


def _correction_derived_from():
    d = _derived_from()
    pkg = _load(BINDING)["package"]
    d["primary_binding"] = collections.OrderedDict([
        ("binding_path", BINDING), ("binding_sha256", INV.sha_file(BINDING)),
        ("run_dir", _closed_run()), ("package_dir", pkg["dir"]),
        ("manifest_sha256", pkg["manifest_sha256"])])
    d["review_receipt"] = collections.OrderedDict([
        ("path", REVIEW_RECEIPT), ("sha256", INV.sha_file(REVIEW_RECEIPT))])
    return d


def _correction_manifest():
    tasks = correction_tasks()
    if not tasks:
        raise ValueError("population refused: no event carries a finding")
    _shards, raws = primary_shards()
    population = {t["source_id"] for t in tasks}
    rows, scripts = [], []
    for task in tasks:
        text = correction_prompt(task)
        script = render_correction_launcher(task)
''', '''    F._swap(lines, "const PROMPT = ", "const PROMPT = "
            + json.dumps(correction_prompt(task, door)), "PROMPT")
    return "\\n".join(lines)


def _correction_derived_from(door=CORR_DOOR):
    d, r, lead = _derived_from(), _ROUNDS[door], _lead_door(door)
    binding = _phase(lead)["binding"]
    pkg = _load(binding)["package"]
    d[r["receipt_key"]] = collections.OrderedDict([
        ("binding_path", binding), ("binding_sha256", INV.sha_file(binding)),
        ("run_dir", _closed_run(lead)), ("package_dir", pkg["dir"]),
        ("manifest_sha256", pkg["manifest_sha256"])])
    d["review_receipt"] = collections.OrderedDict([
        ("path", r["review_receipt"]), ("sha256", INV.sha_file(r["review_receipt"]))])
    return d


def _correction_manifest(door=CORR_DOOR):
    tasks = correction_tasks(door)
    if not tasks:
        raise ValueError("population refused: no event carries a finding")
    _shards, raws, origins = _lead(door)
    population = {t["source_id"] for t in tasks}
    rows, scripts = [], []
    for task in tasks:
        text = correction_prompt(task, door)
        script = render_correction_launcher(task, door=door)
''')
rep('''                for x in correction_leads(task)]),
            ("findings", [collections.OrderedDict(
                [("kind", f["kind"]), ("sha256", _sha(json.dumps(f, sort_keys=True)))])
                for f in correction_findings(task)]),
            ("payload_sha256", _sha(json.dumps(correction_payload(task), sort_keys=True))),''',
    '''                for x in correction_leads(task, door)]),
            ("findings", [collections.OrderedDict(
                [("kind", f["kind"]), ("sha256", _sha(json.dumps(f, sort_keys=True)))])
                for f in correction_findings(task, door)]),
            ("payload_sha256", _sha(json.dumps(correction_payload(task, door), sort_keys=True))),''')
rep('''        ("door", CORR_DOOR), ("version", VERSION), ("authority", "Codex SEQ 1501"),
        ("step", "live Step 1 A4 - the correction of the successor final "
                 "adjudication under the reviewer findings"),
        ("contract_suffix", SUFFIX),
        ("derived_from", _correction_derived_from()),''',
    '''        ("door", door), ("version", VERSION), ("authority", _ROUNDS[door]["authority"]),
        ("step", "live Step 1 A4 - the correction of the successor final "
                 "adjudication under the reviewer findings"),
        ("contract_suffix", SUFFIX),
        ("derived_from", _correction_derived_from(door)),''')
rep('''        ("budget", _budget(len(rows), CORR_BUDGET_RECEIPT)),''',
    '''        ("budget", _budget(len(rows), _ROUNDS[door]["budget_receipt"])),''')
rep('''        ("preserved", [collections.OrderedDict([
            ("source_id", t["source_id"]), ("primary_raw_sha256", _sha(raws[t["source_id"]]))])
            for t in event_tasks() if t["source_id"] not in population]),''',
    '''        ("preserved", [collections.OrderedDict([
            ("source_id", t["source_id"]), ("origin", origins[t["source_id"]]),
            ("raw_sha256", _sha(raws[t["source_id"]]))])
            for t in event_tasks() if t["source_id"] not in population]),''')
rep('''def build_correction(out_dir):
    return build(out_dir, CORR_DOOR)


def correction_package_problems(pkg_dir=None):
    return package_problems(pkg_dir, CORR_DOOR)


def correction_preflight(pkg_dir=None):
    return preflight(pkg_dir, CORR_DOOR)


@_operation
def successor_shards(correction_run=None):
    """The eventual successor shards: the accepted primary shards with the
    correction's accepted replacements over exactly the derived population.
    -> (shards, raws, origins, problems), primary order throughout."""
    shards, raws = primary_shards()
    origins = collections.OrderedDict((s, "final_targeted_primary") for s in shards)
    bad = []
    if correction_run is not None:
        wanted = set(correction_events())
        repl, rraws, rbad = accepted_shards(correction_run)
        bad += rbad
        for sid, shard in repl.items():
            if sid not in wanted:
                bad.append("%s: a correction outside the derived population" % sid)
                continue
            shards[sid], raws[sid], origins[sid] = shard, rraws[sid], "final_targeted_correction"
        missing = sorted(wanted - set(repl))
        if missing:
            bad.append("%d affected events have no accepted correction: %s" % (len(missing), missing[:3]))
    return shards, raws, origins, bad


@_operation
def preservation_problems(correction_run=None):
    """Nothing unaffected moves: the preserved events' raw bytes equal the
    bound primary's, the bound primary itself re-proves, and the locked A4
    history still holds (the ledger's own locked rows)."""
    bad = []
    try:
        proved_spend(_closed_run())
    except ValueError as exc:
        return ["the bound primary does not re-prove: %s" % exc]
    _shards, raws, origins, sbad = successor_shards(correction_run)
    bad += sbad
    bound = {a["attempt"]: a for a in _load(BINDING)["attempts"]}[1]["raw_files"]
    for sid in [t["source_id"] for t in event_tasks() if t["source_id"] not in set(correction_events())]:
        if origins.get(sid) != "final_targeted_primary" or \\
                bound.get("%s.attempt1.proved.json" % sid) != _sha(raws[sid]):
            bad.append("%s: a preserved event's shard is not the bound primary's" % sid)
    import a6_launch_freeze as A6
''', '''def build_correction(out_dir, door=CORR_DOOR):
    return build(out_dir, door)


def correction_package_problems(pkg_dir=None, door=CORR_DOOR):
    return package_problems(pkg_dir, door)


def correction_preflight(pkg_dir=None, door=CORR_DOOR):
    return preflight(pkg_dir, door)


def _overlay(door, run):
    """One round's accepted shards: through its binding when the run is the
    bound one, else re-proved directly. -> (shards, raws, problems)"""
    if os.path.abspath(run) == _closed_run(door):
        shards, raws = bound_shards(door)
        return shards, raws, []
    return accepted_shards(run)


@_operation
def successor_shards(*runs):
    """The accepted key after the given correction runs, one per round in
    door order: the bound primary with each round's accepted replacements
    over exactly that round's derived population. A later round without the
    earlier one is refused. -> (shards, raws, origins, problems), primary
    order throughout."""
    if len(runs) > len(CORRECTION_DOORS):
        raise ValueError("%d correction runs for %d rounds" % (len(runs), len(CORRECTION_DOORS)))
    shards, raws = primary_shards()
    origins = collections.OrderedDict((s, CORR_LEAD_ORIGIN) for s in shards)
    bad = []
    for n, (door, run) in enumerate(zip(CORRECTION_DOORS, runs)):
        if run is None:
            if any(r is not None for r in runs[n + 1:]):
                raise ValueError("a later round is given without the %s run" % door)
            break
        wanted = set(correction_events(door))
        repl, rraws, rbad = _overlay(door, run)
        bad += rbad
        for sid, shard in repl.items():
            if sid not in wanted:
                bad.append("%s: a correction outside the derived population" % sid)
                continue
            shards[sid], raws[sid], origins[sid] = shard, rraws[sid], _ROUNDS[door]["origin"]
        missing = sorted(wanted - set(repl))
        if missing:
            bad.append("%d affected events have no accepted correction: %s" % (len(missing), missing[:3]))
    return shards, raws, origins, bad


def _bound_proved(door, run):
    """{event: {sha256 of every proved text the binding holds}} when `run` is
    the door's bound run; None for any other run (nothing bound to compare)."""
    if run is None or os.path.abspath(run) != _closed_run(door):
        return None
    out = {}
    for attempt in _load(_phase(door)["binding"])["attempts"]:
        for name, sha in attempt["raw_files"].items():
            if name.endswith(".proved.json"):
                out.setdefault(name.split(".attempt")[0], set()).add(sha)
    return out


@_operation
def preservation_problems(*runs):
    """Nothing unaffected moves: every event not replaced by a later round
    keeps the exact shard of the last BOUND round that settled it (the
    primary's, or an earlier correction's, byte for byte), the bound primary
    itself re-proves, and the locked A4 history still holds (the ledger's own
    locked rows)."""
    bad = []
    try:
        proved_spend(_closed_run())
    except ValueError as exc:
        return ["the bound primary does not re-prove: %s" % exc]
    _shards, raws, origins, sbad = successor_shards(*runs)
    bad += sbad
    settled = collections.OrderedDict([(DOOR, _closed_run())])
    for door, run in zip(CORRECTION_DOORS, runs):
        if run is None:
            break
        settled[door] = run
    populations = {d: set(correction_events(d)) for d in settled if d != DOOR}
    for sid in _shards:
        door = DOOR
        for d in populations:
            if sid in populations[d]:
                door = d
        want = CORR_LEAD_ORIGIN if door == DOOR else _ROUNDS[door]["origin"]
        if origins.get(sid) != want:
            bad.append("%s: the shard is not the %s's" % (sid, want))
            continue
        bound = _bound_proved(door, settled[door])
        if bound is not None and _sha(raws[sid]) not in bound.get(sid, ()):
            bad.append("%s: a preserved event's shard is not the bound %s's" % (sid, want))
    import a6_launch_freeze as A6
''')

# ---- full composition pass-through
rep('''@_operation
def full_successor(correction_run=None):''', '''@_operation
def full_successor(*runs):''')
rep('''    b, base, braws, borigins = _baseline()
    targeted, traws, torigins, problems = successor_shards(correction_run)''',
    '''    b, base, braws, borigins = _baseline()
    targeted, traws, torigins, problems = successor_shards(*runs)''')
rep('''@_operation
def full_counts(correction_run=None):
    shards, _raws, prov, _problems = full_successor(correction_run)''',
    '''@_operation
def full_counts(*runs):
    shards, _raws, prov, _problems = full_successor(*runs)''')
rep('''@_operation
def full_preservation_problems(correction_run=None):''', '''@_operation
def full_preservation_problems(*runs):''')
rep('''        shards, raws, prov, problems = full_successor(correction_run)
        targeted, traws, _to, _tb = successor_shards(correction_run)''',
    '''        shards, raws, prov, problems = full_successor(*runs)
        targeted, traws, _to, _tb = successor_shards(*runs)''')
rep('''    bad += preservation_problems(correction_run)
    return bad''', '''    bad += preservation_problems(*runs)
    return bad''')
rep('''@_operation
def full_materialize(correction_run=None):''', '''@_operation
def full_materialize(*runs):''')
rep('''    shards, _raws, _prov, problems = full_successor(correction_run)
    inventory = _corrected_inventory()''', '''    shards, _raws, _prov, problems = full_successor(*runs)
    inventory = _corrected_inventory()''')
io.open(p, "w", encoding="utf-8").write(s)

# ---- a6: the pointer and the row
p = H + "/a6_launch_freeze.py"
s = io.open(p, encoding="utf-8").read()
rep('''                   "final_targeted_dir.txt")''', '''                   "final_targeted_dir.txt", "final_targeted_corr_dir.txt")''')
rep('''    import build_kfields_final_targeted as _FT
    for spent in _FT.proved_spend(_read_ptr("final_targeted_dir.txt")):
        total += spent["calls"]
        rows.append(collections.OrderedDict([
            ("stage", "final_targeted_%s"
             % ("primary" if spent["attempt"] == 1 else "retry")),
            ("run_dir", spent["run_dir"]),
            ("receipt_sha256", spent["receipt_sha256"]),
            ("finalization_sha256", spent["finalization_sha256"]),
            ("raw_tree", spent["raw_tree"]),
            ("calls", spent["calls"])]))
''', '''    import build_kfields_final_targeted as _FT
    for spent in _FT.proved_spend(_read_ptr("final_targeted_dir.txt")):
        total += spent["calls"]
        rows.append(collections.OrderedDict([
            ("stage", "final_targeted_%s"
             % ("primary" if spent["attempt"] == 1 else "retry")),
            ("run_dir", spent["run_dir"]),
            ("receipt_sha256", spent["receipt_sha256"]),
            ("finalization_sha256", spent["finalization_sha256"]),
            ("raw_tree", spent["raw_tree"]),
            ("calls", spent["calls"])]))

    # THE SUCCESSOR FINAL CORRECTION (Codex SEQ 1505 item 1): the same owner
    # re-proves its bound correction run against the PINNED package it ran
    # under and returns one proved row per attempt; this owner only records
    # it. Counting a run accepts none of its outputs.
    for spent in _FT.proved_spend(_read_ptr("final_targeted_corr_dir.txt"), _FT.CORR_DOOR):
        total += spent["calls"]
        rows.append(collections.OrderedDict([
            ("stage", "final_targeted_correction_%s"
             % ("primary" if spent["attempt"] == 1 else "retry")),
            ("run_dir", spent["run_dir"]),
            ("receipt_sha256", spent["receipt_sha256"]),
            ("finalization_sha256", spent["finalization_sha256"]),
            ("raw_tree", spent["raw_tree"]),
            ("calls", spent["calls"])]))
''')
io.open(p, "w", encoding="utf-8").write(s)
print("patched")
