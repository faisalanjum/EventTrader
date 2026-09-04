# -*- coding: utf-8 -*-
# ponytail: an AUDIT RECEIPT builder, not a runtime rule (Codex SEQ 1484 item 5,
# corrected per SEQ 1486: the exact-once label rule is WITHDRAWN - frozen item
# #014 lawfully carries its label twice; raw_label_or_claim may be the exact
# source label OR an exact claim substring of the quote (Codex 1336 / Core 1154),
# so #075 keeps its extended span and takes its old exact row quote as the claim).
# Every marker below is hand-read evidence for ONE named row; the script only
# locates the nearest preceding occurrence of that exact source text, cuts the
# contiguous span to the row's end, and measures. It decides nothing.
import collections, hashlib, io, json, os, sys
H = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import a7_g1_build as G, build_launch_manifest as B, kf_lint
from driver.core.prepared_fact_v2 import verify_occurrence

OUT = "/tmp/a7_source_locator_audit_1486.json"
MANIFEST = "/tmp/a7_v3_prepared_run_1479/plan/a5_exp5_reader.manifest.json"
FREEZE = "/tmp/a7_a6_freeze_1479/a6_exp5_launch_freeze.json"

def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def sha_file(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

# HAND-READ EVIDENCE for the eleven source-incomplete real items: the exact
# source text of the nearest governing header/marker the row needs, and the
# claim-bearing rows that the contiguous span from that marker to the row
# necessarily contains (labels copied from the source, counted by hand).
READ = {
 "0000006201-26-000031#001": {
   "marker": "3 Months Ended Percent Reconciliation of Net Loss Excluding Net Special Items March 31, Decrease 2026 2025 (in millions, except share and per share amounts)",
   "needs": "the '(in millions, except share and per share amounts)' scale caption and the 'Percent ... Decrease' column header that makes (30.8%) a percent",
   "swallowed": ["Net loss as reported $ (382) $ (473)", "Total pre-tax net special items (1), (2) 149 118", "Net tax effect of net special items (34) (31)"]},
 "0000006201-26-000031#006": {
   "marker": "(In millions, except share and per share amounts) (Unaudited) Percent 3 Months Ended Increase March 31, (Decrease) 2026 2025",
   "needs": "the statement's '(In millions, except share and per share amounts)' caption and the 'Percent Increase (Decrease)' header for 10.8",
   "swallowed": ["Passenger $ 12,495 $ 11,391 9.7", "Cargo 214 189 12.9", "Other 1,203 971 23.9"]},
 "0000006201-26-000031#008": {
   "marker": "(In millions, except share and per share amounts) (Unaudited) Percent 3 Months Ended Increase March 31, (Decrease) 2026 2025",
   "needs": "the same statement caption and percent header",
   "swallowed": ["Passenger", "Cargo", "Other", "Total operating revenues", "Aircraft fuel and related taxes", "Salaries, wages and benefits", "Regional operating expenses", "Regional depreciation and amortization", "Maintenance, materials and repairs", "Other rent and landing fees", "Aircraft rent", "Selling expenses", "Depreciation and amortization", "Special items, net", "Other", "Total operating expenses", "Operating loss", "Interest income", "Interest expense, net", "Other expense, net", "Total nonoperating expense, net", "Loss before income taxes", "Income tax benefit"]},
 "0000027904-26-000022#029": {
   "marker": "Favorable (Unfavorable) (in millions) 2026 2025",
   "needs": "the '(in millions)' scale marker and the 'Favorable (Unfavorable)' column header for the third figure",
   "swallowed": ["Interest expense, net $ (151) $ (179) $ 28"]},
 "0000092380-26-000044#042": {
   "marker": "(in millions, except per share amounts) (unaudited) Three months ended March 31, 2026 2025 Percent Change",
   "needs": "the statement's '(in millions, except per share amounts)' caption and the 'Percent Change' header for n.m.",
   "swallowed": ["Passenger", "Freight", "Other", "Total operating revenues", "Salaries, wages, and benefits", "Aircraft fuel and related taxes", "Maintenance materials and repairs", "Landing fees and airport rentals", "Depreciation and amortization", "Other operating expenses", "Total operating expenses", "OPERATING INCOME (LOSS)", "Interest expense", "Capitalized interest", "Interest income", "Other (gains) losses, net", "Total non-operating expenses (income)", "INCOME (LOSS) BEFORE INCOME TAXES"]},
 "0000940944-26-000005#065": {
   "marker": "(In millions, except per share data) (Unaudited) Three Months Ended Nine Months Ended 2/22/2026 2/23/2025 2/22/2026 2/23/2025",
   "needs": "the statement's '(In millions, except per share data)' caption and the period headers",
   "swallowed": ["Sales", "Food and beverage", "Restaurant labor", "Restaurant expenses", "Marketing expenses", "Pre-opening costs", "General and administrative expenses", "Depreciation and amortization", "Impairments and (gain) loss on disposal of assets, net", "Total operating costs and expenses", "Operating income", "Interest, net", "Earnings before income taxes", "Income tax expense", "Earnings from continuing operations"]},
 "0000940944-26-000009#068": {
   "marker": "Three Months Ended Nine Months Ended (in millions) February 22, 2026 February 23, 2025 % Chg February 22, 2026 February 23, 2025 % Chg",
   "needs": "the '(in millions)' marker and the '% Chg' header that makes NM a percent-change cell",
   "swallowed": ["Sales", "Food and beverage", "Restaurant labor", "Restaurant expenses", "Marketing expenses", "Pre-opening costs", "General and administrative expenses", "Depreciation and amortization"]},
 "0000940944-26-000009#072": {
   "marker": "Three Months Ended Nine Months Ended (in millions) February 22, 2026 February 23, 2025 % Chg February 22, 2026 February 23, 2025 % Chg",
   "needs": "the same '(in millions)' marker and '% Chg' headers",
   "swallowed": ["Sales", "Food and beverage", "Restaurant labor", "Restaurant expenses", "Marketing expenses", "Pre-opening costs", "General and administrative expenses", "Depreciation and amortization"]},
 "0001041061-25-000109#075": {
   "marker": "Tabular amounts are displayed in millions of U.S. dollars",
   "needs": "the MD&A introduction sentence that fixes the scale of every table in the part; no table-local scale marker exists near the row",
   "swallowed": ["the entire MD&A between its introduction and the Habit Burger & Grill division table: every division's System Sales, Same-Store Sales, Total revenues and Operating Profit rows and all prose claims in between"]},
 "0001104659-26-027061#115": {
   "marker": "(In thousands, except per share data)",
   "needs": "the Exhibit 1 statement caption '(In thousands, except per share data)'",
   "swallowed": ["Net sales", "Cost of sales", "Gross profit", "Selling, general and administrative expenses", "Pre-opening expenses", "Operating income"]},
 "0001171843-26-001288#133": {
   "marker": "Inventory Statistics (Total Stores) as of as of February 14, 2026 February 15, 2025",
   "needs": "the '($ in thousands)' marker (two rows above) and the table's 'as of' date headers",
   "swallowed": ["Accounts payable/inventory 110.9 % 118.2 %", "Inventory $ 7,449,330 $ 6,588,586", "Inventory per store 958 887"]},
}
# the six real items excluded for a MEANING reason, confirmed by independent
# reading of the reviewer's settlement against the source (not this class)
OTHER = {
 "0000940944-26-000005#066": "definitional recast of how segment profit is computed; states no driver level, change, guidance, surprise or action",
 "0001041061-25-000109#073": "an aggregate 'Special Items' EPS bucket composed of unrelated, independently named causes; one lawful fact cannot be made of it by extension",
 "0001104659-25-118458#107": "a conditional loan-covenant term (a required minimum ratio), not the company's reported level or an event",
 "0001104659-26-017090#109": "a non-GAAP reconciliation elimination netting two opposite causes; a bridge construct, not a driver",
 "0001171843-26-001288#131": "an unnamed extra calendar week inside a trailing-four-quarter window; no lawful period can be stated for it",
 "MCD_2026-02-11T16.30#174": "a sub-span of the same sentence already settled once as the capital-expenditure metric-plus-surprise pair (Rule 1.5, one fact is one record)",
}

key, sidecar = G.gold_by_event()
inv = json.load(open(B.INVENTORY, encoding="utf-8"))["records"]
man = json.load(open(MANIFEST, encoding="utf-8"))
freeze = json.load(open(FREEZE, encoding="utf-8"))
cap = freeze["counts"]["capacity"]
pk_prompt = {p["packet_id"]: p for p in man["packets"]}
prompts = B.one_item_prompts(man["prompt_role"], man["contract_suffix"])   # the frozen bytes, re-rendered
for pid_, p in pk_prompt.items():
    assert sha(prompts[pid_]) == p["prompt_sha256"], pid_       # bound to the run's pins
p2g = {r["packet_id"]: r for r in sidecar["packet_to_gold"]}
reasons = collections.defaultdict(list)
for a in sidecar["abstentions"]:
    reasons[a["packet_id"]].append(a["reason"])
assert len(inv) == len(p2g) == 196

rows, parts_cache = [], {}
def part_text(sid, part):
    if (sid, part) not in parts_cache:
        parts_cache[(sid, part)] = kf_lint.part_lookup(sid, B.INPUTS)[part]
    return parts_cache[(sid, part)]

for n, rec in enumerate(inv):
    pid = "%s#%03d" % (rec["source_id"], n)
    g = p2g[pid]
    suspect = g["proposed_record_kind"] == "real_item" and g["final_outcome"] != "fact"
    row = collections.OrderedDict([
        ("packet_id", pid), ("source_id", rec["source_id"]), ("part_ref", rec["part_ref"]),
        ("proposed_record_kind", g["proposed_record_kind"]), ("final_outcome", g["final_outcome"]),
        ("structural_suspect", suspect)])
    if not suspect:
        row["class"] = None
        rows.append(row); continue
    item = {k: rec[k] for k in ("part_ref", "occurrence_in_part", "quote", "raw_label_or_claim")}
    text = part_text(rec["source_id"], rec["part_ref"])
    row["old_locator"] = collections.OrderedDict([
        ("quote", rec["quote"]), ("quote_sha256", sha(rec["quote"])),
        ("occurrence_in_part", rec["occurrence_in_part"]),
        ("raw_label_or_claim", rec["raw_label_or_claim"]),
        ("occurrence_check", verify_occurrence(text, rec["quote"], rec["occurrence_in_part"]))])
    row["reviewer_settlement"] = reasons.get(pid, [])
    if pid in OTHER:
        row["class"] = "excluded_for_meaning_not_source_incompleteness"
        row["independent_reading"] = OTHER[pid]
        row["outcome"] = "NOT_IN_CLASS"
        rows.append(row); continue
    ev = READ[pid]
    row["class"] = "scale_or_unit_context_outside_quote"
    qpos = text.find(rec["quote"]); assert qpos >= 0 and text.count(rec["quote"]) == 1
    mpos = text.rfind(ev["marker"], 0, qpos); assert mpos >= 0, (pid, "marker not found before the row")
    span = text[mpos:qpos + len(rec["quote"])]
    occ = verify_occurrence(text, span, None)
    claim = rec["raw_label_or_claim"]
    label_count = span.count(claim)
    quote_count_in_span = span.count(rec["quote"])
    corrected_claim = claim if label_count == 1 else rec["quote"]   # SEQ 1486: the old exact row quote IS an exact claim substring
    corrected_claim_count = span.count(corrected_claim)
    new_item = dict(item, quote=span, raw_label_or_claim=corrected_claim)
    old_chars = pk_prompt[pid]["prompt_chars"]
    delta_chars = len(json.dumps(new_item, indent=1)) - len(json.dumps(item, indent=1))
    delta_bytes = len(json.dumps(new_item, indent=1).encode("utf-8")) - len(json.dumps(item, indent=1).encode("utf-8"))
    old_bytes = len(prompts[pid].encode("utf-8"))
    new_chars = old_chars + delta_chars
    new_bytes = old_bytes + delta_bytes
    row["proposed_span"] = collections.OrderedDict([
        ("marker_text", ev["marker"]), ("marker_offset_in_part", mpos), ("row_offset_in_part", qpos),
        ("span", span), ("span_sha256", sha(span)), ("span_chars", len(span)),
        ("span_utf8_bytes", len(span.encode("utf-8"))),
        ("span_count_in_part", text.count(span)),
        ("occurrence_check", occ), ("occurrence_in_part", None if occ is None else "not unique"),
        ("old_quote_count_in_span", quote_count_in_span),
        ("raw_label_or_claim", rec["raw_label_or_claim"]),
        ("label_count_in_span", label_count),
        ("corrected_raw_label_or_claim", corrected_claim),
        ("corrected_claim_changed", corrected_claim != claim),
        ("corrected_claim_count_in_span", corrected_claim_count),
        ("same_part", True), ("contiguous", True),
        ("context_the_row_needs", ev["needs"]),
        ("intervening_rows_already_present_in_the_complete_event", ev["swallowed"]),
        ("intervening_rows_count", len(ev["swallowed"])),
        ("old_prompt_chars", old_chars), ("recalculated_prompt_chars", new_chars),
        ("old_prompt_utf8_bytes", old_bytes), ("recalculated_prompt_utf8_bytes", new_bytes),
        ("observed_frozen_prompt_chars_max", cap["prompt_chars_max"]),
        ("observed_frozen_prompt_utf8_bytes_max", cap["prompt_utf8_bytes_max"]),
        ("within_observed_prompt_size_class", new_chars <= cap["prompt_chars_max"] and new_bytes <= cap["prompt_utf8_bytes_max"]),
        ("runtime_input_tokens", None),
    ])
    if occ is None and quote_count_in_span == 1 and corrected_claim_count == 1:
        row["outcome"] = "EXTENDABLE"
        row["reason"] = ("the span is unique in its part and contains the old quote once; the claim %s occurs once inside it, so the "
                         "existing source-item contract identifies one target (Codex SEQ 1486)"
                         % ("(the old exact row quote, an exact claim substring)" if corrected_claim != claim else "(the unchanged label)"))
        row["withdrawn_1485_premise"] = ("REFUSE for target ambiguity under the exact-once LABEL rule" if label_count != 1 else "EXTENDABLE under that rule too")
    else:
        row["outcome"] = "REFUSE"
        row["reason"] = "the span is not unique, or the old quote or corrected claim does not occur exactly once inside it"
    rows.append(row)

counts = collections.OrderedDict([
    ("rows", len(rows)),
    ("by_proposed_kind_and_final_outcome", collections.OrderedDict(
        ("%s -> %s" % k, v) for k, v in sorted(collections.Counter((r["proposed_record_kind"], r["final_outcome"]) for r in rows).items()))),
    ("structural_suspects", sum(1 for r in rows if r["structural_suspect"])),
    ("class_scale_or_unit_context_outside_quote", sum(1 for r in rows if r.get("class") == "scale_or_unit_context_outside_quote")),
    ("excluded_for_meaning", sum(1 for r in rows if r.get("class") == "excluded_for_meaning_not_source_incompleteness")),
    ("EXTENDABLE", sum(1 for r in rows if r.get("outcome") == "EXTENDABLE")),
    ("REFUSE", sum(1 for r in rows if r.get("outcome") == "REFUSE")),
    ("extendable_within_observed_prompt_size_class", sum(1 for r in rows if r.get("outcome") == "EXTENDABLE" and r["proposed_span"]["within_observed_prompt_size_class"])),
    ("identities", len({r["packet_id"] for r in rows})),
    ("locator_refused", sum(1 for r in rows if r.get("outcome") == "REFUSE")),
    ("selectable_items", len({r["packet_id"] for r in rows}) - sum(1 for r in rows if r.get("outcome") == "REFUSE")),
    ("arms", list(man["arms"])),
    ("blind_calls", (len({r["packet_id"] for r in rows}) - sum(1 for r in rows if r.get("outcome") == "REFUSE")) * len(man["arms"])),
    ("rows_needing_fresh_key_adjudication", sum(1 for r in rows if r.get("outcome") == "EXTENDABLE")),
    ("changed_fields_census", collections.OrderedDict([
        ("quotes_changed", sum(1 for r in rows if r.get("outcome") == "EXTENDABLE")),
        ("raw_label_or_claim_changed", sum(1 for r in rows if r.get("outcome") == "EXTENDABLE" and r["proposed_span"]["corrected_claim_changed"])),
        ("other_fields_changed", 0)])),
    ("withdrawn_1485_result", collections.OrderedDict([("EXTENDABLE", 10), ("REFUSE", 1), ("why_withdrawn", "the exact-once label rule rejects the lawful frozen item #014, whose label occurs twice inside one inseparable quote; a count over label text is not a general ambiguity owner (Codex SEQ 1486)")])),
    ("live_positive_label_twice", [{"packet_id": "%s#%03d" % (inv[n]["source_id"], n), "raw_label_or_claim": inv[n]["raw_label_or_claim"], "count_in_quote": inv[n]["quote"].count(inv[n]["raw_label_or_claim"])} for n in range(len(inv)) if inv[n]["quote"].count(inv[n]["raw_label_or_claim"]) != 1]),
    ("key_accepted_facts_with_unit_m_usd_and_multiplier_1", sum(
        1 for facts in key.values() for f in facts
        if (f.get("item") or f).get("level_unit") == "m_usd" and str(((f.get("item") or f).get("level_low") or {}).get("scale_multiplier")) == "1")),
])
codex_baseline = ["#001", "#006", "#008", "#029", "#042", "#065", "#068", "#072", "#075", "#115", "#133"]
found = ["#" + r["packet_id"].split("#")[1] for r in rows if r.get("class") == "scale_or_unit_context_outside_quote"]
doc = collections.OrderedDict([
    ("schema", "a7_source_locator_class_audit/1486"),
    ("inventory_sha256", sha_file(B.INVENTORY)),
    ("manifest_sha256", sha_file(MANIFEST)), ("a6_freeze_sha256", sha_file(FREEZE)),
    ("suspect_derivation", "proposed_record_kind == real_item AND final_outcome != fact, from the A4 materializer sidecar packet_to_gold; no word list, no id list"),
    ("codex_baseline_eleven", codex_baseline), ("class_found", found), ("baseline_matches", sorted(found) == sorted(codex_baseline)),
    ("counts", counts), ("rows", rows)])
canon = json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
doc["receipt_sha256"] = sha(canon)
with io.open(OUT, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=1, ensure_ascii=False)
print("counts:", json.dumps(counts))
print("baseline matches:", doc["baseline_matches"])
print("receipt:", doc["receipt_sha256"], OUT, os.path.getsize(OUT), "bytes")
for r in rows:
    if r.get("class") == "scale_or_unit_context_outside_quote":
        s = r["proposed_span"]
        print("  %-28s %-10s span %6d ch %6d B  label x%d claim x%d changed=%s quote x%d  in-part x%d  prompt %d->%d ch / %d->%d B  within=%s" % (
            r["packet_id"], r["outcome"], s["span_chars"], s["span_utf8_bytes"], s["label_count_in_span"], s["corrected_claim_count_in_span"], s["corrected_claim_changed"], s["old_quote_count_in_span"],
            s["span_count_in_part"], s["old_prompt_chars"], s["recalculated_prompt_chars"], s["old_prompt_utf8_bytes"],
            s["recalculated_prompt_utf8_bytes"], s["within_observed_prompt_size_class"]))
