"""Phase 0.4 — the 4 measurements (generic, content-independent).

Reads the producer's final registry (v2_schema) + the independent ground (v2_stream). All four lead
with objective / gold-free signals; relatedness leads with PRECISION so "converged-but-too-coarse"
FAILS (it can't both be one core AND keep sibling buckets apart).

  convergence(reg, stream)  -> dup_rate (gold-free) + COLLAPSE sentinel (do sibling buckets keep
                               DISTINCT cores? a collapse = the #1 failure, and it FAILS here).
  relatedness(reg, stream)  -> precision@k per axis using the producer's OWN tags to retrieve, scored
                               vs the INDEPENDENT canonical_bucket ground. Over-merge (same core for
                               sibling buckets) -> low precision. + sibling-discrimination per axis.
  direction(reg, stream)    -> emitted direction vs objective return sign.
  reject(reg, stream)       -> reject-only events correctly deferred; restructuring leaks tracked.

blind_judge_precision(...) -> the NON-Claude (gpt-5.4) evidence-only "is B related to A?" leg (sampled).
"""
from __future__ import annotations
import json, math, itertools, hashlib, re
from collections import defaultdict, Counter
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from v2_schema import Registry, canon_metric
from v2_stream import Stream

EMB_CACHE = HERE.parent / "pass4" / "_wf4_emb_cache.json"
_C = None
def _client():
    global _C
    if _C is None:
        import os
        from openai import OpenAI
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key.startswith("sk-"):
            for line in (HERE.parent.parent / ".env").read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip(); break
        _C = OpenAI(api_key=key)
    return _C
def _embed(texts):
    cache = json.load(open(EMB_CACHE)) if EMB_CACHE.exists() else {}
    need = [t for t in texts if t and t not in cache]
    if need:
        for i in range(0, len(need), 64):
            r = _client().embeddings.create(model="text-embedding-3-large", input=need[i:i+64])
            for t, d in zip(need[i:i+64], r.data): cache[t] = d.embedding
        json.dump(cache, open(EMB_CACHE, "w"))
    return {t: cache.get(t) for t in texts}
def _cos(a, b):
    if not a or not b: return 0.0
    dot = sum(x*y for x, y in zip(a, b)); na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na and nb else 0.0


# ── PRE-COMMITTED generic-earnings-backbone (the universal P&L lines every earnings event reports;
#    NON-discriminative for relatedness -> excluded at the company/Total level. Segment-specific
#    (revenue_actual,iPhone) and all discriminative drivers (demand, drug_approval, capex...) are KEPT.
#    A textbook P&L list, fixed BEFORE scoring run2 — not tuned to the outcome. ──
BACKBONE_CORES = frozenset({
    "revenue_actual", "earnings_per_share_actual", "net_income_actual", "ebitda_actual",
    "gross_profit_actual", "gross_margin_margin_shift", "operating_margin_margin_shift",
    "operating_income_actual", "free_cash_flow_actual", "earnings_actual",
})

# ── driver_state grading key = NAME-INVARIANT (owner-approved measurement bug-fix 2026-06-01; the 0.90 bar is
#    UNCHANGED). The old key hashed the surface metric NAME, so a producer RENAME (oil_production->oil_volume)
#    forced gpt-5.4 to re-grade identical evidence and FLIP the gold (run-to-run noise). Fix: drop the
#    discriminative object from the key (the EVIDENCE disambiguates which object across events) so a rename reuses
#    the same gold; KEEP the object for backbone lines (revenue vs eps co-occur in one event, must stay distinct).
BACKBONE_METRICS = frozenset({"revenue", "earnings_per_share", "net_income", "ebitda", "gross_profit",
                              "gross_margin", "operating_margin", "operating_income", "free_cash_flow", "earnings"})
def state_key(evidence, metric, mechanism, model):
    obj = canon_metric(metric or "") if (metric in BACKBONE_METRICS) else ""
    return hashlib.sha256(("S2\x1f" + evidence + "\x1f" + obj + "\x1f" + (mechanism or "") + "\x1f" + model).encode()).hexdigest()[:16]

# ── seg-precision ROLL-UP (PRE-COMMITTED grading rule, owner-decided 2026-06-01 BEFORE the held-out run): grade
#    seg_sib at the REPORTABLE-segment level. A producer pick that is a sub-line or label-variant of the correct
#    reportable segment rolls UP and counts CORRECT; only a DIFFERENT reportable segment is a miss. The held-out
#    XBRL menu carries sub-line + label-variant members (QCOM 'Handsets' under 'Qct'; MDT 'DiabetesGroup' ≡
#    'DiabetesOperatingUnit'), so WITHOUT this rule the menu manufactures ~18 fake misses on the now-required
#    seg-precision bar. Map = _v2_heldout_seg_rollup.json (XBRL co-tagging + documented renames; never merges two
#    distinct reportable segments). It is a NO-OP for any ticker/segment not in the map (returns segment unchanged),
#    so it relabels consistently and cannot change the grouping (hence the pass/fail) of a run it does not cover.
_SEG_ROLLUP_P = HERE / "_v2_heldout_seg_rollup.json"
_SEG_ROLLUP = json.load(open(_SEG_ROLLUP_P)) if _SEG_ROLLUP_P.exists() else {}
def _norm_seg(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower()).replace("segment", "")
def roll_segment(ticker, segment):
    """Roll a producer's seg pick up to its reportable segment (identity/no-op if ticker/segment unmapped)."""
    return _SEG_ROLLUP.get(ticker, {}).get(_norm_seg(segment), segment)

def emitted_by_event(reg: Registry):
    d = defaultdict(list)
    for c in reg.changes:
        d[c.event_id].append({"core": c.core_ref, "segment": c.segment, "direction": c.direction, "primary": c.primary})
    return d


def convergence(reg: Registry, stream: Stream, dup_thresh=0.86, use_embeddings=True):
    cores = [d.core_name for d in reg.drivers.values()]
    dup_pairs = []
    if use_embeddings and len(cores) > 1:
        E = _embed(cores)
        for a, b in itertools.combinations(cores, 2):
            if _cos(E[a], E[b]) >= dup_thresh:
                dup_pairs.append((a, b))
    dup_rate = round(len(dup_pairs) / max(1, len(cores)), 3)
    # COLLAPSE sentinel: do distinct sibling buckets map to DISTINCT producer cores?
    ground = stream.relatedness_ground(); emit = emitted_by_event(reg)
    collapses = []
    for axis in ("metric_sib", "seg_sib", "object_sib"):
        buckets = ground.get(axis, {})
        dom = {}
        for b, eids in buckets.items():
            tk = b.split("_", 1)[0] if axis == "seg_sib" else None        # seg-precision roll-up (pre-committed)
            cc = Counter((x["core"], roll_segment(tk, x["segment"]) if tk else x["segment"])
                         for eid in eids for x in emit.get(eid, []))       # (core,segment) identity
            dom[b] = cc.most_common(1)[0][0] if cc else None
        for b1, b2 in itertools.combinations(sorted(buckets), 2):
            if dom[b1] and dom[b1] == dom[b2]:
                collapses.append({"axis": axis, "buckets": [b1, b2], "merged_core": dom[b1]})
    return {"registry_size": len(cores), "dup_rate": dup_rate, "n_collapses": len(collapses),
            "collapses": collapses, "near_dup_pairs": dup_pairs[:10]}


def relatedness(reg: Registry, stream: Stream, k=10, use_embeddings=True, exclude_backbone=False):
    """Two GATED legs on the producer's REUSE-GRAPH, both required:
      reuse_precision = of events that SHARE my identity, fraction truly same-bucket -> catches COLLAPSE (too-coarse)
      reuse_recall    = of truly same-bucket events, fraction that SHARE my identity -> catches OVER-SPLIT (too-fine)
    FINAL identity granularity (owner 2026-05-31, the LAST correction before permanent freeze):
      PEER axis matches at the CORE (coarser than siblings) so a cross-sector THEME co-retrieves — two
      airlines' fuel-cost, a bank's + a REIT's rate-reprice, tariff pressure across Materials/Tech/Staples all
      link (this is the run-2' peer recall hole). PRECISION is protected by the PRODUCER giving distinct
      buckets DISTINCT cores (datacenter-demand != obesity-demand), NOT by a sector tie-breaker (which would
      re-fragment the very cross-sector themes being recovered); a producer over-merge shows up as low peer
      precision and is reported, not masked. SIBLING axes keep (core, segment) — segment IS the discriminator.
      exclude_backbone removes the generic earnings P&L (BACKBONE_CORES) from BOTH so a shared revenue/eps
      never fabricates relatedness (objective, pre-committed)."""
    ground = stream.relatedness_ground(); emit = emitted_by_event(reg)
    ev_ids = {e for v in ground.values() for b in v.values() for e in b}
    # seg-precision roll-up (pre-committed): map a producer's seg pick -> its reportable segment for seg_sib events
    seg_tk = {e: b.split("_", 1)[0] for b, eids in ground.get("seg_sib", {}).items() for e in eids}
    def _seg(eid, s): return roll_segment(seg_tk[eid], s) if eid in seg_tk else s
    core_of = {eid: {x["core"] for x in emit.get(eid, [])} for eid in ev_ids}
    cs_of = {eid: {(x["core"], _seg(eid, x["segment"])) for x in emit.get(eid, [])} for eid in ev_ids}
    all_cores = sorted({c for s in core_of.values() for c in s})
    E = _embed(all_cores) if (all_cores and use_embeddings) else {}

    def ident(eid, axis):
        # FINAL identity granularity (owner 2026-05-31, LAST instrument correction before permanent freeze):
        #   PEER axis  -> {core}          [design §2 peer = sector+core; the relatedness METRIC matches at the
        #       CORE — coarser than siblings — so a cross-sector THEME co-retrieves: two airlines' fuel-cost,
        #       a bank's AND a REIT's rate-reprice, tariff margin pressure across Materials+Tech+Staples all
        #       link. PRECISION here is protected by the PRODUCER extracting a DISCRIMINATIVE metric
        #       (datacenter-demand != obesity-demand as distinct cores) — NOT by a sector tie-breaker, which
        #       would re-fragment exactly the cross-sector themes this pass is recovering. If the producer
        #       over-merges to a generic core, precision drops HERE and is reported, not masked.]
        #   SIBLING ax -> {(core, segment)}  [segment IS the discriminator: iphone-rev vs services-rev].
        # Backbone (generic-earnings P&L) excluded from BOTH so a shared revenue/eps never fabricates relatedness.
        if axis == "peer":
            return {c for c in core_of[eid] if not (exclude_backbone and c in BACKBONE_CORES)}
        return {cs for cs in cs_of[eid] if not (exclude_backbone and cs[0] in BACKBONE_CORES and cs[1] == "Total")}

    def emb_sim(cq, cc):
        return max((_cos(E.get(a), E.get(b)) for a in cq for b in cc), default=0.0)

    out = {}
    for axis, buckets in ground.items():
        events = [(eid, b) for b, eids in buckets.items() for eid in eids]
        bof = {e: b for e, b in events}
        rp, rr, fkp, fkr = [], [], [], []
        for q, bq in events:
            iq = ident(q, axis)
            others = [e for e, _ in events if e != q]
            same = [e for e in others if bof[e] == bq]
            shared = [e for e in others if ident(e, axis) & iq] if iq else []
            if shared:
                rp.append(sum(1 for e in shared if bof[e] == bq) / len(shared))   # precision (collapse catch)
            if same:
                rr.append(sum(1 for e in same if ident(e, axis) & iq) / len(same))  # recall (over-split catch)
            def score(e):
                return 2.0 if (ident(e, axis) & iq) else emb_sim(core_of.get(q, set()), core_of.get(e, set()))
            topk = sorted(others, key=score, reverse=True)[:k]
            if topk:
                fkp.append(sum(1 for e in topk if bof[e] == bq) / len(topk))
            if same:
                fkr.append(sum(1 for e in topk if bof[e] == bq) / len(same))
        m = lambda L: round(sum(L)/len(L), 3) if L else None
        out[axis] = {"reuse_precision": m(rp), "reuse_recall": m(rr),
                     f"precision_at_{k}": m(fkp), f"recall_at_{k}": m(fkr),
                     "identity": "core" if axis == "peer" else "(core,segment)",
                     "n_queries": len(events), "n_buckets": len(buckets)}
    return out


def direction(reg: Registry, stream: Stream, primary_only=False, ret_floor=0.0):
    """primary_only (REFINEMENT): score only the producer's DECLARED primary driver (committed before the
    return is known). ret_floor (REFINEMENT, pre-committed 1.0%): drop events with |return| < floor (sign is
    noise on tiny moves). Both objective + pre-committed — no scorer cherry-picking the sign-matching driver."""
    truth = stream.direction_truth_full(); ok = tot = dropped = 0
    misses = []
    for c in reg.changes:
        t = truth.get(c.event_id)
        if not t:
            continue
        if primary_only and not c.primary:
            continue
        if ret_floor and t["mag"] is not None and t["mag"] < ret_floor:
            dropped += 1
            continue
        tot += 1
        if c.direction == t["dir"]:
            ok += 1
        else:
            misses.append({"event_id": c.event_id, "core": c.core_ref, "emitted": c.direction, "truth": t["dir"]})
    return {"direction_accuracy": round(ok/max(1, tot), 3), "n": tot, "n_dropped_below_floor": dropped, "misses": misses[:12]}


def direction_objective(reg: Registry, stream: Stream):
    """DIRECTION = stock impact, DERIVED objectively from the realized move (return sign) and attributed to the
    PRIMARY driver(s) (or all, if none flagged). NOT producer-emitted/graded (owner ruling b: the producer reads
    scrubbed evidence and cannot know the reaction). Reported as a DIAGNOSTIC, never a producer bar. The
    'producer_emit_vs_objective' agreement just exposes the cause-direction (what the producer read) vs
    stock-reaction (the realized move) gap — e.g. a guidance cut on a stock that rose."""
    truth = stream.direction_truth()
    byev = defaultdict(list)
    for c in reg.changes:
        byev[c.event_id].append(c)
    attached = 0
    for eid, cs in byev.items():
        if eid in truth:
            attached += len([c for c in cs if c.primary]) or len(cs)
    n = sum(1 for c in reg.changes if c.event_id in truth)
    agree = sum(1 for c in reg.changes if c.event_id in truth and c.direction == truth[c.event_id])
    return {"note": "objective stock-impact, attached to primary; NOT a producer bar (owner ruling b)",
            "n_attached": attached, "producer_emit_vs_objective": round(agree / max(1, n), 3), "n": n}


def driver_state_accuracy(reg: Registry, stream: Stream, model="gpt-5.4"):
    """NEW GATE metric (replaces direction): does the producer correctly DESCRIBE the metric's move (state polarity
    up/down/unchanged) from the evidence? Graded vs an INDEPENDENT non-Claude (gpt-5.4) read of the SAME metric.
    This is the producer's real directional job ('describe the news') — gradable from evidence, unlike the
    stock-reaction direction. Content-hash cached. No new producer run (grades run-2's existing states)."""
    ev = {e["event_id"]: e["evidence"] for e in stream.producer_events()}
    cache_p = HERE / "_v2_state_grade_cache_ni.json"          # name-invariant cache (see state_key); old churning cache retired
    cache = json.load(open(cache_p)) if cache_p.exists() else {}
    SYS = ("From the evidence, did the named METRIC move UP, DOWN, or stay UNCHANGED for THIS company this period? "
           "beat/raised/grew/increased/record/strong = up ; missed/cut/lowered/declined/fell/weak = down ; "
           "in-line/maintained/reaffirmed = unchanged. Judge the METRIC's own move, NOT the stock price. "
           "Output JSON {state: up|down|unchanged}.")
    SCH = {"type": "object", "additionalProperties": False,
           "properties": {"state": {"type": "string", "enum": ["up", "down", "unchanged"]}}, "required": ["state"]}
    ok = tot = n_new = 0
    mis = []
    for c in reg.changes:
        e = ev.get(c.event_id)
        d = reg.drivers.get(c.core_ref)
        if not e or not d:
            continue
        metric = d.metric
        key = state_key(e, metric, d.mechanism, model)        # NAME-INVARIANT key (rename-stable)
        if key in cache:
            g = cache[key]
        else:
            r = _client().responses.create(model=model,
                input=[{"role": "system", "content": SYS}, {"role": "user", "content": f"METRIC: {metric}\nEVIDENCE: {e}"}],
                text={"format": {"type": "json_schema", "name": "st", "strict": True, "schema": SCH}})
            g = json.loads(r.output_text); cache[key] = g; json.dump(cache, open(cache_p, "w")); n_new += 1
        tot += 1
        if c.state == g["state"]:
            ok += 1
        else:
            mis.append({"event": c.event_id, "metric": metric, "producer": c.state, "gold": g["state"]})
    return {"driver_state_accuracy": round(ok / max(1, tot), 3), "n": tot, "n_new_calls": n_new, "misses": mis[:12]}


def reject(reg: Registry, stream: Stream):
    rej = stream.reject_ids(); emitted_events = reg.changes_event_ids()
    leaked = [r for r in rej if r in emitted_events]
    # restructuring failure-class is a NAMED tracked class (D2: evidence-based, no closed list)
    return {"reject_precision": round(sum(1 for r in rej if r not in emitted_events)/max(1, len(rej)), 3),
            "n_reject": len(rej), "n_leaked": len(leaked), "leaked": leaked,
            "failure_classes": {"cross_entity_or_macro_leak": leaked}}


def scorecard(reg: Registry, stream: Stream, use_embeddings=True, exclude_backbone=False):
    # GATE = convergence + relatedness + driver_state_accuracy(LLM, run separately) + reject.
    # direction is a DERIVED diagnostic (owner ruling b), NOT a producer bar.
    return {"convergence": convergence(reg, stream, use_embeddings=use_embeddings),
            "relatedness": relatedness(reg, stream, use_embeddings=use_embeddings, exclude_backbone=exclude_backbone),
            "direction_objective": direction_objective(reg, stream),
            "reject": reject(reg, stream)}


# ── blind NON-Claude (gpt-5.4) relatedness judge leg (sampled, evidence-only) ──
# Two SYS prompts, selectable via `mode`, so we can report OLD (instance) vs NEW (type) side-by-side.
#   mode="instance" (OLD, gave 0.375): "same business object AND same metric" — grades INSTANCE identity
#       (same drug, same firm). This is the WRONG question for a REUSE registry: it marks two FDA decisions
#       on different drugs "not related" even though they share the reusable `fda_decision` driver.
#   mode="type" (NEW, recalibrated): "would these usefully CO-RETRIEVE for a predictor?" — grades TYPE-level
#       relatedness (same KIND of causal driver), which is what the registry + relatedness metric actually do.
# CAVEAT (recorded, owner 2026-05-31): judge=gpt-5.4 AND the cluster ground=gpt-5.4 -> this is a CONSISTENCY
# check, NOT independent validation. A non-gpt-5.4 / human relatedness check is OWED before the held-out.
_JUDGE_SYS = {
    "instance": ("You judge whether two financial events are about the SAME reusable driver (same business "
        "object AND same metric). Answer strictly from the evidence. demand!=sales, capex!=revenue, "
        "volume!=price, guidance!=actual, different segment, different object => NOT the same. "
        "Output JSON {related: bool}."),
    "type": ("A predictor analyzing what moves a stock keeps a registry of REUSABLE causal drivers and retrieves "
        "related ones as priors. Judge: would these two events USEFULLY CO-RETRIEVE — i.e. are they the SAME "
        "TYPE of driver / same causal mechanism — EVEN IF they are different companies, drugs, commodities, or "
        "segments? Answer strictly from the evidence. SAME type (related=true): two FDA/regulatory decisions; "
        "two hyperscaler AI-capex events; two rate/macro-driven repricings; two fuel-cost pressures; two "
        "GLP-1/obesity demand reads. DIFFERENT type (related=false): demand vs capex, price vs volume, "
        "guidance vs realized actual, a company's own driver vs a pure sympathy/macro-noise move, or two "
        "genuinely unrelated mechanisms. Output JSON {related: bool}."),
}
def blind_judge_precision(reg: Registry, stream: Stream, k=1, sample_per_axis=8, model="gpt-5.4", mode="type"):
    """For a sample of (query, top-1 retrieved) pairs, ask gpt-5.4 evidence-only if they are related, then
    compare to the independent cluster ground (same bucket?). mode selects the judge calibration (see above);
    cache key includes mode so OLD and NEW are scored from separate calls."""
    import os, hashlib
    ground = stream.relatedness_ground(); emit = emitted_by_event(reg)
    ev = {e["event_id"]: e["evidence"] for e in stream.producer_events()}
    all_cores = sorted({x["core"] for v in emit.values() for x in v}); E = _embed(all_cores) if all_cores else {}
    def sim(q, c):
        best = 0.0
        for xq in emit.get(q, []):
            for xc in emit.get(c, []):
                best = max(best, 2.0 if xq["core"] == xc["core"] else _cos(E.get(xq["core"]), E.get(xc["core"])))
        return best
    cache_p = HERE / "_v2_judge_cache.json"; cache = json.load(open(cache_p)) if cache_p.exists() else {}
    SYS = _JUDGE_SYS[mode]
    SCH = {"type": "object", "additionalProperties": False, "properties": {"related": {"type": "boolean"}}, "required": ["related"]}
    rows, agree, n = [], 0, 0
    for axis, buckets in ground.items():
        events = [(eid, b) for b, eids in buckets.items() for eid in eids][:sample_per_axis]
        for q, bq in events:
            cands = [(c, bc) for bb, eids in buckets.items() for c in eids for bc in [bb] if c != q]
            if not cands: continue
            top = max(cands, key=lambda cb: sim(q, cb[0]))
            key = hashlib.sha256((mode + "\x1f" + ev[q] + "\x1f" + ev[top[0]] + "\x1f" + model).encode()).hexdigest()[:16]
            if key in cache:
                jr = cache[key]
            else:
                r = _client().responses.create(model=model,
                    input=[{"role": "system", "content": SYS},
                           {"role": "user", "content": f"A: {ev[q]}\n\nB: {ev[top[0]]}\n\nRelated?"}],
                    text={"format": {"type": "json_schema", "name": "rel", "strict": True, "schema": SCH}})
                jr = json.loads(r.output_text); cache[key] = jr; json.dump(cache, open(cache_p, "w"))
            ground_same = (top[1] == bq)
            agree += (jr["related"] == ground_same); n += 1
            rows.append({"axis": axis, "q_bucket": bq, "top_bucket": top[1], "judge_related": jr["related"], "ground_same": ground_same})
    return {"n": n, "mode": mode, "judge_ground_agreement": round(agree/max(1, n), 3),
            "caveat": "judge=gpt-5.4 AND ground=gpt-5.4 -> consistency check, NOT independent; non-gpt-5.4/human owed before held-out",
            "rows": rows[:20]}


if __name__ == "__main__":
    import sys as _s
    reg = Registry.load(HERE / "_v2_state.json")
    print(json.dumps(scorecard(reg, Stream(), use_embeddings="--no-emb" not in _s.argv), indent=2))
