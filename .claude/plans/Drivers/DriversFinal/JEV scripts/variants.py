import json,copy
QC4=json.load(open('QC4.json'))['fact_type']
def base(): return copy.deepcopy(QC4)
# V0 = the final prompt from last round (unchanged).
def v0(): return base()
# V1 = V0 + the question is asked about the named driver (rules type a fact per Driver: 1.7, 2.31, 7.7). Nothing else changes.
def v1():
    q=base(); q['instructions']['question']="Which kind of fact does `quote` state about the driver `driver_name`?"; return q
# V2a = V1 + clarifications that do NOT conflict with any rule wording (proposed interpretations).
def v2a():
    q=v1(); c=q['criteria']
    c['guidance']['what']=("The company's own forward outlook, target or forecast for a future period, including a forecast range or estimate "
        "and an assumption the company states for its forecast. Outlook verbs such as expect, anticipate, target and plan to make a statement guidance. "
        "A table row counts when its table or section is an outlook, guidance, forecast or estimate.")
    c['metric']['what']=("A standing variable that can be read again over time: a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand. "
        "A figure that a company reports for each period (revenue, an expense, income, a cash flow, a balance) is such a variable, even when the sentence describes it with a verb like recorded, increased or decreased. "
        "A total, count or amount measured for a period is such a variable even when it is made up of transactions. "
        "A method, policy or arrangement that is already in use and continues is a condition in force, not the moment it was created. "
        "A standing per-unit level is a metric.")
    c['action_event']['what']=("A discrete thing that happened: a decision, transaction, incident, approval or one-off charge. "
        "An incident counts even when the quote also states its effect on a result. "
        "A one-time decision to start, change or suspend a policy is an action_event.")
    c['action_event']['not_for']=("A standing variable or condition, or a forecast. A figure reported for each period is not an action_event just because the sentence uses a verb like recorded or increased. "
        "A continuing condition or a measured severity is a metric.")
    q['instructions']['read']+=" When two drivers cover one topic, the driver name tells which fact is meant: a driver named for a per-unit amount is a metric; a driver named for the decision or event is an action_event."
    return q
# V2b = V2a + the proposed clarification that touches rule 1.6 (needs owner approval): the verbs do not decide alone.
def v2b():
    q=v2a(); c=q['criteria']
    q['instructions']['order']=("A statement that compares with an outside expectation is a surprise. Otherwise a forecast of a measured quantity or condition is guidance, even when it contains a number, a rate or a table row. "
        "Otherwise it is a metric if it describes a standing variable, or an action_event if it describes a single thing that happened.")
    c['guidance']['what']=("A forecast, expectation or stated assumption about how a measured quantity or condition will be in a future period, including a forecast range or estimate. "
        "The words expect, anticipate, target, plan and will do not decide the type by themselves: what matters is whether the statement forecasts a measurement or condition. "
        "A table row counts when its table or section is an outlook, guidance, forecast or estimate.")
    c['guidance']['not_for']="Something that already happened or is true now, or an announced, committed or scheduled action (that is an action_event)."
    c['action_event']['what']+=" An announced, committed or scheduled action stays an action_event even when it happens later."
    return q
# mixed-claim detector (one extra yes/no; asked on every item)
QM={"mixed_claims":{"type":"noul",
 "instructions":{"question":"Does `quote` state two or more separate claims that would need different kinds of fact?",
   "read":"Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them only to see what `quote` refers to."},
 "criteria":{"true":{"what":"The quote joins separate claims, for example a statement about something reported or already true together with a statement about the future."},
             "false":{"what":"The quote makes one claim."}}}}
# V3 = V2b + two clauses aimed at the two remaining real errors (rule 4.6 for the first; contract schedules for the second).
def v3():
    q=v2b(); c=q['criteria']
    c['guidance']['what']+=" A clause inside a forecast sentence that states an expected change in a measured quantity belongs to the forecast."
    c['guidance']['not_for']="Something that already happened or is true now, or an announced, committed or scheduled action (that is an action_event), or an amount already owed or committed under a contract (that is a metric)."
    c['metric']['what']+=" An amount already owed or committed under a contract, including a schedule of such amounts, is such a variable, not a forecast."
    return q
# V4 = V2b re-worded to follow the second reviewer: classify the specific claim; the name never decides alone;
# pay change = metric; rate used in the company's own method = metric; agreement in force = metric, work underway = action;
# per-share amount = metric and the declaring decision = separate action; milestone = action, count of what exists = metric.
NAME_RULE=" When two drivers cover one topic, the driver name tells which fact is meant: a driver named for a per-unit amount is a metric; a driver named for the decision or event is an action_event."
def v4():
    q=v2b()
    q['instructions']['read']=q['instructions']['read'].replace(NAME_RULE,"")
    q['instructions']['read']=("Judge the specific claim `quote` makes about the driver, not merely its verb, its number or its date. "
        "`text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. "
        "The driver name shows which claim is meant, but the quote and its context must support the answer: the name alone never decides it.")
    c=q['criteria']
    c['metric']['what']+=(" A change in a level, such as a pay increase, is a metric even when it takes effect on a stated date. "
        "A rate or assumption the company uses in its own current method or calculation is a condition in force; the word projected alone does not make it a forecast. "
        "When one sentence states both a standing per-unit amount and the decision that set it, the amount is a metric and the decision is a separate action_event.")
    c['action_event']['what']+=(" A negotiation or implementation that is still underway is an action_event that continues. "
        "A milestone, such as a delivery or entry into service, is an action_event; a count of what exists now is a metric.")
    return q
# V2bN = V2b with the driver name hidden (state without driver_name, question without the driver): does the name decide anything?
def v2bN():
    q=v2b(); q['instructions']['question']="Which kind of fact does `quote` state?"
    q['instructions']['read']=q['instructions']['read'].replace(NAME_RULE,""); return q
# V5 = V4 with the locked words "the company's own" restored in the guidance definition (V2b/V4 had dropped them by mistake).
def v5():
    q=v4(); c=q['criteria']
    q['instructions']['order']=q['instructions']['order'].replace("Otherwise a forecast of a measured quantity or condition is guidance","Otherwise the company's own forecast of a measured quantity or condition is guidance")
    assert "company's own forecast of a measured" in q['instructions']['order']
    c['guidance']['what']=c['guidance']['what'].replace("A forecast, expectation or stated assumption about how","The company's own forecast, expectation or stated assumption about how")
    assert c['guidance']['what'].startswith("The company's own")
    c['guidance']['not_for']="Something that already happened or is true now, a forecast made by someone other than the company, or an announced, committed or scheduled action (that is an action_event)."
    return q
# V6 = V5 + rule 1.7 restated so the name only picks between two claims the quote actually states (the name never decides alone).
def v6():
    q=v5()
    q['instructions']['read']+=(" When two drivers cover one topic, one named for a per-unit amount and one for the decision or event, "
        "a quote that states the amount is a metric for the first, and a quote that states the decision is an action_event for the second.")
    return q
VARS={'V0':v0,'V1':v1,'V2a':v2a,'V2b':v2b,'V3':v3,'V4':v4,'V2bN':v2bN,'V5':v5,'V6':v6}
if __name__=="__main__":
    pass
    for name in ('V2a','V2b'):
        q=VARS[name](); print(f"===== {name} =====\nQUESTION:",q['instructions']['question']); print("READ:",q['instructions']['read']); print("ORDER:",q['instructions']['order'])
        for k,v in q['criteria'].items(): print(f"[{k}] what: {v['what']}\n         not_for: {v['not_for']}")
