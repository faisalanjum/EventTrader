# PHASE-6 TRUTH EXPANSION PLAN (paper only — zero AI labeling yet; owner review)

TARGET: 50 independent, super-high-quality cases in EACH of five categories:
unclear tables · 8-K prose · prepared remarks · Q&A · numberless.
Current: tables — 8 INDEPENDENT tables (19 fact rows, 7 filings, 4 companies) toward 50 independent · others 0/50.

## 1. Reuse audited truth FIRST (inventory, zero new labeling)
- Tables: the 8 independent tables (19 rows, v4) stand. Candidate reuse: the frozen certified benchmark corpora
  (grand-cert 111-case exam + exam_annual / exam_madrift / exam_mafresh / exam_transcript
  sets with judged verdicts, relocate_probe) — REUSE RULE: only cases whose verdicts were
  human/adversarially adjudicated during certification qualify as truth; inventory each
  set's adjudicated count before claiming it (numbers to be verified from the graded
  artifacts, not assumed).
- Q&A / prepared remarks: exam_transcript's adjudicated cases first; remainder labeled.
- Numberless: no existing truth — all 50 labeled.

## 2. Answer-key creation (OWNER RULING 2026-07-24: no human reviewer)
- Hidden answer keys are created and adjudicated by APPROVED FRONTIER MODELS only.
- NO human reviewer in the loop (supersedes the earlier human-adjudication + 10%-sample design).
- Qwen NEVER creates or adjudicates its own answer keys — it is only ever the examinee.
- The EXACT frontier-model key method (which models, agreement rule, sampling) is HELD
  for a later separate owner approval before any labeling call runs.

## 3. Quality bar (owner order: super-thorough — re-reviewed several times)
Every case, before freeze: (1) source bytes sha-pinned; (2) answer derived twice
independently; (3) key adjudication per the §2 owner ruling (frontier models, method held); (4) leak-check mechanical
(no answers in inputs); (5) competing content included (full tables / full block
neighborhoods); (6) counts + hashes reconcile; (7) a final full re-read pass of all
250 cases before the freeze hash. THREE review passes minimum: build → adversarial
self-audit → reviewer audit.

## 4. Costs (labeling, estimate — separate from the screen)
Codex lane: flat-rate subscription; Fable in-session: subscription quota. Human time:
disagreements + 10% sample (~expected tens of cases). Zero metered API anywhere.

## 5. Sequence
Screen (8 independent tables / 93 requests, approved cap) → inventory the adjudicated exam reuse counts →
owner GO on double-labeling → build 5×50 → freeze v2 manifest (re-hashed) →
production certification package.
