● Bundle components — visual sketch

  Each section is what render_bundle_text (orchestrator.py:1503) emits, in order. JSON source key in parens.

  ---
  §1. Header (quarter_info + top-level)

  ┌──────────────────────────────────────────────────────────┐
  │ AVGO — Q4_FY2023 │ filed 2023-12-07T16:18:51-05:00       │
  │ accession 0001730168-23-000093 │ session post_market     │
  │ period_of_report 2023-10-29 │ pit_cutoff …               │
  └──────────────────────────────────────────────────────────┘
  Role: who/when/what — anchors every downstream timestamp comparison.

  ---
  §2. Results & Expectations (consensus current row + 8k_packet.exhibits_99[EX-99.1])

  ### Consensus Bar              ### Reported Results (EX-99.1)
  | Metric  │ Estimate │         ┌─────────────────────────────┐
  | EPS     │ $10.42   │         │  full press-release text    │
  | Revenue │ $9.28B   │         │  (EPS, revenue, segment      │
                                 │   highlights, guidance hint) │
                                 └─────────────────────────────┘
  Role: the "what was expected vs what was reported" head-to-head — the predictor's first-look surprise read.

  ---
  §3. Forward Guidance (guidance_history)

  ### Quarterly Guidance              ### Full Year Guidance
  #### Q1 FY2024                      #### FY2024
  | Metric    │ Current │ Prior │     | Metric    │ Current │ Prior │
  | Revenue   │ $9.5B   │ —     │     | AI Revenue│ $4B+    │ $3.5B │
  | Op Margin │ 60-62%  │ —     │     ...

  ### Other Horizons       ### Guidance History (3+ updates only)
  Role: forward-looking guidance changes — the "is the bar moving up or down?" signal. Plan §1.2 wants metric_id +
  derivation + sources + xbrl_qname + evhash16 added.

  ---
  §4. Consensus History (consensus.quarterly_rows + forward_estimates)

  Summary: 8 EPS beats in last 8 │ Avg EPS surprise +6.4% │ Avg Rev +2.1%

  ### Beat/Miss History (prior quarters)
  │ Quarter │ EPS Est │ EPS Act │ Surprise │ Rev Est │ Rev Act │ Surprise │
  │ 2023-07 │ $10.43  │ $10.54  │  +1.1%   │ $8.85B  │ $8.88B  │  +0.4%   │
  │ 2023-04 │  …                                                          │

  ### Forward Estimates (live mode only — revision momentum)
  │ Period │ EPS Now │ 7d ago │ 30d ago │ 90d ago │
  Role: streak/rhythm of beats and analyst revision direction over time.

  ---
  §5. Prior Financial Trends (prior_financials.quarters[])

  Coverage: 8 quarters │ Sources: xbrl=7, av=1

  ### Income Statement Trend
  │ Metric          │ Q4_22 │ Q1_23 │ Q2_23 │ Q3_23 │ Q4_23 │ ...
  │ Revenue         │ $8.9B │ $8.7B │ $8.7B │ $8.9B │ $9.3B │
  │ Operating Inc   │  …                                     │
  │ EPS Diluted     │  …                                     │

  ### Margins / Cash Flow / Balance Sheet  (similar grid)

  ### Revenue Splits   ← segment/geo if upstream extracts them
  Role: 8-quarter trend of fundamentals. Plan §1.4 wants derived_metrics + _provenance footer per quarter so predictor
  can tell "filed" from "computed".

  ---
  §6. Inter-Quarter Events (inter_quarter_context)

  Window: prev-8K → cutoff │ X trading days │ Y news │ Z filings

  ### Trading Days
  │ Date │ Trd │ Bnd │ Close │ Ret% │ SPY% │ Sect% │ Adj% │ Sig │ Gap │

  ### News Events
  │ Ref │ Date │ Sess │ Title │ Channels │ AdjH% │ AdjS% │ AdjD% │
  │ N1  │ 2023-09-25 │ pre │ "AVGO upgrade by …" │ Analyst Ratings │ +2.1 │ …

  ### Filing Events / Dividends / Splits   (only if non-empty)
  Role: everything that happened between previous earnings and this one — the "what changed in the gap" surface. Plan
  §1.5 adds industry_return col + bz_id per news.

  ---
  §7. Sector Peer Earnings & Reactions (peer_earnings_snapshot)

  Current (one wide row per peer):
  Industry: Semiconductors │ Window: 2023-10-23 → 2023-12-07 │ 5 peers

  │ Tkr │ Name │ MktCap │ Filed │ Acc │ Sess │ DayStk% │ AdjH% │ SessStk% │ AdjD% │ Horizon │
  │ NVDA│ …    │ …      │ 11-21 │ …   │ post │ -2.46   │  3.02 │  3.99    │ -2.84 │ …       │
  Plan §1.3 redesign — per-peer block (Option D):
  ### NVDA — filed 2023-11-21 (post_market), accession …
  Stock move:  Day -2.46%   Sess +3.99%   Hour +3.18%
  Sector-adj:  Day -1.98%   Sess +4.20%   Hour +0.48%   Best +4.20%
  Macro-adj:   Day -0.75%   Sess +3.12%   Hour +1.45%   Best +3.12%
  Headlines:
  - [N68 | bz:35906540] NVIDIA Q3 Adj $4.02 Beats $3.36 Estimate ...
  Role: how comparable peer prints traded — the cluster-sizing signal. The Day vs Sess sign-flip is the buried gold
  this redesign exposes.

  ---
  §8. Macro Environment (macro_snapshot)

  Session: post_market │ SPY 459.10 │ VIX 12.85 (calm)

  ### SPY Trend
  │ Level │ Open→PIT │ Last60m │ Today │ 5D │ 20D │ YTD │ MA50 │ MA200 │ ...

  ### Sector / Indicators (cross-asset)

  ### Macro Catalysts        ← plan §1.6 adds BzID column
  │ Bucket │ Date │ Time │ Title │ Channels │ BzID │
  │ Today  │ 12-07│ 07:30│ Nov Challenger Job Cuts 45.51K │ Macro │ 36131062 │
  │ Yest   │ …                                                            │
  │ Earlier│ …                                                            │
  Role: regime context — is the tape calm/risk-on/risk-off, what catalysts are firing, what's already priced.

  ---
  §9. Reference (8k_packet)

  ### Filing Metadata           ← plan §1.7 adds CIK / Amendment / Paired periodic
  Accession: 0001730168-23-000093 │ Form: 8-K │ Items: 2.02, 2.05, 8.01, 9.01
  CIK: 0001730168 │ Amendment: no
  Paired periodic filing: 10-K 0001730168-23-000096
  Sections: 2 │ Exhibits: EX-99.1, EX-99.2

  ### EX-99.2  (other exhibits — full text)
  ### 8-K Section Text  (raw item bodies)
  ### Filing Text (fallback)
  Role: the "footnote drawer" — provenance + non-press-release exhibit text + raw 8-K body for verification.

  ---
  §10. Prior Lessons (learning_context) — the keystone redesign

  Current (mixed prefixes — fights the validator):
  ### Ticker Lessons (1 most recent quarters)

  **Q3_FY2023** — prediction correct (short), actual -5.38%, driver: …
    - Predictor: When a stock belongs to an established same-sector …
    - Predictor: A 'headline beat + slight guide miss' is a trap …
    - Data: Fetch the earnings call transcript …
    - Why: The press release headline understated …

  ### Sector Lessons / Macro Lessons / Cross-Ticker Lessons   (globals)

  Plan §1.1 redesign:
  ## Lessons To Label (verbatim, in order)         ← validator-matched

  L1.
  When a stock belongs to an established same-sector sell-the-news …
  learner_result: earnings-analysis/Companies/AVGO/events/Q3_FY2023/learning/result.md

  L2.
  A 'headline beat + slight guide miss' is a trap when segment …
  learner_result: …

  L3. [sector: Technology]
  In the 2023+ hyperscaler-AI-capex regime, semiconductor prints …
  learner_result: …

  ## Context-Only (not labeled)                    ← keeps prefixes

  ### Ticker — Q3_FY2023
  - prediction correct (short), actual -5.38%, driver: ex_ai_segment_deterioration
  - Data: Fetch the earnings call transcript …
  - Why: The press release headline understated …
  - learner_result: …
  Role: prior-quarter learner output the predictor must explicitly label (confirmed/contradicted/irrelevant). Tuple
  return (text, ordered_lesson_texts) from _render_learning_context is the validator's source of truth — the markdown
  changes, the list does not.

  ---
  How they assemble end-to-end

  build_prediction_bundle ──┐
    builders run in parallel ─→ bundle dict ─→ context_bundle.json (verification)
                                            └→ render_bundle_text() ─→ context_bundle_rendered.txt
                                                                         │
                                                    ┌────────────────────┴───┐
                                                    ↓                        ↓
                                            predictor reads (primary)    learner reads (already JSON)

  Sections 1-9 are bundle data; §10 is the closed loop where past predictions feed the next one.



1. _render_header is a private helper that takes the bundle dict and returns a string. Run it on an existing bundle from
   the repo:

---

# Per-section run cheatsheet (live builder + renderer)

Each invocation runs the **live builder + renderer** for one (or all) sections, end-to-end. No `context_bundle.json` involved. Output is byte-identical to what `render_bundle_text(bundle)` produces — i.e. exactly what the predictor LLM `Read`s.

## ⭐ Recommended — two single-purpose dispatcher scripts

| Script | Output |
|---|---|
| `scripts/earnings/render_section.py` | rendered markdown only (what the predictor `Read`s) |
| `scripts/earnings/compare_section.py` | JSON + rendered side-by-side (raw builder output → renderer output) |

Both take the same 3 args: `<TICKER> <ACCESSION> [SECTION]`. Output is a **live rebuild** — byte-identical to what `context_bundle.json` and `context_bundle_rendered.txt` contain when the orchestrator saves them. No file load, no shortcuts.

### Compare JSON ↔ rendered (audit lossy/lossless mapping)

```bash
venv/bin/python scripts/earnings/compare_section.py AVGO 0001730168-23-000093 header
venv/bin/python scripts/earnings/compare_section.py AVGO 0001730168-23-000093 guidance
venv/bin/python scripts/earnings/compare_section.py AVGO 0001730168-23-000093 peers | less
venv/bin/python scripts/earnings/compare_section.py AVGO 0001730168-23-000093 all   | less
```

Output layout:

```
========================================================================
  JSON  bundle.<key>
========================================================================
{ ...pretty-printed json the builder produced... }

========================================================================
  RENDERED  §<section>
========================================================================
...markdown the renderer turned that JSON into...
```

For `all`, the JSON dump is the entire bundle (≈100–500 KB) and the rendered is the entire `context_bundle_rendered.txt`. For section-specific calls, the JSON is just the sub-tree(s) that section's renderer reads — no noise from unrelated packets.

### Render only (no JSON, just the markdown the predictor sees)

`scripts/earnings/render_section.py` — same args, but emits only the rendered half. To switch ticker, accession, or section, change the args — nothing else.

```bash
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 header
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 results
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 guidance
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 consensus
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 prior
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 iq
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 peers
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 macro
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 ref
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 lessons
venv/bin/python scripts/earnings/render_section.py AVGO 0001730168-23-000093 all      # full rendered bundle
```

Switch event:
```bash
venv/bin/python scripts/earnings/render_section.py CRM  0000950170-23-067020 guidance
venv/bin/python scripts/earnings/render_section.py NVDA 0001045810-23-000244 peers
```

Section name → renderer mapping:

| Arg        | Section                         | Renderer                            |
|------------|---------------------------------|-------------------------------------|
| `header`   | §1 Header                       | `_render_header`                    |
| `results`  | §2 Results & Expectations       | `_render_results_and_expectations`  |
| `guidance` | §3 Forward Guidance             | `_render_forward_guidance`          |
| `consensus`| §4 Consensus History            | `_render_consensus_history`         |
| `prior`    | §5 Prior Financial Trends       | `_render_prior_financials`          |
| `iq`       | §6 Inter-Quarter Events         | `_render_inter_quarter`             |
| `peers`    | §7 Sector Peer Earnings         | `_render_peer_earnings`             |
| `macro`    | §8 Macro Environment            | `_render_macro`                     |
| `ref`      | §9 Reference                    | `_render_reference`                 |
| `lessons`  | §10 Prior Lessons               | `_render_learning_context`          |
| `all`      | full rendered bundle (sections 1–10 joined) | `render_bundle_text` |

---

## Manual one-liners (raw form — for debugging / reference only)

These are the long-form equivalents the dispatcher wraps. Self-contained: `T=…` and `A=…` are inlined on the same line as the python call, so env vars are visible to the python subprocess regardless of subshell state.

## §1 Header

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from earnings_orchestrator import _render_header;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);print(_render_header({'ticker':t,'quarter_info':qi,'pit_cutoff':qi['filed_8k']}))"
```

## §2 Results & Expectations (consensus bar + EX-99.1)

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_consensus,build_8k_packet;from earnings_orchestrator import _render_results_and_expectations;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_results_and_expectations({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'consensus':build_consensus(t,qi,p,'/tmp/c.json'),'8k_packet':build_8k_packet(t,qi,p,'/tmp/k.json'),'builder_errors':{}}))"
```

## §3 Forward Guidance

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_guidance_history;from earnings_orchestrator import _render_forward_guidance;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_forward_guidance({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'guidance_history':build_guidance_history(t,qi,p,'/tmp/g.json'),'builder_errors':{}}))"
```

## §4 Consensus History

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_consensus;from earnings_orchestrator import _render_consensus_history;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_consensus_history({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'consensus':build_consensus(t,qi,p,'/tmp/c.json'),'builder_errors':{}}))"
```

## §5 Prior Financial Trends

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_prior_financials;from earnings_orchestrator import _render_prior_financials;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_prior_financials({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'prior_financials':build_prior_financials(t,qi,p,'/tmp/pf.json'),'builder_errors':{}}))"
```

## §6 Inter-Quarter Events

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_inter_quarter_context;from earnings_orchestrator import _render_inter_quarter;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_inter_quarter({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'inter_quarter_context':build_inter_quarter_context(t,qi,p,'/tmp/iq.json'),'builder_errors':{}}))"
```

## §7 Sector Peer Earnings

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_peer_earnings_snapshot;from earnings_orchestrator import _render_peer_earnings;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_peer_earnings({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'peer_earnings_snapshot':build_peer_earnings_snapshot(t,qi,p,'/tmp/pe.json'),'builder_errors':{}}))"
```

## §8 Macro Environment

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_macro_snapshot;from earnings_orchestrator import _render_macro;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_macro({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'macro_snapshot':build_macro_snapshot(t,qi,p,'/tmp/m.json'),'builder_errors':{}}))"
```

## §9 Reference

```bash
T=AVGO A=0001730168-23-000093 venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from quarter_identity import resolve_quarter_info;from builder_adapters import build_8k_packet;from earnings_orchestrator import _render_reference;t,a=os.environ['T'],os.environ['A'];qi=resolve_quarter_info(t,a);p=qi['filed_8k'];print(_render_reference({'ticker':t,'quarter_info':qi,'pit_cutoff':p,'8k_packet':build_8k_packet(t,qi,p,'/tmp/k.json'),'builder_errors':{}}))"
```

## §10 Prior Lessons (no accession needed — only ticker)

```bash
T=AVGO venv/bin/python -c "import os,sys;sys.path.insert(0,'scripts/earnings');from earnings_orchestrator import build_learning_context,_render_learning_context;t=os.environ['T'];txt,_=_render_learning_context(build_learning_context(t,pit_cutoff=None));print(txt)"
```

## Full bundle (all 9 sections, parallel build)

```bash
venv/bin/python scripts/earnings/earnings_orchestrator.py AVGO 0001730168-23-000093
```

Add `--save` to write `context_bundle.json` + `context_bundle_rendered.txt` to `earnings-analysis/Companies/<T>/events/<quarter>/`.

## Try a different event

Just edit the `T=…` and `A=…` values at the start of any block. Examples:

```
T=CRM   A=0000950170-23-067020
T=NVDA  A=0001045810-23-000244
```

`resolve_quarter_info` will Neo4j-lookup the period_of_report, paired periodic filing, fye_month, etc. for whichever ticker+accession you give.

## Why this format

- `T=… A=… venv/bin/python …` puts the env vars on the **same command** as the python invocation. They are visible to the python subprocess regardless of whether your current shell has them exported.
- Inside python, `os.environ['T']` and `os.environ['A']` read the values — no shell `$T`/`$A` substitution involved, so word-wrap from a chat copy-paste won't corrupt anything.
- No need to `bash`, `export`, or set up a shell session beforehand.
