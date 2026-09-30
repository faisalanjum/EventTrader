"""Tag questions for the sweep / missed-fact audit (JEV.md §9): "does this sentence state something the Driver system could store?"
Five Noul questions, one condition each, asked in ONE request per unit (speculative fan-out). Built to follow the TypeSafe docs:
  primitives/noul     one yes/no per Noul; phrase it so a HIGH value means yes; "try with and without criteria and keep whichever gives better answers"
  primitives/advanced instructions may be an object; `inspect` names the part of the state to judge, `focus` says what to look for; criteria.true / criteria.false
                      may be objects with `what` and `examples`; key names are free, so use short ones that label what follows
  primitives          question ids are NOT sent to the model, so the complete question is in `instructions`; fields are referenced by backticked name
Definitions are the rules' own wording (1.5 locked definitions; 2.33 boilerplate). Examples are invented, generic, and NOT taken from any test data.
Three variants of the SAME five questions, so the only difference is the structure the docs describe:
  P  plain: instructions is one string carrying the definition; no criteria
  C  criteria: short instruction string + criteria.true / criteria.false strings
  S  structured: instructions object {question, inspect, focus} + criteria.true / criteria.false objects {what, examples}"""
import re

METRIC = "a standing variable readable again over time (a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand)"
GUIDANCE = "the company's own forward outlook, target or forecast"
SURPRISE = "a company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus or the Street, or for an actual the company's own earlier forecast)"
ACTION = "a discrete thing that happened (a decision, transaction, incident, approval or one-off charge)"
READ = "`text_before_quote` and `text_after_quote` are the text around `quote`; use them only to see what `quote` refers to."

# id -> (short question, definition-bearing question, true.what, false.what, focus, true examples, false examples)
SPEC = {
 "states_metric": (
  "Does `quote` state a value or condition, of something about the company or its markets, that is a standing variable?",
  f"Does `quote` state a value or condition, of something about the company or its markets, that is {METRIC}?",
  f"It states a value or condition that is {METRIC}.",
  "It states no such value or condition: it is a heading, a cross-reference, a forecast, a one-time happening or a comparison with an outside expectation, or it names a measure without stating it.",
  "Judge what `quote` itself states. A heading, a page reference or a row label without a value states nothing.",
  ["Net sales were $2.1 billion.", "The workforce numbered 4,500 at year end.", "Our credit facility remains in place."],
  ["See Note 6 for more information.", "Total revenue", "We expect margins to improve."]),
 "states_guidance": (
  "Does `quote` state the company's own forecast?",
  f"Does `quote` state {GUIDANCE}?",
  f"It states {GUIDANCE}.",
  "It reports what already happened or what is true now, or the forecast belongs to someone other than the company.",
  "Only the company's own outlook counts, not an analyst's or another party's expectation.",
  ["We expect margins to improve in the second half.", "The company is targeting $500 million in savings by 2028."],
  ["Revenue grew 5% last year.", "Analysts expect strong growth next year."]),
 "states_surprise": (
  "Does `quote` compare a company result or forecast with an outside expectation?",
  f"Does `quote` state {SURPRISE}?",
  f"It states {SURPRISE}.",
  "It states no such comparison. A comparison with the prior period, or a new forecast set against the company's own earlier forecast, is not one.",
  "The comparison must be with an outside expectation, or for a result the company's own earlier forecast, and not with the prior period.",
  ["Earnings per share of $1.20 beat the consensus estimate of $1.10.", "Results were in line with the Street's expectations."],
  ["Revenue rose 5% from a year earlier.", "We raised our full-year outlook from our earlier forecast."]),
 "states_action_event": (
  "Does `quote` state something that happened at one point in time?",
  f"Does `quote` state {ACTION}?",
  f"It states {ACTION}.",
  "It states a standing level or condition, a forecast or plan, or nothing that happened.",
  "A continuing condition or a standing level is not a discrete happening.",
  ["The board approved a $200 million share repurchase.", "The company completed the acquisition on March 3.", "We recorded a one-time impairment charge."],
  ["Our fleet includes 900 aircraft.", "We intend to grow through acquisitions."]),
 "is_boilerplate": (
  "Is `quote` only boilerplate?",
  "Is `quote` only boilerplate, a heading, a cross-reference, a definition or a disclaimer, with no specific fact about the company?",
  "It is only boilerplate, a heading, a cross-reference, a definition or a disclaimer, and states no specific fact about the company.",
  "It states something specific about the company's results, position, plans or events.",
  "Boilerplate says nothing specific to this company's results, plans or events.",
  ["Forward-looking statements involve risks and uncertainties.", "See Item 1A for more information.", "Table of Contents"],
  ["Net sales were $2.1 billion.", "The board approved a dividend."]),
}
TYPE_TAGS = ["states_metric", "states_guidance", "states_surprise", "states_action_event"]      # the four fact types of rule 1.5
ORDER = TYPE_TAGS + ["is_boilerplate"]

def variant(v):
    qs = {}
    for qid in ORDER:
        short, long_, t_what, f_what, focus, t_ex, f_ex = SPEC[qid]
        if v == "P":      # plain: one string, no criteria
            qs[qid] = {"type": "noul", "instructions": f"{long_} {READ}"}
        elif v == "C":    # criteria: short question + true/false strings
            qs[qid] = {"type": "noul", "instructions": f"{short} {READ}", "criteria": {"true": t_what, "false": f_what}}
        elif v == "S":    # structured, mirroring the docs' `requests_credentials` example
            qs[qid] = {"type": "noul",
                       "instructions": {"question": short, "inspect": "quote", "focus": focus},
                       "criteria": {"true": {"what": t_what, "examples": t_ex}, "false": {"what": f_what, "examples": f_ex}}}
        else: raise ValueError(v)
    return qs

# ---- checklist taken from the docs' own sentences; run by validate()
def validate():
    problems = []
    for v in ("P", "C", "S"):
        qs = variant(v)
        assert list(qs) == ORDER
        for qid, q in qs.items():
            ins = q["instructions"]; text = ins if isinstance(ins, str) else ins["question"]
            if q["type"] != "noul": problems.append((v, qid, "type must be noul"))
            if "`quote`" not in (ins if isinstance(ins, str) else json_text(ins)): problems.append((v, qid, "field must be referenced by backticked name"))
            if re.search(r"\b(free of|devoid of|lacking|not )\b", text) or re.match(r"^\s*Is `quote` (free|not|without)", text): problems.append((v, qid, "inverted phrasing: a high value must mean yes"))
            if text.count("?") != 1: problems.append((v, qid, "exactly one question"))
            if v != "P" and set(q["criteria"]) != {"true", "false"}: problems.append((v, qid, "Noul criteria has exactly true and false"))
            if v == "P" and "criteria" in q: problems.append((v, qid, "P has no criteria"))
            if v == "S":
                if not (isinstance(ins, dict) and {"question", "inspect", "focus"} <= set(ins)): problems.append((v, qid, "S needs question/inspect/focus like the docs example"))
                for side in ("true", "false"):
                    c = q["criteria"][side]
                    if not (isinstance(c, dict) and {"what", "examples"} <= set(c) and isinstance(c["examples"], list) and c["examples"]): problems.append((v, qid, f"{side}: what + examples"))
            # "Write the complete question in instructions": no reliance on the id
            if qid in text: problems.append((v, qid, "question id leaked into the question text"))
    return problems

def json_text(x):
    import json; return json.dumps(x)

if __name__ == "__main__":
    import json
    p = validate(); print("checklist problems:", p or "none")
    for v in ("P", "C", "S"): print(f"\n=== variant {v}: tokens are counted by the API; JSON of one question below\n", json.dumps(variant(v)["states_surprise"], indent=1, ensure_ascii=False))
