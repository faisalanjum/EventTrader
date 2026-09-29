"""Prompts for the surprise test, written from DRIVER_RULES_Categorized.md: 1.5 + 4.1-4.3 (which comparison), 4.10-4.13 (beat / in_line / missed / unknown)."""
READ="Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."
# S2: which comparison (rule 4.1 table, 4.2 kinds, 4.3 basis + baseline)
S2={"comparison":{"type":"choice",
 "instructions":{"question":"Which comparison does `quote` make about the driver `driver_name`?",
                 "read":READ+" Decide whether the value is a reported result or a forecast from what the quote says, not from whether the period has ended."},
 "criteria":{
  "actual_vs_consensus":{"what":"A result the company has reported, compared with what analysts, the Street or the market expected (the consensus or estimate).",
                         "not_for":"A comparison with last year or last quarter, or with the company's own forecast."},
  "actual_vs_guidance":{"what":"A result the company has reported, compared with the company's own earlier forecast, guidance, outlook or target range.",
                        "not_for":"A comparison with analysts' expectations, or with last year or last quarter."},
  "guidance_vs_consensus":{"what":"A forecast or outlook the company gives for a future period, compared with what analysts, the Street or the market expected.",
                           "not_for":"A new forecast compared with the company's own earlier forecast."},
  "none":{"what":"No company value is compared with an outside expectation or with the company's own earlier forecast. This includes a comparison with last year or last quarter, a new forecast compared with the company's own earlier forecast, a forecast or result with no comparison, and a statement that only mentions consensus or expectations.",
          "not_for":"Any of the three comparisons above."}}}}
# S3: beat / in_line / missed / unknown (rules 4.10, 4.11, 4.12, 4.13)
S3={"state":{"type":"choice",
 "instructions":{"question":"Is the company's value in `quote` a beat, in line, or a miss against the expectation it is compared with, for the driver `driver_name`?",
                 "read":READ+" Judge the whole phrase, including negation, direction and scope. The words above, below, exceeded and ahead of do not mean good or bad on their own, and a higher number is not always better."},
 "criteria":{
  "beat":{"what":"The value is better than the expectation, judged by meaning: the source says beat, better than expected, or gives other words that frame the result as good.",
          "not_for":"A value that is only higher or lower with no sign that it is good."},
  "in_line":{"what":"The value equals the expectation, sits inside a stated expectation range or on its edge, or the source says in line, and no words say good or bad.",
             "not_for":"A value clearly outside the range that the source frames as good or bad."},
  "missed":{"what":"The value is worse than the expectation, judged by meaning: the source says miss, worse than expected, or gives other words that frame the result as bad.",
            "not_for":"A value that is only higher or lower with no sign that it is bad."},
  "unknown":{"what":"The value is outside the expectation but the source gives no words saying good or bad, and a higher number is not clearly better for this driver (for example costs, capital spending, research spending, inventory, hiring or cash burn), or the comparison is unclear.",
             "not_for":"A comparison the source states as a beat, a miss or in line."}}}}
if __name__=="__main__":
    import json; print(json.dumps(S2,indent=1)); print(json.dumps(S3,indent=1))
