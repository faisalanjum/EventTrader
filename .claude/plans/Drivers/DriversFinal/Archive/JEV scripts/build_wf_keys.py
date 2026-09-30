"""Workflow steps 3 and 6 on the 50 fresh facts of the tag hold-out (JEV.md §6.8). Claude's blind answer key (type M/G/S/A, or U = ruling-dependent, left out;
metric state; a neutral driver name that carries no type or state word), written by reading the units BEFORE any Jev call, then frozen with a hash.
Numbers = the order in which build_tag_holdout's facts (label F) appear in tag_holdout.json. Usage: python3 build_wf_keys.py"""
import json, hashlib
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
H = json.load(open(f"{SCRATCH}/tag_holdout.json")); L = json.load(open("tag_holdout_labels.json"))["labels"]
FACTS = [h["id"] for h in H if L[h["id"]] == "F"]; assert len(FACTS) == 50
# n: (type, state or None, driver name)
K = {1:("M","increased","passenger revenues"), 2:("A",None,"CereLink ICP Monitor System"), 3:("M","reported","royalties payable under license agreements"),
 4:("U",None,"insurance receivables"), 5:("M",None,"related-party accounts receivable"), 6:("M","increased","total lease cost"),
 7:("M","reported","loan valuation input, indicative quotes"), 8:("U",None,"cost savings actions"), 9:("M","reported","other intangible assets"),
 10:("M","decreased","Propulsion segment sales"), 11:("M",None,"energy use of the portfolio"), 12:("G",None,"Adjusted EBITDA"), 13:("U",None,"global supply chain centers"),
 14:("U",None,"net cost savings"), 15:("M",None,"total revenue"), 16:("M","decreased","net income attributable to Teledyne"),
 17:("M","decreased","net income (loss) attributable to AeroVironment"), 18:("U",None,"legal settlement gains"), 19:("A",None,"Fanatics partnership"),
 20:("G",None,"revenue synergies"), 21:("A",None,"Shutterstock and Getty Images merger review"), 22:("M","increased","interest expense pro forma adjustment"),
 23:("G",None,"bariatrics and Asia headwinds"), 24:("M","increased","earnings per diluted share"), 25:("M","reported","cash balance"),
 26:("G",None,"free cash flow"), 27:("G",None,"tariff cost impact"), 28:("M",None,"Americas volume"), 29:("U",None,"ending inventories"),
 30:("M","decreased","international segment operating profit"), 31:("U",None,"content packs"), 32:("M","increased","customers using two or more products"),
 33:("M",None,"MG Asia AOI margin"), 34:("M","increased","remote steps completed by customers"), 35:("M","decreased","MacroGEM total revenue"),
 36:("M","reported","organizations building Blueprints"), 37:("A",None,"Azar expansion into the U.S."), 38:("G",None,"promotional velocity"),
 39:("U",None,"cost savings"), 40:("G",None,"market conditions in the first quarter"), 41:("S",None,"vehicle units"), 42:("S",None,"quarterly revenue"),
 43:("A",None,"GameStop equity offering"), 44:("M","decreased","Tesla Model Y and Model 3 prices"), 45:("G",None,"Cytokinetics marketing application"),
 46:("A",None,"SABERHUNT prototype kit"), 47:("M","decreased","Westlake top-line earnings"), 48:("M","reported","Zoom return on assets"),
 49:("S",None,"quarterly EPS"), 50:("M","increased","Intellia top-line earnings")}
assert sorted(K) == list(range(1, 51))
keys = {FACTS[n-1]: {"n": n, "type": t, "state": s, "name": nm} for n, (t, s, nm) in K.items()}
blob = json.dumps(keys, sort_keys=True); h = hashlib.sha256(blob.encode()).hexdigest()[:16]
json.dump({"hash": h, "keys": keys}, open("wf_keys.json", "w"), indent=1)
import collections
print("hash", h, "| types", dict(collections.Counter(v["type"] for v in keys.values())), "| states", dict(collections.Counter(v["state"] for v in keys.values() if v["state"])))
