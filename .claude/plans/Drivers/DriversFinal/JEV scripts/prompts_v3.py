"""v3: rewritten prompts (rule-by-rule, TypeSafe-doc style) on cleanly formatted input.
Pattern C = one Choice, rewritten.  Pattern D = five one-rule Noul questions composed in code in the rules' order.
Every sentence in a prompt traces to a rule in DRIVER_RULES_Categorized.md (1.5 locked wording, 1.6, 2.30). No example is taken from the test data."""
import json, os, sys, time, collections, statistics, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

OUT = os.path.dirname(os.path.abspath(__file__))
PRICE = 0.042 / 1e6
AUDIT = "--audit" in sys.argv
READ = "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."

# ---------------- Pattern D: one rule per question (Noul, high = yes) ----------------
QD = {
 "company_outlook": {"type": "noul",
   "instructions": {"question": "Does `quote` give the company's own forward-looking outlook, forecast, target, plan or expectation for a future period?",
                    "read": READ},
   "criteria": {
     "true": {"what": "The company itself says what it expects, anticipates, targets or plans to happen in a period that has not ended yet, or gives a forecast range or estimate for such a period. A table row counts when its table or section is an outlook, guidance, forecast or estimate."},
     "false": {"what": "It reports what already happened or what is true now, or states a condition that continues, or it is a forecast made by someone other than the company."}}},
 "standing_level": {"type": "noul",
   "instructions": {"question": "Is what `quote` describes a standing variable that can be read again over time?", "read": READ},
   "criteria": {
     "true": {"what": "A number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand, that stays in place between events and could be read again later."},
     "false": {"what": "A single thing that happened at one point in time, so nothing stands to be read again between events, such as a decision, transaction, incident, approval or one-off charge."}}},
 "discrete_event": {"type": "noul",
   "instructions": {"question": "Is what `quote` describes a discrete thing that happened: a decision, transaction, incident, approval or one-off charge?", "read": READ},
   "criteria": {
     "true": {"what": "A single thing that happened at one point in time: a decision, transaction, incident, approval or one-off charge."},
     "false": {"what": "A standing variable or condition that continues between events: a number, cost, price, rate, count or ratio, or a condition in force."}}},
 "beats_outside_expectation": {"type": "noul",
   "instructions": {"question": "Does `quote` compare a company value with what analysts or other outside parties expected, such as the analyst consensus?", "read": READ},
   "criteria": {
     "true": {"what": "A reported actual result, or a company forecast, is compared with an expectation held by another party, such as the analyst consensus or the Street."},
     "false": {"what": "No comparison with an outside party's expectation.",
               "not_for": "A comparison with the prior period's actual, or a new forecast compared with the company's own earlier forecast."}}},
 "beats_own_forecast": {"type": "noul",
   "instructions": {"question": "Does `quote` compare a reported actual result with the company's own earlier forecast for that period?", "read": READ},
   "criteria": {
     "true": {"what": "A delivered result is compared with what the company itself forecast or guided earlier for the same period."},
     "false": {"what": "No comparison of an actual with the company's own earlier forecast.",
               "not_for": "A comparison with the prior period's actual, or a new forecast compared with the company's own earlier forecast."}}},
}

# ---------------- Pattern C: one Choice, criteria aligned with the instruction ----------------
QC = {"fact_type": {"type": "choice",
  "instructions": {"question": "Which kind of fact does `quote` state?", "read": READ,
                   "order": "A statement that compares with an outside expectation is a surprise. Otherwise a statement of the company's own forward outlook is guidance, even when it contains a number, a rate or a table row. Otherwise it is a metric if it describes a standing variable, or an action_event if it describes a single thing that happened."},
  "criteria": {
    "surprise": {"what": "A company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus or the Street), or an actual compared with the company's own earlier forecast.",
                 "not_for": "A comparison with the prior period's actual, or a new forecast compared with the company's own earlier forecast."},
    "guidance": {"what": "The company's own forward outlook, target or forecast for a future period, including a forecast range or estimate. Outlook verbs such as expect, anticipate, target and plan to make a statement guidance. A table row counts when its table or section is an outlook, guidance, forecast or estimate.",
                 "not_for": "Something that already happened or is true now."},
    "metric": {"what": "A standing variable that can be read again over time: a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand.",
               "not_for": "A forecast (that is guidance) or a single thing that happened (that is an action_event)."},
    "action_event": {"what": "A discrete thing that happened: a decision, transaction, incident, approval or one-off charge.",
                     "not_for": "A standing variable or condition, or a forecast."}}}}

def compose_d(a):
    p = {k: v["noul"] for k, v in a.items()}
    if p["beats_outside_expectation"] >= 0.5 or p["beats_own_forecast"] >= 0.5: return "surprise", False
    if p["company_outlook"] >= 0.5: return "guidance", False
    m, e = p["standing_level"], p["discrete_event"]
    if m >= 0.5 and e < 0.5: return "metric", False
    if e >= 0.5 and m < 0.5: return "action_event", False
    return ("metric" if m >= e else "action_event"), True      # both/neither: pick the higher one but flag as uncertain (rule 2.30)

KEY = dict(l.strip().split("=", 1) for l in open("/home/faisal/EventMarketDB/.env") if l.startswith("TYPESAFE_API_KEY="))["TYPESAFE_API_KEY"].strip("'\"")
def call(state, qs):
    body = json.dumps({"state": state, "model": "jev-1.13.0", "questions": qs}).encode()
    for k in range(6):
        try:
            req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", body, {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 ** k); continue
            return {"error": f"HTTP {e.code} {e.read()[:200]}"}
        except Exception: time.sleep(1 + k)
    return {"error": "failed"}

