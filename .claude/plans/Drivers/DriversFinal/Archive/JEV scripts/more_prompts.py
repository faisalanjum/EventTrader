"""Prompts written from DRIVER_RULES_Categorized.md: 3.52 (comparison baseline), 3.40 (vague horizons), 3.13-3.15 (slice kind)."""
READ="Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."
# ---- 3.52 comparison baseline: store only the headline comparison
BASELINE={"baseline":{"type":"choice",
 "instructions":{"question":"What headline comparison does `quote` make for the driver `driver_name`?",
                 "read":READ+" If the quote makes several comparisons, take the headline one."},
 "criteria":{
  "consensus":{"what":"The value is compared with what analysts, the Street or the market expected.","not_for":"The company's own forecast."},
  "prior_year":{"what":"The value is compared with the same period a year earlier (year over year, versus last year, the year-ago period). If the quote also compares with the previous quarter, the year-ago comparison wins.","not_for":"A comparison with the previous quarter only."},
  "sequential_period":{"what":"The value is compared with the immediately previous comparable period, such as the previous quarter or month, and not with a year earlier.","not_for":"A comparison with a year earlier."},
  "previous_guidance":{"what":"The value is compared with the company's own earlier guidance, forecast, outlook or target.","not_for":"Analysts' expectations."},
  "none":{"what":"The quote makes no comparison, or compares with something else: peers, a fixed anchor year such as 2019, or a streak.","not_for":"A comparison with a year earlier, the previous period, analysts or the company's own guidance."}}}}
# ---- 3.40 vague horizons for forecasts with no dates
HORIZON={"horizon":{"type":"choice",
 "instructions":{"question":"Which time horizon does the forecast or goal in `quote` refer to, for the driver `driver_name`?",
                 "read":READ},
 "criteria":{
  "stated_window":{"what":"The quote names a real window: a fiscal year, a quarter, a half, a month, a dated range or a year such as by 2030.","not_for":"A horizon described only in words such as long term or going forward."},
  "short_term":{"what":"The quote looks ahead to the near term or the coming months, in words, with no dates.","not_for":"A dated window."},
  "medium_term":{"what":"The quote looks ahead to the medium term or the next few years, in words, with no dates.","not_for":"A dated window."},
  "long_term":{"what":"The quote looks ahead to the long term, a long-range plan or over time, in words, with no dates.","not_for":"A dated window."},
  "undefined":{"what":"The quote looks ahead to a horizon that is implied but not defined, such as going forward, with no dates.","not_for":"A dated window, or a horizon named as short, medium or long term."}}}}
# ---- 3.13-3.15 slice kind
SLICE={"slice_kind":{"type":"choice",
 "instructions":{"question":"What kind of company part is `slice_value` in `quote`, for the driver `driver_name`?",
                 "read":READ+" A brand is not a kind; the way the quote uses it decides."},
 "criteria":{
  "segment":{"what":"A part the company operates as: a reporting segment or division.","not_for":"Something the company sells, or a place."},
  "product":{"what":"Something the company sells: a product, a service or a program.","not_for":"A reporting segment, or a place."},
  "geography":{"what":"A place the company operates in: a country, a region or a destination.","not_for":"A product or a segment."},
  "customer":{"what":"A group the company sells to.","not_for":"A product or a place."},
  "channel":{"what":"How the company sells or runs something, for example franchised or through partners.","not_for":"A product or a customer group."},
  "entity_ownership":{"what":"A stake the company owns. Joint ventures and part-owned companies are the strongest cases; other entity rows are provisional.","not_for":"A product or a segment."},
  "unknown":{"what":"The kind cannot be told from the quote.","not_for":"A kind the quote makes clear."}}}}
if __name__=="__main__":
    import json
    for n,q in (('BASELINE',BASELINE),('HORIZON',HORIZON),('SLICE',SLICE)): print("=====",n,"\n",json.dumps(q,ensure_ascii=False)[:2600])

# ---- after the three proposed rulings (JEV.md §6.4) ----
import copy
HORIZON2=copy.deepcopy(HORIZON)
HORIZON2["horizon"]["criteria"]["long_term"]["what"]="The quote itself says long term, long-range or longer term, in words, with no dates."
HORIZON2["horizon"]["criteria"]["undefined"]["what"]="The quote looks ahead to a horizon that is implied but not defined, such as going forward, over time, eventually or in the future, with no dates."
SLICE2=copy.deepcopy(SLICE)
SLICE2["slice_kind"]["criteria"]["entity_ownership"]["what"]="A stake the company owns. Joint ventures and part-owned companies are the strongest cases. Other entity rows, such as the company's own subsidiary reported on its own, are provisional."
SLICE2["slice_kind"]["criteria"]["unknown"]["what"]="The kind cannot be told from the quote, or the same name could fit several kinds and nothing says which."
