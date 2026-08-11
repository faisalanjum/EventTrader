"""Where do REAL filings declare their contexts and units?

The rule comes from the spec (Inline XBRL 1.1 §14.1 / §14.1.1). This measures
what it COSTS — a census can price a rule, never define one. Manifest-bound and
hash-checked; independent of the module under test.
"""
import hashlib, json, os
from lxml import etree

# PATHS ARE DERIVED, NEVER FIXED. A machine path baked into a receipt tool makes
# it run on one checkout and silently point somewhere else on any other. The
# NAMESPACE constants below are different in kind: they are fixed because an
# official standard fixes them, and each cites it.
R = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(R, "..", "..", "..", "..", "..", ".."))
ROOT = os.path.join(_REPO, "scripts", "driver_seed", "relocate_probe",
                    "inline_html_cache")
IX = "http://www.xbrl.org/2013/inlineXBRL"
XBRLI = "http://www.xbrl.org/2003/instance"
P = etree.XMLParser(recover=False, resolve_entities=False, load_dtd=False,
                    no_network=True)

def lawful_containers(root):
    """The ix:resources elements that are DIRECT children of an ix:header.

    Returned as a LIST that the caller keeps alive. An earlier version returned
    a set of `id()` values — and lxml creates element proxies on demand and
    frees them when unreferenced, so those ids belonged to objects that no
    longer existed by the time they were compared. It reported 0 of 732,754
    contexts as lawfully placed, which was a bug in this script, not a fact
    about the corpus.
    """
    return [r for h in root.iter("{%s}header" % IX)
            for r in h if isinstance(r.tag, str) and r.tag == "{%s}resources" % IX]

rows = [ln.split() for ln in
        open(os.path.join(R, "01b_ix_input_manifest.txt"), encoding="utf-8")
        .read().split("\n") if ln.strip()]
tot = {"documents": len(rows), "readable": 0, "unreadable": 0,
       "context_total": 0, "unit_total": 0,
       "context_in_lawful_resources": 0, "unit_in_lawful_resources": 0,
       "context_outside": 0, "unit_outside": 0}
outside_files, unreadable = [], []
for name, want in rows:
    path = os.path.join(ROOT, name)
    raw = open(path, "rb").read()
    if hashlib.sha256(raw).hexdigest() != want:
        raise SystemExit(f"frozen cache drifted: {name}")
    try:
        root = etree.fromstring(raw, P)
    except etree.XMLSyntaxError as e:
        tot["unreadable"] += 1
        unreadable.append({"file": name, "why": str(e).split(",")[0]})
        continue
    tot["readable"] += 1
    containers = lawful_containers(root)          # kept alive for the whole loop
    off = {"context": 0, "unit": 0}
    for kind in ("context", "unit"):
        tag = "{%s}%s" % (XBRLI, kind)
        # counted the way PRODUCTION looks: down from each lawful container
        inside = sum(1 for c in containers for k in c if k.tag == tag)
        total = sum(1 for _ in root.iter(tag))
        tot[f"{kind}_total"] += total
        tot[f"{kind}_in_lawful_resources"] += inside
        tot[f"{kind}_outside"] += total - inside
        off[kind] = total - inside
    if off["context"] or off["unit"]:
        outside_files.append({"file": name, **off})
out = {"question": "do real filings put xbrli:context / xbrli:unit as direct "
                   "children of ix:resources under ix:header?",
       "rule_source": "Inline XBRL 1.1 Recommendation 2013-11-18 §14.1 and "
                      "§14.1.1 — the corpus prices this rule, it does not "
                      "define it",
       **tot,
       "files_with_any_declaration_outside": outside_files[:50],
       "files_with_any_declaration_outside_count": len(outside_files),
       "unreadable_files": unreadable}
json.dump(out, open(os.path.join(R, "19_resource_ancestry_census.json"), "w"),
          indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in out.items()
                  if k != "files_with_any_declaration_outside"},
                 indent=1, sort_keys=True))
