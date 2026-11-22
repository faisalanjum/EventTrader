# Step 1 · Gather filing context

Can someone who sees one filing piece and its selected context recover every statement and its qualifications? Code carries the original locations and recorded layout. One AI sees the whole filing and returns piece numbers. Step 2 separates the claims anchored in the main piece and tests Decider for type and details. A passage may supply essential evidence to several groups. [Reader prompt](step1_prompt.txt) · [Driver rules](../../../DRIVER_RULES.md) · [Base and copies](../../BaseAndCopies.md)

**Live result, November 21, 2026.** Four and eight copies each returned 340 usable answers and kept the needed details on the same 14 pieces checked. In a separate audit across four filings, 13 of 100 random pieces still lacked meaning after follow-up. [Random sample and batch-size results](RANDOM_AUDIT.md) · [Original pilot](RESULTS.md) · [Before production](#6-before-production)

## What stays the same across filings

- Number the original pieces once per source version. Keep their order, wording, table layout, images, source links and evidence locations. Show recorded table spans and supply the other parts of the same original paragraph together. Each assigned piece keeps its own answer. A split lead-in may only introduce a table, and a continuation may contain an additional statement of its own. [Saved structure](../../../../../../../driver/prepare/convert/edgartools_html.py)
- For one assignment that fits, send the complete filing with WORK in one call. For several, load the complete filing once and fork from that base. Each copy receives only its assigned numbers and can select context anywhere in that version. Store shared pieces once and keep links by number. In a full run, assign each piece once. The repeat below measures agreement during development.
- Follow a reference only if it supplies something needed to understand a statement anchored in the main piece. Leave optional details with the piece that states them. After searching, mark the group `incomplete` if unreadable or missing material from this filing prevents a complete reading. Retain usable evidence and mark uncertain links with `?`. A reference to another publication alone leaves the status unchanged.
- Step 2 accounts for each marked number in the covered originals, including numbers in skipped pieces. Count a source occurrence once across overlapping groups. Record a fact, supporting use, non-fact reason or unresolved outcome. Word-only disclosures receive the same source review.

## 1. Prepare the pilot

Use Installed Building Products’ 10-K filed February 26, 2026, accession `0001580905-26-000004`. The fixture has 1,350 pieces in seven filed HTML documents, plus the original chart. The commands below are for this archived fixture. Only the prompt and the evidence rules carry forward. [Fixture inventory](../2026-11-12_base_and_copies_claude/fable_reader_tests_2026-11-13_local/README.md) · [Numbered filing](../2026-11-12_base_and_copies_claude/fable_reader_tests_2026-11-13_local/real10k_view.txt)

Run from the repository root in one shell. This block makes the input offline. It uses the saved filing reader’s rows, columns, spans and paragraph membership. Its older text display showed only a cell’s starting column. The original records remain available by file, unit and byte location.

~~~bash
cd /home/faisal/EventMarketDB
export IBP_CONTEXT_EXPERIMENTS="$PWD/.claude/plans/Drivers/DriversFinal/DriverWorkflow/Experiments"
export IBP_CONTEXT_PLAN="$IBP_CONTEXT_EXPERIMENTS/2026-11-21_filing_context"
export IBP_CONTEXT_ARCHIVE="$IBP_CONTEXT_EXPERIMENTS/2026-11-12_base_and_copies_claude/fable_reader_tests_2026-11-13_local"
export REAL_JOB="$IBP_CONTEXT_ARCHIVE/real10k_run2/job_1"
export PROBE_RUN="$(mktemp -d /tmp/ibp-context.XXXXXXXX)"
export IBP_CONTEXT_EFFORT=high

venv/bin/python -B - <<'PY'
import base64
import gzip
import hashlib
import json
import os
import sys
from collections import defaultdict
from operator import itemgetter
from pathlib import Path
from driver.prepare.reconstruct import _first_byte

run = Path(os.environ["PROBE_RUN"])
archive = Path(os.environ["IBP_CONTEXT_ARCHIVE"])
sys.path.insert(0, str(archive / "real10k_tools"))
import real

def extent(start, size):
    return str(start) if size == 1 else f"{start}-{start + size - 1}"

def annotated(text, marks):
    return text + " [" + " | ".join(dict.fromkeys(marks)) + "]" if marks else text

def table_text(unit, markings):
    rows = defaultdict(list)
    for cell in sorted(unit["cells"], key=itemgetter("r", "c")):
        at = _first_byte(cell)
        marks = markings.get((unit["id"], at)) if at is not None else None
        text = annotated(cell["text"], marks)
        if text.strip():
            col = "c" + extent(cell["c"], cell["cs"])
            if cell["rs"] > 1:
                col += ",r" + extent(cell["r"], cell["rs"])
            rows[cell["r"]].append(f"[{col}] {text}")
    return "\n".join(f"r{r}: " + " · ".join(cells) for r, cells in rows.items())

version = "aabf3ebf23d699a42a7f979ce1e7a2f5d4e9f31a37068760a382de31823a6733"
package = archive / "real10k/package/versions/0001580905-26-000004" / version
members = {m["filename"]: m for m in json.loads((package / "manifest.json").read_bytes())["members"]}
with gzip.open(package / "submission.txt.gz") as submission:
    assert hashlib.sha256(submission.read()).hexdigest() == version
metadata = {"company": "Installed Building Products, Inc.", "form": "10-K", "filed": "2026-02-26", "version": version}
files = json.loads((real.JOB / "RESULT.json").read_bytes())["rows"]
pieces, content = {}, []
lines = ["LOAD", " | ".join(metadata[k] for k in ("company", "form", "filed"))]
for file in files:
    name = file["file_id"]
    doc = real.route(file["ordinal"])
    assert file["outcome"] == "verified_saved_output" and doc["status"] == "OK"
    assert doc["file_id"] == name and doc["sha256"] == members[name]["sha256"]
    first = len(pieces) + 1
    paragraphs = defaultdict(list)
    for number, unit in enumerate(doc["units"], first):
        if "paragraph" in unit:
            paragraphs[unit["paragraph"]].append(number)
    markings = defaultdict(list)
    for symbol in doc["source_symbols"]["records"]:
        if symbol.get("status") == "decoded":
            for owner in symbol["owners"]:
                markings[owner["unit"], owner.get("cell")].append(f"{symbol['raw']} → {symbol['unicode']['name']}")
    for link in doc["source_links"]:
        for owner in link["owners"]:
            markings[owner["unit"], owner.get("cell")].append("link " + link["href"])
    lines.append("FILE " + name)
    for number, unit in enumerate(doc["units"], first):
        kind = unit["kind"]
        if kind == "table":
            body = table_text(unit, markings)
        elif kind == "image":
            body = "Image " + unit["src"] + " · " + (unit.get("alt") or "")
        else:
            assert kind in ("text", "heading"), kind
            body = unit["text"]
        body = annotated(body, markings.get((unit["id"], None)))
        location = unit["anchor"]
        piece = {"file": name, "unit": unit["id"], "bytes": [location["byte_start"], location["byte_end_exclusive"]], "body": body}
        pieces[number] = piece
        lines.append(f"PIECE {number}")
        if "paragraph" in unit:
            piece["paragraph"] = paragraphs[unit["paragraph"]]
            lines.append("SAME PARAGRAPH " + " ".join(map(str, piece["paragraph"])))
        lines.extend((body, ""))
        if kind == "image":
            image = archive / "real10k_pic" / unit["src"]
            data = image.read_bytes()
            assert hashlib.sha256(data).hexdigest() == members[image.name]["sha256"] == unit["input"]["input_sha256"]
            piece["image"] = str(image)
            content.append({"type": "text", "text": "\n".join(lines)})
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(data).decode("ascii")}})
            lines = []
content.append({"type": "text", "text": "\n".join(lines)})
assert len(files) == 7 and len(pieces) == 1350 and sum("image" in p for p in pieces.values()) == 1
a = [7, 504, 511, 518, 547, 655, 660, 724, 730, 1009, 1018, 1291]
b = [6, 188, 510, 512, 516, 548, 570, 652, 1010, 1011, 1019, 1267]
assignments = {"A1": a, "A2": a, "B": b}
(run / "index.json").write_text(json.dumps({"metadata": metadata, "pieces": pieces}, ensure_ascii=False))
(run / "assignments.json").write_text(json.dumps(assignments))
message = {"type": "user", "message": {"role": "user", "content": content}}
(run / "base-input.jsonl").write_text(json.dumps(message, ensure_ascii=False) + "\n")
(run / "shared-prompt.txt").write_bytes((Path(os.environ["IBP_CONTEXT_PLAN"]) / "step1_prompt.txt").read_bytes())
print(run, len(pieces), "pieces,", sum(len(c.get("text", "")) for c in content), "text characters, plus the image and prompt")
PY
~~~

Check the prepared view against the original, including exhibits and chart placement. Identify any unique filed material the view misses. The offline check covered 1,350 pieces, 95 tables, 2,842 nonempty cells spanning rows or columns, eight split paragraphs and the original image. This view contains 473,985 text characters plus the image and prompt. Use the base call’s actual token usage and model window to assess space for the work. An oversized or damaged input stays incomplete until it can receive full coverage under rule 8.10.

## 2. Run four calls

Use Sonnet 5.5 at `high` on the subscription with paid overage disabled. A1 and A2 receive the same mixed list. B receives the other 12 pieces. This gives **24 distinct targets and 36 answer lines**. Some tables and their notes fall in different assignments. Each copy still sees them all. The lists and expected examples stay outside the base.

Use the existing call helper. The base must return exactly `READY` with the expected model and complete source. Start the three forks promptly after that check, always from the original base. Each receives the same frozen system prompt. The helper saves raw calls in the scratch folder. [Call helper](../2026-11-12_base_and_copies_claude/fable_reader_tests_2026-11-13_local/probe.py)

~~~bash
venv/bin/python -B - <<'PY'
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

run = Path(os.environ["PROBE_RUN"])
sys.path.insert(0, os.environ["IBP_CONTEXT_ARCHIVE"])
import probe

model = "claude-sonnet-5-5"
settings = dict(model=model, effort=os.environ["IBP_CONTEXT_EFFORT"], system=(run / "shared-prompt.txt").read_text())
base = probe.call("base", (run / "base-input.jsonl").read_text(), session_id=str(uuid.uuid4()),
                  flags=("--input-format", "stream-json"), **settings)
events = [json.loads(line) for line in (run / "calls/base.jsonl").read_text().splitlines() if line.strip()]
assert base["exit"] == 0 and not base["is_error"] and base["subtype"] == "success" and base["num_turns"] == 1
assert base["model"] == model and base["result"].strip() == "READY" and base["apiKeySource"] == "none"
assert all(step["model"] == model for step in base["steps"]) and "True" not in base["overage"]
assert not any("compact" in str(e.get("subtype", "")).lower() or e.get("safety_stops") for e in events)
assert any(e.get("type") == "result" and e.get("stop_reason") == "end_turn" for e in events)
def read(job):
    label, numbers = job
    work = "WORK\n" + " ".join(map(str, numbers))
    return probe.call(label, work, resume=base["session_id"], fork=True, **settings)

with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(read, json.loads((run / "assignments.json").read_text()).items()))
PY
~~~

Inspect the forks’ raw streams for the actual model, a complete response, compaction and safety stops. Record fresh, cache-write, cache-read and output tokens for each response, elapsed time, CLI version, effort and any failed attempts. Display times in `America/Toronto` with EST/EDT. A miss in the cache counts toward cost. Report subscription usage separately when measurable. [Usage accounting](../../archive/DriverWorkflow_History.md#complete-independent-cache-experiment-record)

The CLI includes the parent session in a fork’s cumulative list-price figure. Subtract the parent once per fork. The result event’s `usage` gives that call’s token counts.

## 3. Check replies and assemble the groups offline

Use A1 and B as the primary results. A2 measures agreement. Match answers by target ID. Code sorts support IDs and removes exact duplicates. If one answer is missing, malformed or gives the same link both definite and possible, keep that target open and preserve its siblings. A failed call leaves its whole assignment open. Keep raw replies. A valid `incomplete` answer retains its usable support. Groups reference the original pieces and expand only recorded paragraph membership.

The source identifies pictures. If a picture receives `useless`, leave its row open. Fork the session holding the complete filing and retry only the rejected ID. Ask for `keep` with any needed context, or `incomplete` if the picture or required material cannot be read. Score the first answer and the retry separately.

~~~bash
venv/bin/python -B - <<'PY'
import json
import os
from pathlib import Path

run = Path(os.environ["PROBE_RUN"])
pieces = json.loads((run / "index.json").read_text())["pieces"]
assignments = json.loads((run / "assignments.json").read_text())
answers, failures, groups = {}, {}, {}

def rows(label, targets):
    reply = json.loads((run / f"calls/{label}.summary.json").read_text())
    if reply["exit"] or reply["is_error"] or reply["subtype"] != "success":
        raise ValueError("call failed")
    if reply["model"] != "claude-sonnet-5-5" or reply["num_turns"] != 1 or not isinstance(reply["result"], str):
        raise ValueError("unexpected model, turn count or result")
    by_target = {str(n): [] for n in targets}
    found, issues = {}, []
    for line in reply["result"].splitlines():
        fields = line.split()
        if fields:
            if fields[0] in by_target:
                by_target[fields[0]].append(fields[1:])
            else:
                issues.append(f"unassigned or unrecognized row {line!r}")
    for n in targets:
        entries = by_target[str(n)]
        if len(entries) != 1 or not entries[0]:
            issues.append(f"{n}: expected one labeled answer, got {entries!r}")
            continue
        status, *links = entries[0]
        sure = {v for v in links if not v.endswith("?")}
        possible = {v[:-1] for v in links if v.endswith("?")}
        ids = sure | possible
        if status not in ("keep", "useless", "incomplete") or (status == "useless" and ids):
            issues.append(f"{n}: invalid label or links for {status!r}")
        elif status == "useless" and "image" in pieces[str(n)]:
            issues.append(f"{n}: original image needs a keep or incomplete answer")
        elif str(n) in ids or not all(v in pieces for v in ids) or sure & possible:
            issues.append(f"{n}: self, unknown or contradictory link in {links!r}")
        else:
            ordered = [v + ("?" if v in possible else "") for v in sorted(ids, key=int)]
            found[n] = {"status": status, "links": ordered}
    return found, issues

def with_paragraphs(numbers):
    return {other for n in numbers for other in pieces[str(n)].get("paragraph", [n])}

for label, targets in assignments.items():
    try:
        answers[label], issues = rows(label, targets)
    except (OSError, ValueError, KeyError) as error:
        failures[label] = [str(error)]
        continue
    if issues:
        failures[label] = issues
    if label in ("A1", "B"):
        for n, row in answers[label].items():
            if row["status"] == "useless":
                continue
            sure = with_paragraphs([n] + [int(v) for v in row["links"] if not v.endswith("?")])
            possible = with_paragraphs(int(v[:-1]) for v in row["links"] if v.endswith("?"))
            groups[n] = {"status": row["status"], "needed": sorted(sure - {n}), "possible": sorted(possible - sure)}

(run / "review.json").write_text(json.dumps({"answers": answers, "failures": failures, "groups": groups}))
print("Open calls or rows", failures)
print("Incomplete", [(label, n) for label, rows_ in answers.items() for n, r in rows_.items() if r["status"] == "incomplete"])
if "A1" in answers and "A2" in answers:
    compared = [n for n in assignments["A1"] if n in answers["A1"] and n in answers["A2"]]
    different = [n for n in compared if answers["A1"][n] != answers["A2"][n]]
    print("Agreements", len(compared) - len(different), "of", len(compared), "paired answers;",
          len(assignments["A1"]) - len(compared), "unpaired. Differences", different)
PY
~~~

To give a fresh reviewer one group, set `PIECE` to its main number and run this block. Include the actual image wherever the output names one. Provide just that group and its filing metadata.

~~~bash
PIECE=655 venv/bin/python -B - <<'PY'
import json
import os
from pathlib import Path

run = Path(os.environ["PROBE_RUN"])
index = json.loads((run / "index.json").read_text())
n = int(os.environ["PIECE"])
group = json.loads((run / "review.json").read_text())["groups"][str(n)]
print(index["metadata"], "main", n, group["status"])
for number in sorted([n] + group["needed"] + group["possible"]):
    p = index["pieces"][str(number)]
    role = "main" if number == n else "possible" if number in group["possible"] else "support"
    print(number, role, p["file"], p["unit"], p["bytes"], "\n", p["body"])
    if "image" in p:
        print("Show original image", p["image"])
PY
~~~

## 4. Review meaning

A fresh reviewer first describes each main piece using its group alone. A separate filing-first review checks every assigned original, including `useless` answers. No advance answer key is needed for this pilot.

1. **What meaning disappeared?** Check every statement, including word-only answers, who acted, the period, units, conditions and exceptions. Count a missing disclosure or a detail that changes its meaning.
2. **What would disappear if we removed this attachment?** Name the specific detail or uncertainty. Count wrong and redundant links. For a `?`, identify the wording, mark or layout that makes it plausible. Two different IDs can supply equally complete evidence.
3. Compare A1 and A2 by label, definite IDs and possible IDs after normalizing order and exact duplicates. Report unpaired targets. Judge each difference against the original.

Report lost meaning, support that belongs to a different claim, related but unnecessary context, and harmless label violations separately. A piece can have more than one issue. For surplus context, count the extra links and the source text they add after paragraph companions are included.

Keep these examples outside the reader prompt. [Numbered original](../2026-11-12_base_and_copies_claude/fable_reader_tests_2026-11-13_local/real10k_view.txt)

- **Headings and splits.** Piece 504 states the stock exchange and ticker in a heading. Pieces 570–571 together only introduce a table. Pieces 1018–1019 complete a statement, and 1019 also states a forecast of its own.
- **Optional detail.** Piece 655 states the number of swaps, total hedged and end date. The individual rates in 1010 add detail to those statements. Table 1010 itself needs the unit line in 1009. Judge 655’s separate statement about fair value on its own wording. Table 724 prints a reference to Note 17 with no amount on that row. That pointer alone calls for no attachment and supplies no zero.
- **Reported share count.** Table 730 with its title (728) and units (729) gives 27,327,972 diluted weighted-average shares outstanding for 2025. Removing 1192 leaves that statement intact. Its breakdown of excluded shares belongs with 1192.
- **Necessary context.** Table 512 needs 510 to explain that its figures assume a $100 investment with dividends reinvested. Check the marked notes on 516 and the revised calculation in 548 for table 547. Piece 188 credits “the Foundation” with grants, and 135 identifies the organization.
- **Source links.** In exhibit list 1267, the number 32.2 links to the CFO exhibit while its CFO description links to the CEO exhibit. Retain both original destinations with their cells. The links alone cannot settle the discrepancy.

## 5. Decide whether to expand

Advance from the pilot once every assigned row is accounted for with no open failures, all 24 primary pieces have readable, valid results, every repeat difference is explained, and the filing review finds zero lost disclosures, meaning-changing omissions or wrong or redundant links. Report counts with denominators, possible links, unresolved cases and failures. A justified possible link preserves the filing’s uncertainty. It cannot establish a definite claim.

For a broken input or technical reply, fix the cause and record any retry separately using the intact source. For a genuine reading error, correct a general ambiguity if one exists. Try `xhigh` as a separate development run only if reasoning remains the issue. Use a new base when the prompt, model or effort changes.

To measure batch size separately from release readiness, use one labeled fork at the same settings, for example pieces 500–839 (340 pieces). Use the saved base session ID and pass that same list to the row checker. Check every ID, compare overlapping pilot targets against the original, and report how much of the larger batch received a meaning review. Measure actual cache use, reasoning, output and elapsed time. For a separate distant-footnote check, AMG table 16 reports performance measures whose definitions changed as explained in note 47. AMG is a known development example. [Archived AMG evidence](../2026-11-12_base_and_copies_claude/context_reader_followup_2026-11-12/README.md)

## 6. Before production

Can a reader given only the group recover every statement in its main piece with the right meaning? The steps below are the proposed release test for gathering filing context. Final fact extraction has its own release test. [Quality rules 8.13, 8.17 and 8.18](../../../DRIVER_RULES.md)

1. **Start with known failures.** Use the saved source reviews for the 100-piece audit, including the pieces that were correctly handled. Score a piece as a material failure if it loses a disclosure or a qualification that changes its meaning, discards readable factual material, or attaches evidence belonging to another statement as if it applied. Record lost meaning and wrong context separately. Count harmless extra links and the text they add separately. Grade the initial answer and any allowed follow-up separately. [Individual reviews and failure counts](RANDOM_AUDIT.md)

2. **Choose the cheapest split that works.** Keep the full filings, prompt, model and effort identical. Split the pieces evenly with a limit of 85 per copy, then 43 per copy. These reproduce four and eight copies for 340 pieces. For the third run, keep the second run’s copy count and balance the assigned tokens. Keep each piece whole and in filing order. Reuse each source review across all three runs. Include short and long filings, distant notes, dense tables and scanned exhibits. Compare usable answers, material failures, elapsed time and full-filing cost including retries. Advance the cheapest setup that accounts for every piece and passes the meaning checks. Repeat it once on a development filing and score both runs. If none passes, fix the cause and rerun both the failures and the previously correct cases.

3. **Freeze the final test.** Fix the winning split, prompt, model, settings, reader code, retry limit, sample design, sample size and pass rule. Reserve filings from new issuers across the industries, sizes and layouts expected in use. Draw random pieces from the originals for each form being enabled (10-K, 10-Q or 8-K). Before any release calls, an independent reviewer records the statements and needed details with their original locations for the sampled pieces. Check the reviewers first on intact groups, groups missing a detail and groups with a wrong attachment. Score deliberately selected hard cases separately from the random sample.

4. **Run whole filings with saving off.** Check the source inventory, including exhibits and images, against what the reader received. Code checks every assigned ID for one usable answer and verifies every linked ID. Record technical retries, unreadable sources and anything left open. A reader who sees only the returned group describes what it says. Compare that reading with the locked source review, without revealing which setup made the group. Review discarded pieces against the originals too. A readable piece left unanswered counts as a failure. Report genuinely unreadable material as held, with the reason.

5. **Apply the release bar per form.** I recommend zero material failures in the final review, every piece accounted for and every grading dispute resolved. Among readable pieces that the original shows carry a disclosure, 300 independent, representative checks with zero failures give a one-sided 95% upper bound of 0.994% on materially bad groups. About 3,000 clean independent checks put the bound below 0.1%. Include any disclosures the AI discarded. If the draw groups many pieces within each filing, allow for shared filing errors when computing the bound. A bound above the target leaves that form unqualified. Report counts and denominators, held items, extra context and measured cost per form. Stop early on a confirmed material failure. A pass requires the full frozen sample. Test any general fix against the known cases and qualify the changed setup on fresh filings.
