#!/usr/bin/env python3
"""
dump_bigdata_taxonomy.py — pull the FULL current RavenPack/Bigdata.com event taxonomy to CSV.

WHY THIS EXISTS
---------------
The complete ~7,400-category RavenPack taxonomy is NOT published anywhere free — it lives only behind
WRDS (university login) or the RavenPack/Bigdata API. This script needs ONE credential, then walks the
live taxonomy EXHAUSTIVELY (the API has no "list-all" call, so we do a breadth-first search seeded with
every group/category we already recovered, then expand on every new topic name until nothing new
appears) and writes every topic with its full TOPIC,GROUP,TYPE,SUB_TYPE path.

SETUP
-----
    pip install bigdata-client
    # TRIAL accounts log in with email+password (NO API key needed) — BUT Google-SSO accounts have no
    # password, so use an API key from Bigdata.com -> Settings -> API Keys instead:
    export BIGDATA_API_KEY='your-api-key'
    #   (or, for password accounts:  export BIGDATA_USERNAME=... ; export BIGDATA_PASSWORD=... )
    python3 dump_bigdata_taxonomy.py

OUTPUT
------
    bigdata_taxonomy_full.csv   (topic,group,type,sub_type,id,name,description)
    Prints the distinct count as it converges. Re-run is idempotent.
"""
import os, csv, sys, time, glob, re

try:
    from bigdata_client import Bigdata
except ImportError:
    sys.exit("pip install bigdata-client  first")

# ---------- auth ----------
if os.environ.get("BIGDATA_API_KEY"):
    bd = Bigdata(api_key=os.environ["BIGDATA_API_KEY"])
elif os.environ.get("BIGDATA_USERNAME"):
    bd = Bigdata(os.environ["BIGDATA_USERNAME"], os.environ["BIGDATA_PASSWORD"])
else:
    sys.exit("Set BIGDATA_API_KEY (Settings->API Keys) or BIGDATA_USERNAME/BIGDATA_PASSWORD first.")

# ---------- build a wide seed set from everything already recovered ----------
HERE = os.path.dirname(os.path.abspath(__file__))
seeds = set()

# (a) all category + group + type words from the recovered CSVs (split hyphenated slugs into words)
for csv_path in glob.glob(os.path.join(HERE, "*.csv")):
    try:
        with open(csv_path, newline="") as f:
            for row in csv.reader(f):
                for cell in row:
                    cell = cell.strip().lower()
                    if not cell or cell in ("topic", "group", "type", "sub_type", "category"):
                        continue
                    seeds.add(cell.replace("-", " "))
                    for w in re.split(r"[-,]", cell):
                        if len(w) > 2:
                            seeds.add(w)
    except Exception:
        pass

# (b) a broad finance/event vocabulary so we hit groups not present in the seed CSVs
seeds.update("""
acquisition merger takeover divestiture spinoff buyback dividend earnings revenue guidance ebitda
margin analyst rating upgrade downgrade price target lawsuit litigation settlement fraud antitrust
investigation regulatory approval recall product clinical trial fda patent layoffs hiring executive
ceo resignation appointment strike union credit rating default debt bond loan ipo offering insider
ownership stake short interest stock split delisting bankruptcy restructuring impairment capex buyout
joint venture partnership sanction tariff export import supply demand market share contract award
cyber attack data breach accident fire outage esg emissions pollution donation sponsorship gdp
inflation cpi ppi interest rate employment recession election conflict war terrorism commodity oil
gold currency crypto coverage initiated reputation crime civil unrest natural disaster foreign
exchange consumption exploration drilling refinery harvest housing retail sales consumer confidence
monetary policy central bank treasury yield trade balance industrial accident corruption bribery
discrimination governance human rights labor conditions board director audit covenant
""".split())

# ---------- breadth-first crawl ----------
rows = {}        # topic_id (comma path) -> (name, description)
seen_query = set()
queue = list(seeds)
calls = 0
MAX_CALLS = 20000   # safety cap

def query(term):
    global calls
    if term in seen_query:
        return []
    seen_query.add(term)
    calls += 1
    try:
        return bd.knowledge_graph.find_topics(term, limit=50)
    except Exception as e:
        print(f"  ! {term!r}: {e}", file=sys.stderr)
        return []

i = 0
while queue and calls < MAX_CALLS:
    term = queue.pop(0)
    before = len(rows)
    for t in query(term):
        tid = t.id
        if tid not in rows:
            rows[tid] = (getattr(t, "name", ""), getattr(t, "description", "") or "")
            # expand: re-query on the human name + the leaf token of the path (BFS)
            nm = (getattr(t, "name", "") or "").strip().lower()
            if nm and nm not in seen_query:
                queue.append(nm)
            leaf = [p for p in tid.split(",") if p]
            if leaf:
                lt = leaf[-1].replace("-", " ")
                if lt not in seen_query:
                    queue.append(lt)
    i += 1
    if i % 25 == 0 or len(rows) != before:
        print(f"[calls {calls} | queue {len(queue)}] distinct topics: {len(rows)}")
    time.sleep(0.15)

# ---------- write ----------
out = os.path.join(HERE, "bigdata_taxonomy_full.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["topic", "group", "type", "sub_type", "id", "name", "description"])
    for tid in sorted(rows):
        parts = (tid.split(",") + ["", "", "", ""])[:4]
        name, desc = rows[tid]
        w.writerow([parts[0], parts[1], parts[2], parts[3], tid, name, desc])

print(f"\nDONE: {len(rows)} distinct topics ({calls} API calls) -> {out}")
print("If the count is still climbing near MAX_CALLS, raise MAX_CALLS and re-run (idempotent).")
