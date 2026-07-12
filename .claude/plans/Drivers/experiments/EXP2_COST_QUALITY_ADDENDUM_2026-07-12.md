# EXP-2 Cost/Quality Addendum (production-feasibility) — 2026-07-12, Fable

Scope: cost analysis only. The Fable-signed EXP-2 result (adopt Sonnet@high, 40k, 1 run) is NOT reopened.

## 1. Measured token economics of the EXP-2 arms

Per-call tokens measured from uninterrupted workflow runs (subagent totals ÷ completed agents):
40k full-rules reader ~65–78K/call · para-8k full-rules ~50–57K/call · ablated 40k ~61K/call · grading batch ~50–58K/call.

**Key fact:** a para call costs ~0.75× a 40k call DESPITE chunks being 4.6× smaller — in the agent harness, overhead
(rules-file read, multi-turn tool echoes, thinking at effort=high, system prompt) dominates chunk size.

Per-pass totals over the 40-chunk corpus (tokens; API-equivalent dollars at ASSUMED list prices
Haiku ~$1.8/M, Sonnet ~$5.4/M, Opus ~$27/M blended 80/20 in/out — verify current prices before contracting):

| Arm | Tokens/pass | API-equiv $ |
|---|---|---|
| haiku_40k | ~2.6M | ~$4.7 |
| sonnet_40k (ADOPTED) | ~2.8M | ~$15 |
| opus_40k | ~2.8M | ~$76 |
| sonnet_para | ~9.7M | ~$52 |
| opus_para | ~9.0M | ~$243 |
| 2u union | ~5.6M | ~$30 |
| 3u union | ~8.4M | ~$45 |

EXP-2 whole run: readers ~57M + grading ~52M ≈ **~109M subagent tokens; API-equivalent ~$850–900.**
ACTUAL marginal dollars: **$0** (Claude Max subscription). The real currencies spent: ~109M quota tokens,
2 session-limit lockouts, ~7h wall-clock. **Grading, not reading, was the cost driver (57% of calls).**

Cost-robustness of the signed verdicts: sonnet-vs-opus adoption saves ~5× per token; the para rejection is
CONFIRMED in token terms (3.5× tokens in-harness), not only call counts.

## 2. WP-FC-RUN estimate (adopted reader: Sonnet@high, 40k, 1 run)

~478 chunk-source readers × ~70–78K = 33–37M, plus ~90 strong judges (dedup/gate/refute/D5/repair) × ~60K ≈ 5.4M,
plus clerks ~1–2M → **~40–45M subagent tokens (±30%).** API-equivalent ~$215–245; subscription cost ≈ one 5-hour
session window at recent throughput (~50M/window sustained before limits); wall ~3–4h.

## 3. Cheap small-chunk lanes — verified facts

**(a) Haiku para-8k** (never run; A4 was best-cheap=Sonnet per the pre-registered rule).
Hypothesis: para lifted sonnet +7.9pts and opus +8.9pts recall; if the lift transfers, haiku-para lands ~38–40%,
≈ sonnet-40k (40.4%). UNPROVEN: haiku's misses may be rule-following failures (not attention) — the lift may not
transfer; haiku precision under para is unknown. Economics: in-harness ≈ parity with sonnet-40k (quota-weighted);
in a production SINGLE-SHOT API deployment (no agent loop: chunk+rules in, JSON out) haiku-para ≈ 0.6–0.7× the
sonnet-40k dollars. **Bounded saving (~30–50%).** Bigger lever regardless of model: single-shot deployment cuts
per-chunk cost ~4× vs the agent-loop harness (~17K vs ~70K tokens) — a deployment-architecture note for Track-B.

**(b) Codex lane — VERIFIED in this environment:** codex-cli 0.144.1 on PATH; `auth_mode=chatgpt` (owner's
ChatGPT/Codex subscription — SEPARATE quota pool, zero Anthropic draw, no metered key; OPENAI_API_KEY null);
effort control exists (`model_reasoning_effort`, currently max) plus `-m` model override; JSON output schema
supported → the reader contract is satisfiable single-shot with inline chunk+rules (work-order probe-served-inline
note applies). Models verifiably present: **gpt-5.6-sol** (default) and **gpt-5.5**; **"gpt-5.6-luna" NOT FOUND**
in config/migrations — unverified; a probe would begin with a 1-call smoke test of the exact cheap slug.
Governance: a NEW billing lane (neither `agent()` nor the O16 OpenRouter lane, whose key is still absent) →
needs owner approval + a work-order note. Like O16: results inform PRODUCTION model strategy only; in-program
steps stay `agent()`-only. Practical point: under the CURRENT bottleneck (Anthropic session quota), the codex
lane is the only option that ADDS capacity instead of reallocating it.

## 4. Proposed minimal probe (NOT run; awaiting owner approval)

Pre-registered screen, reusing the locked key and existing baselines (no new gold, no baseline re-reads):
- **Sample:** h32-seeded 15 of 40 key chunks (~440 gold items; seed recorded). Paired against the EXISTING
  sonnet-40k verdicts on the same items (free baseline).
- **Arms (max 2):** P1 `haiku_para` (Anthropic, ~70 para reader calls, effort=high);
  P2 `codex_para` (gpt-5.5 or cheapest accepted slug; single-shot; ChatGPT-sub billing; 1-call smoke test first).
- **Grading:** ~44 coverage + 6 precision batches per arm ≈ 100 Sonnet calls total (both arms).
- **Screen bars (pre-registered):** paired recall ≥ sonnet-40k − 5pts (one-sided 90%) AND precision Wilson-lower
  ≥ 70% AND invalid-rate ≤ 0.02. PASS → owner decides a full-key confirm (~190 further calls) before any
  production adoption. FAIL → question closed.
- **Cost:** ~9.5M Anthropic tokens (<9% of EXP-2; API-equiv ~$37) + ~70 external codex calls (separate sub).

## 5. Sample-size review and minimal sampling plan

Findings: grading = 57% of EXP-2 calls; full-key coverage for ALL 8 arms exceeded decision needs — only the
final cheap-vs-strong comparison needed full-key precision (paired CI ±2.7pts at n=1,175). Honest note: the 2pt
cheap-reader bar sits AT that noise floor; the signed verdict stands (plan bars are point-estimate by text), but
future bars should be set wider than the design CI or stated one-sided.

MINIMAL PLAN (future experiments, throughput metrics only):
1. **Two-stage screen/confirm:** every arm screens at n≈450 stratified h32 (±4–5pts paired); ONLY the
   adoption-decisive comparison confirms on the full key. EXP-2 replayed under this plan: ~45% fewer grading calls.
2. Always pair on the same gold items; reuse prior arms' verdicts as baselines (never re-grade a baseline).
3. Precision stays n=60 (adequate for the Wilson noise-gate; never cite it for absolute claims — ±11pts).
4. Optional two-look sequential stop (n≈300, then full screen) with a pre-registered alpha-spending rule.
5. NEVER shrink zero-tolerance identity domains (K-pairs / EXP-0 / EXP-4): exhaustive by design.

**Recommendation:** proceed to WP-FC-RUN with the adopted reader (its ~40–45M cost is one session window and the
catalog build is on the critical path); run the §4 probe in parallel or after, at owner discretion — its outcome
affects PRODUCTION reading economics, not the WP-FC-RUN build.
