"""Phase 0.2 — DEV warm-stream assembler.

Unifies the BASE own-recurrence corpus (pass4/eval_corpus.json, 61) + the CURATED relatedness
ground (_v2_dev_clusters_labeled.json, 200) into one PIT-ordered stream. The PRODUCER sees only
{event_id, source_type, date, evidence} with the evidence LIGHTLY anonymized (ticker symbol) — the
ticker/sector (side-channel) and the return + cluster ground are HIDDEN from it. The SCORERS read the
hidden truth (direction = return sign / base gold; relatedness ground = independent canonical_bucket).

DEV bar: light anonymization is fine (we iterate). The Phase-2 held-out gets the full LLM scrub.

API:
  Stream(...).producer_events()      -> [{event_id, source_type, date, evidence}]  (PIT order, blind)
  .direction_truth()                 -> {event_id: 'long'|'short'}
  .relatedness_ground()              -> {axis: {canonical_bucket: [event_id,...]}}   (independent ground)
  .sidechannel(event_id)             -> {ticker, sector}
  .family_of(event_id)               -> family_id | None
"""
from __future__ import annotations
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "pass4" / "eval_corpus.json"
CLUSTERS = HERE / "_v2_dev_clusters_labeled.json"
BASE_ADMIT_OVERRIDE = {"base::s05",   # ground fix: s05 is a real EPS beat, v1 gold mis-marked it reject
                       "base::s49",   # ANCHORING ground relabel (owner-verified 2026-06-01): GM robotaxi-cancel
                       #                is a specific attributable ONE-OFF -> admit-provisional, not reject (decision 3)
                       "base::s54"}   # ANCHORING ground relabel (owner-verified): $40B buyback authorization is a
                       #                large/quantified capital_return driver -> admit, not reject (decision 2)


def _light_anon(evidence: str, ticker: str) -> str:
    """DEV-grade anonymization: strip the bare ticker symbol token only (company NAMES are left —
    they do not change the {metric, mechanism} the producer extracts; full scrub is held-out-only)."""
    if not ticker:
        return evidence
    return re.sub(rf"\b{re.escape(ticker)}\b", "the company", evidence)


class Stream:
    def __init__(self, base_path=BASE, clusters_path=CLUSTERS):
        self.events: dict[str, dict] = {}          # event_id -> full record (incl hidden truth)
        import os
        if os.environ.get("HELDOUT"):              # Phase-2 fire: serve the frozen ho:: set instead of DEV
            self._load_heldout(HERE / "_v2_heldout_events.json")
        else:
            self._load_base(base_path)
            self._load_clusters(clusters_path)
        # PIT order
        self._order = sorted(self.events.values(), key=lambda e: (e["date"], e["event_id"]))

    def _load_heldout(self, path):
        """Phase-2 held-out: the frozen ho:: events (already leakage-scrubbed at build time). Ground = the
        independent canonical_bucket. Evidence ticker is additionally light-anon'd for blindness (the ticker is a
        side-channel for the parts menu, never needed inside the evidence)."""
        for x in json.load(open(path))["events"]:
            ax = x["axis"]
            self._add({"event_id": x["event_id"], "ticker": x.get("ticker", ""), "sector": "",
                       "date": x.get("date", ""), "source_type": x.get("source_type", "news"),
                       "evidence": _light_anon(x.get("evidence", ""), x.get("ticker", "")),
                       "direction": None, "ret_mag": None,
                       "axis": ax, "bucket": (None if ax == "reject" else x.get("canonical_bucket")),
                       "family": None, "is_reject": ax == "reject"})

    def _add(self, rec):
        self.events[rec["event_id"]] = rec

    def _load_base(self, path):
        for x in json.load(open(path))["corpus"]:
            gd = x.get("gold", {}).get("expected_drivers", [])
            direction = gd[0]["direction"] if gd else None
            eid = f"base::{x['id']}"
            self._add({"event_id": eid, "ticker": x.get("ticker", ""),
                       "sector": x.get("sector", ""), "date": x.get("date", ""),
                       "source_type": x.get("source_type", "8k"),
                       "evidence": _light_anon(x.get("evidence_text", ""), x.get("ticker", "")),
                       "direction": direction, "ret_mag": None, "axis": None, "bucket": None, "family": None,
                       "is_reject": (not bool(gd)) and eid not in BASE_ADMIT_OVERRIDE})

    def _load_clusters(self, path):
        for f in json.load(open(path))["families"]:
            axis = f["axis"]
            for i, m in enumerate(f["members"]):
                eid = m.get("member_id") or f"{f['family_id']}#{i}"
                eid = f"clu::{eid}"
                rp = m.get("return_pct")
                direction = ("long" if rp > 0 else "short") if isinstance(rp, (int, float)) and rp != 0 else None
                self._add({"event_id": eid, "ticker": m.get("ticker", ""), "sector": m.get("sector", ""),
                           "date": (m.get("date", "") or "")[:10], "source_type": m.get("source_type", "news"),
                           "evidence": _light_anon(m.get("evidence", ""), m.get("ticker", "")),
                           "direction": direction, "ret_mag": abs(rp) if isinstance(rp, (int, float)) else None,
                           "axis": axis, "bucket": m.get("canonical_bucket"),
                           "family": f["family_id"], "is_reject": axis == "reject"})

    # ── producer-facing (BLIND) ──
    def producer_events(self):
        return [{"event_id": e["event_id"], "source_type": e["source_type"], "date": e["date"],
                 "evidence": e["evidence"]} for e in self._order]

    # ── scorer-facing (HIDDEN truth) ──
    def direction_truth(self):
        return {e["event_id"]: e["direction"] for e in self._order if e["direction"]}

    def direction_truth_full(self):
        # {event_id: {"dir": long|short, "mag": abs_return or None (None = base/no-magnitude, never filtered)}}
        return {e["event_id"]: {"dir": e["direction"], "mag": e.get("ret_mag")}
                for e in self._order if e["direction"]}

    # owner-ruled 2026-06-01: the seg_sib "total" bucket is the un-split COMPANY-WIDE baseline (revenue@Total =
    # backbone, carries no segment identity) -> it is NOT a valid segment-sibling and is excluded from seg_sib.
    SEG_BASELINE_EXCLUDE = {("seg_sib", "total")}

    def relatedness_ground(self):
        ground: dict[str, dict[str, list]] = {}
        for e in self._order:
            if e["axis"] in (None, "reject") or not e["bucket"]:
                continue
            if (e["axis"], e["bucket"]) in self.SEG_BASELINE_EXCLUDE:
                continue
            ground.setdefault(e["axis"], {}).setdefault(e["bucket"], []).append(e["event_id"])
        return ground

    def reject_ids(self):
        return [e["event_id"] for e in self._order if e["is_reject"]]

    def sidechannel(self, event_id):
        e = self.events[event_id]
        return {"ticker": e["ticker"], "sector": e["sector"]}

    def family_of(self, event_id):
        return self.events[event_id].get("family")

    def stats(self):
        from collections import Counter
        axes = Counter(e["axis"] or "base" for e in self._order)
        return {"n_events": len(self._order), "by_axis": dict(axes),
                "n_direction_truth": len(self.direction_truth()),
                "n_reject": len(self.reject_ids()),
                "date_span": (self._order[0]["date"], self._order[-1]["date"])}


if __name__ == "__main__":
    s = Stream()
    print(json.dumps(s.stats(), indent=2))
    g = s.relatedness_ground()
    print("relatedness axes:", {ax: {"buckets": len(b), "events": sum(len(v) for v in b.values())} for ax, b in g.items()})
