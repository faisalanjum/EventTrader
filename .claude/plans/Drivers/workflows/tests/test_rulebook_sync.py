"""Rulebook-sync guard (round 23, 2026-07-16).

The three engine prompts (gate.js, reconcile.js, menu_build.js) inline the NAME rulebook.
Law lives in FINAL_DESIGN §3; the inlined copies must (a) agree with each other and
(b) carry the OD-21 NAME-17 surprise law, never the pre-OD-21 "actual vs expected" form.
menu_build's block may append producer-specific guidance AFTER the shared rules (prefix rule).
"""
import re
import pathlib

BASE = pathlib.Path(__file__).parent.parent


def _block(fname: str, const: str) -> str:
    s = (BASE / fname).read_text()
    m = re.search(const + r"\s*=\s*`((?:\\.|[^`\\])*)`", s, re.S)
    assert m, f"{fname}: {const} template literal not found"
    t = m.group(1)
    i = t.find("## Naming rules")
    assert i >= 0, f"{fname}: '## Naming rules' header missing"
    return t[i:]


def test_gate_reconcile_identical():
    assert _block("gate.js", "RULEBOOK") == _block("reconcile.js", "RULEBOOK")


def test_menu_build_prefix():
    common = _block("gate.js", "RULEBOOK")
    menu = _block("menu_build.js", "RULES")
    assert menu.startswith(common), "menu_build rulebook diverges before its trailing addendum"


def test_name17_carries_od21():
    for f, c in [("gate.js", "RULEBOOK"), ("reconcile.js", "RULEBOOK"), ("menu_build.js", "RULES")]:
        b = _block(f, c)
        for t in ("actual_vs_consensus", "actual_vs_guidance", "guidance_vs_consensus"):
            assert t in b, f"{f}: NAME-17 missing OD-21 surprise type {t}"
        assert "(actual vs expected)" not in b, f"{f}: stale pre-OD-21 NAME-17 wording present"


if __name__ == "__main__":
    test_gate_reconcile_identical()
    test_menu_build_prefix()
    test_name17_carries_od21()
    print("rulebook sync: ALL GREEN")
