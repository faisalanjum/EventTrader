"""Claim checker (JEV.md §6.5): does `quote` support a claim someone wrote about it?
Recipe: Jev docs `citation_check` (one Choice: supports / contradicts / says_nothing).
Claim wording comes from the rules: fact type = 1.5 locked wording + the table in 2a; metric state = the rows of rule 3.6.
No example is taken from the test data. Rule 8.2: the checker sees only the claim and the source evidence,
never the reader's reasoning, an earlier verdict or a score."""

READ = ("Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them only to see "
        "what `quote` refers to, including any heading or table title.")

CHECK = {"verdict": {"type": "choice",
  "instructions": {"question": "Does `quote` support `claim`?", "read": READ},
  "criteria": {
    "supports": {"what": "`quote` states the claim or directly implies that it is true."},
    "contradicts": {"what": "`quote` states the opposite of the claim or implies that it is false."},
    "says_nothing": {"what": "`quote` does not address what the claim asserts, either way."}}}}

TYPES = ["metric", "guidance", "surprise", "action_event"]
TYPE_DEF = {
 "metric": "a standing variable readable again over time (a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand), not only a number",
 "guidance": "the company's own forward outlook, target or forecast",
 "surprise": "a company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus or the Street, or for an actual the company's own prior guide)",
 "action_event": "a discrete thing that happened (a decision, transaction, incident, approval or one-off charge)"}

def type_claim(name, t):
    art = "an" if t[0] in "aeiou" else "a"
    return f"The fact about {name} is {art} {t} fact: {TYPE_DEF[t]}."

STATES = ["increased", "decreased", "unchanged", "persists", "reported"]
STATE_DEF = {   # rule 3.6, first matching row wins
 "increased": "{n} increased (the quote states a direction: up, or gives a value with a lower prior value).",
 "decreased": "{n} decreased (the quote states a direction: down, or gives a value with a higher prior value).",
 "unchanged": "{n} is unchanged (the quote states it is flat).",
 "persists": "{n} persists (the quote says it is ongoing, with no direction).",
 "reported": "{n} is reported as a bare value (the quote gives a value with no direction and no prior value)."}

def state_claim(name, s):
    return STATE_DEF[s].format(n=name)

# ---- v2 wording (JEV.md §6.5): v1 escapes read the definitions literally (a discrete event with an amount = "a number"; a forecast with a
# number = "a standing variable"). v2 adds only two sentences that are already rule text: the persistence test (1.5) and the forecast words (1.6).
PERSIST = "Test: between two events, is there a standing level you could read again?"
FORECAST_WORDS = "Forecast words (expect, anticipate, target, plan to) make a fact guidance, never a metric."
TYPE_DEF_V2 = dict(TYPE_DEF)
TYPE_DEF_V2["metric"] = TYPE_DEF["metric"] + ". " + PERSIST + " Yes means metric. " + FORECAST_WORDS
TYPE_DEF_V2["action_event"] = TYPE_DEF["action_event"] + ". " + PERSIST + " No means action_event."
TYPE_DEF_V2["guidance"] = TYPE_DEF["guidance"] + ". " + FORECAST_WORDS

def type_claim_v2(name, t):
    art = "an" if t[0] in "aeiou" else "a"
    return f"The fact about {name} is {art} {t} fact: {TYPE_DEF_V2[t]}."
