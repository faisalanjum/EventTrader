"""Build the frozen claim-checker items (JEV.md §6.5). Every fact appears as a RIGHT claim (its decided label) and a
WRONG copy (the label swapped for a clearly different one, chosen by a hash of the id, so no AI picks it).
Labels are stored as L_*; the input is `state` (with the claim inside it). Asserted so a label can never overwrite the input.
Usage: python3 build_claims.py   -> items_claims.json (hash printed; record it before any Jev call)"""
import json, hashlib, collections
from claim_prompts import TYPES, STATES, type_claim, state_claim

def h(s): return int(hashlib.sha1(s.encode()).hexdigest(), 16)

def mk(cid, base, claim, true, **lab):
    st = dict(base); st["claim"] = claim
    assert isinstance(st, dict) and "quote" in st and "claim" in st
    return dict(id=cid, state=st, L_true=true, **{"L_" + k: v for k, v in lab.items()})

items = []
# ---- fact type: every decided fact (keys = rules + reviewer rulings, §3.5/§3.11)
fin = [x for x in json.load(open("items_final.json")) + json.load(open("items_extra.json")) if x["key"] in TYPES]
for x in fin:
    n, k = x["state"]["driver_name"], x["key"]
    items.append(mk(f"FT|{x['id']}|R", x["state"], type_claim(n, k), True, task="type", claimed=k, key=k, kind="right"))
    alts = [t for t in TYPES if t != k]; w = alts[h(x["id"]) % 3]
    items.append(mk(f"FT|{x['id']}|W", x["state"], type_claim(n, w), False, task="type", claimed=w, key=k, kind=f"{k}->{w}"))

# ---- metric state: agreed earlier-model labels; all rare states, a fixed hash-ordered sample of the common ones
WRONG = {"increased": ["decreased", "unchanged", "reported"], "decreased": ["increased", "unchanged", "reported"],
         "reported": ["increased", "decreased", "unchanged"], "unchanged": ["increased", "decreased"],
         "persists": ["increased", "decreased", "unchanged"]}
QUOTA = {"persists": 999, "unchanged": 999, "decreased": 60, "reported": 90, "increased": 130}
card = [x for x in json.load(open("card_items.json")) if x["fact_type"] == "metric" and x["L_state_agreed"] and x["L_state"] in STATES]
pick = []
for s, q in QUOTA.items():
    pick += sorted([x for x in card if x["L_state"] == s], key=lambda x: h(x["id"]))[:q]
for x in pick:
    n, k = x["state"]["driver_name"], x["L_state"]
    items.append(mk(f"ST|{x['id']}|R", x["state"], state_claim(n, k), True, task="state", claimed=k, key=k, kind="right"))
    w = WRONG[k][h(x["id"]) % len(WRONG[k])]
    items.append(mk(f"ST|{x['id']}|W", x["state"], state_claim(n, w), False, task="state", claimed=w, key=k, kind=f"{k}->{w}"))

assert len({i["id"] for i in items}) == len(items)
json.dump(items, open("items_claims.json", "w"), indent=1)
blob = json.dumps([[i["id"], i["state"]["claim"], i["L_true"]] for i in items], sort_keys=True)
print("items", len(items), "| hash", hashlib.sha256(blob.encode()).hexdigest()[:16])
print("by task/kind:", collections.Counter((i["L_task"], i["L_true"]) for i in items))
print("wrong kinds:", collections.Counter(i["L_kind"] for i in items if not i["L_true"]).most_common(30))
