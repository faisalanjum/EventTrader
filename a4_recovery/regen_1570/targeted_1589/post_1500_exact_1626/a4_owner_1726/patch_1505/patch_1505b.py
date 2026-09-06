import io, sys
H = sys.argv[1]
p = H + "/build_kfields_final_targeted.py"
s = io.open(p, encoding="utf-8").read()
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:70]); s = s.replace(old, new)
rep('''CORR2_DOOR = "a4_final_targeted_correction_2"
CORR2_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr2_1505")
CORR2_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1505.json"
CORR2_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1505.json")
''', '''CORR_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr_binding.json")
CORR2_DOOR = "a4_final_targeted_correction_2"
CORR2_PKG_DIR = os.path.join(K._X, "kfields_key_a4", "final_targeted_corr2_1505")
CORR2_BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1505.json"
CORR2_REVIEW_RECEIPT = os.path.join(K.EVIDENCE, "a4_final_review_receipt_1505.json")
CORR2_BINDING = os.path.join(K.EVIDENCE, "final_targeted_corr2_binding.json")
CORRECTION_DOORS = (CORR_DOOR, CORR2_DOOR)      # the rounds, in the order their overlays apply
_DOORS = (DOOR,) + CORRECTION_DOORS
''')
rep('''    if door in _ROUNDS:
        r, P = _ROUNDS[door], functools.partial
''', '''    if door in CORRECTION_DOORS:
        r, P = _round(door), functools.partial
''')
rep('''                "lead_origins": (CORR_LEAD_ORIGIN,) + tuple(_ROUNDS[d]["origin"] for d in earlier),''',
    '''                "lead_origins": (CORR_LEAD_ORIGIN,) + tuple(_round(d)["origin"] for d in earlier),''')
rep('''#: THE correction rounds, in the order their overlays apply. What a round
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
''', '''def _round(door):
    """What one correction round genuinely owns, resolved from module globals
    at call time (so a forged global reaches every gate); nothing else
    differs between rounds."""
    return {
        CORR_DOOR: {
            "pkg_dir": CORR_PKG_DIR, "budget_receipt": CORR_BUDGET_RECEIPT,
            "review_receipt": REVIEW_RECEIPT, "binding": CORR_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME, "authority": "Codex SEQ 1501",
            "origin": "final_targeted_correction", "receipt_key": "primary_binding",
            "population": _review_population},
        CORR2_DOOR: {
            "pkg_dir": CORR2_PKG_DIR, "budget_receipt": CORR2_BUDGET_RECEIPT,
            "review_receipt": CORR2_REVIEW_RECEIPT, "binding": CORR2_BINDING,
            "launcher_name": CORR_LAUNCHER_NAME + "-2", "authority": "Codex SEQ 1505",
            "origin": "final_targeted_correction_2", "receipt_key": "lead_binding",
            "population": _open_issue_population}}[door]
''')
rep('''    r, lead = _ROUNDS[door], _lead_door(door)
    doc = _load(r["review_receipt"])''', '''    r, lead = _round(door), _lead_door(door)
    doc = _load(r["review_receipt"])''')
rep('''    return _ROUNDS[door]["population"](shards, findings, order)''', '''    return _round(door)["population"](shards, findings, order)''')
rep('''    F._swap(lines, "  name:", "  name: '%s'," % _ROUNDS[door]["launcher_name"], "meta name")''',
    '''    F._swap(lines, "  name:", "  name: '%s'," % _round(door)["launcher_name"], "meta name")''')
rep('''    d, r, lead = _derived_from(), _ROUNDS[door], _lead_door(door)''', '''    d, r, lead = _derived_from(), _round(door), _lead_door(door)''')
rep('''        ("door", door), ("version", VERSION), ("authority", _ROUNDS[door]["authority"]),''',
    '''        ("door", door), ("version", VERSION), ("authority", _round(door)["authority"]),''')
rep('''        ("budget", _budget(len(rows), _ROUNDS[door]["budget_receipt"])),''', '''        ("budget", _budget(len(rows), _round(door)["budget_receipt"])),''')
rep('''            shards[sid], raws[sid], origins[sid] = shard, rraws[sid], _ROUNDS[door]["origin"]''',
    '''            shards[sid], raws[sid], origins[sid] = shard, rraws[sid], _round(door)["origin"]''')
rep('''        want = CORR_LEAD_ORIGIN if door == DOOR else _ROUNDS[door]["origin"]''', '''        want = CORR_LEAD_ORIGIN if door == DOOR else _round(door)["origin"]''')
assert "_ROUNDS" not in s, [l for l in s.splitlines() if "_ROUNDS" in l]
io.open(p, "w", encoding="utf-8").write(s)

p = H + "/test_a4_second_correction_1505.py"
s = io.open(p, encoding="utf-8").read()
rep('''    monkeypatch.setitem(FT._ROUNDS[FT.CORR_DOOR], "binding", device)''', '''    monkeypatch.setattr(FT, "CORR_BINDING", device)''')
rep('''    doc = _load(FT._ROUNDS[CORR2]["review_receipt"])''', '''    doc = _load(FT.CORR2_REVIEW_RECEIPT)''')
rep('''        doc[FT._ROUNDS[CORR2]["receipt_key"]]["binding_sha256"] = "0" * 64''', '''        doc[FT._round(CORR2)["receipt_key"]]["binding_sha256"] = "0" * 64''')
rep('''    monkeypatch.setitem(FT._ROUNDS[CORR2], "review_receipt", p)''', '''    monkeypatch.setattr(FT, "CORR2_REVIEW_RECEIPT", p)''')
rep('''    receipt = _load(FT._ROUNDS[CORR2]["review_receipt"])
    for t in tasks:''', '''    receipt = _load(FT.CORR2_REVIEW_RECEIPT)
    for t in tasks:''')
rep('''    receipt = _load(FT._ROUNDS[CORR2]["review_receipt"])
    boundary''', '''    receipt = _load(FT.CORR2_REVIEW_RECEIPT)
    boundary''')
rep('''    lead = d[FT._ROUNDS[CORR2]["receipt_key"]]''', '''    lead = d[FT._round(CORR2)["receipt_key"]]''')
rep('''    assert d["review_receipt"]["sha256"] == _sha(FT._ROUNDS[CORR2]["review_receipt"])''', '''    assert d["review_receipt"]["sha256"] == _sha(FT.CORR2_REVIEW_RECEIPT)''')
assert "_ROUNDS" not in s
io.open(p, "w", encoding="utf-8").write(s); print("refactored")
