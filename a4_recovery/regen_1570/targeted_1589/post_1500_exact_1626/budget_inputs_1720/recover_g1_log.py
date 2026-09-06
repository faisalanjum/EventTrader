# -*- coding: utf-8 -*-
"""Recover the SUCCESSFUL G1 two-step log from the ORIGINAL captured tool result
(Codex SEQ 1722 item 1).

The log my runner overwrote survives verbatim inside the reviewer's own recorded
tool output. Nothing here is retyped: the record is decoded, the one output chunk
is taken by its stated id, and the exact contiguous block from the first step
verdict through the final preserved line is copied out and required to hash to the
value the reviewer independently extracted. A miss writes nothing.
"""
import hashlib, io, json, os, sys

ROLL = ("/home/faisal/.codex/sessions/2026/08/31/"
        "rollout-2026-08-31T10-11-29-01a05829-3086-73e0-89c9-e5773b322d80.jsonl")
OUT = sys.argv[1]
LINE, CHUNK = 145056, "24bb9e"
FIRST, LAST = "ok   64861_v16_build", "PRESERVED 2 artifacts"
WANT = "11b8115bd0663ee37155025349e8d33e952f0033c0c63a1208d735b618b7641a"

with io.open(ROLL, encoding="utf-8") as fh:
    for n, ln in enumerate(fh, 1):
        if n == LINE:
            rec = json.loads(ln)
            break
    else:
        sys.exit("REFUSE: line %d absent" % LINE)

pay = rec["payload"]
if pay.get("type") != "custom_tool_call_output":
    sys.exit("REFUSE: line %d is %s" % (LINE, pay.get("type")))

chunks = [c["text"] for c in pay["output"]
          if c.get("type") == "input_text" and ('"chunk_id":"%s"' % CHUNK) in c.get("text", "")]
if len(chunks) != 1:
    sys.exit("REFUSE: %d output chunks carry chunk_id %s" % (len(chunks), CHUNK))
doc = json.loads(chunks[0])
if doc.get("chunk_id") != CHUNK:
    sys.exit("REFUSE: decoded chunk_id is %r" % doc.get("chunk_id"))

# the captured stdout, wherever this record carries it
body = None
for k, v in doc.items():
    if isinstance(v, str) and FIRST in v and LAST in v:
        body, field = v, k
        break
if body is None:
    sys.exit("REFUSE: no field of the decoded chunk carries the block")

lines = body.splitlines(True)
starts = [i for i, l in enumerate(lines) if l.startswith(FIRST)]
ends = [i for i, l in enumerate(lines) if l.startswith(LAST)]
if len(starts) != 1 or len(ends) != 1:
    sys.exit("REFUSE: %d starts / %d ends (need exactly one of each)" % (len(starts), len(ends)))
block = "".join(lines[starts[0]:ends[0] + 1])
if not block.endswith("\n"):
    block += "\n"
got = hashlib.sha256(block.encode("utf-8")).hexdigest()
if got != WANT:
    sys.exit("REFUSE: block is %s over %d lines, not the required %s"
             % (got[:16], block.count("\n"), WANT[:16]))
if os.path.exists(OUT):
    sys.exit("REFUSE: %s exists; evidence is never overwritten" % OUT)
io.open(OUT, "w", encoding="utf-8", newline="").write(block)
print("recovered from %s field %r: %d lines, sha256 %s" % (CHUNK, field, block.count("\n"), got))
print(block, end="")
