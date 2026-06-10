"""TDD for chunk_company_sources.py — the §8/§12.2/§12.5 layered-fallback chunker.

Invariants under test:
- byte-exact conservation: ordered concat(parts) == event_text, always (§8.7c)
- ladder: whole -> natural units -> paragraph -> sentence -> char; ALWAYS finds a split
- order preserved; part_index contiguous 1..part_count; parts <= budget
- KPIs ride in chunk_001 only; chunk packing groups whole small events
- chunks_manifest.json rows per §12.5 (sha256 of part content bytes)
- deterministic across runs; --verify mode green on intact output, red on corruption
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from chunk_company_sources import build_event_text, chunk_run  # noqa: E402

PY = sys.executable
CLI = str(WORKFLOWS / "chunk_company_sources.py")


def report_event(source_id, sections=None, ex991=None, is_earnings=False, desc=""):
    return {"source_id": source_id, "source_type": "8-K" if is_earnings else "10-K",
            "date": "2026-01-01", "daily_stock": 1.0, "high_signal": False,
            "is_earnings": is_earnings, "items": "2.02" if is_earnings else "",
            "description": desc, "sections": sections or [], "ex991": ex991}


def trans_event(source_id, prepared=None, qa=None):
    return {"source_id": source_id, "source_type": "transcript", "date": "2026-01-02",
            "daily_stock": 0.5, "high_signal": False, "is_earnings": False,
            "fy": "2026", "q": "1", "prepared": prepared, "qa_exchanges": qa or []}


def write_sources(tmp_path, ticker, events, kpis=None):
    sd = tmp_path / "sources"
    sd.mkdir(exist_ok=True)
    (sd / f"{ticker}.json").write_text(json.dumps(
        {"ticker": ticker, "fiscal_kpis": kpis or [], "events": events}))
    return tmp_path


def read_chunks(tmp_path, ticker):
    return [json.loads(f.read_text())
            for f in sorted((tmp_path / "chunks").glob(f"{ticker}__chunk_*.json"))]


def reassemble(tmp_path, ticker, source_id):
    parts = []
    for ch in read_chunks(tmp_path, ticker):
        for e in ch["events"]:
            if e["source_id"] == source_id:
                parts.append((e["part_index"], e["content"]))
    parts.sort()
    return "".join(p for _, p in parts)


def test_event_text_join_order_report():
    ev = report_event("r1", sections=[{"name": "RiskFactors", "content": "risk text"}],
                      ex991="press body", is_earnings=True, desc="d")
    text = build_event_text(ev)
    assert text == ("FORM: 8-K\n\nITEMS: 2.02\n\nDESC: d\n\n"
                    "PRESS RELEASE (EX-99.1):\npress body\n\n[RiskFactors]\nrisk text")


def test_event_text_join_order_transcript():
    ev = trans_event("t1", prepared="hello", qa=["q1 text", "q2 text"])
    assert build_event_text(ev) == "PREPARED REMARKS:\nhello\n\nQ&A:\nq1 text\n---\nq2 text"


def test_small_events_pack_whole_into_one_chunk(tmp_path):
    write_sources(tmp_path, "AAA", [report_event("r1", sections=[{"name": "Business", "content": "x" * 100}]),
                                    trans_event("t1", prepared="y" * 100)], kpis=["Same Store Sales"])
    chunk_run(tmp_path, budget=40000)
    chunks = read_chunks(tmp_path, "AAA")
    assert len(chunks) == 1
    assert chunks[0]["fiscal_kpis"] == ["Same Store Sales"]
    assert [e["part_count"] for e in chunks[0]["events"]] == [1, 1]
    man = json.loads((tmp_path / "chunks_manifest.json").read_text())
    assert all(r["split_level"] == "whole" for r in man["rows"])


def test_big_event_splits_at_natural_units_and_conserves(tmp_path):
    secs = [{"name": f"S{i}", "content": f"sec{i} " + "a" * 900} for i in range(5)]
    write_sources(tmp_path, "BBB", [report_event("r1", sections=secs)])
    chunk_run(tmp_path, budget=2000)
    ev = report_event("r1", sections=secs)
    assert reassemble(tmp_path, "BBB", "r1") == build_event_text(ev)  # §8.7c byte-exact
    man = json.loads((tmp_path / "chunks_manifest.json").read_text())
    rows = [r for r in man["rows"] if r["source_id"] == "r1"]
    assert rows[0]["part_count"] > 1
    assert sorted(r["part_index"] for r in rows) == list(range(1, rows[0]["part_count"] + 1))
    assert all(r["split_level"] in ("natural", "paragraph", "sentence", "char") for r in rows)
    assert all((r["char_end"] - r["char_start"]) <= 2000 for r in rows)


def test_paragraph_then_sentence_then_char_fallback(tmp_path):
    # one giant section with paragraphs > budget, sentences > budget -> char rung must fire
    para = ("word " * 300).strip()                      # ~1500 chars, no sentence ends
    giant = "\n\n".join([para] * 3)                      # paragraphs of ~1500 with blank lines
    write_sources(tmp_path, "CCC", [report_event("r1", sections=[{"name": "MDA", "content": giant}])])
    chunk_run(tmp_path, budget=600)                      # < paragraph size, no '.' -> char rung
    ev = report_event("r1", sections=[{"name": "MDA", "content": giant}])
    assert reassemble(tmp_path, "CCC", "r1") == build_event_text(ev)
    man = json.loads((tmp_path / "chunks_manifest.json").read_text())
    assert any(r["split_level"] == "char" for r in man["rows"])
    sent = "Alpha is one. " * 100                        # sentences ~14 chars, paragraph ~1400
    write_sources(tmp_path, "DDD", [report_event("r2", sections=[{"name": "MDA", "content": sent.strip()}])])
    chunk_run(tmp_path, budget=600)
    man = json.loads((tmp_path / "chunks_manifest.json").read_text())
    rows = [r for r in man["rows"] if r["source_id"] == "r2"]
    assert rows and all(r["split_level"] in ("sentence", "paragraph") for r in rows)
    ev2 = report_event("r2", sections=[{"name": "MDA", "content": sent.strip()}])
    assert reassemble(tmp_path, "DDD", "r2") == build_event_text(ev2)


def test_manifest_sha_matches_content(tmp_path):
    write_sources(tmp_path, "EEE", [trans_event("t1", prepared="p" * 50, qa=["q" * 50])])
    chunk_run(tmp_path, budget=40000)
    man = json.loads((tmp_path / "chunks_manifest.json").read_text())
    ch = read_chunks(tmp_path, "EEE")[0]
    for row in man["rows"]:
        e = next(e for e in ch["events"] if e["source_id"] == row["source_id"]
                 and e["part_index"] == row["part_index"])
        assert hashlib.sha256(e["content"].encode("utf-8")).hexdigest() == row["sha256"]


def test_cli_deterministic_and_verify(tmp_path):
    secs = [{"name": f"S{i}", "content": "z" * 1500} for i in range(4)]
    write_sources(tmp_path, "FFF", [report_event("r1", sections=secs)])
    shas = []
    for _ in range(2):
        out = subprocess.run([PY, CLI, str(tmp_path), "--budget", "2000"],
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        blob = b"".join(f.read_bytes() for f in sorted((tmp_path / "chunks").glob("*.json")))
        shas.append(hashlib.sha256(blob).hexdigest())
    assert shas[0] == shas[1]
    ver = subprocess.run([PY, CLI, str(tmp_path), "--budget", "2000", "--verify"],
                         capture_output=True, text=True)
    assert ver.returncode == 0 and "VERIFY OK" in ver.stdout
    # corrupt one chunk -> verify must fail
    f = sorted((tmp_path / "chunks").glob("FFF__chunk_*.json"))[0]
    d = json.loads(f.read_text())
    d["events"][0]["content"] = d["events"][0]["content"][:-1] + "X"
    f.write_text(json.dumps(d))
    bad = subprocess.run([PY, CLI, str(tmp_path), "--budget", "2000", "--verify"],
                         capture_output=True, text=True)
    assert bad.returncode == 1


def test_summary_line_lists_chunk_ids(tmp_path):
    write_sources(tmp_path, "GGG", [trans_event("t1", prepared="p" * 10)])
    out = subprocess.run([PY, CLI, str(tmp_path)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    summary = json.loads(out.stdout.strip().splitlines()[-1])
    assert summary["chunk_ids"] == ["GGG__chunk_001"]
    assert summary["per_ticker"] == {"GGG": 1}
