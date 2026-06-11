#!/usr/bin/env python3
"""ONE-OFF rescue (2026-06-11): rebuild repair_review.json for the Arm-1 batched run
wf_b94d7063-212 from the workflow agents' machine-recorded StructuredOutput inputs
(harness-written agent-*.jsonl transcripts) — ZERO LLM retyping anywhere in the byte
path. The original relay clerk's single-shot Write of the 529-row review JSON was
truncated by its output-token limit; its hand re-transcription drifted >=1 byte and
apply's --expect h32 gate (rightly) refused it.

Proof gate: the rebuilt string must hit the ORIGINAL pinned expect (rv=529,
h32=3294346535 — recorded in the workflow failure message) or NOTHING is written.
A hash hit proves byte-identity with the source string the workflow itself built.

Replicates repair_duplicates.js assembly EXACTLY (read the lane code before touching):
  rows      = batch verdicts concatenated by batch id ascending, each batch's rows in
              the judge's emitted order (JS: parallel() preserves input order; rows
              pushed in verdict-array order).
  finalRows = non-SAME proposer rows pass through UNCHANGED (emitted key order);
              proposer-SAME rows are REPLACED by the literal object
              { idx, a: <pinned cand a>, b: <pinned cand b>, verdict: <confirm verdict>,
                why: <confirm why>, confirmed: true }.
              (This run had ZERO refute2 agents -> no high_blast keys, no UNCLEAR flips.)
  reviews   = finalRows with why -> clean(why)  (clean: U+0000-U+001F -> space)
  bytes     = JSON.stringify({reviews}) == json.dumps(..., ensure_ascii=False,
              separators=(",",":")) in insertion order (NOT sort_keys).
"""
import glob
import json
import re
import sys
from pathlib import Path

from fold_catalogs import norm
from repair_duplicates import h32

SUCCESS_MARK = "Structured output provided successfully"


def clean(s):
    """JS: (s || '').replace(/[\u0000-\u001f]/g, ' ')"""
    return re.sub(r"[\x00-\x1f]", " ", s or "")


def prompt_text(jsonl_path):
    j = json.loads(open(jsonl_path, encoding="utf-8").readline())
    c = (j.get("message") or {}).get("content")
    return c if isinstance(c, str) else json.dumps(c)


def accepted_structured_output(jsonl_path):
    """The LAST StructuredOutput tool_use whose tool_result reported success —
    the validated object exactly as the workflow's agent() call received it."""
    pending, accepted = {}, None
    for line in open(jsonl_path, encoding="utf-8"):
        j = json.loads(line)
        content = (j.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == "StructuredOutput":
                pending[b.get("id")] = b.get("input")
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                res = b.get("content")
                txt = res if isinstance(res, str) else json.dumps(res)
                if SUCCESS_MARK in txt:
                    accepted = pending[b.get("tool_use_id")]
    if accepted is None:
        raise SystemExit(f"RESCUE FAIL: no accepted StructuredOutput in {jsonl_path}")
    return accepted


def main():
    wf_dir, run_dir, expect = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    m = re.fullmatch(r"rv=(\d+),h32=(\d+)", expect)
    if not m:
        raise SystemExit(f"RESCUE FAIL: bad --expect format: {expect}")
    expect_rv, expect_h32 = int(m.group(1)), int(m.group(2))

    cands = json.load(open(run_dir / "repair_candidates.json")).get("candidates") or []
    plan = json.load(open(run_dir / "repair_plan.json"))
    planned = {b["id"]: list(b["idx"]) for b in plan["batches"]}

    batch_files, confirm_files = {}, []
    for f in sorted(glob.glob(f"{wf_dir}/agent-*.jsonl")):
        p = prompt_text(f)
        bm = re.search(r"repair_batches/batch_(\d{4})\.json", p)
        if bm:
            bid = int(bm.group(1))
            if bid in batch_files:
                raise SystemExit(f"RESCUE FAIL: two transcripts claim batch {bid}")
            batch_files[bid] = f
        elif "A deterministic suggester found a possible missed duplicate pair" in p:
            confirm_files.append(f)

    if sorted(batch_files) != sorted(planned):
        raise SystemExit(f"RESCUE FAIL: batch transcripts {sorted(batch_files)} != plan {sorted(planned)}")

    # rows: concat batch verdicts by bid ascending, emitted order within each batch
    rows = []
    for bid in sorted(batch_files):
        verdicts = accepted_structured_output(batch_files[bid]).get("verdicts") or []
        got = [v["idx"] for v in verdicts]
        if sorted(got) != sorted(planned[bid]) or len(set(got)) != len(got):
            raise SystemExit(f"RESCUE FAIL: batch {bid} idx {got} != planned {planned[bid]}")
        for v in verdicts:
            if v.get("verdict") not in ("SAME", "DIFFERENT", "UNCLEAR"):
                raise SystemExit(f"RESCUE FAIL: batch {bid} idx {v.get('idx')} bad verdict {v.get('verdict')!r}")
            if norm(v.get("a")) != norm(cands[v["idx"]].get("a")) or norm(v.get("b")) != norm(cands[v["idx"]].get("b")):
                raise SystemExit(f"RESCUE FAIL: batch {bid} idx {v['idx']} names {v.get('a')!r}|{v.get('b')!r} != pinned candidate")
        rows.extend(verdicts)
    if len(rows) != len(cands):
        raise SystemExit(f"RESCUE FAIL: {len(rows)} rows != {len(cands)} pinned candidates")

    # confirm verdicts: map each confirm transcript to its idx via normalized (a,b)
    same_idx = [r["idx"] for r in rows if r["verdict"] == "SAME"]
    key_to_idx = {}
    for i in same_idx:
        k = (norm(cands[i]["a"]), norm(cands[i]["b"]))
        if k in key_to_idx:
            raise SystemExit(f"RESCUE FAIL: SAME pairs {key_to_idx[k]} and {i} share normalized names — cannot map confirms")
        key_to_idx[k] = i
    if len(confirm_files) != len(same_idx):
        raise SystemExit(f"RESCUE FAIL: {len(confirm_files)} confirm transcripts != {len(same_idx)} proposer SAMEs")
    confirm_by_idx = {}
    for f in confirm_files:
        v = accepted_structured_output(f)
        k = (norm(v.get("a")), norm(v.get("b")))
        if k not in key_to_idx:
            raise SystemExit(f"RESCUE FAIL: confirm {v.get('a')!r}|{v.get('b')!r} matches no proposer-SAME pair")
        i = key_to_idx[k]
        if i in confirm_by_idx:
            raise SystemExit(f"RESCUE FAIL: two confirm transcripts map to idx {i}")
        if v.get("verdict") not in ("SAME", "DIFFERENT", "UNCLEAR"):
            raise SystemExit(f"RESCUE FAIL: confirm idx {i} bad verdict {v.get('verdict')!r}")
        confirm_by_idx[i] = v
    missing = [i for i in same_idx if i not in confirm_by_idx]
    if missing:
        raise SystemExit(f"RESCUE FAIL: no confirm transcript for SAME idx {missing}")

    # finalRows + clean(why), JS key orders preserved
    reviews = []
    for r in rows:
        if r["verdict"] == "SAME":
            cf = confirm_by_idx[r["idx"]]
            row = {"idx": r["idx"], "a": cands[r["idx"]]["a"], "b": cands[r["idx"]]["b"],
                   "verdict": cf["verdict"], "why": cf["why"], "confirmed": True}
        else:
            row = dict(r)                  # emitted key order preserved
        row["why"] = clean(row["why"])
        reviews.append(row)

    review_json = json.dumps({"reviews": reviews}, ensure_ascii=False, separators=(",", ":"))
    rv, got_h32 = len(reviews), h32(review_json)
    print(json.dumps({"rv": rv, "h32": got_h32, "expect_rv": expect_rv, "expect_h32": expect_h32,
                      "proposer_same": len(same_idx),
                      "confirmed_same": sum(1 for r in reviews if r["verdict"] == "SAME"),
                      "match": rv == expect_rv and got_h32 == expect_h32}))
    if rv != expect_rv or got_h32 != expect_h32:
        raise SystemExit("RESCUE FAIL: rebuilt bytes do not hit the pinned expect — NOTHING written (fail-close)")
    out = run_dir / "repair_review.json"
    out.write_text(review_json, encoding="utf-8")
    print(f"RESCUE OK: byte-identical review written to {out}")


if __name__ == "__main__":
    main()
