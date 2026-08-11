"""#827 round 9 — do the two-view controls actually CATCH anything?

A green suite proves nothing on its own: a test that asserts a rule can be
satisfied by code that never had the rule. So each named defect is put BACK,
one at a time, and the suite must go red.

HOW, and why this way: every mutation is applied IN MEMORY, in a fresh
subprocess, before pytest imports anything. No file is edited — this repository
is under an audit freeze, and a mutation harness that writes to the tree can
leave it dirty if it dies half way. The rc is therefore a real pytest exit
status, not a simulated one.

EACH MUTATION IS SCORED TWICE:
  * MUTATED  -> pytest must exit 1. If it exits 0 the control does not bind and
                the claim it makes is worthless.
  * CONTROL  -> the same command with no mutation must exit 0. If it does not,
                the mutation proved nothing about the rule; it only proved the
                suite was already red.
Both halves must hold or the group is void.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
OUT = os.path.join(_HERE, "17_two_view_mutations.json")
#: THE PUBLIC SUITES these mutations are scored against. A mutation whose
#: tests live outside this list selects nothing — which the rc-5 guard
#: below turns into an ERROR rather than a verdict.
SUITES = ["driver/relocation/test_two_view_bridge.py",
          "driver/core/test_dimension_identity_at_the_door.py"]

#: name -> (what defect is re-introduced, the patch, the tests that must catch it)
MUTATIONS = [
    ("recovery_parsing",
     "the strict parse RECOVERS instead of refusing, so a document nobody "
     "wrote is repaired into one that looks readable",
     "IH._semantic_parse = lambda t: E.fromstring("
     "t.encode('utf-8','surrogatepass'), E.XMLParser(recover=True))",
     "-k not_well_formed or refusal_reason"),

    ("literal_prefix_lookup",
     "the FACT element's renderer spelling is hard-coded to `ix:nonfraction` "
     "instead of the one the document actually used",
     # NARROWED: only the fact element is hard-coded. Replacing `_lexical` for
     # EVERY element also destroyed the alignment counts, so the suite could
     # have gone red for a reason that had nothing to do with the prefix rule.
     "IH._lexical = _fact_prefix_hardcoded",
     "-k lawful_prefix"),

    ("global_scope_qname",
     "a QName resolves against the ROOT element's prefix map instead of the "
     "scope it is written in, so a locally rebound prefix keeps its outer "
     "meaning",
     # NARROWED: still a real resolver, still returns lawful (uri, local) —
     # only the SCOPE is wrong. The previous version returned a constant
     # namespace for everything, which breaks far more than the scope rule.
     "IH._qname = _root_scope_qname",
     "-k QNAME_VALUE_resolves"),

    # mispaired_views: RETIRED (SEQ 346) — no longer a mutation. Its injected lambda
    # is byte-for-behavior the CURRENT _bridge (count guard + source-order zip into
    # _Fact): SEQ 264 deliberately made source order the pairing truth, _align_views
    # proves per-spelling totals/order upstream, and duplicate/ambiguous identities
    # refuse downstream (test_two_view_bridge.py:955-960 records the fingerprint's
    # removal; :988-1009 pin the replacement contract).

    ("exception_escapes",
     "a malformed document raises the parser's own exception out of the public "
     "door instead of one truthful refusal",
     "IH.prepare = _raising_prepare",
     "-k not_well_formed"),

    ("collapse_everything",
     "the whitespace facet is applied to EVERY attribute rather than to the "
     "ones whose declared type calls for it, so a padded sign becomes a "
     "negation",
     "IH._COLLAPSED = IH._COLLAPSED | {'sign'}",
     "-k sign_PRESERVES"),

    ("optional_empty_accepted",
     "an optional attribute present-and-EMPTY is accepted, so `sign=\"\"` "
     "states a sign the filing never wrote and `format=\"\"` asserts a "
     "transform by no name at all",
     "IH._typed = (lambda el, name, _t=IH._typed: _t(el, name) or None)",
     "-k optional_attribute or absent_or_lawful"),

    ("reference_looked_up_before_validated",
     "an unlawful contextRef/unitRef is reported as an UNDEFINED reference — a "
     "true-sounding statement about the filing when the fault is in the markup",
     "IH._xml_id = lambda v: v if isinstance(v, str) and v else None",
     "-k absent_or_lawful or collapse_faceted"),

    ("unitRef_optional",
     "a numeric fact with no unitRef binds anyway, stating no measure for its "
     "own number",
     "IH._evidence_from = _unitless_evidence",
     "-k REQUIRED_reference"),

    ("collapse_nothing",
     "the whitespace facet is not applied at all, so a lawfully padded id, "
     "contextRef or measure is called malformed",
     "IH._collapse = lambda v: v",
     "-k collapse_faceted or PADDED"),

    ("renderer_decides_facts",
     "the renderer tree is asked which of its own nodes are facts — a question "
     "only the strict view can answer",
     "IH._has_number_fact = lambda row, nodes: False",
     "-k ALTERNATE_PREFIX"),

    ("document_wide_xmlns_walk",
     "prefixes are collected from EVERY xmlns attribute anywhere in the "
     "document instead of the ones in scope, so a declaration on an unrelated "
     "sibling is trusted — the hand-written walk this round deleted",
     "IH._qname = _document_wide_qname",
     "-k SIBLING"),

    ("case_insensitive_prefix",
     "prefix lookup is case-insensitive, so `xmlns:ZZ` is taken to declare "
     "`zz` — prefixes are case-SENSITIVE names, not labels",
     "IH._qname = _case_insensitive_qname",
     "-k ANOTHER_CASE"),

    ("normalized_namespace_uri",
     "namespace URIs are compared after stripping a trailing slash and lower- "
     "casing, so a near-miss URI is treated as the official one",
     "IH._clark = _lenient_clark; IH._is = _lenient_is",
     "-k NEAR_MISS"),

    ("xmlns_by_text_search",
     "declarations are found by searching the raw markup for `xmlns:`, so text "
     "inside a script or a comment declares a prefix",
     "IH._qname = _text_search_qname",
     "-k xmlns_looking_TEXT"),

    ("graph_measure_by_colon_slicing",
     "an instance-namespace measure reaches the graph as the text AFTER a "
     "colon instead of as its resolved local name, so a value resolved "
     "through a default namespace — which has no colon — becomes the empty "
     "string and a lawful filing is refused",
     "IH._graph_measure = _colon_sliced_measure",
     "-k INSTANCE_measure or NON_instance_measure"),

    ("global_resource_discovery",
     "contexts and units are found ANYWHERE in the document instead of as "
     "direct children of an ix:resources under ix:header, so a declaration "
     "buried in a div or inside ix:hidden binds exactly like a real one",
     "IH._resources = lambda root: [root]; "
     "IH._kids_of = lambda parents, uri, local: "
     "[e for p in parents for e in IH._all(p, uri, local)]",
     "-k OUTSIDE_ix_resources or INSIDE_ix_resources or child_of_ix_header"),

    ("repeated_axis_by_raw_spelling",
     "one value per dimension is checked on the SPELLING, so two prefixes "
     "bound to one URI give the same axis two values and the context is "
     "accepted — XBRL Dimensions 1.0 §3.1.4.2",
     "IH._parse_context = _raw_axis_uniqueness",
     "-k repeated_dimension or GENUINELY_DIFFERENT"),

    ("ascii_name_grammar",
     "XML name legality is restated as an ASCII regex, which rejects the "
     "Unicode names XML permits",
     "IH.xml_name_ok = lambda n: bool(_ASCII.fullmatch(n))",
     "-k LAWFUL_xml_id"),
]

PRELUDE = """
import re, sys
from lxml import etree as E
import driver.relocation.inline_html as IH
import driver.xml_names as XNM   # #827 B8: the moved XML-name owner
_ASCII = re.compile(r'[A-Za-z_][A-Za-z0-9_.\\\\-]*\\\\Z')
def _raising_prepare(html_text):
    return IH._semantic_parse(html_text) and {}
_real_lexical = IH._lexical
def _fact_prefix_hardcoded(el):
    # THE defect, and only it: the fact element spelling is assumed.
    if IH._is(el, IH._INLINE_NS, 'nonFraction'):
        return 'ix:nonfraction'
    return _real_lexical(el)
def _root_scope_qname(value, el):
    # THE defect, and only it: resolve in the ROOT scope, not this one.
    root = el.getroottree().getroot() if hasattr(el, 'getroottree') else el
    return _real_qname(value, root)
_real_qname = IH._qname
def _document_wide_qname(value, el):
    # THE defect: every xmlns anywhere, not the ones in scope.
    if not isinstance(value, str):
        return None
    wide = {}
    for node in el.getroottree().getroot().iter():
        if isinstance(node.tag, str):
            wide.update({k: v for k, v in node.nsmap.items() if k})
    prefix, sep, local = value.partition(':')
    if not sep:
        return _real_qname(value, el)
    uri = wide.get(prefix) or el.nsmap.get(prefix)
    return (uri, local) if uri and XNM.xml_name_ok(local) else None
def _case_insensitive_qname(value, el):
    # THE defect: prefixes matched without regard to case.
    if not isinstance(value, str):
        return None
    prefix, sep, local = value.partition(':')
    if not sep:
        return _real_qname(value, el)
    folded = {(k or '').lower(): v for k, v in el.nsmap.items()}
    uri = folded.get(prefix.lower())
    return (uri, local) if uri and XNM.xml_name_ok(local) else None
def _lenient_uri(u):
    return (u or '').rstrip('/').lower()
def _lenient_clark(uri, local):
    return '{%s}%s' % (uri, local)
def _lenient_is(el, uri, local):
    # THE defect: a near-miss URI counts as the official one.
    if not isinstance(el.tag, str) or not el.tag.startswith('{'):
        return False
    got_uri, _, got_local = el.tag[1:].partition('}')
    return _lenient_uri(got_uri) == _lenient_uri(uri) and got_local == local
def _text_search_qname(value, el):
    # THE defect: declarations found by searching the markup as text.
    import re as _re
    if not isinstance(value, str):
        return None
    prefix, sep, local = value.partition(':')
    if not sep:
        return _real_qname(value, el)
    raw = E.tostring(el.getroottree().getroot(), encoding='unicode')
    quotes = chr(34) + chr(39)
    m = _re.search('xmlns:' + _re.escape(prefix) + '=([^ >]+)', raw)
    uri = m.group(1).strip(quotes + ';') if m else el.nsmap.get(prefix)
    return (uri, local) if uri and XNM.xml_name_ok(local) else None
def _colon_sliced_measure(m):
    # THE defect: punctuation stands in for the resolved local name.
    raw = IH._measure_text(m)
    resolved = IH._qname(raw, m)
    return (raw.partition(chr(58))[2]
            if resolved is not None and resolved[0] == IH._INSTANCE_NS else raw)
_real_parse_context = IH._parse_context
def _raw_axis_uniqueness(context):
    # THE defect: uniqueness judged on how each axis is SPELLED.
    out = _real_parse_context(context)
    if out is not None:
        return out
    # the expanded rule refused it; re-admit it if the RAW spellings differ
    import lxml.etree as _E
    axes = [m.get('dimension') for m in
            context.iter('{http://xbrl.org/2006/xbrldi}explicitMember')]
    if len(set(axes)) == len(axes) and len(axes) > 1:
        return {'period': ('2026-01-01', '2026-03-31'), 'dims': (),
                'typed': False, 'entity': '0000320193'}
    return None
_real_evidence = IH._evidence_from
def _unitless_evidence(fact, prepared):
    if not (IH._typed(fact.sem, 'unitRef') or ''):
        fact.sem.set('unitRef', 'u1')        # the old "absence is fine" path
    return _real_evidence(fact, prepared)
"""


#: THE PROOF ENVIRONMENT. Nothing is inherited that could carry credentials or
#: configuration: `HOME` is redirected to an EMPTY temp directory outside the
#: repository, so `~/.config`, `~/.netrc`, `~/.aws` and every credentials file
#: are simply not there to be read; pytest loads no plugin that was not asked
#: for. A green or red result therefore cannot come from outside this repo.
#:
#: The real HOME used to be inherited while this comment claimed otherwise.
ALLOWED_ENV = ("PATH", "LANG", "LC_ALL")


def _env(home):
    env = {k: os.environ[k] for k in ALLOWED_ENV if k in os.environ}
    env.update(HOME=home, TMPDIR=home,
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONPATH=_REPO,
               PYTHONDONTWRITEBYTECODE="1")
    return env


def run(patch, selector):
    """(rc, [test node ids that FAILED]) for the suite under `patch`.

    WHAT IS RECORDED IS THE TEST NODE ID, and nothing else. An exit status alone
    proves a mutation broke SOMETHING; the node id proves it broke the test the
    mutation is named after. An earlier version mixed node ids with traceback
    lines and described them both as "the assertion", which overstated what the
    receipt contained — `-rf` reports one `FAILED <nodeid>` line per failure,
    so the list is uniform.
    """
    args = ["-q", "-p", "no:randomly", "--tb=no", "-rf", *SUITES, "-k", selector]
    home = tempfile.mkdtemp(prefix="core827-mut-home-")
    code = (PRELUDE + patch + "\nimport pytest\n"
            "sys.exit(pytest.main(%r))" % (args,))
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=_REPO,
                           capture_output=True, text=True, env=_env(home))
    finally:
        shutil.rmtree(home, ignore_errors=True)
    failed = [ln.strip()[len("FAILED "):].split(" - ")[0]
              for ln in r.stdout.split("\n") if ln.strip().startswith("FAILED ")]
    return r.returncode, failed


def main():
    rows, ok = [], True
    for name, defect, patch, selector in MUTATIONS:
        sel = selector.split(" ", 1)[1] if selector.startswith("-k ") else selector
        mutated, how = run(patch, sel)
        control, _ = run("pass", sel)
        # rc 5 is pytest's "no tests collected". A selector that matches nothing
        # must be an ERROR, never a verdict: both halves would be non-zero and
        # could be misread as "the mutation was caught".
        if 5 in (mutated, control):
            rows.append({"mutation": name, "selector": sel,
                         "rc_mutated": mutated, "rc_control": control,
                         "verdict": "*** SELECTOR MATCHED NO TEST ***"})
            print(f"{name:36} *** SELECTOR {sel!r} MATCHED NO TEST ***",
                  flush=True)
            ok = False
            continue
        caught, clean = mutated == 1, control == 0
        named = bool(how)
        ok &= caught and clean and named
        rows.append({"mutation": name, "defect_reintroduced": defect,
                     "selector": sel, "rc_mutated": mutated,
                     "rc_control": control,
                     "failed_test_node_ids": how,
                     "verdict": "CAUGHT" if caught else "*** NOT CAUGHT ***",
                     "control": "clean" if clean else "*** CONTROL BROKEN ***",
                     "named_failure": "the named test failed" if named
                                      else "*** NO NAMED FAILURE ***"})
        print(f"{name:36} mut={mutated} ctrl={control}  "
              f"{rows[-1]['verdict']:18} {rows[-1]['control']:22}", flush=True)
        for h in how[:2]:
            print(f"     └─ {h[:110]}", flush=True)
    out = {"suites": SUITES, "environment": {
               "inherited": list(ALLOWED_ENV),
               "HOME": "an empty temp dir outside the repo, removed after each run",
               "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
           "all_caught_with_named_failures_and_clean_controls": bool(ok),
           "mutations": rows}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print("\nALL CAUGHT WITH NAMED FAILURES, CONTROLS CLEAN" if ok
          else "\n*** GROUP VOID ***")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
