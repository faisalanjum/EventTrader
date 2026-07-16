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


def test_all_19_name_headings_present():
    b = _block("gate.js", "RULEBOOK")
    for i in range(1, 20):
        h = f"#### NAME-{i:02d}"
        assert b.count(h) == 1, f"rulebook: {h} appears {b.count(h)} times (expected exactly 1)"


def test_law_coupled_to_final_design():
    """Anti-collective-drift anchor: law-critical strings must appear in BOTH FINAL_DESIGN
    (the law) and the shared rulebook — if either side changes vocabulary, this trips."""
    fd = (BASE.parent / "FinalDesign" / "FINAL_DESIGN.md").read_text()
    b = _block("gate.js", "RULEBOOK")
    for anchor in ("actual_vs_consensus", "actual_vs_guidance", "guidance_vs_consensus",
                   "BASE_METRIC", "fed_rate", "aws_outage", "operating_margin"):
        assert anchor in fd, f"FINAL_DESIGN lost law anchor {anchor}"
        assert anchor in b, f"rulebook lost law anchor {anchor}"


if __name__ == "__main__":
    test_gate_reconcile_identical()
    test_menu_build_prefix()
    test_name17_carries_od21()
    test_all_19_name_headings_present()
    test_law_coupled_to_final_design()
    print("rulebook sync: ALL GREEN")
