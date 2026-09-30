"""Step 5 identity check prompts (JEV.md §6.8b). Wording = the text of rule 2.40 only (its test and five-check list); no clause of 2.45 is added (rule 1.9/2.21/2.44),
so the run also shows whether 2.40 alone stops the 'always different' cases. Check 4 (no equally plausible competing driver) needs a shortlist and is NOT tested by a pair.
Two variants, frozen before any call:  V1 one question;  V2 four one-check questions (checks 1, 2, 3, 5).  A pair merges only if every question is >= t (t = 0.5 and 0.7).
State shape (docs: one record per candidate, evidence as an object): {"existing": side, "newcomer": side}, side = name, type, where_it_appears, text_before_quote, quote."""
READ = ("Judge by meaning from the evidence in each side's `quote` and the text around it. The `name` of a side is only the proposed label. "
        "A detail that only one side mentions is not a conflict, but it is not proof of a match either.")
def q(question, true, false): return {"type": "noul", "instructions": {"question": question, "read": READ}, "criteria": {"true": {"what": true}, "false": {"what": false}}}
V1 = {"same_driver": q("Are `existing` and `newcomer` the same driver?",
        "They concern the same exact object, the same business scope and the same mechanism.",
        "They differ in object, business scope or mechanism.")}
V2 = {
 "same_object": q("Do `existing` and `newcomer` concern the same exact object, not a broader or narrower class?",
        "Both sides concern the same exact object.", "One side concerns a broader or narrower class, or a different object."),
 "same_scope": q("Do `existing` and `newcomer` concern the same business population and ownership scope?",
        "Both sides concern the same business population and ownership scope.", "The business population or ownership scope differs."),
 "same_mechanism": q("Do `existing` and `newcomer` concern the same causal mechanism and position?",
        "Both sides concern the same causal mechanism and position.", "The causal mechanism or position differs."),
 "coherent": q("Does the evidence of `existing` describe one coherent mechanism?",
        "The evidence of `existing` describes one coherent mechanism.", "The evidence of `existing` mixes several mechanisms or is not coherent."),
}
VARS = {"V1": V1, "V2": V2}

# ---- EXPLORATORY (JEV.md §6.8c): V3 = V2 and V4 = V1 with ONE added sentence in `read` (source: rule 2.42, drivers are company-neutral). It is a new clause, so it needs owner approval (rules 1.9/2.21/2.44).
# Written once, after seeing only the aggregate result of the frozen run (159 of 170 same-measure pairs are cross-company and the literal 2.40 questions read "same" as "same company"); never iterated.
READ3 = READ + (" The two sides may come from different companies, periods or documents and may show different amounts; that alone does not make them different. "
                "Compare what kind of thing is measured and how, not which company reports it.")
def _with_read(qs):
    out = {}
    for k, v in qs.items():
        w = json.loads(json.dumps(v)); w["instructions"]["read"] = READ3; out[k] = w
    return out
import json
VARS["V3"] = _with_read(V2); VARS["V4"] = _with_read(V1)
