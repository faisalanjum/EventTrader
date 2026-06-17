#!/usr/bin/env python3
"""
merge_taxonomy_sources.py — build the assembled RavenPack/Bigdata event-taxonomy union from all FREE,
no-credential public sources we have recovered, and (optionally) fold in new candidate files.

WHY: the complete current taxonomy (~7,400 / "more than 7,000" categories, per docs.bigdata.com) is
RavenPack paid IP — no complete free copy exists (verified by an exhaustive multi-channel hunt 2026-06-17:
GitHub/Gitee/CSDN, WRDS, Nasdaq/Quandl, DoltHub/data.world/Socrata, HF/Kaggle, academic appendices, web
dorks, Wayback, the live API). The live autosuggest/find_topics endpoint is credential-gated (HTTP 401,
SDK = password/key only — no anonymous path). So we assemble the maximal FREE union from public scraps.

LOCAL SOURCES (all free, no auth, verified genuine):
  legacy leaf slugs:
    - RavenPack_categories.csv      col `category`           (381; PLOS One pone.0296927 S4-S6 + cross-checks)
    - etda7728_appendixB_categories.txt  bare hyphen lines   (261; Penn State ETDA #7728 App.B via Wayback)
  modern compound topic IDs (topic,group,type,sub_type,):
    - bigdata_docs_topic_paths.csv  4-col -> compound        (128; crawled docs.bigdata.com)
    - bigdata_cookbook_topic_ids.txt  compound lines         (519; Bigdata-com/bigdata-cookbook API outputs)

USAGE
    python3 merge_taxonomy_sources.py [EXTRA_FILE ...]
Outputs (next to this script):
    bigdata_taxonomy_assembled.csv   (kind,topic,group,type,sub_type,id_or_slug)  — combined union
    taxonomy_CURRENT_modern.csv      (529 current Bigdata.com compound IDs — the live ~7,400-era taxonomy)
    taxonomy_LEGACY_rpa.csv          (441 legacy RPA 1.0 single-slug leaf categories — older naming)
  ^ the two split files keep CURRENT vs LEGACY cleanly segregated to avoid any confusion.
Any EXTRA_FILE is scanned with regex extraction and folded in (modern compound IDs + RPA-suffix slugs).
"""
import os, re, csv, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
TOTAL_TARGET = 7400

TOPICS = r"(?:business|society|politics|economy|economics|environment|markets|market|technology|geopolitics)"
COMPOUND_RE = re.compile(rf"\b{TOPICS}(?:,[a-z0-9][a-z0-9-]*)" + r"{1,4},{0,3}")
SLUG_RE = re.compile(r"\b[a-z][a-z0-9]+(?:-[a-z0-9]+){1,6}\b")
RPA_SUFFIXES = (
    "above-expectations", "below-expectations", "meet-expectations", "-up", "-down", "-positive", "-negative",
    "-completed", "-failed", "-terminated", "-suspended", "-rumor", "-withdrawn", "-denied", "-recall",
    "-acquiree", "-acquirer", "-defendant", "-plaintiff", "-upgrade", "-downgrade", "-increase", "-decrease",
    "-set", "-start", "-filed", "-granted", "-rejected", "-approval", "-investigation", "-guidance",
)


def norm_compound(s):
    s = s.strip().rstrip(",")
    parts = (s.split(",") + ["", "", "", ""])[:4]
    return ",".join(parts) + ","


def read_legacy_csv_col(path, col="category"):
    out = set()
    if os.path.exists(path):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if row.get(col):
                    out.add(row[col].strip())
    return out


def read_modern_csv4(path):
    out = set()
    if os.path.exists(path):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                out.add(norm_compound(f"{row.get('topic','')},{row.get('group','')},{row.get('type','')},{row.get('sub_type','')}"))
    return out


def read_slug_lines(path):
    out = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="ignore") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#") and re.fullmatch(r"[a-z0-9][a-z0-9-]+", ln):
                    out.add(ln)
    return out


def read_compound_lines(path):
    out = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="ignore") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#") and COMPOUND_RE.fullmatch(ln.rstrip(",") + ","):
                    out.add(norm_compound(ln))
    return out


def extract_any(text):
    compound = {norm_compound(m.group(0)) for m in COMPOUND_RE.finditer(text)}
    compound = {c for c in compound if len([x for x in c.split(",") if x]) >= 2}
    slugs = set()
    for m in SLUG_RE.finditer(text):
        w = m.group(0)
        if any(w.endswith(suf) or (suf.startswith("-") and suf[1:] in w) for suf in RPA_SUFFIXES):
            slugs.add(w)
    blob = "|".join(compound)
    slugs = {w for w in slugs if w not in blob}
    return compound, slugs


def main():
    legacy = read_legacy_csv_col(os.path.join(HERE, "RavenPack_categories.csv")) | read_slug_lines(os.path.join(HERE, "etda7728_appendixB_categories.txt"))
    modern = read_modern_csv4(os.path.join(HERE, "bigdata_docs_topic_paths.csv")) | read_compound_lines(os.path.join(HERE, "bigdata_cookbook_topic_ids.txt"))
    print(f"LOCAL SOURCES -> {len(legacy)} legacy slugs + {len(modern)} modern paths = {len(legacy)+len(modern)}")

    extra = []
    for a in sys.argv[1:]:
        extra.extend(glob.glob(a) or [a])
    for path in extra:
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except Exception as e:
            print(f"  ! {path}: {e}"); continue
        c, s = extract_any(text)
        am, al = (c - modern), (s - legacy)
        modern |= c; legacy |= s
        print(f"  + {os.path.basename(path):42s} +{len(am):4d} modern  +{len(al):4d} legacy")

    allm, alll = sorted(modern), sorted(legacy)
    # (1) combined union (kind column segregates the two vintages)
    outp = os.path.join(HERE, "bigdata_taxonomy_assembled.csv")
    with open(outp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "topic", "group", "type", "sub_type", "id_or_slug"])
        for c in allm:
            p = (c.split(",") + ["", "", "", ""])[:4]
            w.writerow(["modern", p[0], p[1], p[2], p[3], c])
        for s in alll:
            w.writerow(["legacy", "", "", "", "", s])
    # (2) CURRENT (modern Bigdata.com) — the live ~7,400-era taxonomy, compound-ID form
    cur = os.path.join(HERE, "taxonomy_CURRENT_modern.csv")
    with open(cur, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vintage", "topic", "group", "type", "sub_type", "compound_id"])
        for c in allm:
            p = (c.split(",") + ["", "", "", ""])[:4]
            w.writerow(["CURRENT-bigdata", p[0], p[1], p[2], p[3], c])
    # (3) LEGACY (RPA 1.0 naming) — older single-slug leaf categories
    leg = os.path.join(HERE, "taxonomy_LEGACY_rpa.csv")
    with open(leg, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vintage", "leaf_slug"])
        for s in alll:
            w.writerow(["LEGACY-rpa1.0", s])
    total = len(allm) + len(alll)
    # group breadth across modern paths
    groups = {c.split(",")[1] for c in allm if len(c.split(",")) > 1 and c.split(",")[1]}
    print(f"\nASSEMBLED union: {len(alll)} legacy + {len(allm)} modern = {total}  ({100*total/TOTAL_TARGET:.1f}% of ~{TOTAL_TARGET})")
    print(f"  modern groups covered: {len(groups)}")
    print(f"  -> {outp}  (combined, kind column)")
    print(f"  -> {cur}  ({len(allm)} CURRENT/modern)")
    print(f"  -> {leg}  ({len(alll)} LEGACY/rpa)")


if __name__ == "__main__":
    main()
