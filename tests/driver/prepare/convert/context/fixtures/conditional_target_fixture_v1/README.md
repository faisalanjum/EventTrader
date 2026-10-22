# One invented conditional-target fixture

Runnable public fixture and independently authored expectations, not a new checker. No private source values, labels, identifiers, layout or answers were used. One fixed child/card is loaded by the existing public v2 jQuery parent. The outer and inner activating controls have **no IDs**; a unique declared ID belongs to the source target. Fixture selectors in `probe.py` are test data, not proposed runtime decision rules.

`EXPECTATIONS_BEFORE.json` specifies exact required text, emphasis, ordered-list entries, reference destination, table caption/headers/rows, picture identity and relationships before browser observations. It also specifies state order and expected control-label changes. Required internal order is title → summary → notes group → counts group; notes contain paragraph → ordered list → reference, and counts contain table → picture/caption. Every group belongs to the same declared source target, not an arbitrary matching string elsewhere.

The native action classes are: first outer `cloneNode(true)` copy; inner in-place display change; an already-visible no-op; close without deletion; repeat outer reuse of the **same node**, preserving expanded groups. The copy is appended within the control's owning entry **after another paragraph**, so immediate sibling adjacency is false even in the positive. No invented global displayed order is imposed.

The positive browser witness records nine states: initial; outer open with both optional groups closed; visible no-op; notes only; both open; closed; same-copy reopen with both groups still open; counts only; both collapsed again. Thus all four combinations of the two independent hidden groups are exercised. A scrollable panel is retained. Recorded group flags are local display-enabled states: closed outer content is not claimed painted. These observations do not claim every descendant is simultaneously within the viewport or permanent quiescence.

The productive controls change their state labels, including replacing their text nodes. Do not assume injected comments/text-node identity inside a control survives `textContent` assignment. This witness uses a native element/copy observation, not a new source-marker rule; qualified source identity through those state changes remains the integrated implementation's obligation. No UI-label whitelist or semantic classifier is proposed.

Two deliberate replay-input negatives preserve the fixed source and expected truth:

- **Content damage:** the copied table changes one authored count to `999`. Its origin is still the right child target, so origin alone is insufficient. The changed controller is saved separately.
- **Scope/identity damage:** the parent supplies an identical target before the selected child. Its ID, text and native subtree equality all match, but the actual clone receiver is parent-owned, not the selected child's occurrence. The mutated parent is saved separately. The negative must not earn own-source binding from ID/text/structure alone. This does not claim a specific extraction candidate was run or failed.

The picture is the existing public native fixture PNG referenced in `ASSET_REFERENCES.json`: SHA256 `6d811fd7070cde013062f8d8b739309f0c0cf0088ecf264230a3c1cd49528115`, 100 bytes, 40×24. The local fixture supplies those exact bytes at the authored picture URL; native Chromium decodes them successfully. Alt, caption, source URL and response digest are recorded. No OCR/image interpretation or new download occurs. The jQuery loader and native copy observer are also reused by explicit public reference; the observer has no timer wrapper. A new parser, geometry engine, scorer or automation framework was not built.

One native browser-only command exited 0, 21:28:56.474317–21:28:58.075302 UTC, wall 1.89s, peak 213,796 KiB. Three variants yielded 17 recorded states: nine positive, four per negative. Both deliberate negative facts were observed. Zero page errors, real network, extraction, scoring, installs or retries. All `.invalid` responses are explicitly synthetic fixture responses, not downloaded HTTP evidence. Exact command/resource usage is in `NATIVE.time`; all variant inputs, JSON observations and screenshots are under `native_attempt1`. Actual input hashes exclude active output logs.

To reproduce, use the qualified environment and an unused output directory:

```sh
env -u PYTHONPATH /home/faisal/prepare_work/venvs/prepare-closeout-20261011/bin/python -I -B probe.py /absolute/unused/output
```

The retained public campaign dependencies named by `ASSET_REFERENCES.json` are required. The probe records all actual input hashes and explicitly checks the predeclared PNG, copy-observer and browser identities; the closing manifest verifies its recorded inputs remained unchanged. It uses Playwright 1.59.0 and the byte-pinned Chromium 147.0.7727.15 executable. The native-copy hook is reused only as an observation; source-owned root/target scope is checked separately in the witness. Full extraction, measurement, reconstructed state delivery and real automatic selection remain unqualified here. No candidate/private rerun, method adoption or readiness credit follows. **Current readiness stays 78%; final replay remains held.**
