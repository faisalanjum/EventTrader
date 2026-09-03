#!/usr/bin/env python3
"""ONE-TIME RECOVERY TOOL, not a proof step: rebuild invrev_run4/transport_proof_replacements.json
exactly, from the accepted transcript prefix and the durable review-run files.

The ledger was created and amended by saved programs that name it, and ALSO by runs of
the scratch script harvest.py - whose commands never name the ledger, so a text-derived
route misses them. The route here is DERIVED, not hand-listed: every record that names
the ledger, plus every record that executes the scratch script once the script's own
replayed text names the ledger. Harvest runs launch nothing: each post-processes one
already-saved workflow result. The result is checked against what history itself
printed (record 30179 listed every row's identities) before it is written.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import sys

R = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [R, os.path.join(R, "ledger")]
import replay_transcript as RT                                   # noqa: E402
import chrono_replay as CR                                       # noqa: E402

LEDGER = RT._SCRATCH + "/invrev_run4/transport_proof_replacements.json"
HARVEST = RT._SCRATCH + "/harvest.py"
DEST = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments",
                    "invrev_run4", "transport_proof_replacements.json")
END = 111621                       # the accepted prefix's last row
PRINTED = 30179                    # history printed every ledger row here


def _replay(full, recs, base=""):
    import traceback
    text, side = base, {}
    for n, rec in recs:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                text, _ = RT.apply_saved_edits(text, {n: rec}, full, side=side)
        except Exception:
            # the record and the full traceback, never a bare message: a refusal is
            # only actionable when the program line and the resolved module are named
            print("REFUSED at record %d" % n)
            traceback.print_exc()
            raise
        print("  record %d ok -> %d bytes" % (n, len(text.encode("utf-8"))), flush=True)
    return text


def _bash_records(first, upto):
    out = []
    with io.open(RT.TRANSCRIPT, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if n < first:
                continue
            if n > upto:
                break
            if '"Bash"' not in line:
                continue
            rec = json.loads(line)
            for b in ((rec.get("message") or {}).get("content") or []):
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Bash":
                    out.append((n, rec, b.get("input", {}).get("command", "")))
    return out


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        hrecs, _ = CR.route_records(HARVEST, 1, END)
    # the first record after which harvest's own text names the ledger
    text, side, names_from = "", {}, None
    for n, rec in hrecs:
        with contextlib.redirect_stdout(io.StringIO()):
            text, _ = RT.apply_saved_edits(text, {n: rec}, HARVEST, side=side)
        if names_from is None and "transport_proof_replacements" in text:
            names_from = n
    print("harvest.py route:", [n for n, _ in hrecs], "| names the ledger from record", names_from)
    with contextlib.redirect_stdout(io.StringIO()):
        lrecs, _ = CR.route_records(LEDGER, 1, END)
    runs = [(n, rec) for n, rec, cmd in _bash_records(names_from or END, END)
            if re.search(r"""python3?\s+(?:-B\s+)?["']?\$?S?/?[^"'\s]*harvest\.py""", cmd)
            or "harvest.py" in RT.expand(cmd, RT.shell_vars(cmd))]
    merged = sorted({n: rec for n, rec in list(lrecs) + runs}.items())
    print("ledger route: %d text-named + %d harvest runs -> %d records" % (len(lrecs), len(runs), len(merged)))
    text = _replay(LEDGER, merged)
    rows = json.loads(text)
    got = [(r.get("source_id"), (r.get("quarantined_call") or {}).get("run_id")) for r in rows]
    printed = RT.saved_result(PRINTED) or ""
    want = [(m.group(1), m.group(2)) for m in re.finditer(r"^(\S+) (wf_[0-9a-f-]+) ", printed, re.M)]
    print("rows recovered:", got)
    print("rows history printed at %d:" % PRINTED, want)
    if got != want:
        raise SystemExit("FAIL: the recovered ledger does not carry the identities history printed")
    raw = text.encode("utf-8")
    io.open(DEST, "wb").write(raw)
    sha = hashlib.sha256(raw).hexdigest()
    rel = os.path.relpath(DEST, R)
    tsv = os.path.join(R, "evidence", "RESUME_INPUTS.tsv")
    lines = [l for l in io.open(tsv, encoding="utf-8").read().split("\n") if l and not l.startswith(rel + "\t")]
    lines.append("%s\t%d\t%s\t%s" % (rel, len(raw), sha,
                 "replayed: records %s (recover_ledger.py), identities == saved output of row %d"
                 % ([n for n, _ in merged], PRINTED)))
    io.open(tsv, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("written: %s %d bytes sha %s" % (rel, len(raw), sha))


def _dump_misses():
    """Every object the world was asked for and did not hold, MEASURED by this run:
    the store extension and the mount recovery consume these lists, so a hand-typed
    object name never enters the evidence. Written even when the run fails."""
    out = os.path.join(os.environ.get("RECOVER_SCRATCH", "/tmp/claude-1000"), "recover_ledger_misses.json")
    d = {"show_objects": sorted(set(RT.STORE_MISSES)), "mount_misses": sorted(set(map(str, RT.MOUNT_MISSES))),
         "import_misses": sorted(set(map(str, RT.IMPORT_MISSES))),
         "sibling_refusals": [{k: v for k, v in r.items() if k != "traceback"} for r in CR.SIBLING_REFUSALS]}
    io.open(out, "w", encoding="utf-8").write(json.dumps(d, indent=1, sort_keys=True))
    print("misses: %d store, %d mount, %d import, %d sibling refusals -> %s"
          % (len(d["show_objects"]), len(d["mount_misses"]), len(d["import_misses"]), len(d["sibling_refusals"]), out))


if __name__ == "__main__":
    try:
        main()
    finally:
        _dump_misses()
