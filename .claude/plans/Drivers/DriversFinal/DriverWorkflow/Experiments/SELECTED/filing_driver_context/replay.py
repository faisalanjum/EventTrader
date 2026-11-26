"""Replay the selected filing experiment from original provider responses, without API calls."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import gzip
import json
from math import ceil
from pathlib import Path
import re
import sqlite3
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "recorded_run.zip"

def require(result, message):
    if not result:
        raise ValueError(message)

def digest(data):
    return sha256(data).hexdigest()

class Record:
    def __init__(self, archive):
        self.archive = archive
        checksums = self.read("checksums.json")
        require(set(archive.namelist()) == set(checksums) | {"checksums.json"}, "Archive inventory changed")
        for name, expected in checksums.items():
            require(digest(archive.read(name)) == expected, f"Changed archived file {name}")
        self.tokens = Counter()

    def read(self, name):
        return json.loads(self.archive.read(name))

    def decisions(self, folder, prefix=""):
        answers = {}
        names = [name for name in self.archive.namelist()
                 if name.startswith(f"{folder}/{prefix}") and name.endswith(".raw.json")]
        for name in names:
            reply = self.read(name)
            request = self.read(name.replace(".raw.json", ".request.json"))
            require(reply["model"] == request["model"] == "pplx-decider-v1.3", "Changed model")
            values = reply["answers"]
            require(values.keys() == request["questions"].keys() and not (answers.keys() & values.keys()), "Missing or duplicate decisions")
            for key, answer in values.items():
                require(answer["choice"] in request["questions"][key]["criteria"], "Unexpected choice")
            answers.update(values)
            self.tokens[folder + ("/" + prefix if prefix else "")] += reply["usage"]["input_tokens"]
        require(bool(names), f"No receipts for {folder}/{prefix}")
        return answers

def issuer_phrases(pieces, width):
    words = defaultdict(list)
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE VIRTUAL TABLE text USING fts5(body, tokenize='unicode61')")
        db.execute("CREATE VIRTUAL TABLE tokens USING fts5vocab(text,instance)")
        db.executemany("INSERT INTO text(rowid,body) VALUES(?,?)", ((int(n), p["text"]) for n,p in pieces.items()))
        for n, word in db.execute("SELECT doc,term FROM tokens ORDER BY doc,offset"):
            words[n].append(word)
    phrases = {n:{tuple(v[i:i+width]) for i in range(len(v)-width+1)} for n,v in words.items()}
    df = Counter(phrase for group in phrases.values() for phrase in group)
    return phrases, df

def replay(record):
    from structure import material
    cfg = record.read("protocol.json")
    source = record.archive.read("inputs/filing.json.gz")
    require(digest(source) == cfg["source_sha256"], "Changed filing index")
    index = json.loads(gzip.decompress(source))
    pcs, edges = index["pieces"], index["source_structure"]["edges"]
    js = range(1, len(cfg["names"])+1)
    first = record.decisions("first")
    require(set(first)=={f"p{n}_d{j}" for n in pcs for j in js}, "First read omitted a pairing")
    coarse = record.decisions("reference", "coarse_")
    fine = record.decisions("reference", "fine_")
    blocks = record.read("inputs/blocks.json")
    require(set(coarse)=={f"b{a}_d{j}" for a,b in blocks for j in js}, "Incomplete second full read")
    expected = set()
    for j in js:
        seeds = {int(n) for n in pcs if first[f"p{n}_d{j}"]["choice"] in {"reports","explains","context"}}
        expected.update(f"p{n}_d{j}" for n in material(pcs,seeds,edges)[1])
        for a,b in blocks:
            p = coarse[f"b{a}_d{j}"]["probabilities"]
            if p["context"]+p["uncertain"] >= p["unrelated"]:
                expected.update(f"p{n}_d{j}" for n in range(a,b+1))
    require(set(fine)==expected, "Second-pass selection differs")
    direct = {j:set() for j in js}
    for key,ans in fine.items():
        n,j = map(int,re.fullmatch(r"p(\d+)_d(\d+)",key).groups())
        if ans["choice"]!="unrelated":
            direct[j].add(n)
    notes = record.read("search/issuer_notes.json")
    roots = {}
    for j,s in direct.items():
        eligible = material(pcs,s,edges)[1]
        roots[j] = eligible.union(*(notes.get(str(n),[]) for n in eligible))
    sealed = record.read("sealed/roots.json")
    require(all(sorted(direct[j])==sealed[str(j)]["selected"] and sorted(roots[j])==sealed[str(j)]["with_companions"] for j in js), "Issuer-note replay differs")

    plan = record.read("links/plan.json")["mapping"]
    routes = defaultdict(list)
    for key, ans in record.decisions("links").items():
        j,n,root,a,b = plan[key[1:]]
        if ans["choice"]=="linked" and n not in roots[j]:
            routes[j,n].append([j,root,a,b])
    qual = record.read("qualify/protocol.json")
    require({k:sorted(v) for k,v in routes.items()}==
            {(j,n):sorted(v) for j,n,v in qual["added_candidates"]}, "Source links differ")
    known = {tuple(qual["question_mapping"][key[1:]]) for key,ans in record.decisions("qualify").items() if ans["choice"]=="direct"}
    bad = {int(j) for j,root in qual["singleton_root"].items() if tuple(root) not in known}
    result = {j:(set() if j in bad else set(roots[j])) for j in js}
    for (j,n),leads in routes.items():
        own = (j,n,0,len(pcs[str(n)]["text"])) in known
        if own or (j not in bad and any(tuple(lead) in known for lead in leads)):
            result[j].update(material(pcs,{n},edges)[0])
    cplan = record.read("chain/protocol.json")["map"]
    for key,ans in record.decisions("chain").items():
        if ans["choice"]=="linked":
            j,n,*_ = cplan[key[1:]]
            result[j].update(material(pcs,{n},edges)[0])
    quotes = record.read("explanation/grounded_quotes.json")
    for cases in quotes["cases"].values():
        for v in cases:
            n,a,b = v["candidate"]
            require(pcs[str(n)]["text"][a:b]==v["candidate_source"] and
                    any(pcs[str(i)]["text"][x:y]==v["basis_source"] for i,x,y in v["basis"]), "Issuer quote mismatch")
    vplan = record.read("verify/protocol.json")["map"]
    yes = {tuple(vplan[key[1:]]) for key,ans in record.decisions("verify").items() if ans["choice"]=="direct"}
    for j,n,axis in yes:
        if axis==0 and (j,n,1) in yes:
            result[j].update(material(pcs,{n},edges)[0])
    require({str(j):sorted(v) for j,v in result.items()}==record.read("verify/delivery.json"), "Disputed evidence replay differs")

    phrases,df = issuer_phrases(pcs,cfg["chosen_word_count"])
    final = {}
    for j,ns in result.items():
        new_sources = ns - roots[j]
        proven = material(pcs,(direct[j] & ns)|new_sources,edges)[0] & ns
        allowed = set(proven)
        for n in ns-proven:
            key = f"p{n}_d{j}"
            second = fine.get(key,{}).get("choice")
            if first[key]["choice"]!="other" or second in {"context","uncertain"}:
                allowed.add(n)
        shared = set().union(*(phrases.get(n,set()) for n in new_sources))
        rare = {v for v in shared if df[v]<=max(2,ceil(.01*len(pcs)))}
        final[j] = allowed | {n for n in ns-allowed if rare & phrases.get(n,set())}
    require({str(j):sorted(v) for j,v in final.items()}==record.read("sealed/selections.json"), "Final packet differs")

    raw_visual = record.read("visual/raw.json")
    visual_input = record.read("visual/inputs.json")
    require(digest(record.archive.read("visual/original_render.pdf"))==visual_input["pdf_sha256"], "Changed sliced PDF")
    question = record.read("visual/request.json")
    require(raw_visual["answers"].keys()==question["questions"].keys(), "Chart response incomplete")
    pictures = {j:[] for j in js}
    for i,img in visual_input["images"].items():
        require(digest(record.archive.read("visual/"+img["file"]))==img["sha256"], "Chart bytes differ")
        for j in js:
            if raw_visual["answers"][f"c{i}_d{j}"]["noul"]>=.5:
                pictures[j].append(img["file"])
    checks = record.read("checks.json")
    groups = {
        "Required context": [any(set(v)<=final[j] for v in alternatives) for j,_,_,alternatives in checks["required"]],
        "Unrelated passages excluded": [n not in final[j] for j,n in checks["unrelated"]],
        "Disputed passages": [(n in final[j])==keep for j,n,keep,_ in checks["disputed"]],
        "Expanded context and relevance": [(c["n"] in final[c["j"]])==c["keep"] for c in checks["expanded"]],
        "Tagged source locations": [bool(set(v["any"])&final[int(j)]) for j,rs in checks["tagged"].items() for v in rs],
        "Chart decisions": [set(pictures[int(j)])==set(c["exact"]) for j,c in checks["visual"].items()]}
    require(all(all(v) for v in groups.values()), "Published source checks differ")
    amounts = sum(record.tokens.values())*Decimal(cfg["first_per_million_usd"])/1000000
    amounts += raw_visual["usage"]["total_input_tokens"]*Decimal(cfg["slice_per_million_usd"])/1000000
    require(amounts==Decimal("0.03976032"), "Original stages' cost differs")
    from replay_phrase_evidence import source_additions
    more, extra_cost = source_additions(record,cfg,pcs,final,direct,roots,phrases,df)
    amounts += extra_cost
    require(amounts==Decimal("0.03986340") <= Decimal(cfg["baseline_usd"]), "Complete cost replay differs")
    exists = lambda j,n: n in final[j] or (j,n) in more
    groups["Unrelated passages excluded"] = [not exists(j,n) for j,n in checks["unrelated"]]
    groups["Disputed passages"] = [exists(j,n)==keep for j,n,keep,_ in checks["disputed"]]
    groups["Expanded context and relevance"] = [exists(c["j"],c["n"])==c["keep"] for c in checks["expanded"]]
    require(all(all(v) for v in groups.values()), "Supplement changed original controls")
    audit = json.loads((HERE / "followup_checks.json").read_text())
    require(audit["filing_sha256"] == cfg["source_sha256"], "Follow-up audit belongs to a different filing")
    for check in audit["checks"]:
        j, n, quote = check["driver"], check["piece"], check["quote"]
        raw = pcs[str(n)]["text"]
        require(quote in raw and (n in final[j])==check["recorded_in_original"], "Original follow-up source differs")
        found = n in final[j] or any(quote in raw[s["a"]:s["b"]] for s in more.get((j,n),{}).get("spans",[]))
        require(found == check["selected_now"], "Retained excerpt differs from the recorded audit")
        label = check.get("group") or ("Later required source details" if check["keep"] else "Later unrelated details excluded")
        groups.setdefault(label, []).append(found == check["keep"])
    originals = {}
    results = []
    for j,name in enumerate(cfg["names"],1):
        lines = []
        for n in sorted(final[j] | {n for driver,n in more if driver==j}):
            p = pcs[str(n)]
            if p["file"] not in originals:
                originals[p["file"]]=record.archive.read("originals/"+p["file"])
            a,b=p["bytes"]
            require(digest(originals[p["file"]][a:b])==p["sha256_bytes"], "Original source byte mismatch")
            evidence = {"passage":n, **{k:p[k] for k in ("file","bytes","sha256_bytes","kind","text")}}
            supplement = more.get((j,n))
            if supplement:
                spans = [dict(s,text=p["text"][s["a"]:s["b"]]) for s in supplement["spans"]]
                evidence.update(text="\n".join(s["text"] for s in spans),excerpts=spans,
                                referenced_originals=supplement["roots"])
            lines.append(evidence)
        results.append({"driver":name,"passages":lines,"original_images":pictures[j]})
    return {"source":cfg["source"],"measured_api_usd":str(amounts),"checks":{k:[sum(v),len(v)] for k,v in groups.items()},"drivers":results}

def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--driver", action="append", help="Display a recorded driver; repeat for multiple names.")
    args.add_argument("--json", action="store_true", help="Return the original passages, source locations and charts as JSON.")
    options=args.parse_args()
    sys.path.insert(0,str(ARCHIVE)+"/code")
    with ZipFile(ARCHIVE) as archive:
        result=replay(Record(archive))
    if options.driver:
        wanted = set(options.driver)
        missing = wanted - {d["driver"] for d in result["drivers"]}
        if missing:
            args.error("Names outside this recorded run: "+", ".join(sorted(missing)))
        result["drivers"] = [d for d in result["drivers"] if d["driver"] in wanted]
    if options.json:
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    for d in result["drivers"]:
        print(f'{d["driver"]} ({len(d["passages"])} passages)')
        if options.driver:
            for p in d["passages"]:
                print(f'\n[{p["passage"]}] {p["file"]} · bytes {p["bytes"][0]}–{p["bytes"][1]}\n{p["text"]}')
    print("\n"+", ".join(f"{k} {got}/{total}" for k,(got,total) in result["checks"].items()))
    print("Recorded API cost — US$"+result["measured_api_usd"])

if __name__=="__main__":
    main()
