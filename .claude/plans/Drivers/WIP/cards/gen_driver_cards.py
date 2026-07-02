# -*- coding: utf-8 -*-
"""Generate a print-ready A4 PDF of Driver-state index cards (6 per sheet).
Section 1 = filled reference deck (3 ref + 27 state cards).
Section 2 = handwriting deck (same 27 cards with number fields + quote BLANKED).
Vector HTML/CSS -> Chrome headless -> PDF. Borders are exact by construction.
"""
import os, subprocess, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "driver_state_cards.html")
PDF  = os.path.join(HERE, "driver_state_cards.pdf")

FT_CLASS = {"metric":"ft-metric","guidance":"ft-guidance",
            "surprise":"ft-surprise","action_event":"ft-action","ref":"ft-ref"}

def esc(s):
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

def V(i, w=None, c=None, prod=None, note=None, r=None):
    return {"i":i, "w":w, "c":c, "prod":prod, "note":note, "r":r}

def verdict_html(verdict):
    if verdict.get("i") in ("long", "short"):
        arrow = "▲" if verdict["i"] == "long" else "▼"
        cls = verdict["i"]
        txt = "%s %s · w %s · conf %s" % (arrow, verdict["i"], verdict["w"], verdict["c"])
        if verdict.get("prod"): txt += " · " + verdict["prod"]
        if verdict.get("note"): txt += "  (%s)" % verdict["note"]
    else:
        cls = "none"; txt = "— no verdict · %s" % verdict.get("r", "")
    return '<div class="vd %s"><span class="vl">VERDICT</span>%s</div>' % (cls, esc(txt))

def render_state(d, blank=False):
    ftc = FT_CLASS[d["ft"]]
    numlabel = d["ft"].replace("_", " ")
    numtag = ("✎ #%s" % d["n"]) if blank else ("#%s" % d["n"])

    if blank:
        nums = ('<div class="nums blank">'
                '<div class="nrow"><span class="nk">level</span><span class="bl"></span></div>'
                '<div class="nrow"><span class="nk">change</span><span class="bl"></span></div>'
                '<div class="nrow"><span class="nk">compare</span><span class="bl"></span></div></div>')
        quote = '<div class="quote blank"><span class="ql"></span><span class="ql"></span></div>'
        chip = ""
    else:
        def nr(k, v):
            nul = " nul" if v.strip().startswith("—") else ""
            return ('<div class="nrow"><span class="nk">%s</span>'
                    '<span class="nv%s">%s</span></div>' % (k, nul, esc(v)))
        nums = '<div class="nums">%s%s%s</div>' % (nr("level", d["level"]),
                                                   nr("change", d["change"]),
                                                   nr("compare", d["compare"]))
        quote = '<div class="quote">“%s”</div>' % esc(d["quote"])
        chip = ('<div class="chip">%s</div>' % esc(d["tag"])) if d.get("tag") else ""

    return """<div class="card %s">
  <div class="hd">
    <div class="top"><span class="ftlab">%s</span><span class="num">%s</span></div>
    <div class="state">%s</div>
    <div class="gloss">%s</div>
  </div>
  <div class="bd">
    <div class="kv driver"><span class="k">driver</span><span class="v">%s</span></div>
    %s
    %s
    %s
    <div class="scope">%s · %s · %s</div>
  </div>
  %s
</div>""" % (ftc, numlabel, numtag, esc(d["state"]), esc(d["gloss"]),
            esc(d["driver"]), nums, quote, chip,
            esc(d["scope"]), esc(d["src"]), esc(d["date"]), verdict_html(d["verdict"]))

def render_ref(badge, title, points, note):
    pts = "".join('<div class="pt"><b>%s</b>%s</div>' % (esc(k), (" — "+esc(v)) if v else "")
                  for k, v in points)
    return """<div class="card ft-ref">
  <div class="hd">
    <div class="top"><span class="ftlab">reference</span><span class="num">%s</span></div>
    <div class="state">%s</div>
  </div>
  <div class="bd ref">%s<div class="rnote">%s</div></div>
</div>""" % (esc(badge), esc(title), pts, esc(note))

def render_notes():
    lines = "".join('<span class="nl"></span>' for _ in range(5))
    return """<div class="card ft-note">
  <div class="hd"><div class="top"><span class="ftlab">notes</span><span class="num">✎</span></div>
    <div class="state">spare card</div></div>
  <div class="bd notes">%s</div>
</div>""" % lines

def render_driver_node(d):
    """One REAL Driver (class) node card — real CAKE catalog record + its edges."""
    ftc = FT_CLASS[d["ft"]]
    def rows(items):
        return "".join('<div class="frow"><span class="fk">%s</span>'
                       '<span class="fv">%s</span></div>' % (esc(k), esc(v))
                       for k, v in items)
    return """<div class="card %s dnode">
  <div class="hd">
    <div class="top"><span class="ftlab">DRIVER · class node</span><span class="num real">REAL</span></div>
    <div class="state">%s</div>
    <div class="gloss">%s</div>
  </div>
  <div class="bd">
    <div class="cap">properties</div>
    <div class="nums">%s</div>
    <div class="cap">evidence · real quote</div>
    <div class="quote">“%s”<div class="qsrc">%s</div></div>
    <div class="cap">edges</div>
    <div class="nums">%s</div>
    <div class="rnote">%s</div>
  </div>
</div>""" % (ftc, esc(d["name"]), esc(d["gloss"]), rows(d["fields"]),
            esc(d["quote"]), esc(d["qsrc"]), rows(d["edges"]), esc(d["note"]))

# ---- reference cards ----
REF = [
  render_ref("REF A", "How to read a card", [
    ("DRIVER","the reusable cause (class) + its fact_type"),
    ("STATE","the event-level state word — this deck = all 27"),
    ("NUMBERS","level / change / compare  ( — = null )"),
    ("QUOTE","verbatim source text = the truth"),
    ("SCOPE","which version of the fact · source · date"),
    ("VERDICT","the separate EXPLAINED_BY edge — only if it moved the stock"),
  ], "Hidden edges every card has: OF_DRIVER→Driver, FROM_SOURCE→Event.   "
     "id = event ⊕ driver ⊕ scope.   ★ STATE ≠ direction ≠ good/bad."),
  render_ref("REF B", "The 4 fact_types", [
    ("metric","a standing variable you can re-read (incl. qualitative)"),
    ("guidance","the company’s own forward outlook"),
    ("surprise","an actual result vs an expectation"),
    ("action_event","a discrete thing that happened"),
  ], "Decider metric vs action: can you re-read a standing level between two events? "
     "yes → metric · no → action_event.   "
     "Dual framing: dividend (action) vs dividend_per_share (metric)."),
  render_ref("REF C", "The verdict edge", [
    ("stock_impact","long / short — can oppose the net move"),
    ("weightage","0.1–1.0 — a FORCE, not a share; never summed; nullable"),
    ("confidence","0–100 — how sure the attribution is true"),
    ("produced_mode","live (PIT-clean) / backfill"),
    ("llm_producer","earnings-learner (filings) / news-driver (news)"),
  ], "It hangs on the Event (Event→fact) so it is graded vs the real return. "
     "A fact can exist with NO verdict."),
]

# ---- 27 state cards (DATA) ----
def D(ft,state,n,gloss,driver,level,change,compare,quote,scope,src,date,verdict,tag=None):
    return dict(ft=ft,state=state,n=n,gloss=gloss,driver=driver,level=level,change=change,
                compare=compare,quote=quote,scope=scope,src=src,date=date,verdict=verdict,tag=tag)

STATE_DATA = [
 # METRIC (7)
 D("metric","increased","01","direction stated — up","same_store_sales",
   "1.6 percent_yoy","—","—",
   "Comparable sales increased 1.6% versus the prior-year quarter.",
   "company_comp_sales","8-K","2024-10-29", V("long","0.4","60")),
 D("metric","decreased","02","direction stated — down","labor_cost",
   "35.1 percent","−40 basis_points","—",
   "Labor as a percentage of sales decreased 40 bps to 35.1%.",
   "labor_pct_of_sales","8-K","2024-10-29", V("long","0.3","50",note="cost fell = good")),
 D("metric","unchanged","03","explicit flat number","average_unit_volume",
   "12.2 m_usd","—","—",
   "AUV remained flat at approximately $12.2 million.",
   "auv","10-Q","2024-11-05", V("none", r="reported only")),
 D("metric","mixed","04","one driver: up in parts & down in others","comparable_sales",
   "—","—","—",
   "Comparable sales were mixed — off-premise growth offset by softer dine-in traffic.",
   "company_comp_sales","transcript","2024-10-29", V("none", r="no clear net push")),
 D("metric","reported","05","bare value — no compare, no direction","average_check",
   "28.40 usd","—","—",
   "Average check was $28.40 in the quarter.",
   "average_check","transcript","2024-10-29", V("none", r="not the move’s driver")),
 D("metric","persists","06","ongoing condition, no up/down","commodity_cost",
   "—","—","—",
   "Commodity cost pressures remained elevated during the period.",
   "commodity_costs","10-Q","2024-11-05", V("short","0.3","50")),
 D("metric","unknown","07","real fact, no readable state","foreign_exchange",
   "—","—","—",
   "Results were affected by foreign currency; the net effect was not quantified.",
   "fx_impact","10-K","2025-02-26", V("none", r="direction unreadable")),
 # GUIDANCE (6)
 D("guidance","introduced","08","first time issued","revenue_guidance",
   "3600–3700 m_usd","—","— (no prior)",
   "We are initiating FY2025 revenue guidance of $3.6 to $3.7 billion.",
   "FY2025_revenue","8-K","2025-02-26", V("long","0.4","60")),
 D("guidance","raised","09","prior guide moved up","eps_guidance",
   "3.70–3.80 usd","—","3.55–3.65 previous_guidance",
   "We now expect full-year EPS of $3.70–$3.80, up from our prior $3.55–$3.65.",
   "FY_eps","8-K","2024-07-31", V("long","0.6","80")),
 D("guidance","lowered","10","prior guide moved down","comparable_sales_guidance",
   "0–1 percent_yoy","—","2–3 previous_guidance",
   "We are lowering our full-year comparable-sales outlook to flat-to-up-1%, from 2–3%.",
   "FY_comp_sales","8-K","2024-10-29", V("short","0.7","80")),
 D("guidance","reaffirmed","11","kept the same","capital_expenditure_guidance",
   "180 m_usd","—","— (held)",
   "We reaffirmed our capex guidance of approximately $180 million for the year.",
   "FY_capex","transcript","2024-07-31", V("none", r="a reaffirm rarely moves px")),
 D("guidance","withdrawn","12","guidance pulled","revenue_guidance",
   "—","—","—",
   "Given the uncertainty, we are withdrawing our previously issued FY2020 guidance.",
   "FY2020_revenue","8-K","2020-03-23", V("short","0.6","70")),
 D("guidance","unknown","13","rare last resort","full_year_guidance",
   "—","—","—",
   "Management referenced its full-year guidance without specifying any change.",
   "FY_outlook","transcript","2024-07-31", V("none", r="no change stated")),
 # SURPRISE (4)
 D("surprise","beat","14","actual > expectation","eps_surprise",
   "1.30 usd","+0.10 usd","1.20 consensus",
   "Adjusted EPS of $1.30 beat the $1.20 consensus estimate.",
   "Q_eps","8-K","2024-10-29", V("long","0.7","80")),
 D("surprise","in_line","15","actual ≈ expectation","revenue_surprise",
   "918 m_usd","—","918 consensus",
   "Revenue of $918 million matched the $918 million consensus.",
   "Q_revenue","8-K","2024-10-29", V("none", r="matched — no surprise")),
 D("surprise","missed","16","actual < expectation","comparable_sales_surprise",
   "0.5 percent_yoy","−1.3 percent_points","1.8 consensus",
   "Comparable sales rose 0.5%, below the 1.8% analysts expected.",
   "Q_comp_sales","8-K","2024-10-29", V("short","0.8","90")),
 D("surprise","unknown","17","rare last resort","eps_surprise",
   "—","—","—",
   "Whether earnings topped Wall Street forecasts was unclear; estimates varied widely.",
   "Q_eps","news","2024-10-29", V("none", r="not readable")),
 # ACTION_EVENT (10)
 D("action_event","at_risk","18","specific threat — not happened, not own plan","labor_strike",
   "—","—","—",
   "The union warned workers may strike if no contract is reached by month-end.",
   "union_labor_strike","news","2024-09-10", V("short","0.4","50", prod="news-driver")),
 D("action_event","announced","19","own plan, not yet done","share_repurchase",
   "200 m_usd","—","—",
   "The Board authorized a new $200 million share repurchase program.",
   "buyback_authorization_2025","8-K","2025-02-26", V("long","0.5","60")),
 D("action_event","occurred","20","happened / deal closed","acquisition",
   "353 m_usd","—","—",
   "The Company completed its acquisition of North Italia and Fox Restaurant Concepts.",
   "north_italia_fox","8-K","2019-10-02", V("long","0.4","50"), tag="★ real event — CAKE 2019"),
 D("action_event","continued","21","prior action still ongoing","restructuring",
   "—","—","—",
   "The company continued executing its previously announced restructuring plan.",
   "2024_restructuring","10-Q","2024-11-05", V("none", r="ongoing, no new stage")),
 D("action_event","resolved","22","two-sided dispute settled","legal_settlement",
   "45 m_usd","—","—",
   "The company settled the wage-and-hour class action for $45 million.",
   "wage_hour_class_action","8-K","2024-05-14", V("long","0.3","40", note="overhang removed")),
 D("action_event","canceled","23","the company’s OWN withdrawal","initial_public_offering",
   "—","—","—",
   "The company withdrew its planned IPO, citing unfavorable market conditions.",
   "ipo_2022","news","2022-09-20", V("none", r="minor for the issuer")),
 D("action_event","suspended","24","paused — can resume","dividend",
   "—","—","—",
   "The Board suspended the Company’s quarterly cash dividend, effective immediately.",
   "quarterly_dividend","8-K","2020-04-21", V("short","0.8","90"), tag="★ real event — CAKE 2020"),
 D("action_event","rumored","25","3rd-party report, unconfirmed","company_sale",
   "—","—","—",
   "Bloomberg reported the company is exploring a potential sale to private equity.",
   "potential_sale","news","2023-08-15", V("long","0.6","60", prod="news-driver")),
 D("action_event","failed","26","blocked by an OUTSIDE party","merger",
   "—","—","—",
   "After the FTC won a court order blocking the deal, the merger was called off.",
   "proposed_merger","news","2024-01-30", V("short","0.8","80", note="target loses premium")),
 D("action_event","unknown","27","rare last resort","corporate_transaction",
   "—","—","—",
   "An 8-K disclosed a material transaction whose status was not specified.",
   "undisclosed_transaction","8-K","2024-12-01", V("none", r="status not specified")),
]

# ---- 4 REAL Driver (class node) cards — real CAKE catalog records, one per fact_type ----
# Source: runs/2026-06-10_005333_restaurants/catalog.json (573-driver CAKE leaf).
# Real: id/name/companies/evidence/quote/source_id/date/SAME_AS/optional_links.
# Assigned by the classifier step (catalog stores no fact_type): fact_type only.
DRV = [
 dict(ft="metric", name="same_store_sales",
   gloss="a standing variable you can re-read (incl. qualitative)",
   fields=[("id","driver:same_store_sales"), ("companies","CAKE"),
           ("fact_type","metric  ·assigned"), ("first_seen","2023-02-22"),
           ("evidence","56 real refs")],
   quote="Our revenue growth is primarily driven by new restaurant openings and "
         "increases in comparable restaurant sales.",
   qsrc="10-K · 2026-02-23 · 0001104659-26-018643",
   edges=[("OF_DRIVER","← 0 · producer not run yet"),
          ("SAME_AS","→ 0 · self-canonical head"),
          ("MAPS_TO_CONCEPT","→ none (null)")],
   note="REAL Driver record — CAKE catalog, run 2026-06-10. fact_type is assigned "
        "by the classifier (the catalog stores none); evhash16 is excluded on the class."),
 dict(ft="guidance", name="revenue_guidance",
   gloss="the company’s own forward outlook",
   fields=[("id","driver:revenue_guidance"), ("companies","CAKE"),
           ("fact_type","guidance  ·assigned"), ("first_seen","2023-02-22"),
           ("evidence","24 real refs")],
   quote="we anticipate total revenue for fiscal 2024 to be approximately $3.57 billion",
   qsrc="10-Q · 2024-11-04 · 0001410578-24-001742",
   edges=[("OF_DRIVER","← 0 · producer not run yet"),
          ("SAME_AS","→ 0 · self-canonical head"),
          ("MAPS_TO_CONCEPT","→ us-gaap:Revenues")],
   note="REAL record (CAKE, run 2026-06-10). The MAPS_TO_CONCEPT → us-gaap:Revenues "
        "link is a real optional_link captured by the run."),
 dict(ft="surprise", name="eps_surprise",
   gloss="an actual result vs an expectation",
   fields=[("id","driver:eps_surprise"), ("companies","CAKE"),
           ("fact_type","surprise  ·assigned"), ("first_seen","2023-02-22"),
           ("evidence","16 real refs")],
   quote="Net income and diluted net income per share were $54.8 million and $1.14, "
         "respectively, in the second quarter of fiscal 2025.",
   qsrc="8-K · 2025-07-29 · 0001104659-25-071758",
   edges=[("OF_DRIVER","← 0 · producer not run yet"),
          ("SAME_AS","→ 0 · self-canonical head"),
          ("MAPS_TO_CONCEPT","→ us-gaap:EarningsPerShareDiluted")],
   note="REAL record (CAKE, run 2026-06-10). The consensus a surprise is measured "
        "against lives on the (not-yet-built) DriverUpdate, never on the class."),
 dict(ft="action_event", name="dividend",
   gloss="a discrete thing that happened",
   fields=[("id","driver:dividend"), ("companies","CAKE"),
           ("fact_type","action_event  ·assigned"), ("first_seen","2023-02-22"),
           ("evidence","12 real refs")],
   quote="Future decisions to pay or to increase or decrease dividends or to "
         "repurchase shares are at the discretion of the Board",
   qsrc="10-Q · 2024-08-05 · 0001410578-24-001151",
   edges=[("OF_DRIVER","← 0 · producer not run yet"),
          ("SAME_AS","→ 6 in: cash_dividend, dividend_payment, …"),
          ("MAPS_TO_CONCEPT","→ us-gaap:PaymentsOfDividendsCommonStock")],
   note="REAL record (CAKE, run 2026-06-10) with 6 real SAME_AS variants collapsing "
        "into this head — each variant keeps its own evidence."),
]

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
html, body { margin:0; padding:0; }
body { font-family:'DejaVu Sans','Helvetica Neue','Segoe UI',Arial,sans-serif; color:#1b2026; }
.page { width:210mm; height:297mm; padding:9mm 9mm 6mm; display:flex; flex-direction:column;
        overflow:hidden; break-after:page; page-break-after:always; }
.page:last-child { break-after:auto; page-break-after:auto; }
.grid { flex:1; display:grid; grid-template-columns:repeat(2,1fr); grid-template-rows:repeat(3,1fr);
        column-gap:6mm; row-gap:6mm; }
.foot { flex:0 0 7mm; display:flex; align-items:flex-end; justify-content:space-between;
        font-size:6pt; color:#aab0b7; letter-spacing:.3pt; padding:0 .5mm 1mm; }
.card { border:0.35mm solid #c7cbd1; border-radius:2mm; overflow:hidden;
        display:flex; flex-direction:column; background:#fff; }
.hd { color:#fff; padding:2.1mm 2.6mm 1.9mm; flex:0 0 auto; }
.hd .top { display:flex; justify-content:space-between; align-items:center;
           font-size:6pt; font-weight:700; letter-spacing:.7pt; text-transform:uppercase; opacity:.95; }
.hd .num { font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; opacity:.9; }
.hd .state { font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; font-size:13pt; font-weight:700;
             line-height:1.04; margin-top:1mm; }
.hd .gloss { font-size:6.3pt; font-style:italic; opacity:.96; margin-top:.7mm; line-height:1.12; }
.bd { padding:2.2mm 2.6mm 2.2mm; flex:1; display:flex; flex-direction:column; gap:1.5mm; }
.kv { display:flex; align-items:baseline; gap:1.8mm; }
.kv .k { flex:0 0 11mm; color:#828a93; font-size:5.6pt; font-weight:700; letter-spacing:.4pt; text-transform:uppercase; }
.kv .v { font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; font-size:8pt; font-weight:700; color:#14181d; }
.nums { font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; font-size:6.7pt; line-height:1.4;
        background:#f6f7f9; border:0.3mm solid #e7e9ec; border-radius:1mm; padding:1.3mm 1.8mm; }
.nrow { display:flex; }
.nrow .nk { flex:0 0 15mm; color:#828a93; }
.nrow .nv { color:#14181d; }
.nrow .nv.nul { color:#b6bcc3; }
.quote { font-style:italic; font-size:7.1pt; line-height:1.22; color:#2a3037;
         border-left:0.9mm solid; padding:1.5mm 1.9mm; border-radius:.8mm; }
.chip { align-self:flex-start; font-size:5.7pt; font-weight:700; padding:.5mm 1.6mm; border-radius:3mm;
        background:#fff6da; color:#7a5a00; border:0.3mm solid #ecd884; }
.scope { margin-top:auto; font-size:6pt; color:#828a93; font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; }
.vd { flex:0 0 auto; padding:1.7mm 2.6mm; font-size:6.9pt; font-weight:700; color:#fff;
      font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; letter-spacing:.2pt; }
.vd .vl { opacity:.82; margin-right:1.6mm; font-size:5.8pt; }
.vd.long { background:#1c7a3e; } .vd.short { background:#b22d22; }
.vd.none { background:#eef0f2; color:#6b7280; font-weight:600; } .vd.none .vl { color:#9aa0a7; }
/* reference cards */
.bd.ref { gap:1.4mm; font-size:7pt; }
.bd.ref .pt { line-height:1.24; }
.bd.ref .pt b { font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; font-size:7.2pt; color:#14181d; }
.rnote { margin-top:auto; font-size:6.3pt; line-height:1.26; color:#48515b;
         background:#f3f5f7; border:0.3mm solid #e3e6ea; border-radius:1mm; padding:1.5mm 1.8mm; }
/* handwriting blanks */
.nums.blank .nrow { align-items:flex-end; padding:.55mm 0; }
.bl { flex:1; border-bottom:0.25mm dotted #aab0b7; height:3mm; margin-left:1.5mm; }
.quote.blank { min-height:13mm; padding-top:3.2mm; }
.quote.blank .ql { display:block; border-bottom:0.25mm dotted #aab0b7; margin-bottom:4.2mm; height:0; }
.bd.notes { gap:0; padding-top:3.5mm; }
.bd.notes .nl { display:block; border-bottom:0.25mm dotted #aab0b7; margin-bottom:5.4mm; height:0; }
/* Driver-node cards */
.dnode .gloss { font-size:6.3pt; }
.cap { font-size:5.3pt; font-weight:700; letter-spacing:.6pt; text-transform:uppercase;
       color:#9aa0a7; margin:.6mm 0 .4mm; }
.frow { display:flex; gap:1.5mm; line-height:1.46; }
.frow .fk { flex:0 0 23mm; color:#828a93; }
.frow .fv { flex:1; color:#14181d; }
.num.real { background:#fff; color:#1c7a3e; padding:.4mm 1.7mm; border-radius:2mm;
            font-size:5.6pt; font-weight:800; letter-spacing:.7pt; }
.dnode .quote { font-size:6.8pt; line-height:1.2; }
.qsrc { margin-top:1.1mm; font-style:normal; font-size:5.5pt; color:#7a828c;
        font-family:'DejaVu Sans Mono','SF Mono',Menlo,Monaco,'Courier New',monospace; }
/* fact_type palettes */
.ft-metric   .hd{background:#1f5fa8} .ft-metric   .quote{background:#eef4fb;border-color:#1f5fa8}
.ft-guidance .hd{background:#6a3d9a} .ft-guidance .quote{background:#f2ecf9;border-color:#6a3d9a}
.ft-surprise .hd{background:#b5670f} .ft-surprise .quote{background:#fbf0e1;border-color:#b5670f}
.ft-action   .hd{background:#1b7f6b} .ft-action   .quote{background:#e7f4f1;border-color:#1b7f6b}
.ft-metric   .quote.blank{background:#f4f8fc} .ft-guidance .quote.blank{background:#f8f4fc}
.ft-surprise .quote.blank{background:#fdf6ec} .ft-action .quote.blank{background:#eef7f4}
.ft-ref      .hd{background:#39424d}
.ft-note     .hd{background:#7a828c}
"""

def build_pages(cards, foot_label, total):
    out, NP = [], (len(cards)+5)//6
    pages = [cards[i:i+6] for i in range(0, len(cards), 6)]
    for pi, pg in enumerate(pages, 1):
        foot = ('<div class="foot"><span>EventMarketDB · Driver-state index cards</span>'
                '<span>%s page %d / %d</span></div>' % (foot_label, pi, NP))
        out.append('<div class="page"><div class="grid">%s</div>%s</div>'
                   % ("".join(pg), foot))
    return out

# Section 1: filled deck (3 ref + 27 states + 4 Driver-node + 2 spare) = 6 pages
filled = (REF + [render_state(d, blank=False) for d in STATE_DATA]
          + [render_driver_node(x) for x in DRV] + [render_notes(), render_notes()])
# Section 2: handwriting deck (27 blanked states + 3 spare-note cards) = 5 pages
hand = [render_state(d, blank=True) for d in STATE_DATA] + [render_notes() for _ in range(3)]

body = build_pages(filled, "", "") + build_pages(hand, "✎ handwriting ·", "")
html = ("<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head>"
        "<body>%s</body></html>" % (CSS, "".join(body)))

with open(HTML, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote HTML:", HTML, "(%d cards total)" % (len(filled)+len(hand)))

chrome = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
if not chrome:
    print("No Chrome; open the HTML and Print -> Save as PDF (A4)."); sys.exit(0)

args = ["--disable-gpu","--no-sandbox","--no-first-run","--disable-extensions",
        "--user-data-dir=/tmp/chrome_cards_profile","--no-pdf-header-footer",
        "--print-to-pdf="+PDF, "file://"+HTML]
for hl in ("--headless=new","--headless"):
    try:
        if os.path.exists(PDF): os.remove(PDF)
    except OSError: pass
    r = subprocess.run([chrome, hl]+args, capture_output=True, text=True, timeout=120)
    if os.path.exists(PDF) and os.path.getsize(PDF) > 8000:
        print("rendered PDF via", hl, "->", PDF, "(%d bytes)" % os.path.getsize(PDF)); break
    print("attempt", hl, "rc=", r.returncode, (r.stderr or "")[-300:])
else:
    print("render failed; open HTML and Print to PDF."); sys.exit(1)
