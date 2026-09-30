# the ORIGINAL (v1/v2) prompts, kept only for the control experiment
DEF = {
 "metric": "Any standing variable readable again over time: a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand.",
 "guidance": "The company's own forward outlook, target or forecast. Outlook verbs (expect, anticipate, target, plan to) make it guidance, never a metric state.",
 "surprise": "A company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus), or an actual compared with the company's own earlier forecast. Not a comparison with a prior-period actual, and not a new forecast compared with the company's own earlier forecast.",
 "action_event": "A discrete thing that happened: a decision, transaction, incident, approval or one-off charge.",
}
PERSIST = "Between two events, is there a standing level or severity you could re-read? Yes means metric; no means action_event."
QA = {"fact_type": {"type": "choice", "instructions": "What kind of fact does the quote state about the driver? " + PERSIST, "criteria": DEF}}
QB = {
 "surprise_kind": {"type": "choice", "instructions": DEF["surprise"] + " Which comparison, if any, does the quote make?",
   "criteria": {"none": "The quote makes none of these comparisons.", "actual_vs_consensus": "A delivered actual compared with analyst consensus or another party's expectation.",
                "actual_vs_guidance": "A delivered actual compared with the company's own earlier forecast.", "guidance_vs_consensus": "A company forecast compared with analyst consensus."}},
 "forward_looking": {"type": "noul", "instructions": "Is the quote the company's own forward outlook, target or forecast for a future period?",
   "criteria": {"true": DEF["guidance"], "false": "A statement about something that is or was, not a forecast."}},
 "standing_level": {"type": "noul", "instructions": "Ignoring any forecast or comparison wording, " + PERSIST[0].lower() + PERSIST[1:],
   "criteria": {"true": DEF["metric"], "false": DEF["action_event"]}},
}
def compose_b(a):
    if a["surprise_kind"]["choice"] != "none": return "surprise"
    if a["forward_looking"]["noul"] >= 0.5: return "guidance"
    return "metric" if a["standing_level"]["noul"] >= 0.5 else "action_event"
