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
| `convert/html_route.py` | `prepare(raw, file_id, sha256, browser, source=None, parse=None)` returns `(route, facts)` using EdgarTools and the existing browser measurements. `parse` is the tool call `convert` makes (default `edgartools_html.parse`); a caller that must keep the raw reading wraps it and stores the returned plain dump and version itself, before the route is built. `prepare` stores nothing. EdgarTools 5.60.0's own exports (`Document.to_json`, `TableNode.to_dict`) drop cell spans, header flags and row groups, so the dump is the raw reading to keep. |
| `convert/xml_fields.py` | `convert(raw, file_id, sha256)` returns ordered fields and XML elements, with attributes, namespaces, parents and mixed content. |
| `pictures/pdf.py` | `pages(raw, file_id, sha256)` uses PDFium to return a source-bound route and page pictures for the existing `join` function. |
| `pictures/join.py` | `read_pictures(raw, route, members, browser, folder, make_readers)` returns the complete route and one entry per picture occurrence. |
| `pictures/worker.py` | Stores and reuses one reading per input hash and reader settings, with locking, validation and retry behavior. |
| `compare.py` | Shared text/number comparison; imported by conversion and picture code. |

Keep the returned route, facts, picture entries and the source/archive files they
name. A packet is only a presentation of the readings: it can omit evidence retained
in the raw records. Repeated image bytes share worker results while their occurrences
keep separate source context. The caller's source/version identity must remain with
these outputs when they are serialized or moved.
For packaged HTML, pass the same `screen_grid.Source` through HTML conversion and
picture preparation; it binds the document address, package and dependency evidence.

The HTML route's evidence members are listed below. Members appear where applicable;
keep their `read`, `error`, `fallback` and unresolved states with the values.

| Member | Evidence retained |
|---|---|
| `schema`, `file_id`, `sha256`, `route` | Payload schema, source identity, tool version and conversion settings. The schema alone is not a code-version identity. |
| `source_links` | Written links, source occurrences, destinations and proved owners; unknown ownership stays explicit. |
| `source_relations` | Explicit Inline XBRL references and continuation chains. An unread source is not evidence that it has no relationships. |
| `source_symbols` | Raw symbol-font readings, decoder results, source places and unknown codes. |
| `source_inline` | Native raised/lowered text evidence and its source-bound owners. |
| `page_visibility` | Browser visibility evidence used for conversion, including unbound source fragments. |
| `resources` | When a `Source` is supplied: document/bundle identity and the exact dependency responses or refusals used by the renders. |
| `source_style`, `generated_content` | Native style, position and generated-content readings, described below. |

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

`source_table` retains a table's original opening-tag byte and the number of
route tables claiming it. Repeated claims remain explicit; this point proves
neither the table's extent nor its geometry. Unknown source identity is `None`;
older adapters without table identity omit the field. Unbound cells likewise
keep unknown source evidence explicit.

A native caption bound to its own HTML `<caption>` element is emitted as a
separate `caption` unit in source order. Its `source` records that element,
its `anchor` locates the text, and its `source_table` identifies the owning
table. The table does not duplicate this text in its `caption` list. A retained
table keeps an unbound native caption in that list.

`struck` lists an item's struck phrases and `struck_at` their character places in
its text. Where a stylesheet could change decoration, the existing screen render
reads the browser's effective decoration per source text run (settings
`source_formatting: 'rendered'`; `facts['screen']['source_formatting']` counts
struck items). Runs without a native verdict are listed in
`source_formatting.unresolved` and make the route `PARTIAL`; an item holding one
keeps the converter's claim and gets no places.

`source_style` has one record per source text run, bound by its source bytes and
its owners' text places (cells included); repeated text is never matched by text.
Each record keeps the browser's raw computed values: `color`, `weight`,
`font_style`, `decorations` (in effect, inherited too), `text_transform` and, where any is
observed, `background` — `[depth, colour, image, opacity]` from the element
holding the text up its ancestors. These are readings, not a paint or coverage
verdict: an empty stack means none observed on that chain. A first-letter or
first-line value that differs stays uncertainty (`pseudo` for colour,
`style_pseudo` named by property). `text_transform` is the CSS property as computed
(`none` included), never the printed string: language-dependent case mapping, `capitalize`
word boundaries, fonts and a first-letter / first-line value's character reach are not
claimed, and the source text is never rewritten. Hidden runs keep their reading with no owner;
unread or literal runs stay `unresolved`. Each record also keeps `boxes`: the raw
`[x, y, width, height]` CSS-pixel client rectangles the browser returns for the
whole native run (Range.getClientRects, unrounded, in its returned order), in the
section's one `frame` (`viewport`, `scroll` origin, `device_pixel_ratio`) of the
same render. The boxes cover the entire run, preserved white space included; where
that source extent differs from `at`, `boxes_at` names it. Boxes are positions:
not a reading order, not a visibility proof (hidden runs keep theirs, with no
owner); a missing box is no proof of missing content. Generated-content `bounds`
come from the DOMSnapshot layout of the same page: the pinned browser's protocol
declares `LayoutTreeSnapshot.bounds` "the absolute position bounding box"
(document coordinates), while `Range.getClientRects` returns client (viewport)
coordinates. They are equal only at scroll origin (0, 0); otherwise document =
client + the recorded `scroll` (measured: +400 at a vertical scroll of 400).

`generated_content` keeps the page's own pseudo-element readings (before, after,
marker, first-letter): raw fragments, computed values and, from the same
snapshot, a raw background stack. A record is placed (`at`: unit or cell and
character offset) only where its owner's whole source text is proved; records
at one offset apply in their order. A first-letter only formats existing text.
Unplaced required text, non-text content, unknown visibility and any background
image (`background_images`, its content never read here) make it `PARTIAL`.
Units made from the parser's own list items keep `lists`: `[{list, ordered,
item}]`, the outer list first. These are source-order records; no universal
display order is claimed.

PDF pages use the same archive, workers and picture records:

```python
route, images = pdf.pages(raw, file_id, sha256)
route, pictures = join.join(route, images, folder, make_readers)
```

The route retains page order, one-based page references, native boxes/rotation,
links, annotations and attachment names before rendering. Coordinate fields
declare their frames. Unread attachments, unsupported actions/forms and failed
pages remain explicit; unsupported URI bytes are preserved without guessing
their encoding. Original PDF bytes remain required. This entry point does not
read the hidden text layer or dispatch an entire filing inventory.

Default picture reading uses Chandra, PP-OCR/RapidOCR and OnnxTR. Sonnet is off by
default. Raw readings, disagreement, cutoffs and failures remain visible. Reader
agreement does not establish correctness against the original. The current Chandra
factory uses MLX; a production NVIDIA worker is not yet qualified.

`OK` means that conversion completed, not that every source fact or picture was
independently checked. Inspect `uncovered`, unresolved source evidence, picture input
errors and reader statuses. `PARTIAL` and `FAILED` preserve their reasons. Broken source
identity and storage/resource faults stop the caller instead of becoming a success.

Before use, retain the exact inputs, code, dependencies, browser and settings with
the outputs. Use bounded batches and record every input's outcome, including failures
before an output exists and inputs never started. An absent reading is unobserved;
it does not prove that the source lacks content. Keep partial results and their reasons.

After interruption, preserve the incomplete attempt and start a fresh attempt only
after checking its input and version identity. Reuse requires a valid completion and
verified output bytes. Rollback requires retained earlier code, outputs **and environment**;
hashes detect changes but cannot restore missing software. Same-host interruption
controls do not establish power-loss or off-host recovery.

Production stays automatic. After the release gates, expand use in bounded batches,
retain failure and uncertainty signals, and stop expansion on a new material regression.
Independent source review belongs to release validation and separate periodic audits,
not a required step for each production document. Fix a demonstrated class at its
existing owner and rerun the relevant controls before resuming expansion.

Use the pinned [offline test environment and both regression commands](../../tests/driver/prepare/README.md).
Those checks make no model calls; independent scoring and actual-worker qualification
remain separate gates. The [current extraction plan](../../.claude/plans/Drivers/DriversFinal/PrepareTools.md)
records the current scope and release requirements. The native PDF connection
has offline regression coverage; actual OCR and worker qualification remain
open. Semantic document trees and downstream drivers are outside this package.

Reuse native library functionality before extending an adapter. Keep one owner for
each rule, tests under `tests/driver/prepare/`, and large fixtures and experiments
outside runtime. Runtime must not import benchmark or research code.
