import re,collections,json
# class: A = Jev carries the judgment (code composes) | B = Jev does part (select/judge), code/other does the rest
#        C = code only (structure, arithmetic, dates, storage, views) | D = policy / off-for-now / open question / constraint | E = needs a generating model (not Jev)
# tier for A/B: 1 = proven analog (fact-type test) | 2 = same shape, high expectation | 3 = harder, must be measured
R={}
def s(cls,ids,note,tier=None):
    for i in ids.split(): R[i]=(cls,tier,note)
# ---- 1 Driver record
s('C','1.2 2.1 2.2 2.38 6.15 6.16 6.17 6.19','structure / storage / mechanical check')
s('D','1.1 1.19 5.6 9.6 9.9 9.10 10.2','principle, off-for-now or open question')
s('A','6.13 6.14','Noul: does text explicitly say old label continues as new, same composition? (release 2)',3)
# ---- 2a fact type
s('A','1.5 1.6 2.29 2.30 7.7','Choice/Noul persistence + outlook test (measured 99.6% on decidable facts)',1)
s('A','2.23','Noul x2: is the base a standing metric? is the source forecasting/comparing it?',2)
s('C','1.8 2.19 2.22 2.25 2.27 2.28','fixed lookup / string suffix / cache')
s('D','1.7 1.9 1.10 2.31','principle or examples')
s('E','2.24','needs a generating model to propose a specific name')
# ---- 2b name (Jev validates; does not name)
s('A','2.3 2.11 2.17 2.18','fan-out Noul checklist on a proposed name: one question per forbidden item (state, direction, company, period, number, source label, measurement word, two causes)',2)
s('A','2.12 2.13 2.14','Choice: company\'s own measured part / outside cause / unclear; population word vs whole company (role test)',2)
s('B','2.6 2.8 2.9 2.10 2.15 2.16','Noul checks (too broad? standard phrase kept whole? denominator stated? acronym certain?); code handles format and order',2)
s('C','2.7','regex format check')
s('D','2.5 2.21','policy')
# ---- 2c which name / family / identity
s('A','2.26 2.32 2.40 2.47','5 Noul per candidate (same object / scope / mechanism / no rival / coherent evidence); family gate = same checks vs each family member',3)
s('B','2.4 2.43','code finds candidates (search / lexical); Jev Choice among K candidates + "none"',3)
s('C','1.18 2.45 2.46','name/type comparison, cache')
s('D','2.41 2.42 2.44','constraint (no counts, hidden tests only)')
# ---- 3 creating
s('A','2.20 2.33 1.11','Noul checklist: real fact vs boilerplate/bare mention? reusable kind not one instance? causal evidence? unambiguous?',2)
s('C','2.35 2.36 2.37 2.39','write-order and state checks')
s('D','2.34','architecture')
# ---- U1a
s('B','1.13','Noul: vendor-calculated ratio / common-size row? code checks numbers appear in quote',2)
s('C','1.17 3.1 3.2 3.9 3.10 3.12','identity keys, substring and link checks')
s('D','3.3 3.7','process')
# ---- U1b period
s('A','3.40 3.47','Choice: short/medium/long/undefined horizon; Noul: span or single moment',2)
s('B','3.36 3.37 3.39','Jev picks period kind and whether a window is stated; code resolves real dates (Jev is weak on dates)',2)
s('C','3.38 3.41 3.42 3.43 3.44 3.45 3.46','fiscal calendar and date arithmetic')
# ---- U1c slices / tags
s('A','3.13 3.14 3.15','Choice: slice kind (segment/product/geography/customer/channel/entity_ownership/unknown) with what/not_for; Noul: real business population?',2)
s('A','3.16 3.21','offline batch: classify each XBRL axis by its members; flag pure eliminations; owner reviews the list (one-time, pennies)',2)
s('B','3.18 3.25 3.26','Choice among company\'s existing slice values + none; Noul per candidate qualifier word; code copies text',2)
s('C','3.17 3.19 3.20 3.22 3.24 3.27','exact-match and storage')
s('D','3.23 9.3','policy')
# ---- U1d states / amounts
s('A','3.6 3.8','Choice among allowed states, with the row order as criteria',2)
s('A','3.33 3.50 3.52 7.8','Choice: growth basis; value vs change; comparison baseline (consensus / prior_year / sequential / previous_guidance / none)',2)
s('B','3.28 3.34 3.48 3.49 9.1','Jev classifies unit kind, sign words, floor/ceiling wording, is-comparison-stated, currency; code does scale, negate, store',2)
s('C','3.5 3.29 3.30 3.31 3.32 3.35 3.51','arithmetic, validity and grouping')
s('D','10.4','open question')
# ---- U2a saving
s('C','3.4 5.1 5.2 5.3 5.4 5.5 5.7','write logic')
# ---- U2b links
s('A','6.1 6.5','Choice among the company\'s line items + none; Noul per pair: same metric? (cost vs revenue, subtotal vs total)',3)
s('A','6.4','Noul: event/macro? ratio, derived or growth figure? non-GAAP?',2)
s('C','3.11 6.2 6.3 6.6 6.7 6.8 6.9 6.10','structural checks and candidate lists')
s('D','6.11 6.12','off for now')
# ---- U2c reading
s('C','7.1 7.2 7.3 7.4 7.5 7.6 7.9 7.10 7.11','queries and views')
# ---- U3a forecasts
s('A','4.5 4.6 4.9 4.19','Noul/Choice: correction wording? revision vs forecast-of-change? who said it (company / third party / unclear)? same source replaces it?',2)
s('B','4.4 4.8 4.18 4.21','Jev: which movement is stated; condition attached; is it a clear withdrawal with exact scope; code: midpoint arithmetic and matching open forecasts',2)
s('E','4.7','writing tidy text (needs a generator; Jev can only judge whether numbers are present)')
s('C','4.20','add-only write rule')
s('D','9.2 9.8','off for now')
# ---- U3b surprises
s('A','4.1 4.2 4.3 4.16','Choice: which comparison (result vs consensus / vs own guidance / forecast vs consensus / new vs old forecast / vs last year); Noul: is there also an outside-expectation comparison?',2)
s('A','4.11','Choice beat / in_line / missed / unknown (negation, direction, scope) - literal-reading risk',3)
s('B','4.10 4.12 4.15 4.17','Jev: good/bad wording present? stated basis? grounded to a metric?; code: range containment, dates',3)
s('C','4.14','structural matching of home fact')
s('D','4.13','constraint')
# ---- S1..S5
s('D','1.12 1.15 1.16 6.18 6.20 6.21 8.1 8.2 8.3 8.4 8.5 8.6 8.7','ground rules and constraints on how any AI may be used')
s('C','1.20 1.21 8.8 8.9 1.14 8.14 8.15','eligibility lists, exact quote check, schema check, outcomes, retry triggers')
s('D','1.3 1.4 8.10 8.11 9.4 9.5 10.3 8.12 8.13 8.17 8.18 9.7 10.1 A2.1 A2.5','purpose, off-for-now, open, or qualification rule')
s('B','8.16','Noul fan-out: does this passage update known Driver X? (code lists candidates)',2)
s('A','A2.3','producer of a verdict: Choice long/short + Score weightage 0.1-1.0 + confidence (separately approved source)',3)
s('C','A2.2 A2.4 A2.6 A2.7 A2.8','keys, shares, grading, records')
ids=[]; home=None; homes={}
for l in open('/home/faisal/EventMarketDB/.claude/plans/Drivers/DriversFinal/DRIVER_RULES_Categorized.md'):
    m=re.match(r'^#{3,4} (.+)',l)
    if m: home=m.group(1).strip()
    m=re.match(r'^- (A?\d+\.\d+)\b(.*)',l)
    if m: ids.append(m.group(1)); homes[m.group(1)]=home
miss=[i for i in ids if i not in R]; extra=[i for i in R if i not in ids]
print("rules",len(ids),"classified",len(R),"missing",miss,"extra",extra)
cnt=collections.Counter(R[i][0] for i in ids); print(dict(cnt))
tot=len(ids); D=cnt['D']; ex=tot-D
print(f"A {cnt['A']} ({100*cnt['A']/tot:.0f}% of all)  B {cnt['B']}  A+B {cnt['A']+cnt['B']} ({100*(cnt['A']+cnt['B'])/tot:.0f}% of all; {100*(cnt['A']+cnt['B'])/ex:.0f}% of the {ex} non-policy rules)  C {cnt['C']}  D {D}  E {cnt['E']}")
tiers=collections.Counter(R[i][1] for i in ids if R[i][0] in 'AB'); print("tiers (A+B):",dict(tiers))
ta=collections.Counter(R[i][1] for i in ids if R[i][0]=='A'); print("tiers (A only):",dict(ta))
hc=collections.defaultdict(collections.Counter)
for i in ids: hc[homes[i]][R[i][0]]+=1
print(f"\n{'home':32s} n   A  B  C  D  E")
for h,c in hc.items(): print(f"{h[:32]:32s} {sum(c.values()):3d} {c['A']:2d} {c['B']:2d} {c['C']:2d} {c['D']:2d} {c['E']:2d}")
json.dump({i:dict(home=homes[i],cls=R[i][0],tier=R[i][1],note=R[i][2]) for i in ids},open('rules_vs_jev.json','w'),indent=1)
with open('rules_vs_jev.md','w') as f:
    f.write("# Every rule vs Jev\n\nA = Jev carries the judgment | B = Jev does part | C = code only | D = policy / off / open / constraint | E = needs a generator\nTier: 1 = proven analog | 2 = same shape, high expectation | 3 = harder, measure first\n\n| rule | home | class | tier | how |\n|---|---|---|---|---|\n")
    for i in ids: f.write(f"| {i} | {homes[i]} | {R[i][0]} | {R[i][1] or ''} | {R[i][2]} |\n")
