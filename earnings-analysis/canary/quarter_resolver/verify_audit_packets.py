#!/usr/bin/env python3
"""
verify_audit_packets.py — Independent structural verifier for Goal 1.5 output.

HAND-WRITTEN BY HUMANS (NOT BY THE AGENT). This script enforces structural
properties of the audit packets — it does NOT verify quarter identity (that's
the human reviewer's job, packet-by-packet). It only ensures Codex produced
the right SHAPE of output.

EXIT CODES:
  0  = packets pass structural checks; ready for human review
  1  = structural violation; Codex must regenerate
  2  = verifier infrastructure issue

USAGE:
  cd /home/faisal/EventMarketDB
  venv/bin/python earnings-analysis/canary/quarter_resolver/verify_audit_packets.py

CHECKS PERFORMED:
  P1.  Verifier file is git-clean (anti-tampering)
  P2.  Required deliverables exist and non-empty (audit_packets.json,
       audit_packets.csv, SAMPLING_REPORT.md)
  P3.  audit_packets.json is valid JSON, list-of-objects, total count in [150,200]
  P4.  Every packet has all required top-level + nested fields
  P5.  No duplicate accession_8k across packets (each appears at most once)
  P6.  Every packet's accession_8k exists in ground_truth.csv
  P7.  Every packet's bucket ∈ VALID_BUCKETS
  P8.  Bucket counts match the target distribution: edge buckets may be below
       target if SAMPLING_REPORT.md explains; only random may exceed target to
       backfill those shortfalls.
  P9.  Every packet's human_verdict is null (Codex must NOT fill verdicts)
  P10. URL fields are well-formed (filed_8k_url + accession_archive_url)
"""
from __future__ import annotations
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
PACKETS_JSON = _HERE / "audit_packets.json"
PACKETS_CSV = _HERE / "audit_packets.csv"
SAMPLING_REPORT = _HERE / "SAMPLING_REPORT.md"
GROUND_TRUTH = _HERE / "ground_truth.csv"
PROJECT_ROOT = _HERE.parents[2]

REQUIRED_DELIVERABLES = ("audit_packets.json", "audit_packets.csv", "SAMPLING_REPORT.md")

VALID_BUCKETS = {
    "random", "week_52_53", "non_dec_fye", "q4_10k",
    "denylist_adjacent", "boundary",
}

# Target packet count range (per Goal 1.5 prompt)
PACKET_COUNT_MIN = 150
PACKET_COUNT_MAX = 200

# Target distribution per bucket (matches Goal 1.5 prompt's table)
TARGET_BUCKET_COUNTS = {
    "random": 100,
    "week_52_53": 20,
    "non_dec_fye": 20,
    "q4_10k": 20,
    "denylist_adjacent": 20,
    "boundary": 20,
}
# Shortfall tolerance: bucket can be smaller than target if shortfall is
# documented in SAMPLING_REPORT.md (verifier doesn't read the doc — it just
# allows missing rows, but flags them).

# Required packet schema
REQUIRED_TOP_LEVEL = {
    "bucket", "accession_8k", "ticker", "filed_8k", "filed_8k_url",
    "accession_archive_url", "ex_99_1_first_500_chars",
    "matched_periodic", "xbrl", "fiscal_math",
    "denylist_adjacent", "fye_class", "prev_8k", "human_verdict",
}
REQUIRED_MATCHED_PERIODIC = {
    "accession", "form_type", "period_of_report", "filed", "filed_after_8k",
}
REQUIRED_XBRL = {"fy", "q", "raw_fiscal_year_focus", "raw_fiscal_period_focus"}
REQUIRED_FISCAL_MATH = {"fy", "q", "fye_month", "form_type_used"}
REQUIRED_PREV_8K_OR_NULL = {"accession", "filed"}  # if not None


# ── helpers ──────────────────────────────────────────────────────────
def fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"INFO: {msg}")


# ── P1: git freeze ───────────────────────────────────────────────────
def check_verifier_git_clean() -> None:
    rel_path = str(Path(__file__).resolve().relative_to(PROJECT_ROOT))
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", rel_path],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        fail(f"git diff check failed: {e}", code=2)

    if result.returncode != 0:
        fail(
            f"Verifier file has uncommitted changes vs HEAD: {rel_path}",
            code=2,
        )

    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel_path],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        fail(
            f"Verifier file is not git-committed: {rel_path}\n"
            f"Commit it before running /goal so this check has a baseline.",
            code=2,
        )
    info("P1 git-clean: verifier matches committed version ✓")


# ── P2: deliverables exist + non-empty ──────────────────────────────
def check_deliverables_exist() -> None:
    for fname in REQUIRED_DELIVERABLES:
        path = _HERE / fname
        if not path.is_file():
            fail(f"Required deliverable missing: {path}")
        if path.stat().st_size == 0:
            fail(f"Required deliverable is empty: {path}")
    if not GROUND_TRUTH.is_file():
        fail(f"ground_truth.csv missing — Goal 1 must complete first", code=2)
    info(f"P2 deliverables: {list(REQUIRED_DELIVERABLES)} present + non-empty ✓")


# ── P3: JSON parse + count ──────────────────────────────────────────
def load_packets() -> list[dict]:
    try:
        packets = json.loads(PACKETS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"audit_packets.json is not valid JSON: {e}")
    if not isinstance(packets, list):
        fail("audit_packets.json must be a list of packet objects")
    if not all(isinstance(p, dict) for p in packets):
        fail("Every entry in audit_packets.json must be an object")

    n = len(packets)
    if not (PACKET_COUNT_MIN <= n <= PACKET_COUNT_MAX):
        fail(
            f"P3 packet count {n} outside [{PACKET_COUNT_MIN},{PACKET_COUNT_MAX}]"
        )
    info(f"P3 packets: {n} total, range [{PACKET_COUNT_MIN},{PACKET_COUNT_MAX}] ✓")
    return packets


# ── P4: schema check ────────────────────────────────────────────────
def check_schema(packets: list[dict]) -> None:
    errors: list[str] = []
    for i, p in enumerate(packets):
        accn = p.get("accession_8k", f"<packet {i}>")
        # Top-level
        missing = REQUIRED_TOP_LEVEL - set(p.keys())
        if missing:
            errors.append(f"P4 packet {accn}: missing top-level fields {sorted(missing)}")
            continue

        # matched_periodic substructure
        mp = p.get("matched_periodic")
        if not isinstance(mp, dict):
            errors.append(f"P4 packet {accn}: matched_periodic not an object")
        else:
            mp_missing = REQUIRED_MATCHED_PERIODIC - set(mp.keys())
            if mp_missing:
                errors.append(
                    f"P4 packet {accn}: matched_periodic missing {sorted(mp_missing)}"
                )

        # xbrl substructure
        xbrl = p.get("xbrl")
        if not isinstance(xbrl, dict):
            errors.append(f"P4 packet {accn}: xbrl not an object")
        else:
            x_missing = REQUIRED_XBRL - set(xbrl.keys())
            if x_missing:
                errors.append(f"P4 packet {accn}: xbrl missing {sorted(x_missing)}")

        # fiscal_math substructure
        fm = p.get("fiscal_math")
        if not isinstance(fm, dict):
            errors.append(f"P4 packet {accn}: fiscal_math not an object")
        else:
            f_missing = REQUIRED_FISCAL_MATH - set(fm.keys())
            if f_missing:
                errors.append(f"P4 packet {accn}: fiscal_math missing {sorted(f_missing)}")

        # prev_8k: either null OR object with required fields
        prev = p.get("prev_8k")
        if prev is not None:
            if not isinstance(prev, dict):
                errors.append(f"P4 packet {accn}: prev_8k must be null or object")
            else:
                prev_missing = REQUIRED_PREV_8K_OR_NULL - set(prev.keys())
                if prev_missing:
                    errors.append(
                        f"P4 packet {accn}: prev_8k missing {sorted(prev_missing)}"
                    )

    if errors:
        for e in errors[:25]:
            print(f"  {e}")
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")
        fail(f"P4 schema: {len(errors)} violations")
    info(f"P4 schema: every packet has required fields ✓")


# ── P5: no duplicate accessions ─────────────────────────────────────
def check_no_duplicate_accessions(packets: list[dict]) -> None:
    from collections import Counter
    accs = [p["accession_8k"] for p in packets]
    counts = Counter(accs)
    dups = [a for a, c in counts.items() if c > 1]
    if dups:
        fail(
            f"P5 {len(dups)} duplicate accession_8k values across packets. "
            f"Sample: {dups[:5]}"
        )
    info(f"P5 no duplicates: {len(accs)} unique accessions ✓")


# ── P6: cross-check against ground_truth.csv ────────────────────────
def check_packets_in_ground_truth(packets: list[dict]) -> None:
    with open(GROUND_TRUTH, encoding="utf-8") as f:
        gt_accns = {r["accession_8k"] for r in csv.DictReader(f)}

    missing = [p["accession_8k"] for p in packets if p["accession_8k"] not in gt_accns]
    if missing:
        fail(
            f"P6 {len(missing)} packets reference accessions NOT in ground_truth.csv. "
            f"Sample: {missing[:5]}"
        )
    info(f"P6 cross-check: every packet's accession_8k present in ground_truth.csv ✓")


# ── P7: bucket validity ─────────────────────────────────────────────
def check_bucket_validity(packets: list[dict]) -> None:
    bad = [(p["accession_8k"], p.get("bucket")) for p in packets if p.get("bucket") not in VALID_BUCKETS]
    if bad:
        fail(
            f"P7 {len(bad)} packets have invalid bucket. "
            f"Valid: {sorted(VALID_BUCKETS)}. Sample: {bad[:5]}"
        )
    info(f"P7 bucket validity: every packet has bucket ∈ {sorted(VALID_BUCKETS)} ✓")


# ── P8: bucket count distribution ───────────────────────────────────
def check_bucket_counts(packets: list[dict]) -> None:
    from collections import Counter
    actual = Counter(p["bucket"] for p in packets)
    over: list[str] = []
    under: list[str] = []
    for b, target in TARGET_BUCKET_COUNTS.items():
        got = actual.get(b, 0)
        if b != "random" and got > target:
            over.append(f"{b}: got {got} > target {target}")
        elif got < target:
            under.append(f"{b}: got {got} < target {target}")
    if over:
        fail(f"P8 bucket counts EXCEED targets (cherry-picking?): {over}")
    if under:
        # Shortfall is allowed if SAMPLING_REPORT.md documents it.
        # We just warn — the human reviewer is the final judge.
        info(
            f"P8 bucket counts: shortfalls present (allowed if "
            f"SAMPLING_REPORT.md documents): {under}"
        )
    else:
        info("P8 bucket counts: every bucket meets target ✓")


# ── P9: human_verdict must be null ──────────────────────────────────
def check_human_verdict_unfilled(packets: list[dict]) -> None:
    bad = [p["accession_8k"] for p in packets if p.get("human_verdict") is not None]
    if bad:
        fail(
            f"P9 {len(bad)} packets have human_verdict pre-filled by Codex "
            f"(Codex must NOT fill verdicts; that's the human's job). "
            f"Sample: {bad[:5]}"
        )
    info(f"P9 human_verdict: all null ✓")


# ── P10: URL fields ─────────────────────────────────────────────────
_CIK_BROWSE_RE = re.compile(
    r"^https://www\.sec\.gov/cgi-bin/browse-edgar\?action=getcompany&CIK="
)
_ARCHIVE_RE = re.compile(
    r"^https://www\.sec\.gov/Archives/edgar/data/\d+/\d+/?$"
)


def check_urls(packets: list[dict]) -> None:
    errors: list[str] = []
    for p in packets:
        accn = p["accession_8k"]
        f8u = p.get("filed_8k_url", "")
        if not isinstance(f8u, str) or not _CIK_BROWSE_RE.match(f8u):
            errors.append(f"P10 packet {accn}: filed_8k_url malformed: {f8u!r}")
        au = p.get("accession_archive_url", "")
        if not isinstance(au, str) or not _ARCHIVE_RE.match(au):
            errors.append(f"P10 packet {accn}: accession_archive_url malformed: {au!r}")
    if errors:
        for e in errors[:20]:
            print(f"  {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        fail(f"P10 URL checks: {len(errors)} violations")
    info(f"P10 URL fields: all packets have well-formed SEC URLs ✓")


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    print("=== Goal 1.5 audit-packet structural verifier ===")
    print(f"Packets JSON: {PACKETS_JSON}")
    print()

    check_verifier_git_clean()
    check_deliverables_exist()
    packets = load_packets()
    check_schema(packets)
    check_no_duplicate_accessions(packets)
    check_packets_in_ground_truth(packets)
    check_bucket_validity(packets)
    check_bucket_counts(packets)
    check_human_verdict_unfilled(packets)
    check_urls(packets)

    print()
    info("=" * 60)
    info("ALL CHECKS PASSED — Goal 1.5 packets ready for human review")
    info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
