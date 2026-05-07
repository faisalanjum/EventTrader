#!/usr/bin/env python3
"""Verifier for Goal 6f research-only candidate discovery.

This verifier does not decide financial truth. It checks that Goal 6f stayed
inside the research sandbox, did not use banned heuristic classes, and that the
reported candidate metrics exactly match per-row artifacts.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]

PROMPT = PROJECT_ROOT / ".claude/plans/goal_6f_prompt.md"
VERIFY = Path(__file__).resolve()

D_MEASUREMENT = HERE / "goal6a_d_measurement.csv"
EDGE_DIR = HERE / "audit_evidence/sec_34_edge_ticker_audit_2026-05-07"
EDGE_SIM = EDGE_DIR / "advance_xbrl_simulation.csv"
EDGE_TRUTH = EDGE_DIR / "master_truth.csv"
EDGE_REPORT = EDGE_DIR / "validation_report.md"
EDGE_DECISION = EDGE_DIR / "DECISION_FLAG.md"
EDGE_ADVERSARIAL = EDGE_DIR / "adversarial_review.json"

CANDIDATES = HERE / "goal6f_candidates.py"
BUILDER = HERE / "build_goal6f_outputs.py"
MATRIX = HERE / "goal6f_candidate_matrix.csv"
REPORT = HERE / "GOAL6F_REPORT.md"
FAILURE_MODEL = HERE / "GOAL6F_FAILURE_MODEL.md"

EXPECTED_TOTAL = 10674

PRODUCTION_LOCK_PREFIXES = [
    "scripts/earnings/",
    "scripts/harvest_guidance_sessions.py",
    ".claude/skills/earnings-orchestrator/scripts/",
]

IMMUTABLE_INPUTS = [
    PROMPT,
    VERIFY,
    D_MEASUREMENT,
    EDGE_SIM,
    EDGE_TRUTH,
    EDGE_REPORT,
    EDGE_DECISION,
    EDGE_ADVERSARIAL,
]

EDGE_TICKERS = {
    "ACI", "ANF", "ASO", "BJ", "BOX", "BURL", "CHWY", "CNM", "DKS",
    "DLTR", "FIVE", "GBX", "GIII", "GME", "KR", "KSS", "LOW", "LULU",
    "NTAP", "NTNX", "OLLI", "OXM", "PHM", "PHR", "PINC", "PLAY", "PLCE",
    "PRU", "PVH", "RH", "ROST", "ULTA", "WDAY", "WMS",
}

PER_ROW_COLUMNS = {
    "candidate_id", "ticker", "accession_8k", "oracle_source", "oracle_fy",
    "oracle_q", "warm_start", "latest_per_ticker", "d_outcome", "d_fy",
    "d_q", "d_source", "outcome", "fy", "q", "source", "correct",
    "changed_vs_d", "feature_notes",
}

MATRIX_COLUMNS = {
    "candidate_id", "description", "uses_banned_features", "shippable",
    "full_correct", "full_wrong", "full_fail_closed", "full_new_wrong_vs_d",
    "warm_correct", "warm_wrong", "warm_fail_closed", "warm_new_wrong_vs_d",
    "latest_correct", "latest_wrong", "latest_fail_closed",
    "latest_new_wrong_vs_d", "edge_ab_correct", "edge_ab_wrong",
    "edge_ab_fail_closed", "edge_ab_new_wrong_vs_d",
    "edge_ab_recovered_correct_from_d_fc",
}


def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


def run_git(args: list[str], *, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=text,
        timeout=60,
    )


def check_inputs_git_clean() -> None:
    for path in IMMUTABLE_INPUTS:
        if not path.is_file():
            fail(f"immutable input missing: {path}", 2)
        rel = str(path.relative_to(PROJECT_ROOT))
        tracked = run_git(["ls-files", "--error-unmatch", rel])
        if tracked.returncode != 0:
            fail(f"immutable input is not committed: {rel}", 2)
        dirty = run_git(["status", "--short", "--", rel])
        if dirty.stdout.strip():
            fail(f"immutable input has uncommitted changes: {rel}\n{dirty.stdout}", 2)
    info(f"G1 immutable prompt/verifier/evidence files git-clean: {len(IMMUTABLE_INPUTS)}")


def check_no_production_changes() -> None:
    dirty = []
    for prefix in PRODUCTION_LOCK_PREFIXES:
        r = run_git(["status", "--short", "--", prefix])
        dirty.extend(line for line in r.stdout.splitlines() if line.strip())
    if dirty:
        fail("production/guidance files changed during research goal:\n" + "\n".join(dirty[:80]))
    info("G2 production/guidance files unchanged")


def check_research_files() -> None:
    for path in [FAILURE_MODEL, CANDIDATES, BUILDER, MATRIX, REPORT]:
        if not path.is_file():
            fail(f"required research artifact missing: {path}")
    text = CANDIDATES.read_text(encoding="utf-8")
    if "RESEARCH-ONLY Goal 6f candidates" not in text:
        fail("goal6f_candidates.py missing RESEARCH-ONLY marker")

    prod_scan = run_git(["grep", "-n", "goal6f_candidates", "--", "scripts", ".claude/skills"], text=True)
    if prod_scan.returncode == 0 and prod_scan.stdout.strip():
        fail("goal6f_candidates.py is referenced from production paths:\n" + prod_scan.stdout)
    info("G3 research files present and isolated")


def check_banned_patterns() -> None:
    scanned = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [CANDIDATES, BUILDER]
        if p.is_file()
    )
    banned_regexes = [
        r"\bindustry\b", r"\bsector\b", r"\bSIC\b", r"\bGICS\b", r"\bNAICS\b",
        r"\bcik\b",
        r"industry_normalized", r"_RISK_INDUSTR", r"Company\.industry",
        r"EX-99", r"press[-_ ]?release", r"raw_sec", r"evidence_quote",
        r"Reports?\s+(?:First|Second|Third|Fourth)\s+Quarter",
        r"(?:first|second|third|fourth)\s+quarter\s+of\s+fiscal",
        r"\brequests\b", r"\bhttpx\b", r"urllib", r"urlopen",
        r"sec_api", r"\bedgar\b",
        r"\bopenai\b", r"\banthropic\b", r"\bsklearn\b", r"\bxgboost\b",
        r"\blightgbm\b", r"\btorch\b", r"tensorflow", r"\bkeras\b",
        r"transformers", r"\bspacy\b", r"\bnltk\b",
        r"datetime\.now\(", r"\btime\.time\(\)",
    ]
    for pat in banned_regexes:
        if re.search(pat, scanned, flags=re.IGNORECASE):
            fail(f"banned pattern found in Goal 6f research code: {pat}")

    for ticker in EDGE_TICKERS:
        if re.search(rf"['\"]{re.escape(ticker)}['\"]", scanned):
            fail(f"ticker-specific literal found in research code: {ticker}")
    info("G4 banned heuristic scan passed")


def check_failure_model() -> None:
    text = FAILURE_MODEL.read_text(encoding="utf-8")
    required = [
        "D_FAIL_CLOSED_TAXONOMY",
        "D_WRONG_FIRE_TAXONOMY",
        "G2_NEW_WRONG_TAXONOMY",
        "MISSING_SIGNAL_ANALYSIS",
        "ALLOWED_SIGNAL_INVENTORY",
        "CANDIDATE_FAMILIES_JUSTIFIED",
        "IRREDUCIBLE_CLASSES",
        "TRACTABLE_CLASSES",
        "EVIDENCE_ROWS",
    ]
    for item in required:
        if item not in text:
            fail(f"GOAL6F_FAILURE_MODEL.md missing required section: {item}")
    if len(text.split()) < 500:
        fail("GOAL6F_FAILURE_MODEL.md is too thin; expected real diagnosis before candidates")
    info("G4b failure model exists with required diagnosis sections")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truth_maps() -> tuple[dict[str, dict[str, str]], dict[str, tuple[str, str]]]:
    d_rows = read_csv(D_MEASUREMENT)
    if len(d_rows) != EXPECTED_TOTAL:
        fail(f"D measurement row count changed: {len(d_rows)} != {EXPECTED_TOTAL}", 2)
    d_by_acc = {r["accession_8k"]: r for r in d_rows}
    if len(d_by_acc) != EXPECTED_TOTAL:
        fail("D measurement accessions are not unique", 2)

    edge_rows = read_csv(EDGE_SIM)
    edge_truth = {
        r["accession_8k"]: (r["sec_truth_fy"], r["sec_truth_q"])
        for r in edge_rows
        if r.get("sec_truth_tier") in {"A", "B"}
    }
    if len(edge_truth) < 390:
        fail(f"edge Tier A/B count unexpectedly low: {len(edge_truth)}", 2)
    return d_by_acc, edge_truth


def classify(row: dict[str, str], truth_fy: str, truth_q: str) -> str:
    if row.get("outcome") != "AUTO_OK":
        return "fail_closed"
    if str(row.get("fy")) == str(truth_fy) and str(row.get("q")) == str(truth_q):
        return "correct"
    return "wrong"


def boolish(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def check_candidate_outputs() -> tuple[dict[str, dict[str, int]], list[dict[str, str]]]:
    d_by_acc, edge_truth = truth_maps()
    per_row_files = sorted(HERE.glob("goal6f_candidate_*_per_row.csv"))
    if len(per_row_files) < 4:
        fail("expected at least 4 candidate per-row files, including baselines")

    metrics: dict[str, dict[str, int]] = {}
    candidate_ids = set()
    for path in per_row_files:
        rows = read_csv(path)
        if not rows:
            fail(f"empty per-row file: {path.name}")
        missing = PER_ROW_COLUMNS - set(rows[0])
        if missing:
            fail(f"{path.name} missing columns: {sorted(missing)}")
        if len(rows) != EXPECTED_TOTAL:
            fail(f"{path.name} row count {len(rows)} != {EXPECTED_TOTAL}")
        accessions = {r["accession_8k"] for r in rows}
        if accessions != set(d_by_acc):
            fail(f"{path.name} accession set differs from D measurement")

        cid_values = {r["candidate_id"] for r in rows}
        if len(cid_values) != 1:
            fail(f"{path.name} has multiple candidate_id values: {sorted(cid_values)[:5]}")
        cid = next(iter(cid_values))
        candidate_ids.add(cid)

        if cid == "D_BASELINE":
            for r in rows:
                d = d_by_acc[r["accession_8k"]]
                actual = (r["outcome"], r["fy"], r["q"], r["source"])
                expected = (d["outcome"], d["fy"], d["q"], d["source"])
                if actual != expected:
                    fail(
                        f"D_BASELINE row {r['accession_8k']} diverges from "
                        f"goal6a_d_measurement.csv: {actual} != {expected}"
                    )

        m = {
            "full_correct": 0, "full_wrong": 0, "full_fail_closed": 0,
            "full_new_wrong_vs_d": 0,
            "warm_correct": 0, "warm_wrong": 0, "warm_fail_closed": 0,
            "warm_new_wrong_vs_d": 0,
            "latest_correct": 0, "latest_wrong": 0, "latest_fail_closed": 0,
            "latest_new_wrong_vs_d": 0,
            "edge_ab_correct": 0, "edge_ab_wrong": 0, "edge_ab_fail_closed": 0,
            "edge_ab_new_wrong_vs_d": 0,
            "edge_ab_recovered_correct_from_d_fc": 0,
        }

        for r in rows:
            acc = r["accession_8k"]
            if acc in edge_truth:
                truth_fy, truth_q = edge_truth[acc]
                if str(r["oracle_fy"]) != str(truth_fy) or str(r["oracle_q"]) != str(truth_q):
                    fail(
                        f"{path.name} row {acc} does not use edge Tier A/B SEC truth "
                        f"({truth_q}_FY{truth_fy}); found {r['oracle_q']}_FY{r['oracle_fy']}"
                    )
            else:
                truth_fy = r["oracle_fy"]
                truth_q = r["oracle_q"]
            cls = classify(r, truth_fy, truth_q)
            expected_correct = {
                "correct": "true",
                "wrong": "false",
                "fail_closed": "fail_closed",
            }[cls]
            if str(r.get("correct", "")).strip().lower() != expected_correct:
                fail(
                    f"{path.name} row {acc} has stale correct={r.get('correct')!r}; "
                    f"expected {expected_correct}"
                )
            d_cls = classify(
                {
                    "outcome": d_by_acc[acc]["outcome"],
                    "fy": d_by_acc[acc]["fy"],
                    "q": d_by_acc[acc]["q"],
                },
                truth_fy,
                truth_q,
            )
            expected_changed = (
                str(r.get("outcome", "")) != str(d_by_acc[acc]["outcome"])
                or str(r.get("fy", "")) != str(d_by_acc[acc]["fy"])
                or str(r.get("q", "")) != str(d_by_acc[acc]["q"])
            )
            if boolish(r.get("changed_vs_d", "")) != expected_changed:
                fail(
                    f"{path.name} row {acc} has stale changed_vs_d={r.get('changed_vs_d')!r}; "
                    f"expected {str(expected_changed).lower()}"
                )

            m[f"full_{cls}"] += 1
            if cls == "wrong" and d_cls != "wrong":
                m["full_new_wrong_vs_d"] += 1

            if boolish(r["warm_start"]):
                m[f"warm_{cls}"] += 1
                if cls == "wrong" and d_cls != "wrong":
                    m["warm_new_wrong_vs_d"] += 1
            if boolish(r["latest_per_ticker"]):
                m[f"latest_{cls}"] += 1
                if cls == "wrong" and d_cls != "wrong":
                    m["latest_new_wrong_vs_d"] += 1
            if acc in edge_truth:
                m[f"edge_ab_{cls}"] += 1
                if cls == "wrong" and d_cls != "wrong":
                    m["edge_ab_new_wrong_vs_d"] += 1
                if cls == "correct" and d_cls == "fail_closed":
                    m["edge_ab_recovered_correct_from_d_fc"] += 1

        metrics[cid] = m

    new_ids = candidate_ids - {"D_BASELINE", "G2_CALENDAR_ONLY", "G2_ALL_FY_DISAGREE"}
    if len(new_ids) < 4:
        fail(f"expected at least 4 new candidates beyond baselines, got {sorted(new_ids)}")
    info(f"G5 per-row artifacts valid for {len(candidate_ids)} candidates")

    matrix_rows = read_csv(MATRIX)
    if not matrix_rows:
        fail("candidate matrix is empty")
    missing = MATRIX_COLUMNS - set(matrix_rows[0])
    if missing:
        fail(f"candidate matrix missing columns: {sorted(missing)}")
    return metrics, matrix_rows


def check_matrix_matches(metrics: dict[str, dict[str, int]], matrix_rows: list[dict[str, str]]) -> None:
    matrix_by_id = {r["candidate_id"]: r for r in matrix_rows}
    if set(metrics) - set(matrix_by_id):
        fail(f"matrix missing candidates: {sorted(set(metrics) - set(matrix_by_id))}")
    for cid, m in metrics.items():
        row = matrix_by_id[cid]
        for key, expected in m.items():
            raw = row.get(key, "")
            try:
                actual = int(raw)
            except ValueError:
                fail(f"matrix {cid}.{key} is not an int: {raw!r}")
            if actual != expected:
                fail(f"matrix mismatch {cid}.{key}: reported {actual}, recomputed {expected}")

        if row.get("uses_banned_features", "").lower() not in {"true", "false"}:
            fail(f"matrix {cid}.uses_banned_features must be true/false")
        if row.get("shippable", "").lower() not in {"true", "false"}:
            fail(f"matrix {cid}.shippable must be true/false")
        if row.get("shippable", "").lower() == "true":
            if row.get("uses_banned_features", "").lower() == "true":
                fail(f"{cid} marked shippable despite banned features")
            if m["full_new_wrong_vs_d"] != 0 or m["edge_ab_new_wrong_vs_d"] != 0:
                fail(f"{cid} marked shippable despite new wrongs vs D")
            if m["edge_ab_recovered_correct_from_d_fc"] <= 0:
                fail(f"{cid} marked shippable but recovers no edge D fail-closed rows")
    info("G6 matrix metrics exactly match per-row recompute")


def check_report_flags(matrix_rows: list[dict[str, str]]) -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = [
        "STRUCTURAL_DIRECTIONS_TESTED",
        "multi-prior",
        "period-end",
        "8-K own XBRL",
        "advance-result agreement",
        "TARGET_FAILURE_CLASS",
        "BANNED_FEATURES_AUDIT",
        "DECISION_FLAG_GOAL6F_FOUND_SHIPPABLE",
        "DECISION_FLAG_GOAL6F_BEST_CANDIDATE",
        "DECISION_FLAG_GOAL6F_RECOMMENDATION",
    ]
    for item in required:
        if item not in text:
            fail(f"GOAL6F_REPORT.md missing required text: {item}")

    found = re.search(r"^DECISION_FLAG_GOAL6F_FOUND_SHIPPABLE\s*=\s*(yes|no)\s*$", text, re.M)
    best = re.search(r"^DECISION_FLAG_GOAL6F_BEST_CANDIDATE\s*=\s*([A-Za-z0-9_\\-]+|NONE)\s*$", text, re.M)
    rec = re.search(r"^DECISION_FLAG_GOAL6F_RECOMMENDATION\s*=\s*(SHIP_CANDIDATE|KEEP_D|NEEDS_MORE_GT)\s*$", text, re.M)
    if not (found and best and rec):
        fail("GOAL6F_REPORT.md decision flags are malformed")

    shippable_ids = {
        r["candidate_id"]
        for r in matrix_rows
        if r.get("shippable", "").lower() == "true"
    }
    if found.group(1) == "yes":
        if not shippable_ids:
            fail("report says shippable=yes but matrix has no shippable candidates")
        if best.group(1) not in shippable_ids:
            fail("report best candidate is not marked shippable in matrix")
        if rec.group(1) != "SHIP_CANDIDATE":
            fail("report says shippable=yes but recommendation is not SHIP_CANDIDATE")
    else:
        if rec.group(1) == "SHIP_CANDIDATE":
            fail("report says shippable=no but recommendation is SHIP_CANDIDATE")
    info("G7 report flags are internally consistent")


def main() -> int:
    check_inputs_git_clean()
    check_no_production_changes()
    check_research_files()
    check_banned_patterns()
    check_failure_model()
    metrics, matrix_rows = check_candidate_outputs()
    check_matrix_matches(metrics, matrix_rows)
    check_report_flags(matrix_rows)
    info("ALL CHECKS PASSED - Goal 6f research artifacts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
