"""v2 driver-naming harness — STRUCTURED schema + registry (Phase 0.1 foundation).

Design (per UnifiedRedesign_v2_BuildPlan.md, owner-confirmed 2026-05-31):

  core = {metric, mechanism}      both EXTRACTED from evidence -> core_name = f"{metric}_{mechanism}".
                                  Granularity FOLLOWS the evidence (the metric is named, not a free
                                  word-choice) -> kills the v1 forward_guidance-vs-revenue_guidance flip-flop.
                                  A metric-less core (e.g. bare "forward_guidance") is INVALID.

  DriverChange (per-event observation):
      direction   long|short                (stock impact — FINITE)
      state       up|down|unchanged          (FINITE polarity — NOT free text; renders raised/cut/maintained
                                              for guidance, beat/missed/inline for actuals via mechanism)
      state_note  optional free text         (the ONLY free field — exact verb/magnitude)
      segment     default "Total"            (THE retrieval-precision discriminator + XBRL MAPS_TO_MEMBER hook;
                                              specific iphone/china/datacenter ONLY when evidence names it.
                                              Phase 0 leaves it "Total" — turned on only if the segment-sibling
                                              precision test measurably fails. Do NOT over-build.)
      filer_ticker, sector  SIDE-CHANNEL      (the PRODUCER PROMPT never sees these; only code + scorers do.
                                              sector is a CHEAP GICS lookup for the coarse peer slice — NOT
                                              the discriminator. filer_ticker powers company-mismatch.)
      about_entity                            (the entity the driver is ASSERTED about; default = filer.
                                              about_entity != filer -> company-mismatch reject.)

  Recurrence: first sight = provisional; recurs across >=2 DISTINCT events -> durable. Provisionals are
              RECORDED and OFFERED for reuse (labeled) so promotion can happen (no cold-start deadlock);
              they are excluded from convergence/dup SCORING by the scorers, not hidden from the producer.

  Aliases / canonicalization are LEXICAL ONLY (slot-level synonym/order fold). We deliberately do NOT import
  vocab_seed's closed-vocab / slot-grammar / banned-category REJECT path (that was the dead 82%-reject gate);
  unknown metric/mechanism tokens PASS THROUGH unchanged (open vocabulary), never rejected.

Pure stdlib. No LLM here. JSON-persistable.
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ── finite enums (state is a closed polarity; free text only in state_note) ──
STATE_ENUM = ("up", "down", "unchanged")
DIRECTION_ENUM = ("long", "short")
DEFAULT_SEGMENT = "Total"
PROMOTE_AT = 2                      # recur across >=2 distinct events -> durable

# ── segment = the producer PICKS from the company's official XBRL parts MENU (anchoring upgrade):
#    the LLM returns a real member label (or "whole_company"); code does a PURE MEMBERSHIP CHECK + canonical
#    snap, never parses prose. _v2_parts_menu.json = {ticker: [official member labels]} (PIT-approx XBRL, the
#    3 part axes). Falls back to the older _v2_member_fixture only for tickers the menu doesn't cover. ──
_HERE = Path(__file__).resolve().parent
_FIX = json.loads((_HERE / "_v2_member_fixture.json").read_text())
_MEMBERS = _FIX["per_ticker"]
_COMMODITY = set(_FIX["commodity_passthrough"])
import os as _os
_PARTS_FILE = "_v2_heldout_parts_menu.json" if _os.environ.get("HELDOUT") else "_v2_parts_menu.json"   # Phase-2 fire
_PARTS = json.loads((_HERE / _PARTS_FILE).read_text()) if (_HERE / _PARTS_FILE).exists() else {}

def _norm(s) -> str:
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(s or ""))   # split CamelCase (DataCenter -> Data Center)
    return "_".join(re.findall(r"[a-z0-9]+", s.lower()))

def parts_menu(ticker: str) -> list:
    """The official member labels the producer may pick from for this company (the menu shown in the packet)."""
    return _PARTS.get((ticker or "").upper(), [])

def snap_member(ticker: str, segment_text) -> str:
    t = _norm(segment_text)
    if t in ("", "total", "company", "consolidated", "totals", "whole_company", "wholecompany"):
        return "Total"
    # (1) PRIMARY: membership check against this company's official parts menu (normalized + collapsed) ──
    norm2label = {}
    for m in parts_menu(ticker):
        norm2label[_norm(m)] = m
        norm2label[_norm(m).replace("_", "")] = m     # collapsed form: "datacenter" == "data_center"
    if t in norm2label:
        return norm2label[t]                          # canonical official member, as picked
    if t.replace("_", "") in norm2label:
        return norm2label[t.replace("_", "")]
    # (2) FALLBACK (tickers not covered by the menu): the older per-ticker fixture + commodity passthrough ──
    fx = _MEMBERS.get((ticker or "").upper(), {})
    if t in fx:
        return fx[t]
    toks = set(t.split("_"))
    for k, m in fx.items():
        if set(k.split("_")) <= toks:
            return m
    if t in _COMMODITY:
        return t.title()
    for c in _COMMODITY:
        if c in toks:
            return c.title()
    return t                                       # unknown -> pass through (reuse-catalog value)

# ── slot-level synonym fold (LEXICAL only — the alias mechanism, NOT a reject gate).
#    Unknown tokens pass through (open vocab). Maps a raw slot token to its canonical form. ──
METRIC_SYNONYMS = {
    "sales": "revenue", "net_sales": "revenue", "topline": "revenue", "turnover": "revenue",
    "eps": "earnings_per_share", "fcf": "free_cash_flow", "gm": "gross_margin",
    "comp_sales": "comparable_store_sales", "comparable_sales": "comparable_store_sales",
}
MECHANISM_SYNONYMS = {
    "outlook": "guidance", "forecast": "guidance", "guide": "guidance",
    "actuals": "actual", "result": "actual", "results": "actual", "reported": "actual",
}
_TOK = re.compile(r"[a-z0-9]+")

def _norm(s) -> str:
    return "_".join(_TOK.findall(str(s).lower()))

def canon_metric(m) -> str:
    m = _norm(m); return METRIC_SYNONYMS.get(m, m)

def canon_mechanism(x) -> str:
    x = _norm(x); return MECHANISM_SYNONYMS.get(x, x)

def core_name(metric, mechanism) -> str:
    cm, cx = canon_metric(metric), canon_mechanism(mechanism)
    if not cm:
        raise ValueError("metric-less core is invalid (the metric must be named from the evidence)")
    if not cx:
        raise ValueError("mechanism-less core is invalid")
    return f"{cm}_{cx}"


@dataclass
class Driver:
    metric: str
    mechanism: str
    definition: str = ""
    aliases: list = field(default_factory=list)        # lexical variants (raw slot forms != canonical)
    status: str = "provisional"                        # provisional | durable
    distinct_events: list = field(default_factory=list)

    @property
    def core_name(self) -> str:
        return f"{self.metric}_{self.mechanism}"

    @property
    def recurrence_count(self) -> int:
        return len(self.distinct_events)


@dataclass
class DriverChange:
    core_ref: str
    direction: str
    state: str
    event_id: str
    filer_ticker: str                                  # SIDE-CHANNEL (producer never sees)
    sector: str = ""                                   # SIDE-CHANNEL cheap lookup (peer slice, not discriminator)
    segment: str = DEFAULT_SEGMENT                      # discriminator + XBRL MAPS_TO_MEMBER hook
    about_entity: str = ""                             # asserted entity (default = filer)
    state_note: str = ""                               # optional free text (only free field)
    context_note: str = ""                             # per-event, <=2 sentences
    primary: bool = False                              # producer-DECLARED primary driver (for direction)
    source: str = ""
    date: str = ""


class Registry:
    """Live registry of structured Drivers + the append-only DriverChange log + reject log."""

    def __init__(self) -> None:
        self.drivers: dict[str, Driver] = {}
        self.changes: list[DriverChange] = []
        self.rejects: list[dict] = []                  # {event_id, reason, ...} — incl. deferred + company_mismatch

    # ── reuse-catalogs shown to the producer (open lists; reuse, don't re-coin) ──
    def metric_catalog(self) -> list[str]:
        return sorted({d.metric for d in self.drivers.values()})

    def mechanism_catalog(self) -> list[str]:
        return sorted({d.mechanism for d in self.drivers.values()})

    def durable_view(self) -> list[Driver]:
        return [d for d in self.drivers.values() if d.status == "durable"]

    def candidate_view(self) -> list[dict]:
        """durable + provisional (labeled) — BOTH offered for reuse so promotion isn't deadlocked."""
        return [{"core_name": d.core_name, "metric": d.metric, "mechanism": d.mechanism,
                 "status": d.status, "recurrence_count": d.recurrence_count, "definition": d.definition}
                for d in sorted(self.drivers.values(), key=lambda d: (d.status != "durable", d.core_name))]

    # ── the cross-entity bug-fix (objective) ──
    @staticmethod
    def company_mismatch(about_entity, filer_ticker) -> bool:
        a, f = _norm(about_entity), _norm(filer_ticker)
        return bool(a) and a != f                       # asserted about a DIFFERENT entity than the filer

    # ── reuse-or-create + lexical alias recording ──
    def reuse_or_create(self, metric, mechanism, definition="") -> Driver:
        cn = core_name(metric, mechanism)               # raises on metric/mechanism-less
        if cn not in self.drivers:
            self.drivers[cn] = Driver(metric=canon_metric(metric), mechanism=canon_mechanism(mechanism),
                                      definition=definition)
        else:
            raw = f"{_norm(metric)}_{_norm(mechanism)}"  # record the losing lexical variant as an alias
            d = self.drivers[cn]
            if raw != cn and raw not in d.aliases:
                d.aliases.append(raw)
            if definition and not d.definition:
                d.definition = definition
        return self.drivers[cn]

    # ── admit one event's producer decision (list of driver dicts; [] = DEFER) ──
    def admit_event(self, event_id, filer_ticker, decision, *, sector="", source="", date="") -> list[DriverChange]:
        emitted: list[DriverChange] = []
        if not decision:
            self.rejects.append({"event_id": event_id, "reason": "deferred"})
            return emitted
        for dr in decision:
            about = dr.get("about_entity") or filer_ticker
            if self.company_mismatch(about, filer_ticker):
                self.rejects.append({"event_id": event_id, "reason": "company_mismatch",
                                     "about_entity": _norm(about), "filer": _norm(filer_ticker),
                                     "proposed": f"{_norm(dr.get('metric',''))}_{_norm(dr.get('mechanism',''))}"})
                continue
            direction = dr["direction"]; state = dr.get("state", "unchanged")
            if direction not in DIRECTION_ENUM:
                raise ValueError(f"direction must be one of {DIRECTION_ENUM}, got {direction!r}")
            if state not in STATE_ENUM:
                raise ValueError(f"state must be one of {STATE_ENUM} (free text -> state_note), got {state!r}")
            d = self.reuse_or_create(dr["metric"], dr["mechanism"], dr.get("context_note", ""))
            if event_id not in d.distinct_events:
                d.distinct_events.append(event_id)
            if d.status == "provisional" and d.recurrence_count >= PROMOTE_AT:
                d.status = "durable"
            ch = DriverChange(core_ref=d.core_name, direction=direction, state=state, event_id=event_id,
                              filer_ticker=filer_ticker, sector=sector,
                              segment=snap_member(filer_ticker, dr.get("segment", DEFAULT_SEGMENT)),
                              about_entity=_norm(about), state_note=dr.get("state_note", ""),
                              context_note=dr.get("context_note", ""), primary=bool(dr.get("primary", False)),
                              source=source, date=date)
            self.changes.append(ch)
            emitted.append(ch)
        return emitted

    # ── processed-event tracking (for the PIT loop) ──
    def changes_event_ids(self) -> set:
        return {c.event_id for c in self.changes}

    def processed_event_ids(self) -> set:
        return self.changes_event_ids() | {r["event_id"] for r in self.rejects}

    # ── persistence ──
    def to_dict(self) -> dict:
        return {"drivers": {k: asdict(v) for k, v in self.drivers.items()},
                "changes": [asdict(c) for c in self.changes], "rejects": self.rejects}

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path) -> "Registry":
        r = cls(); d = json.loads(Path(path).read_text())
        r.drivers = {k: Driver(**v) for k, v in d.get("drivers", {}).items()}
        r.changes = [DriverChange(**c) for c in d.get("changes", [])]
        r.rejects = d.get("rejects", [])
        return r

    # ── summary stats (for the run header) ──
    def stats(self) -> dict:
        return {"drivers": len(self.drivers),
                "durable": sum(1 for d in self.drivers.values() if d.status == "durable"),
                "provisional": sum(1 for d in self.drivers.values() if d.status == "provisional"),
                "changes": len(self.changes),
                "rejects": len(self.rejects),
                "deferred": sum(1 for r in self.rejects if r["reason"] == "deferred"),
                "company_mismatch": sum(1 for r in self.rejects if r["reason"] == "company_mismatch")}
