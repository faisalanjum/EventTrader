"""Claim-checker v2 items (JEV.md §6.5): the SAME fact-type items and the SAME real mistakes as v1, with only the claim wording changed
(type_claim_v2). Designed after reading v1's DEV misses only; the other sets are the fresh check.
Usage: python3 build_claims_v2.py  -> items_claims_v2.json (hash printed)"""
import json, hashlib
from claim_prompts import type_claim_v2
items = [i for i in json.load(open("items_claims.json")) + json.load(open("items_claims_real.json")) if i["L_task"] == "type"]
for i in items:
    assert i["state"]["claim"].startswith("The fact about")
    i["state"]["claim"] = type_claim_v2(i["state"]["driver_name"], i["L_claimed"])
    assert "quote" in i["state"] and "claim" in i["state"]
json.dump(items, open("items_claims_v2.json", "w"), indent=1)
blob = json.dumps([[i["id"], i["state"]["claim"], i["L_true"]] for i in items], sort_keys=True)
print("items", len(items), "| hash", hashlib.sha256(blob.encode()).hexdigest()[:16])
