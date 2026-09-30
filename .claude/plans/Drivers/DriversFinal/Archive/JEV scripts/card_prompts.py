"""'Fact card' prompts written from DRIVER_RULES_Categorized.md: 3.5 + 3.6 (metric state), 3.28-3.33 (unit), 3.47 (span vs single moment)."""
READ="Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."
# ---- metric state (rule 3.6, first matching row wins; 3.5: good or bad news never decides a state)
STATE={"state":{"type":"choice",
 "instructions":{"question":"Which state does `quote` give for the driver `driver_name`?",
   "read":READ+" Apply these in order and take the first that fits: a stated direction is increased or decreased; the same driver moving differently across parts is mixed; stated flat is unchanged; ongoing with no direction is persists; a bare value is reported, but a value that also states the prior value is increased or decreased; otherwise unknown. Good or bad news never decides the state."},
 "criteria":{
  "increased":{"what":"The quote states an increase, or gives a value together with a lower prior value. A loss that narrows counts as an increase.","not_for":"A bare value with no direction and no prior value."},
  "decreased":{"what":"The quote states a decrease, or gives a value together with a higher prior value. A loss that widens counts as a decrease.","not_for":"A bare value with no direction and no prior value."},
  "mixed":{"what":"The same driver moves in different directions in different parts of the quote.","not_for":"A single direction."},
  "unchanged":{"what":"The quote states that the driver is flat or unchanged.","not_for":"A small increase or decrease."},
  "persists":{"what":"The quote says the driver is ongoing or continues, with no direction and no value.","not_for":"A bare value, or a stated direction."},
  "reported":{"what":"The quote gives a bare value with no stated direction and no prior value.","not_for":"A value stated together with its prior value, or with a direction."},
  "unknown":{"what":"None of the other states fits.","not_for":"Anything the other states describe."}}}}
# ---- unit (rules 3.28, 3.30, 3.31, 3.33): one prompt for the stated value, one for the stated change
UNITS={
 "usd":{"what":"Money per unit: a price, a per-share amount or a per-barrel amount, in US dollars.","not_for":"A money total."},
 "m_usd":{"what":"A money total in US dollars (millions or billions of dollars).","not_for":"Money per unit."},
 "percent":{"what":"A percentage that is itself a level, such as a margin, a rate or a share of a total.","not_for":"Growth against an earlier period, or a difference in percentage points."},
 "percent_yoy":{"what":"Growth compared with a year earlier (year over year, comparable or annual growth). Growth is never plain percent.","not_for":"Growth against the previous quarter, or a difference in points."},
 "percent_sequential":{"what":"Growth compared with the immediately previous comparable period, for a period shorter than a year.","not_for":"Growth against a year earlier."},
 "percent_points":{"what":"A difference between two percentages, in percentage points. Points win over year-over-year or sequential wording.","not_for":"Growth in percent."},
 "basis_points":{"what":"A difference or move in basis points. Basis points win over year-over-year or sequential wording.","not_for":"Growth in percent."},
 "count":{"what":"A number of things, such as shares, stores, aircraft, employees or customers.","not_for":"Money or a percentage."},
 "x":{"what":"A multiple, such as 2.5x.","not_for":"A percentage."},
 "unknown":{"what":"The unit cannot be settled from the quote, for example money in a currency other than US dollars, growth over a vague horizon, or up or down X% on a metric that is itself a percentage with no points, basis points or \"to X%\".","not_for":"A unit the quote states clearly."}}
UNIT_LEVEL={"unit":{"type":"choice","instructions":{"question":"What is the unit of the stated value in `quote` for the driver `driver_name`, ignoring any change or comparison amount?","read":READ},"criteria":UNITS}}
UNIT_CHANGE={"unit":{"type":"choice","instructions":{"question":"What is the unit of the stated change (the increase, decrease or difference) in `quote` for the driver `driver_name`?","read":READ},"criteria":UNITS}}
# ---- span vs single moment (rule 3.47: stated from the meaning, never defaulted)
TIMETYPE={"time_type":{"type":"choice",
 "instructions":{"question":"Does the value in `quote` for the driver `driver_name` cover a span of time or a single moment?","read":READ+" Decide from the meaning of the value, never from a default."},
 "criteria":{
  "duration":{"what":"The value covers a span of time, such as a quarter, a year or a year to date, for example revenue, expenses or cash flow for the period.","not_for":"A balance or count measured as of a date."},
  "instant":{"what":"The value is measured at a single moment, such as a balance, a count or a rate as of a date.","not_for":"An amount earned or spent over a period."}}}}
if __name__=="__main__":
    import json
    for n,q in (('STATE',STATE),('UNIT_LEVEL',UNIT_LEVEL),('TIMETYPE',TIMETYPE)): print("=====",n); print(json.dumps(q,ensure_ascii=False,indent=1)[:3500])
