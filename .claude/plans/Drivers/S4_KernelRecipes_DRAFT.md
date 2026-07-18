# S4 Rehearsal Recipe — DRAFT v2.5 (paper only; #804; runtime order APPROVED 2026-07-17)

> **Owner ruling: DRY-RUN REHEARSAL ONLY, fiscal.ai METRIC lane only. The real kernel stays OFF. No
> live LLM calls, no prompts, no graph writes, no production activation. No code/law/prompt edits under
> this paper. No new ledger, receipt system, production write path, or fake-transaction machinery.**

**What exists:** the S1 packet builder (pending the Fiscal fixes; stale smoke files banned) · the
frozen `PreparedFactV1` schema · the proven writer (`run_event`, dry-run default). **What does NOT
exist:** decomposer code · kernel code · any selector/cursor runtime. The rehearsal uses **RECORDED
ANSWERS** for both — independently checked (a second party/pass, documented) and **sha256-pinned**;
the harness consumes them and NEVER grades answers it created itself.

**Runtime order (approved):** [future: eligibility] → raw packet → proposed meaning → recorded Core
decision → final fact → dry-run writer.
**Fixtures:** freshly regenerated Fiscal 10-K/10-Q packets AFTER the Fiscal fixes; 8-Ks excluded;
pinned by source ID + packet sha256 + generating commit; every raw item carries an ID and is accounted
for (incl. skips); candidate- and decision-fixture hashes recorded in the EXISTING write-ahead audit.

**⚖️ What passing PROVES — and does not:** a pass proves the WIRING lost nothing (order, identity
plumbing, admissions handoff, outcome accounting). It does NOT prove Fiscal extraction quality,
decomposer precision/recall, or kernel precision/recall — their answers are recorded gold. Those are
measured separately when each component is built (its own certification), before any connection is
trusted live.

## Step 0 — PER-20 at the FUTURE real selector (nothing built now)
- Two gates, never conflated: **PER-20 eligibility** (XBRL landed) = WHEN a source may process; the
  **pilot fence** = WHAT may enter Core — an 8-K is PER-20-eligible yet fenced out of this XBRL-only
  pilot. Entry-into-Core gate, never the resolver's (BUILD :213-214). **Future selector's required
  test:** incomplete 10-Q not offered · complete → offered · 8-K eligible-but-fenced.

## Step 1 — Packet → recorded decomposer candidate (NO final name, NO PreparedFactV1 yet)
- **In:** one regenerated 10-K/Q packet. **Out:** per item, a recorded CANDIDATE = **proposed_name +
  fact evidence only** (slice_tokens, spans, signed unscaled values, period signals). A candidate is
  NOT a `PreparedFactV1` (the schema requires the final `driver_name`, which does not exist yet).
  **Fail:** Part B park/skip → excluded WITH recorded reason, counted by item ID. **Test:** every
  candidate carries the Part-B-required outputs; item-ID accounting covers 100% of raw items; no
  candidate carries a final driver_name.

## Step 2 — Recorded kernel decision (metric lane only)
- **In:** candidate + read-only graph state. **Out:** per fact, its OWN triple
  `{decision: attach|create, driver_name, fact_type}` — the kernel ALONE names/types, by recording.
  **Rehearsal fence, mechanical:** every admission triple MUST carry `fact_type=metric` — any other
  fact_type is a fixture bug and HARD-ERRORS (guidance/surprise/action rehearse later, separately).
  **Fail:** recorded refusal stops the fact with its reason. **Test:** unlawful name (NAME-05) = a
  refusal; the harness never repairs a name; every triple complete; a non-metric fact_type hard-errors.

## Step 3 — PreparedFactV1 constructed HERE + the ATTACH/CREATE handoff
- **In:** candidate + decision triple. **Out:** the `PreparedFactV1` (first construction point) inside
  a `RunInputV1`, plus the ONE handoff: an `admissions` input to `run_event` **keyed by the zero-based
  index of each fact in `RunInputV1.facts`**.
- **The two modes, exactly (no third):** `admissions=None` (parameter absent) → today's behavior
  unchanged — a missing Driver parks `DRIVER_NOT_READY`. A rehearsal map SUPPLIED → completeness is
  enforced BOTH ways: every fact has exactly ONE entry and every entry matches a fact — a missing OR
  extra entry is a fixture bug and HARD-ERRORS before any planning.
- **Verification (all three fields, both paths):** ATTACH to an EXISTING graph Driver → the stored
  name AND fact_type must equal the admission's (mismatch parks, never silent). CREATE → non-existence
  checked; the born-complete bundle (`create_driver` + accepted first fact, FINAL_DESIGN §4.2) enters
  the PLAN as one atomic group. **Offline-card ATTACH (no graph node yet):** plans the SAME
  born-complete bundle — never a park, never a bare create — and its `fact_type` comes FROM the
  admission, exactly like CREATE (there is no stored Driver to read; verifying the card is the future
  kernel's job). **Node invariant:** a Driver is planned ONLY if ≥1 of its facts is accepted.
  **Grouping rule (the Revenue-Q1 + Revenue-Q2 case):** accepted facts are GROUPED by driver_name;
  all triples in a group must agree on decision AND fact_type — any disagreement is a fixture bug and
  HARD-ERRORS. For a missing Driver the plan emits exactly ONE `create_driver` operation, and EVERY
  accepted fact of the group links to it — never one create per fact.
  **Wiring rule:** any fact whose Driver is not in the graph (create OR offline-card attach) takes the
  `fact_type` period resolution consumes FROM its admission; a graph-backed attach reads the stored
  Driver. **Rehearsal clamp:** recorded admissions + `enable_writes=True` HARD-FAILS before any
  planning — recordings produce dry-run PLANS, never nodes. **This rehearsal tests PLANS, not
  execution:** transaction execution and rollback proofs are DEFERRED — real activation must later
  prove transactional rollback before any enabled run. **Tests:** enable_writes+recordings hard-fails ·
  graph-attach wrong-fact_type parks · offline-card attach plans the bundle with the admission's
  fact_type · all-facts-parked plans NO Driver · the dry-run plan groups `create_driver`+first-fact
  atomically · supplied-map completeness: extra entry hard-errors, missing entry hard-errors,
  admissions=None still parks `DRIVER_NOT_READY` · a CREATE metric fact resolves its period from the
  admission's fact_type · TWO accepted facts for ONE new Driver produce exactly ONE `create_driver`
  operation and TWO fact operations (and disagreeing triples within a group hard-error).

## Step 4 — FINAL ACCEPTANCE TEST (not a component)
- End to end on pinned fixtures → `run_event` DRY-RUN. **The expected table covers ALL FIVE outcomes —
  written · merged · parked · rejected · SKIPPED (Part B exclusions).** **Reconciliation is by ITEM
  ID, not a count equation** (one raw item may legitimately produce several facts): every raw item is
  either skipped/parked-with-reason or linked to one-or-more facts; every fact links back to
  one-or-more raw items (fusion); NO orphan on either side. Audit carries the fixture pins + both
  fixture hashes. ZERO writes, ZERO prompts, kernel OFF. Pass = exact table match + a complete item-ID
  reconciliation — which proves the WIRING only (see the proof-limit note above).

**Excluded:** scheduler · retries · new ledger/receipts · API versioning · News/Transcript ·
guidance/latent anchors (deferred) · new abstractions · prompt text · production write path · new
fake-tx machinery · transaction-execution tests (deferred to activation). Kernel activation, write
enablement, and every future prompt = separate owner gates. **Blocked on:** the Fiscal fixes + packet
regeneration before Step-1 fixtures can exist.
