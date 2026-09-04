"""Build the ONE read-only reconciliation proposal (Codex SEQ 1340).

Reads only immutable evidence: the 36 accepted raws, the 72-row pending ledger,
the frozen package/inputs/menus. Writes exactly one artifact plus a rendered
text view into the run directory. It edits nothing it reads.

The RULINGS below are my judgments carried as DATA. The code applies declared
effects mechanically and never decides from text: no keyword list, no threshold,
no case branch. Candidate ENUMERATION (menu-value ambiguity) is exact equality
over the menus themselves, which proposes candidates; the ruling data decides.
"""
import collections, hashlib, io, json, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
     "/scratchpad")
RUN = S + "/invrev_run4"
E = S + "/bench_1306/.claude/plans/Drivers/experiments"
MAILBOX = "/home/faisal/.core827-orchestrator"
sys.path.insert(0, E + "/harness")
import raw_transport as RT                                    # noqa: E402
import validate_benchmark_inventory as V                      # noqa: E402

FD = ".claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md"
TR = ".claude/plans/Drivers/experiments/FABLE_LOCK_BLIND_REVIEW_TRACKER_2026-07-10.md"
ST1 = ".claude/plans/Drivers/FinalDesign/LeftOverSteps/step1.md"

# ---------------------------------------------------------------- immutable in
sha = lambda b: hashlib.sha256(b).hexdigest()
shaf = lambda p: sha(io.open(p, "rb").read())
shat = lambda t: sha(t.encode("utf-8"))

MAN = json.load(io.open(E + "/inventory_review/package.manifest.json", encoding="utf-8"))
ORDER = [e["source_id"] for e in MAN["events"]]
LEDGER = json.load(io.open(RUN + "/pending_ledger.json", encoding="utf-8"))
ATTS = json.load(io.open(RUN + "/attempts.json", encoding="utf-8"))
ACCEPTED = {}
for a in ATTS:
    if (a["source_id"] not in ACCEPTED
            or a["attempt"] > ACCEPTED[a["source_id"]]["attempt"]):
        ACCEPTED[a["source_id"]] = a


def reply(sid):
    return RT.parse_reply(io.open(os.path.join(RUN, "replies",
                                               ACCEPTED[sid]["raw_name"]),
                                  encoding="utf-8").read())


def source_parts(sid):
    d = json.load(io.open(E + "/inventory_review/inputs/%s.json" % sid, encoding="utf-8"))
    return {p["part"]: p["content"] for p in d["event"]["text_parts"]}, d["menu"]


BASE, MENUS, CONSIDERED = collections.OrderedDict(), {}, {}
for sid in ORDER:
    o = reply(sid)
    rows = [dict(v["row"], _origin="verdict", _decision=v["decision"])
            for v in (o.get("verdicts") or []) if v.get("row")]
    rows += [dict(ad["row"], _origin="addition", _decision="addition")
             for ad in (o.get("additions") or [])]
    BASE[sid] = rows
    CONSIDERED[sid] = o.get("exclusions_considered") or []
    _, MENUS[sid] = source_parts(sid)

# ------------------------------------------------------- mechanical candidates
# Exact normalized menu equality only: a value carried by two or more kinds
# inside one event's own menu. This PROPOSES; the rulings decide.
AMB = collections.OrderedDict()
for sid in ORDER:
    per = collections.defaultdict(set)
    for m in MENUS[sid]:
        k, _, v = m.partition(":")
        per[v].add(k)
    for v in sorted(per):
        if len(per[v]) >= 2:
            AMB.setdefault(v, collections.OrderedDict())[sid] = sorted(per[v])

# ------------------------------------------------------------------- the data
# Aggregate changes. Each carries ONE owner: the Codex SEQ 1340 class ruling
# plus the ledger ordinals that raised it, and the live authority anchor.
POINT_ADD = [
    ("0000006201-26-000031", "Net loss excluding net special items"),
    ("0000006201-26-000031", "Total unit revenue was 7.6%"),
    ("0000006201-26-000031", "Passenger revenue per ASM (cents)"),
    ("0000006201-26-000031", "an estimated $320 million revenue impact"),
    ("0000006201-26-000031", "Total operating revenues 13,912"),
    ("0000006201-26-000031", "Atlantic passenger unit revenue up 16.7"),
    ("0000006201-26-000031", "Net loss $ (382)"),
    ("0000027904-26-000020", "Non‑fuel unit costs grew 6 percent"),
    ("0000027904-26-000022", "Domestic passenger revenue increased 8%"),
    ("0000898173-26-000006", "Comparable store sales increased 4.7%"),
    ("0000898173-26-000006", "33 consecutive years"),
    ("0001104659-25-102611", "The fourth quarter of fiscal year 2025 represented 33.0%"),
    ("0001104659-25-102611", "in 6,098 of our domestic stores"),
    ("0001104659-25-105631", "The Revolver Facility contains a commitment increase feature"),
    ("0001104659-26-027061", "Comparable sales increased 5.8%"),
    ("0001104659-26-027061", "Interest expense (income), net"),
    ("0001104659-26-027061", "Diluted earnings per share increased 1.2%"),
    ("0001104659-26-027061", "Net sales increased 11.8%"),
    ("0001104659-26-027061", "As a percentage of net sales, SG&A expenses increased to 26.6%"),
    ("0001104659-26-027061", "remained available under the $3.0 billion share repurchase"),
    ("0001171843-26-001288", "additional week of sales of approximately $359.1 million"),
    ("MCD_2026-02-11T16.30", "Adjusted earnings per share on a constant currency basis"),
    ("MCD_2026-02-11T16.30", "accelerate sequentially from the 5.2%"),
    ("MCD_2026-02-11T16.30", "sequential decrease from the 4.5%"),
    ("MCD_2026-02-11T16.30", "decelerate sequentially from the 6.8%"),
]
SEQ_KEEP = [
    ("DAL_2026-04-08T10.00", "meaningful acceleration from mid-single-digit unit revenue"),
    ("MCD_2026-02-11T16.30", "accelerate sequentially from the 5.2%"),
    ("MCD_2026-02-11T16.30", "sequential decrease from the 4.5%"),
    ("MCD_2026-02-11T16.30", "decelerate sequentially from the 6.8%"),
]
AGGREGATE = [
    {"id": "AGG-A-point",
     "owner": "Codex SEQ 1340 ruling A + ledger 00,12,37,39,45,50,60",
     "authority": [FD, "### 7.1 The 24 counted fields — exact split"],
     "what": "point_range_floor_ceiling is added to every row whose own item "
             "states a numeric point, range, floor or ceiling. Rows whose only "
             "digits are dates, period labels, item numbers or standard "
             "identifiers are NOT numeric values and are untouched. A surprise "
             "or direction row that states no numeric value of its own is not "
             "a numeric point and is untouched.",
     "op": "add_tag", "tag": "point_range_floor_ceiling", "targets": POINT_ADD},
    {"id": "AGG-B-sequential",
     "owner": "Codex SEQ 1340 ruling B + ledger 03,36,46,47,55,57,59",
     "authority": [FD, "- **OD-11 (growth basis):**"],
     "what": "sequential_comparison is kept ONLY where the item itself compares "
             "a period against the immediately preceding period. Ordinary "
             "YoY/default-YoY, percent-of-sales levels, balance-sheet YoY "
             "changes and points/bps changes lose the tag.",
     "op": "keep_tag_only", "tag": "sequential_comparison", "targets": SEQ_KEEP},
]

# Per-ledger rulings. status: authority_resolved | source_resolved |
# remains_genuinely_unsettled. effect: declared, mechanical, never inferred.
def none():
    return {"op": "none"}


def retag(sid, find, add=(), remove=()):
    return {"op": "retag", "sid": sid, "find": find,
            "add": list(add), "remove": list(remove)}


def rekind(sid, find, to, add=(), remove=()):
    return {"op": "rekind", "sid": sid, "find": find, "to": to,
            "add": list(add), "remove": list(remove)}


def promote(sid, part_ref, quote, label, kind, tags, why):
    return {"op": "promote", "sid": sid, "row": {
        "source_id": sid, "part_ref": part_ref, "occurrence_in_part": None,
        "quote": quote, "raw_label_or_claim": label,
        "proposed_record_kind": kind, "proposed_hard_classes": list(tags)},
        "why": why}


A = ("Codex SEQ 1340 ruling A", [FD, "### 7.1 The 24 counted fields — exact split"])
B = ("Codex SEQ 1340 ruling B", [FD, "- **OD-11 (growth basis):**"])
C = ("Codex SEQ 1340 ruling C", [ST1, "**The benchmark is built from sources, never from failed output.**"])
D = ("Codex SEQ 1340 ruling D", [TR, "## T1-05 - Slice-kind decision ladder"])
Ee = ("Codex SEQ 1340 ruling E", [FD, "- Within one event: fuse before collision."])
F = ("Codex SEQ 1340 ruling F", [FD, "### 5.3 Measurement — FS-25, OD-9 `[FINAL]`"])
G = ("Codex SEQ 1340 ruling G", [FD, "- Same company/series/day: source rank"])
H = ("Codex SEQ 1340 ruling H", [ST1, "**The benchmark is built from sources, never from failed output.**"])
F17 = ("Codex SEQ 1340 ruling F", [FD, "12. **OD-17 (portions)**"])
F05 = ("Codex SEQ 1340 ruling F", [FD, "### 5.2 Slices — FS-05..24"])
F12 = ("Codex SEQ 1340 ruling F", [FD, "- **OD-12 (signed axis):**"])
F21 = ("Codex SEQ 1340 ruling F", [FD, "Routing consequences:"])
F13 = ("Codex SEQ 1340 ruling F", [FD, "14. **NAME-13**"])

RULINGS = {
 0: (A, "authority_resolved", "A plain numeric point exercises the shape rule; the tag is not reserved for range/floor/ceiling. Applied as aggregate AGG-A-point.", none()),
 1: (D, "authority_resolved", "Controls are selected in this aggregate reconciliation, never opportunistically per event. The per-event abstention was correct.", none()),
 2: (C, "authority_resolved", "A total and its per-X form stay distinct facts, but representative selection never requires every lawful sibling. No row is owed here.", none()),
 3: (B, "authority_resolved", "This event is entirely YoY; sequential_comparison does not apply. Removed by AGG-B-sequential.", none()),
 4: (C, "authority_resolved", "Differently named co-stated Drivers are distinct items when selected and may share one smallest complete quote. Keeping pre-tax loss and adding net loss is correct.", none()),
 5: (C, "authority_resolved", "One coherent same-label item may carry several periods and values; split only on a real label/series/scope/measurement/state distinction. No atomisation.", none()),
 6: (G, "authority_resolved", "A business loan amendment is not automatically an OD-14 data correction, but the hidden tag lawfully marks it as the negative boundary trap that tests that exact distinction.", retag("0000027904-26-000013", "entered into an amendment to the SkyMiles", add=["corrections_and_amendments"])),
 7: (F, "authority_resolved", "Non-fuel and all-in modifiers stay in measurement when not otherwise losslessly owned; the measurement_wording tag stands.", none()),
 8: (F05, "authority_resolved", "Cabin class is a product slice; slices and portion may co-apply.", retag("0000027904-26-000020", "main cabin", add=["slices_and_unknown_axes"])),
 9: (C, "authority_resolved", "This is a located source-item inventory, not the completed-fact key; the prior-year comparative stays a located item and its field binding belongs to the later stage.", none()),
 10: (C, "authority_resolved", "One coherent same-label item may contain several periods; no split without a real distinction.", none()),
 11: (C, "authority_resolved", "Same ruling: the four period columns share one label and one place, so this is one located item.", none()),
 12: (A, "authority_resolved", "Point applies to every numeric self-describing point. Applied as aggregate AGG-A-point.", none()),
 13: (F, "authority_resolved", "Table line items can be real facts; the reconciliation line is a source-stated item in its own right.", none()),
 14: (H, "authority_resolved", "Event 9's metadata-only row is the intentional negative control. Nothing is missing and nothing is invented.", none()),
 15: (Ee, "authority_resolved", "A flattened table that cannot bind one item exactly is abstained from or excluded; never infer a cell. Drawing no row was correct.", none()),
 16: (F21, "authority_resolved", "Grounded numberless surprise is lawful, and a company's own 'our expectations' means its own prior guidance absent explicit Street evidence.", none()),
 17: (F, "authority_resolved", "A current contractual/compliance state may be a real state fact, so the item is lawful; representative selection does not require promoting it.", none()),
 18: (Ee, "authority_resolved", "Supplied text_parts order IS source order for the first-complete-quote rule.", none()),
 19: (G, "authority_resolved", "The covenant amendment is not a data correction, but the hidden tag lawfully marks the boundary trap. Tag stands.", none()),
 20: (C, "authority_resolved", "Row count is settled: one located item. Which period the later fact resolves to is the completed-fact key's question, not this inventory's.", none()),
 21: (C, "authority_resolved", "Average check and guest counts are differently named co-stated Drivers, so they are distinct items when selected; representative selection does not require the sibling here.", none()),
 22: (D, "authority_resolved", "Controls needed only for cross-event coverage are selected in this aggregate reconciliation, not per event.", none()),
 23: (D, "authority_resolved", "A hidden tag marks the rule the item tests, judged from the item in its own source context; it does not require the triggering words inside the quote.", none()),
 24: (F17, "authority_resolved", "Geography and portion tags may co-apply.", retag("0001041061-25-000109", "The Pizza Hut Division has 19,872 units", add=["portion_versus_whole"])),
 25: (C, "authority_resolved", "One coherent same-label item may contain several periods; no split without a real distinction.", none()),
 26: (F05, "authority_resolved", "company-owned is entity_ownership, i.e. a slice, not a population portion.", None),
 27: (G, "authority_resolved", "A rounding/presentation-basis change is a presentation note, not an OD-14 data correction; it is promoted as the negative boundary trap that tests that exact distinction.", promote("0001041061-26-000003", "exhibit_99_1", "In the first quarter of 2025, the Company prospectively changed its basis of presentation to round financial figures in the Consolidated Summary of Results, Consolidated Balance Sheets, Consolidated Statements of Cash Flows and as presented in the tabular presentations in these Notes to the nearest whole number in millions in all instances.", "the Company prospectively changed its basis of presentation to round financial figures", "negative_control", ["corrections_and_amendments"], "presentation-basis change: a negative boundary trap for OD-14, never a corrected metric")),
 28: (C, "authority_resolved", "Representative selection never requires every lawful cell of a summary table.", none()),
 29: (Ee, "authority_resolved", "A bare table row without its headers inside the span cannot bind the item exactly, so the self-contained prose occurrence stays the locator.", none()),
 30: (F12, "authority_resolved", "'headwind' is not OD-12 by itself.", retag("0001041061-26-000084", "one-point headwind", remove=["losses_and_sign"])),
 31: (F, "authority_resolved", "A definitional presentation note is not a company Driver fact; the correct reader behaviour is omission, which is exactly what a negative_control records.", none()),
 32: (F17, "authority_resolved", "Portion may co-apply; digital sales as a share of total revenue is a population portion.", none()),
 33: (G, "authority_resolved", "The maturity-date amendment is not a data correction, but the hidden tag lawfully marks the boundary trap. Tag stands.", none()),
 34: (F, "authority_resolved", "Calendar mechanics do not become company Driver facts; the correct behaviour is omission, recorded as a negative control.", rekind("0001104659-25-102611", "Each of the first three quarters", "negative_control")),
 35: (F05, "authority_resolved", "Geography tags may co-apply; a geography-scoped operational count is a slice item.", retag("0001104659-25-102611", "in 6,098 of our domestic stores", add=["slices_and_unknown_axes"])),
 36: (B, "authority_resolved", "Ordinary YoY does not become sequential. Removed by AGG-B-sequential.", none()),
 37: (A, "authority_resolved", "Every numeric point exercises the shape rule. Applied as aggregate AGG-A-point.", none()),
 38: (F, "authority_resolved", "A current contractual right may be a real state fact; the condition-gated capacity clause states a real, dollar-quantified current right.", rekind("0001104659-25-105631", "commitment increase feature", "real_item")),
 39: (A, "authority_resolved", "Same as ledger 37.", none()),
 40: (F, "authority_resolved", "A reportable-segment-count disclosure is reporting metadata, not a company Driver fact; the correct behaviour is omission, recorded as a negative control.", rekind("0001104659-25-118458", "one reportable segment", "negative_control", remove=["slices_and_unknown_axes"])),
 41: (H, "authority_resolved", "Moving a proposal to the first complete occurrence is 'replace'; proposal-id allocation cannot create or erase a source item.", none()),
 42: (D, "authority_resolved", "Hidden tags mark the rule an item or control tests. An abstention that never reaches the direction or routing decision does not test those rules, so the empty list is right.", none()),
 43: (Ee, "authority_resolved", "Garbled or flattened header text that cannot bind one item exactly is abstained from or excluded; never infer a cell.", none()),
 44: (F, "authority_resolved", "Table line items can be real facts.", none()),
 45: (A, "authority_resolved", "Every numeric point exercises the shape rule. Applied as aggregate AGG-A-point.", none()),
 46: (B, "authority_resolved", "Percent-of-sales levels do not become sequential. Removed by AGG-B-sequential.", none()),
 47: (B, "authority_resolved", "An explicit prior-year comparison is ordinary YoY, not sequential. Removed by AGG-B-sequential.", none()),
 48: (Ee, "authority_resolved", "The source itself declines to state a direction, so the item abstains; never infer.", none()),
 49: (F, "authority_resolved", "This is not calendar mechanics: it quantifies a stated dollar sales effect, so it is a real operational fact.", none()),
 50: (A, "authority_resolved", "Every numeric point exercises the shape rule. Applied as aggregate AGG-A-point.", none()),
 51: (F, "authority_resolved", "Conflicting evidence abstains: the conflicted unit-revenue characterisation is not certified. The row stands for the geography slice and its stated share.", none()),
 52: (F, "authority_resolved", "A supplied full-context acronym may use its earlier source definition, so the measurement tag stands.", none()),
 53: (Ee, "authority_resolved", "Extend the quote contiguously until the label is inside it; the long span is correct.", none()),
 54: (G, "authority_resolved", "An explicit same-source clarification judged from its complete evidence is a genuine correction exemplar; promoted with the tag.", promote("BBY_2026-03-03T08.00", "qa", "Just to be clear that the 20% reference was 20% growth in labor in the second part of last year.", "the 20% reference was 20% growth in labor", "real_item", ["corrections_and_amendments"], "explicit same-source clarification of the prepared-remarks antecedent 'after growing 20% in the second half of last year'")),
 55: (B, "authority_resolved", "All of this event's percentages resolve to ordinary YoY. Removed by AGG-B-sequential.", none()),
 56: (C, "authority_resolved", "Split only on a real label/series/scope/measurement/state distinction; these two statements carry different scope labels, so they are distinct items and neither merges into the other.", none()),
 57: (B, "authority_resolved", "A balance-sheet YoY change does not become sequential. Removed by AGG-B-sequential.", none()),
 58: (C, "authority_resolved", "Representative selection never requires every lawful sibling; the co-located facts stay considered, not owed.", none()),
 59: (B, "authority_resolved", "Ordinary and default YoY do not become sequential. Removed by AGG-B-sequential.", none()),
 60: (A, "authority_resolved", "Every numeric point exercises the shape rule. Applied as aggregate AGG-A-point.", none()),
 61: (C, "authority_resolved", "Differently named co-stated Drivers are distinct items when selected, and representative selection never requires every sibling; the trim-and-exclude reading is correct and no rows are owed.", none()),
 62: (F21, "authority_resolved", "A company's own 'our expectations' means its own prior guidance absent explicit Street evidence, so actual_vs_guidance is right.", none()),
 63: (F12, "authority_resolved", "An ordinary 'lower' bps change is not OD-12 by itself; leaving the tag off was correct.", none()),
 64: (C, "authority_resolved", "This is a located source-item inventory, not the completed-fact key; level-versus-change is decided at the later stage, and the row still carries a numeric point.", none()),
 65: (F, "authority_resolved", "Specific promotional volume may be a real operational fact, so the items are lawful; promoting them is an aggregate decision and none is needed.", none()),
 66: (D, "authority_resolved", "Coverage additions belong to this aggregate reconciliation, not to a single event; the rows added per-event are re-judged here on their own merits and none is removed for that reason alone.", none()),
 67: (D, "authority_resolved", "A lawful abstention control is never invented; absence in one event is correct and coverage is settled here.", none()),
 68: (F, "authority_resolved", "Pure industry macro commentary does not become a company Driver fact.", none()),
 69: (F, "authority_resolved", "Uncertain transcription abstains; the abstention control stands.", none()),
 70: (Ee, "authority_resolved", "Supplied text_parts order IS source order, so the teaser occurrence is the first complete one.", none()),
 71: (F13, "authority_resolved", "A leadership appointment is a discrete action_event source item, so it is a real item, not an abstention.", rekind("bzNews_51962983", "Best Buy Appoints Jason Bonfig", "real_item")),
}
# ledger 26 needs two targets in one event; declared explicitly.
RULINGS[26] = (F05, "authority_resolved",
               "company-owned is entity_ownership, i.e. a slice rather than a population portion.",
               {"op": "multi", "steps": [
                   retag("0001041061-26-000003", "For the quarter, company-owned restaurant margins",
                         add=["slices_and_unknown_axes"], remove=["portion_versus_whole"]),
                   retag("0001041061-26-000003", "The impact of lapping the 53rd week",
                         add=["slices_and_unknown_axes"], remove=["portion_versus_whole"])]})

# Aggregate coverage selections that no single ledger row owns. Each names its
# own authority owner and its own source evidence.
COVERAGE = [
    {"id": "COV-amb-1", "tag": "ambiguous_menus",
     "owner": "Codex SEQ 1340 ruling D + section 2 ambiguous-menu enumeration",
     "authority": [TR, "## T1-05 - Slice-kind decision ladder"],
     "effect": retag("MCD_2026-02-11T16.30", "accelerate sequentially from the 5.2%",
                     add=["ambiguous_menus"]),
     "evidence": "IOM names International Operated Markets, whose exact normalized "
                 "menu value is carried by both entity_ownership and segment in this event."},
    {"id": "COV-amb-2", "tag": "ambiguous_menus",
     "owner": "Codex SEQ 1340 ruling D + section 2 ambiguous-menu enumeration",
     "authority": [TR, "## T1-05 - Slice-kind decision ladder"],
     "effect": retag("MCD_2026-02-11T16.30", "sequential decrease from the 4.5%",
                     add=["ambiguous_menus"]),
     "evidence": "IDL names International Developmental Licensed Markets, carried by both "
                 "entity_ownership and segment in this event."},
    {"id": "COV-amb-3", "tag": "ambiguous_menus",
     "owner": "Codex SEQ 1340 ruling D + section 2 ambiguous-menu enumeration",
     "authority": [TR, "## T1-05 - Slice-kind decision ladder"],
     "effect": retag("0001041061-26-000084",
                     ("90% of which are located outside the U.S.",
                      "90% of which are located outside the U.S."),
                     add=["ambiguous_menus"]),
     "evidence": "us is carried by both geography and segment in this event's menu; the "
                 "source uses it as geography."},
    {"id": "COV-amb-4", "tag": "ambiguous_menus",
     "owner": "Codex SEQ 1340 ruling D + F reporting-metadata direction",
     "authority": [TR, "## T1-05 - Slice-kind decision ladder"],
     "effect": promote("0000764478-25-000057", "mdna",
                       "We have two reportable segments: Domestic and International.",
                       "two reportable segments: Domestic and International",
                       "negative_control", ["ambiguous_menus"],
                       "reporting metadata, so omission is correct; it is the exact negative "
                       "boundary trap in which domestic and international are segment names "
                       "while the same menu also carries them as geography"),
     "evidence": "domestic and international are each carried by geography and segment in "
                 "this event's own menu."},
    {"id": "COV-amb-5", "tag": "ambiguous_menus",
     "owner": "Codex SEQ 1340 ruling D + section 2 ambiguous-menu enumeration",
     "authority": [TR, "## T1-05 - Slice-kind decision ladder"],
     "effect": promote("BBY_2026-03-03T08.00", "prepared_remarks",
                       "In our domestic segment, revenue decreased 1.1% to $12.6 billion, "
                       "driven by a comparable sales decline of 0.8%.",
                       "our domestic segment", "real_item",
                       ["ambiguous_menus", "point_range_floor_ceiling",
                        "slices_and_unknown_axes"],
                       "the source itself resolves domestic to the segment reading"),
     "evidence": "domestic is carried by geography and segment in this event's menu."},
    {"id": "COV-amb-6", "tag": "ambiguous_menus",
     "owner": "Codex SEQ 1340 ruling D + section 2 ambiguous-menu enumeration",
     "authority": [TR, "## T1-05 - Slice-kind decision ladder"],
     "effect": promote("0000063908-26-000032", "exhibit_99_1",
                       "International Operated Markets increased 3.2%",
                       "International Operated Markets", "real_item",
                       ["ambiguous_menus", "point_range_floor_ceiling",
                        "slices_and_unknown_axes"],
                       "the source uses the value as a reporting segment"),
     "evidence": "internationaloperatedmarkets is carried by entity_ownership and segment "
                 "in this event's own menu."},
    {"id": "COV-seq-1", "tag": "sequential_comparison",
     "owner": "Codex SEQ 1342 + Codex SEQ 1340 ruling D aggregate coverage repair",
     "authority": [FD, "- **OD-11 (growth basis):**"],
     "effect": promote("0001171843-26-001288", "exhibit_99_1",
                       "Net inventory, defined as merchandise inventories less "
                       "accounts payable, on a per store basis, was negative $105 "
                       "thousand versus negative $161 thousand last year and "
                       "negative $145 thousand last quarter.",
                       "Net inventory, defined as merchandise inventories less "
                       "accounts payable, on a per store basis",
                       "real_item",
                       ["point_range_floor_ceiling", "losses_and_sign",
                        "sequential_comparison"],
                       "one located source item stating current, prior-year and "
                       "immediately prior-quarter values; the later one-item "
                       "reader may produce the rule-required basis split"),
     "evidence": "frozen input 0001171843-26-001288.json sha256 6c0c3af79d7969282"
                 "929d2c512479f7c2cf09d449ad6bc18555b8867ccd2137c; the sentence "
                 "occurs exactly once in exhibit_99_1 and the label lies inside "
                 "it. The failed attempt-1 reply is the lead only and supplies "
                 "no evidence and no credit."},
]

_BASE_COVERAGE = [c for c in COVERAGE if c["id"] != "COV-seq-1"]

UNSETTLED_NOTES = []          # populated below if any ruling is unsettled

# ------------------------------------------------------------------ mechanics
def find_row(rows, find):
    """`find` is a quote substring, or (quote substring, label substring) when
    two rows lawfully share one quote. It must resolve to exactly one row."""
    q, lab = find if isinstance(find, tuple) else (find, None)
    hit = [r for r in rows if q in r["quote"]
           and (lab is None or lab in r["raw_label_or_claim"])]
    if len(hit) != 1:
        raise SystemExit("target %r matches %d rows, not 1" % (find, len(hit)))
    return hit[0]


def apply_effect(inv, eff, log, owner):
    if eff is None or eff["op"] == "none":
        return
    if eff["op"] == "multi":
        for st in eff["steps"]:
            apply_effect(inv, st, log, owner)
        return
    if eff["op"] == "promote":
        sid = eff["sid"]
        row = dict(eff["row"], _origin="aggregate_promotion", _decision="promotion")
        if any(r["quote"] == row["quote"] and r["raw_label_or_claim"] ==
               row["raw_label_or_claim"] for r in inv[sid]):
            raise SystemExit("promotion duplicates an existing row: %r" % row["quote"][:60])
        inv[sid].append(row)
        log.append({"owner": owner, "op": "promote", "source_id": sid,
                    "quote": row["quote"], "label": row["raw_label_or_claim"],
                    "kind": row["proposed_record_kind"],
                    "tags": row["proposed_hard_classes"]})
        return
    r = find_row(inv[eff["sid"]], eff["find"])
    before = {"kind": r["proposed_record_kind"],
              "tags": list(r["proposed_hard_classes"])}
    if eff["op"] == "rekind":
        r["proposed_record_kind"] = eff["to"]
    tags = [t for t in r["proposed_hard_classes"] if t not in eff.get("remove", ())]
    for t in eff.get("add", ()):
        if t not in tags:
            tags.append(t)
    r["proposed_hard_classes"] = tags
    log.append({"owner": owner, "op": eff["op"], "source_id": eff["sid"],
                "quote": r["quote"], "label": r["raw_label_or_claim"],
                "before": before,
                "after": {"kind": r["proposed_record_kind"], "tags": list(tags)}})


def counts(inv):
    kind, tag, rows = collections.Counter(), collections.defaultdict(set), 0
    for sid, rs in inv.items():
        for r in rs:
            rows += 1
            kind[r["proposed_record_kind"]] += 1
            for t in r["proposed_hard_classes"]:
                tag[t].add((sid, r["quote"], r["raw_label_or_claim"]))
    return {"rows": rows, "kinds": dict(kind),
            "tags": {t: len(tag[t]) for t in V.HARD_CLASSES},
            "events": len(inv)}


def build():
    inv = collections.OrderedDict((sid, [dict(r) for r in BASE[sid]]) for sid in ORDER)
    changes = []
    for agg in AGGREGATE:
        if agg["op"] == "add_tag":
            for sid, find in agg["targets"]:
                apply_effect(inv, retag(sid, find, add=[agg["tag"]]), changes, agg["id"])
        elif agg["op"] == "keep_tag_only":
            keep = {(sid, find) for sid, find in agg["targets"]}
            for sid, rs in inv.items():
                for r in rs:
                    if agg["tag"] not in r["proposed_hard_classes"]:
                        continue
                    if any(s == sid and f in r["quote"] for s, f in keep):
                        continue
                    apply_effect(inv, retag(sid, (r["quote"], r["raw_label_or_claim"]),
                                            remove=[agg["tag"]]), changes, agg["id"])
    resolutions = []
    for i, row in enumerate(LEDGER):
        cite, status, plain, eff = RULINGS[i]
        apply_effect(inv, eff, changes, "ledger#%02d" % i)
        if status == "remains_genuinely_unsettled":
            UNSETTLED_NOTES.append(i)
        resolutions.append({
            "ordinal": i, "source_id": row["source_id"],
            "question": row["question"],
            "question_sha256": shat(row["question"] or ""),
            "reviewer_note_sha256": shat(row["cited"] or ""),
            "status": status, "ruling_class": cite[0],
            "authority": {"file": cite[1][0], "anchor": cite[1][1]},
            "ruling": plain,
            "effect": eff if eff else {"op": "none"}})
    for cov in COVERAGE:
        apply_effect(inv, cov["effect"], changes, cov["id"])
    return inv, changes, resolutions


def render(art):
    L = ["RECONCILIATION PROPOSAL (unapproved evidence, not a lock)",
         "artifact schema: %s" % art["schema"], ""]
    b, a = art["counts"]["before"], art["counts"]["after"]
    L.append("COUNTS                       before   after")
    L.append("  rows                       %6d  %6d" % (b["rows"], a["rows"]))
    for k in sorted(set(b["kinds"]) | set(a["kinds"])):
        L.append("  kind %-22s %6d  %6d" % (k, b["kinds"].get(k, 0), a["kinds"].get(k, 0)))
    for t in V.HARD_CLASSES:
        flag = "" if a["tags"][t] >= V.TAG_FLOOR else "   BELOW FLOOR"
        L.append("  tag  %-22s %6d  %6d%s" % (t, b["tags"][t], a["tags"][t], flag))
    L += ["", "RESOLUTION STATUS"]
    st = collections.Counter(r["status"] for r in art["resolutions"])
    for k, v in st.most_common():
        L.append("  %-30s %d" % (k, v))
    L += ["", "AGGREGATE AND LEDGER CHANGES (%d)" % len(art["changes"])]
    for c in art["changes"]:
        L.append("  [%s] %s %s | %s" % (c["owner"], c["op"], c["source_id"],
                                        c["quote"].replace("\n", " ")[:80]))
    return "\n".join(L) + "\n"


def main():
    # VARIANT. "proposal" reproduces Core1158 exactly; "final" is the fresh
    # reviewed candidate that also carries the Codex SEQ 1342 coverage row.
    variant = sys.argv[1] if len(sys.argv) > 1 else "proposal"
    if variant not in ("proposal", "final"):
        raise SystemExit("variant must be proposal or final")
    if variant == "proposal":
        del COVERAGE[:]
        COVERAGE.extend(_BASE_COVERAGE)
    inv, changes, resolutions = build()
    art = collections.OrderedDict()
    art["schema"] = "one-item-inventory-reconciliation-proposal-v1"
    art["status"] = "UNAPPROVED PROPOSAL - read-only evidence, not a lock"
    art["inputs"] = {
        # THE ARCHIVED instruction, never the live mailbox: the mailbox holds
        # one message and moves on, so reading it would make this artifact
        # depend on when it was built.
        "instruction": {"seq": 1340 if variant == "proposal" else 1342,
                        "sha256": shaf(MAILBOX + "/archive_CODEX_%d.md"
                                       % (1340 if variant == "proposal" else 1342))},
        "package_manifest_sha256": shaf(E + "/inventory_review/package.manifest.json"),
        "inventory_sha256": shaf(E + "/one_item_benchmark_inventory.json"),
        "prefix_sha256": shaf(E + "/inventory_review/prefix.md"),
        "pending_ledger": {"rows": len(LEDGER),
                           "sha256": shaf(RUN + "/pending_ledger.json")},
        "accepted_raws": [
            {"source_id": sid, "attempt": ACCEPTED[sid]["attempt"],
             "raw_name": ACCEPTED[sid]["raw_name"],
             "sha256": shaf(os.path.join(RUN, "replies", ACCEPTED[sid]["raw_name"]))}
            for sid in ORDER],
        "sources": [{"source_id": sid,
                     "input_sha256": shaf(E + "/inventory_review/inputs/%s.json" % sid),
                     "menu_entries": len(MENUS[sid])} for sid in ORDER]}
    art["class_rulings_applied"] = [a["id"] for a in AGGREGATE]
    art["aggregate_changes"] = AGGREGATE
    art["coverage_selections"] = COVERAGE
    art["resolutions"] = resolutions
    art["changes"] = changes
    art["proposed_inventory"] = collections.OrderedDict(
        (sid, [{k: v for k, v in r.items() if not k.startswith("_")} for r in inv[sid]])
        for sid in ORDER)
    art["sidecar"] = [
        {"source_id": sid,
         "accepted_rows": len(BASE[sid]),
         "considered": len(CONSIDERED[sid]),
         "proposed_rows": len(inv[sid]),
         "row_origins": collections.Counter(r["_origin"] for r in inv[sid])}
        for sid in ORDER]
    art["counts"] = {"before": counts(BASE), "after": counts(inv)}
    art["candidate_tables"] = {
        "ambiguous_menus": {
            "population_rule": "exact normalized menu values carried by two or more "
                               "kinds inside one event's own menu",
            "values": [{"value": v, "events": {s: k for s, k in AMB[v].items()}}
                       for v in AMB],
            "selected": [c["id"] for c in COVERAGE if c["tag"] == "ambiguous_menus"]},
        "corrections_and_amendments": {
            "population_rule": "every selected or considered positive correction and "
                               "every genuine boundary trap, from exact source evidence",
            "selected": ["ledger#06 SkyMiles amendment (boundary trap)",
                         "ledger#19 Darden covenant amendment (boundary trap)",
                         "ledger#27 YUM rounding/presentation note (boundary trap)",
                         "ledger#33 AutoZone maturity amendment (boundary trap)",
                         "ledger#54 Best Buy same-call clarification (positive correction)"]}}
    art["future_seam_design_only"] = (
        "The existing experiment materializer gains one input: the immutable accepted "
        "raws it already reads, PLUS one reviewed reconciliation artifact. It records "
        "both hashes in its current sidecar, validates the resolved inventory with the "
        "frozen validator, and hands the signer one statement: the result equals the "
        "accepted event verdicts plus exactly that reviewed reconciliation. No second "
        "parser, no proof framework, no compatibility layer, no rewritten raw, no extra "
        "model call.")
    stem = ("/reconciliation_proposal" if variant == "proposal"
            else "/reconciliation_final")
    out = RUN + stem + ".json"
    io.open(out, "w", encoding="utf-8").write(json.dumps(art, indent=1, default=str))
    io.open(RUN + stem + ".txt", "w", encoding="utf-8").write(render(art))
    print("wrote %s\n  sha256 %s" % (out, shaf(out)))
    print("  rendered sha256 %s" % shaf(RUN + stem + ".txt"))
    print(render(art))


if __name__ == "__main__":
    main()
