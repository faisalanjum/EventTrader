# Prepare

Preserve original files, extract source-linked HTML/XML content, and attach picture
inputs and raw readings. These are reusable functions; the caller owns the browser,
input inventory, output storage and job lifecycle.

```text
original package -> get -> exact member bytes
                            |-- convert -> HTML/XML content + source evidence
                            `-- pictures -> image inputs + raw readings + packets
```

| Code | Responsibility and entry point |
|---|---|
| `get/` | Verified acquisition, member inventory and lossless storage. See [usage](get/README.md). |
| `convert/html_route.py` | `prepare(raw, file_id, sha256, browser)` returns `(route, facts)` using EdgarTools and the existing browser measurements. |
| `convert/xml_fields.py` | `convert(raw, file_id, sha256)` returns ordered fields and XML elements, with attributes, namespaces, parents and mixed content. |
| `pictures/join.py` | `read_pictures(raw, route, members, browser, folder, make_readers)` returns the complete route and one entry per picture occurrence. |
| `pictures/worker.py` | Stores and reuses one reading per input hash and reader settings, with locking, validation and retry behavior. |
| `compare.py` | Shared text/number comparison; imported by conversion and picture code. |

Keep the returned route, facts, picture entries and the source/archive files they
name. A packet is only a presentation of the readings: it can omit evidence retained
in the raw records. Repeated image bytes share worker results while their occurrences
keep separate source context. The caller's source/version identity must remain with
these outputs when they are serialized or moved.

HTML records retain ordered units, table cells and source anchors, picture occurrences,
native paragraph/heading evidence, explicit source links and available style evidence.
XML keeps literal source structure. Native heading claims are evidence, not an inferred
governing section tree. Table coordinates and raw source evidence must be read together;
unmeasured placement is not certified browser geometry. Every cell of a retained
content or nested table keeps its source span, including blanks. A cell marked
`grid: screen` uses measured display coordinates; without that marker its numbers
remain native parser coordinates. Those two frames must not be mixed. A nested
table names its holder cell, whose `tables` list names its children. The holder's
native aggregate text can overlap the child text; the source spans and containment
identify that shared content. Wholly blank top-level spacer tables keep the
existing omission policy.

Default picture reading uses Chandra, PP-OCR/RapidOCR and OnnxTR. Sonnet is off by
default. Raw readings, disagreement, cutoffs and failures remain visible. Reader
agreement does not establish correctness against the original. The current Chandra
factory uses MLX; a production NVIDIA worker is not yet qualified.

`OK` means that conversion completed, not that every source fact or picture was
independently checked. Inspect `uncovered`, unresolved source evidence, picture input
errors and reader statuses. `PARTIAL` and `FAILED` preserve their reasons. Broken source
identity and storage/resource faults stop the caller instead of becoming a success.

Use the pinned [offline test environment and both regression commands](../../tests/driver/prepare/README.md).
Those checks make no model calls; independent scoring and actual-worker qualification
remain separate gates. The [extraction handover](../../.claude/plans/Drivers/DriversFinal/PrepareExtractionHandover.md)
records the current scope and release requirements, including the bounded PDF decision.
No production PDF route, semantic document tree or downstream driver is supplied here.

Reuse native library functionality before extending an adapter. Keep one owner for
each rule, tests under `tests/driver/prepare/`, and large fixtures and experiments
outside runtime. Runtime must not import benchmark or research code.
