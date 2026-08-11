"""#827 Stage 3 — proof that the fixed-value inventory reaches the DECISION SITES.

An inventory is only worth its blind spots, and a completeness test is only
worth what it pins. Two rounds of correction are baked in here:

1. The scanner first scored literals with a candidate regex and called 279 rows
   complete. That filter WAS the classification it claimed not to perform.
2. The replacement tests then accepted a matching literal ANYWHERE, so several
   passed on a test fixture rather than the rule they named — `ixt:fixed-zero`
   was green because a fixture mentions it, not because production compares it.

So every control below pins BUCKET + EXACT FILE + OWNER-or-BINDING + USE, and
each is bite-proved: with that exact literal removed from a temp copy of its
own file, the detector must fail. A same word in a comment, a fixture or
another module cannot keep it green.

Read-only: builds the inventory in memory; the bite-proofs edit throwaway
copies under `tmp_path` and never a tracked file.
"""
import ast
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hardcoding_inventory as INV                            # noqa: E402

RCPT = os.path.relpath(os.path.dirname(os.path.abspath(__file__)), INV.ROOT)


def _text(row):
    """The literal as recorded — bytes stay bytes, never latin-1 prose."""
    if 'value' in row:
        return row['value']
    import base64
    return base64.b64decode(row['value_b64']).decode('latin-1')


# ---------------------------------------------------------------------------
# THE KNOWN DECISION SITES. Each names a different KIND of hiding place, and
# each is anchored to the one place that actually decides something.
#   (label, bucket, file, predicate, the exact source text whose removal must
#    kill this detector)
# ---------------------------------------------------------------------------
SITES = [
    ("Site B raw `segment` key", 'production', 'driver/relocation/locator.py',
     lambda r: (_text(r) == 'segment' and r['owner'] == 'seg_parse'
                and r['use'].startswith('call:')),
     "fc.get('segment')", "fc.get('SENTINEL_REMOVED')"),

    ("`_CANDIDATE_EXACT` unit words", 'production', 'driver/core/xbrl_attach.py',
     lambda r: r['binding'] == '_CANDIDATE_EXACT' and _text(r) == 'shares',
     "'shares'", "'SENTINEL_REMOVED'"),

    # WAS `startswith('iso4217:')`, twice inside `candidate_units_for`. Stage 3
    # DELETED both: a prefix is the filer's alias and could not say which
    # currency was declared. What the inventory must now reach is the cited
    # constant that replaced them — the namespace URI itself.
    # FOLLOWED ITS VALUE to the one owner (#827 B1 packet 1 dedup): the URI
    # now lives at exact_numbers.ISO_4217_NAMESPACE and the consumers import it.
    ("the ISO-4217 namespace constant", 'production',
     'driver/relocation/exact_numbers.py',
     lambda r: (r['binding'] == 'ISO_4217_NAMESPACE'
                and _text(r) == 'http://www.xbrl.org/2003/iso4217'),
     "ISO_4217_NAMESPACE = 'http://www.xbrl.org/2003/iso4217'",
     "ISO_4217_NAMESPACE = 'SENTINEL_REMOVED'"),

    ("`EXAMPLES_LIMIT` numeric cap", 'proof_tools',
     RCPT + '/structure_census.py',
     lambda r: (r['type'] == 'int' and r['binding'] == 'EXAMPLES_LIMIT'
                and _text(r) == '50'),
     'EXAMPLES_LIMIT = 50', 'EXAMPLES_LIMIT = None'),

    # PINNED TO ITS BINDING. Matching the URI anywhere in the file broke this
    # file's own stated rule — a fixture or a comment-adjacent copy of the same
    # string would have kept it green after the real constant was gone.
    # FOLLOWED ITS VALUE to the one owner (#827 B1 packet 1 dedup), same as
    # the ISO-4217 row above.
    ("the XBRL instance namespace URI", 'production',
     'driver/relocation/exact_numbers.py',
     lambda r: (r['binding'] == 'XBRL_INSTANCE_NAMESPACE'
                and _text(r) == 'http://www.xbrl.org/2003/instance'),
     "XBRL_INSTANCE_NAMESPACE = 'http://www.xbrl.org/2003/instance'",
     "XBRL_INSTANCE_NAMESPACE = 'SENTINEL_REMOVED'"),
]


@pytest.fixture(scope='module')
def inventory():
    inv = INV.build()
    assert inv, 'the inventory found nothing at all'
    return inv


def _rows(inv, bucket, rel):
    return inv.get(bucket, {}).get(rel, [])


@pytest.mark.parametrize('site', SITES, ids=[s[0] for s in SITES])
def test_the_inventory_reaches_this_decision_site(inventory, site):
    """PINNED, not merely present: bucket, file, owner/binding and use."""
    label, bucket, rel, pred, _old, _new = site
    rows = _rows(inventory, bucket, rel)
    assert rows, f'{rel} is not being scanned at all (bucket {bucket})'
    assert any(pred(r) for r in rows), \
        f'{label}: not found at its own decision site in {bucket}/{rel}'


@pytest.mark.parametrize('site', SITES, ids=[s[0] for s in SITES])
def test_removing_the_literal_KILLS_its_detector(inventory, site, tmp_path):
    """THE BITE-PROOF. Copy the real file, delete that exact literal, rescan.

    Without this, a detector can be satisfied by the same word in a comment, a
    fixture or a neighbouring module and would stay green after the rule it
    claims to guard was deleted — which is how the previous round passed.
    """
    label, bucket, rel, pred, old, new = site
    src_path = os.path.join(INV.ROOT, rel)
    source = open(src_path, encoding='utf-8').read()
    assert source.count(old) >= 1, \
        f'{label}: the removal anchor {old!r} is not in {rel} — the bite-proof ' \
        f'would silently test nothing'
    copy = tmp_path / os.path.basename(rel)
    # EVERY OCCURRENCE, because the target is the RULE and not one instance of
    # it. Replacing just the first left `iso4217:` alive — that rule is written
    # (Historical: the `iso4217:` prefix rule was written twice inside one
    # function, so a single-instance removal left the detector alive. Both are
    # deleted now — Stage 3 replaced them with the cited namespace constant —
    # but the every-occurrence rule stays, because it is the general one.)
    # a single-instance bite-proof reported a live detector as dead. The
    # duplication is itself an audit finding, recorded for classification.
    copy.write_text(source.replace(old, new), encoding='utf-8')
    assert not any(pred(r) for r in INV.scan(str(copy))), \
        f'{label}: the detector still passes with its literal removed'


# ---------------------------------------------------------------------------
# THE SCANNER CONTRACT, on a synthetic file whose every literal is known
# ---------------------------------------------------------------------------

#: RAW, so what is written here is exactly what the scanner will read. Spelled
#: with escapes it produced a different literal than the assertions named, and
#: the test failed on its own quoting rather than on the scanner.
_CONTRACT = r'''
"""A module docstring — the one lawful exclusion."""
import re

TABLE = {'alpha': 1, 'nested': ['beta', 2.5]}
PATTERN = re.compile(r'[0-9]\s')
CAP = 4096
MAGIC = b'\x00raw'


def f(x):
    """A function docstring, also excluded."""
    if x == 'compare-me':
        return x.startswith('call-me')
    return x[2:], TABLE['alpha'], 'kwarg' if x else CAP
'''


def test_the_SCANNER_CONTRACT_on_a_file_with_known_literals(tmp_path):
    """Every non-docstring literal present exactly once; both docstrings gone.

    The previous `DOCSTRINGS_are_the_only_exclusion` test did not prove its
    title — it checked one prefix and that some prose-shaped literal survived,
    which any half-working scanner passes.
    """
    p = tmp_path / 'contract_sample.py'
    p.write_text(_CONTRACT, encoding='utf-8')
    rows = INV.scan(str(p))

    strs = [_text(r) for r in rows if r['type'] == 'str']
    assert sorted(strs) == sorted(
        ['alpha', 'nested', 'beta', '[0-9]\\s', 'compare-me', 'call-me',
         'kwarg', 'alpha']), strs           # 'alpha' twice: key and subscript
    # SORTED: the contract is WHICH literals are found, not the order
    # `ast.walk` happens to yield them in — asserting that would pin a CPython
    # traversal detail as if it were the scanner's promise.
    assert sorted(_text(r) for r in rows if r['type'] == 'int') == \
        sorted(['1', '4096', '2'])
    assert [_text(r) for r in rows if r['type'] == 'float'] == ['2.5']

    import base64
    assert [base64.b64decode(r['value_b64']) for r in rows
            if r['type'] == 'bytes'] == [b'\x00raw']

    # THE DOCSTRINGS, and ONLY the docstrings, are absent.
    assert not any('lawful exclusion' in _text(r) or 'also excluded' in _text(r)
                   for r in rows)

    by_value = {_text(r): r for r in rows if r['type'] == 'str'}
    assert by_value['compare-me']['use'] == 'compare'
    assert by_value['call-me']['use'] == 'call:startswith'
    assert by_value['beta']['use'].startswith('membership-table')
    assert by_value['[0-9]\\s']['binding'] == 'PATTERN'
    assert by_value['nested']['binding'] == 'TABLE'
    caps = [r for r in rows if r['type'] == 'int' and _text(r) == '4096']
    assert caps and caps[0]['binding'] == 'CAP'


#: BOOLEANS, in the four shapes production actually uses them. The scanner
#: docstring says booleans are kept because `recover=False` decides whether a
#: malformed filing is repaired — but nothing pinned that, so a future
#: shape-based exclusion could drop them all and every test would stay green.
_BOOLEANS = r'''
FLAGS = {'divide': True, 'plain': False}


def g(recover=False):
    if recover is True:
        return True
    return False
'''


def test_BOOLEANS_are_retained_at_their_exact_owner_and_use(tmp_path):
    """A named-mapping boolean and a bare/default/control-flow boolean both
    survive, each carrying the use that would decide its classification.

    The distinction matters: a mapping member is a product rule, while a
    control-flow return may be mechanical — but only a reader of the owning
    statement can say which, and that reader needs the row to exist."""
    p = tmp_path / 'booleans_sample.py'
    p.write_text(_BOOLEANS, encoding='utf-8')
    rows = [r for r in INV.scan(str(p)) if r['type'] == 'bool']
    seen = sorted((r['owner'], r['use'], _text(r)) for r in rows)
    assert seen == sorted([
        ('', 'dict-value:FLAGS', 'True'),      # the named mapping
        ('', 'dict-value:FLAGS', 'False'),
        ('g', 'arguments', 'False'),           # a default
        ('g', 'compare', 'True'),              # a comparison
        ('g', 'return', 'True'),               # control flow
        ('g', 'return', 'False'),
    ]), seen


#: SIGNED NUMBERS. `-4` is not a literal in Python's grammar: it is a `UnaryOp`
#: wrapped around the constant `4`. A scanner that walks `Constant` nodes alone
#: therefore reports the MAGNITUDE and calls the use `unaryop`, losing both the
#: sign and the statement that owns the decision.
_SIGNED = r'''
SCALE = -4
OFFSET = +3
LIMITS = [-1, 2]


def h(pad=-2):
    return pad - 5
'''


def test_a_SIGNED_number_is_ONE_value_at_its_REAL_use(tmp_path):
    """`-4` is recorded once, as -4, under the statement that owns it.

    Three separate defects in one shape: the sign was dropped, so `-4` and `4`
    were indistinguishable in the worklist; the use became the wrapper
    `unaryop` instead of the assignment or table that gives the value meaning;
    and `decimals="-4"`-class rules in live production — `exact_numbers.py`
    among them — were being classified from the wrong number."""
    p = tmp_path / 'signed_sample.py'
    p.write_text(_SIGNED, encoding='utf-8')
    rows = INV.scan(str(p))

    assert not any(r['use'] == 'unaryop' for r in rows), \
        [r for r in rows if r['use'] == 'unaryop']
    seen = sorted((r['owner'], r['use'], _text(r)) for r in rows
                  if r['type'] in ('int', 'float'))
    assert seen == sorted([
        ('', 'assign:SCALE', '-4'),
        ('', 'assign:OFFSET', '3'),            # +3 IS 3; the fix is the use
        ('', 'membership-table:LIMITS', '-1'),
        ('', 'membership-table:LIMITS', '2'),
        ('h', 'arguments', '-2'),
        ('h', 'binop', '5'),                   # not a unary: untouched
    ]), seen
    # ONE row per literal — the wrapped constant must not also appear alone.
    assert len(seen) == len(rows), rows


# ---------------------------------------------------------------------------
# SCOPE AND SEPARATION
# ---------------------------------------------------------------------------

def _ast_import_edges(rel):
    """Dotted module names `rel` really imports — read from the PARSE TREE.

    SEQ 445 A1: this check used raw substring searches (`f'import {dotted}' in
    text`). A comment mentioning a module credited an edge that did not exist,
    and `from pkg import helper` — the submodule form — was missed entirely.
    Proving an import by string search is the defect #827 exists to remove, so
    it cannot be the thing that certifies the scope.

    Written here, independently, on purpose: a coverage test that calls
    `production_closure` proves only that the implementation agrees with
    itself.
    """
    try:
        tree = ast.parse(open(os.path.join(INV.ROOT, rel), encoding='utf-8').read())
    except (OSError, SyntaxError):
        return set()
    edges = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            edges |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            edges.add(node.module)
            edges |= {f'{node.module}.{a.name}' for a in node.names}
    return edges


def test_the_SCANNED_SET_EQUALS_the_independently_globbed_set(inventory):
    """SCOPE PROVED BY EQUALITY, not by five happy examples.

    The expected set is rebuilt here from the filesystem — every `.py` under
    both production directories, every active receipt tool, and every exact
    `SEED_FILES` member — and compared BOTH WAYS. Naming a handful of files
    could never have caught a whole directory quietly dropped, which is the
    mistake this replaces.
    """
    expected = set()
    for d in (os.path.join('driver', 'core'), os.path.join('driver', 'relocation')):
        base = os.path.join(INV.ROOT, d)
        expected |= {os.path.relpath(os.path.join(base, n), INV.ROOT)
                     for n in os.listdir(base) if n.endswith('.py')}
    rbase = os.path.join(INV.ROOT, RCPT)
    expected |= {os.path.relpath(os.path.join(rbase, n), INV.ROOT)
                 for n in os.listdir(rbase) if n.endswith('.py')}
    # `SEED_FILES` are already repo-relative.
    expected |= {p for p in INV.SEED_FILES
                 if os.path.exists(os.path.join(INV.ROOT, p))}

    scanned = {f for fs in inventory.values() for f in fs}
    # SEQ 447: THE ZERO-RULE EXEMPTION IS GONE. This used to filter the
    # difference through `INV.scan(...)`, excusing any file that detected no
    # literals — but `build()` retains every input precisely so a zero-rule
    # file still counts as scanned, and its hash still pins the run. The
    # exemption meant such a file could be dropped entirely and this test
    # would stay green.
    assert not expected - scanned, \
        f'in scope but never scanned: {sorted(expected - scanned)}'

    # SEQ 444: production is now an import CLOSURE, so a scanned file may
    # lawfully sit outside the globbed directories — but only if some file
    # already in scope really imports it. That justification is RE-DERIVED
    # here by reading import statements directly, never by calling
    # `production_closure`: a coverage test that asks the implementation to
    # confirm itself is precisely the defect this file's history records.
    extra = scanned - expected
    justified, changed = set(), True
    while changed:
        changed = False
        for cand in sorted(extra - justified):
            dotted = cand[:-3].replace(os.sep, '.')
            for src in sorted(expected | justified):
                if dotted in _ast_import_edges(src):
                    justified.add(cand)
                    changed = True
                    break
    assert extra == justified, (
        f'scanned outside the declared scope with no import edge: '
        f'{sorted(extra - justified)}')


def test_evidence_is_SEPARATED_but_not_dropped(inventory):
    """A fixture literal is what a filing said, not a rule the product
    applies — labelled, still counted. Dropping it would hide a false law
    encoded in a test, which has happened here more than once."""
    assert {'production', 'evidence'} <= set(inventory)
    assert all(not os.path.basename(f).startswith('test_')
               for f in inventory['production']), \
        'test payloads are leaking into the production bucket'
    assert all(os.path.basename(f).startswith('test_')
               for f in inventory['evidence']), \
        'non-test files are being filed as evidence'


_REBIND = r'''
def one():
    d = 'first-rule'
    return d


def two():
    d = 'second-rule'
    return d


def thrice():
    key = 'a'
    key = 'b'
    return key
'''


def test_a_REUSED_BINDING_NAME_never_merges_two_rules(tmp_path):
    """THE IDENTITY IS THE STATEMENT, not the name bound by it.

    `d` in `one()` and `d` in `two()` are unrelated rules that happen to share
    a local name, and `key` is reassigned twice inside one function. Keyed by
    name they collapse into one or two adjudications and a reviewer signs off
    on a rule they never saw. Keyed by (owner, statement line) each stays its
    own row.
    """
    p = tmp_path / 'rebind_sample.py'
    p.write_text(_REBIND, encoding='utf-8')
    rules = INV.decision_rules({'production': {'rebind_sample.py': INV.scan(str(p))}})

    named = [r for r in rules if r['bindings']]
    assert len(named) == 4, [(r['owner'], r['stmt_line'], r['bindings'])
                             for r in named]
    # the two `d` rules are DIFFERENT rows, in different owners...
    ds = [r for r in named if r['bindings'] == ['d']]
    assert len(ds) == 2 and {r['owner'] for r in ds} == {'one', 'two'}
    # ...and the two `key` assignments are two rows in the SAME owner.
    keys = [r for r in named if r['bindings'] == ['key']]
    assert len(keys) == 2 and {r['owner'] for r in keys} == {'thrice'}
    assert keys[0]['stmt_line'] != keys[1]['stmt_line']
    assert sorted(v for r in named for v in r['values']) == \
        ['a', 'b', 'first-rule', 'second-rule']


def test_EVERY_literal_folds_into_exactly_one_rule(inventory):
    """No prefilter survives: the rule view's coverage must equal the raw
    occurrence count, per bucket and overall. The deleted decides/emitted
    split was a hand-written allowlist of function names — a literal passed to
    a function not on that list can still decide behaviour, so calling it
    `emitted` was a guess, not an AST fact."""
    rules = INV.decision_rules(inventory)
    totals = {b: sum(len(rows) for rows in fs.values())
              for b, fs in inventory.items()}
    covered = {}
    for r in rules:
        covered[r['bucket']] = covered.get(r['bucket'], 0) + r['covered']
    assert covered == totals, f'{covered} != {totals}'


def test_values_are_stored_WHOLE(inventory):
    """No silent truncation: the old `[:160]` cap could cut away the very
    substring under classification. Length is recorded beside the value."""
    longest = max((r for fs in inventory.values() for rows in fs.values()
                   for r in rows if r['type'] == 'str'),
                  key=lambda r: r['length'])
    assert len(longest['value']) == longest['length'] > 160, \
        'a long literal is being truncated, or none exists to prove it is not'


# ---- SEQ 278 §2 / 281 / 284: the permanent stable-identity controls --------
# One import shift once renumbered 1,595 rules and buried a real packet delta,
# so the statement identity is CONTENT (normalized-ast sha + per-owner
# ordinal), never line numbers. These pin exactly that, on throwaway files.

_ID_BASE = 'X = "alpha"\ndef f():\n    y = "beta"\n    return "gamma"\n'
_ID_SHIFTED = ('import os\n\nX = "alpha"\n\ndef f():\n\n'
               '    y = "beta"\n    return "gamma"\n')
_ID_TWINS = 'def f():\n    a("dup")\n    a("dup")\n'
_ID_ONE_LIT = 'X = "alpha"\ndef f():\n    y = "beta"\n    return "CHANGED"\n'


def _ids_by_value(tmp_path, name, src):
    p = tmp_path / name
    p.write_text(src)
    out = {}
    for r in INV.scan(str(p)):
        out.setdefault(r.get('value'), set()).add(r['stmt_id'])
    return out


def test_identity_survives_blank_lines_and_an_unrelated_import(tmp_path):
    a = _ids_by_value(tmp_path, 'a.py', _ID_BASE)
    b = _ids_by_value(tmp_path, 'b.py', _ID_SHIFTED)
    for v in ('alpha', 'beta', 'gamma'):
        assert a[v] == b[v], (v, a[v], b[v])


def test_identical_twin_statements_stay_two_distinct_rules(tmp_path):
    p = tmp_path / 'twins.py'
    p.write_text(_ID_TWINS)
    ids = {r['stmt_id'] for r in INV.scan(str(p)) if r.get('value') == 'dup'}
    assert len(ids) == 2, ids


def test_changing_one_literal_moves_exactly_one_rule(tmp_path):
    a = _ids_by_value(tmp_path, 'a.py', _ID_BASE)
    c = _ids_by_value(tmp_path, 'c.py', _ID_ONE_LIT)
    assert a['alpha'] == c['alpha']
    assert a['beta'] == c['beta']
    assert a['gamma'] != c['CHANGED']


def test_raw_row_coverage_equals_folded_rule_coverage(tmp_path):
    pa, pt = tmp_path / 'a.py', tmp_path / 'twins.py'
    pa.write_text(_ID_BASE)
    pt.write_text(_ID_TWINS)
    rows = INV.scan(str(pa)) + INV.scan(str(pt))
    rules = INV.decision_rules({'production': {'a.py': rows}})
    assert sum(r['covered'] for r in rules) == len(rows)


_ID_NESTED_OLD = 'if FLAG == "header":\n    x = "old"\n'
_ID_NESTED_NEW = 'if FLAG == "header":\n    x = "new"\n'


_ID_SAME_NAMED = ('class A:\n    def f(self):\n        return "same"\n\n\n'
                  'class B:\n    def f(self):\n        return "same"\n')


def test_same_named_owners_keep_identical_statements_apart(tmp_path):
    """SEQ 284: the rule key carries only the owner's SIMPLE NAME, so the
    duplicate ordinal must be scoped by that same label — not by the owning
    AST object — or two same-named functions each holding an identical
    statement collapse into one rule (7 merged keys / 8 lost rules found in
    the live scope)."""
    p = tmp_path / 'sn.py'
    p.write_text(_ID_SAME_NAMED)
    rows = [r for r in INV.scan(str(p)) if r.get('value') == 'same']
    assert len({r['stmt_id'] for r in rows}) == 2, rows
    rules = INV.decision_rules({'production': {'sn.py': INV.scan(str(p))}})
    same_rules = [r for r in rules if 'same' in r['values']]
    assert len(same_rules) == 2, same_rules


def test_editing_a_nested_statement_never_moves_its_parent_rule(tmp_path):
    """SEQ 281: the fingerprint is the nearest statement ITSELF, excluding
    every descendant statement body — so editing the nested assignment moves
    exactly the nested rule and the parent `if` rule stays put. The id also
    carries the FULL 64-hex SHA-256, never a truncation."""
    import re
    a = _ids_by_value(tmp_path, 'a.py', _ID_NESTED_OLD)
    b = _ids_by_value(tmp_path, 'b.py', _ID_NESTED_NEW)
    assert a['header'] == b['header'], (a['header'], b['header'])
    assert a['old'] != b['new']
    for ids in (a['header'], a['old']):
        for i in ids:
            assert re.fullmatch(r'[A-Za-z]+:[0-9a-f]{64}:\d+', i), i


_ID_CTL_BASE = (
    "def f():\n"
    "    LIMIT = 10\n"
    "    return LIMIT\n"
)
_ID_CTL_MOVED = (
    "import os\n"
    "\n"
    "\n"
    "def f():\n"
    "    LIMIT = 10\n"
    "    return LIMIT\n"
)
_ID_CTL_CHANGED = (
    "def f():\n"
    "    LIMIT = 11\n"
    "    return LIMIT\n"
)
_ID_CTL_TWINS = (          # genuinely identical statements: same target-free call
    "def f():\n"
    "    log('/x.jsonl')\n"
    "    log('/x.jsonl')\n"
)


def test_IDENTITY_a_line_only_move_preserves_stmt_id(tmp_path):
    """SEQ 427 control 1. `stmt_id` is a location-free content hash, so adding
    an unrelated import above must NOT invalidate a pin. This is exactly the
    failure that made line-keyed matching useless."""
    a = _ids_by_value(tmp_path, 'a.py', _ID_CTL_BASE)
    b = _ids_by_value(tmp_path, 'b.py', _ID_CTL_MOVED)
    assert a['10'] == b['10'], (a, b)      # scanner records values as strings


def test_IDENTITY_a_semantic_change_INVALIDATES_stmt_id(tmp_path):
    """SEQ 427 control 2. Editing the literal must break the pin and force
    review — a pin that survived an edit would certify the wrong statement."""
    a = _ids_by_value(tmp_path, 'a.py', _ID_CTL_BASE)
    b = _ids_by_value(tmp_path, 'b.py', _ID_CTL_CHANGED)
    assert '10' in a and '11' in b, (sorted(a), sorted(b))
    assert a['10'] != b['11'], 'a changed literal must not keep its identity'


def test_IDENTITY_two_identical_statements_stay_DISTINCT(tmp_path):
    """SEQ 427 control 3. Two textually identical statements under one owner
    hash the same content, so identity carries an occurrence index. Without it
    they would collapse and one could borrow the other's verdict."""
    p = tmp_path / 'twins.py'
    p.write_text(_ID_CTL_TWINS)
    rows = INV.scan(str(p))
    ids = sorted({r['stmt_id'] for r in rows})
    assert len(ids) == 2, ids
    # SAME content hash (they are the same statement) …
    assert len({i.rsplit(':', 1)[0] for i in ids}) == 1, ids
    # … but DIFFERENT occurrence, so neither can borrow the other's verdict
    assert {i.rsplit(':', 1)[1] for i in ids} == {'0', '1'}, ids


_ID_CTL_TWO_OWNERS = (
    "def alpha():\n"
    "    return True\n"
    "\n"
    "\n"
    "def beta():\n"
    "    return True\n"
)


def test_IDENTITY_the_same_statement_under_TWO_OWNERS_needs_the_owner_key():
    """SEQ 428 control 4 — the one my SEQ 427 controls missed.

    The occurrence ordinal is scoped BY OWNER, and the owner is not embedded in
    `stmt_id`. So identical statements in two different functions of one file
    carry the SAME `stmt_id`, and a join on `(file, stmt_id)` credits an
    unrelated function. That really happened: two old `_xml_name_ok` pins
    credited seven current rules owned by `_accuracy_ok`, `_nil_true`,
    `_display_valid`, `_hidden_cell` and `reconcile`.

    The fix is not to redesign `stmt_id` but to key on `(file, owner,
    stmt_id)`, which the inventory already carries.
    """
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, 'two_owners.py')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(_ID_CTL_TWO_OWNERS)
    rows = INV.scan(p)
    report = {'proof_tools': {'two_owners.py': rows}}
    rules = INV.decision_rules(report)
    owners = {r['owner'] for r in rules}
    assert owners == {'alpha', 'beta'}, owners
    # THE COLLISION IS REAL: one stmt_id, two owners
    assert len({r['stmt_id'] for r in rules}) == 1, [r['stmt_id'] for r in rules]
    # THE CORRECTED KEY SEPARATES THEM: closing alpha cannot close beta
    keys = {(r['file'], r['owner'], r['stmt_id']) for r in rules}
    assert len(keys) == 2, keys
    closed = {next(k for k in keys if k[1] == 'alpha')}
    still_open = [r for r in rules
                  if (r['file'], r['owner'], r['stmt_id']) not in closed]
    assert [r['owner'] for r in still_open] == ['beta'], still_open


def test_the_manifest_covers_EVERY_yielded_input_including_zero_row_files():
    """SEQ 426: `build()` used to drop files whose scan returned no rows, so
    the report described files WITH literals, not files SCANNED — and the
    manifest derived from it listed 103 of 104 inputs. A file that contributed
    nothing is still an input, and its hash still pins the run."""
    yielded = {rel for scope, dirs in INV.SCOPES.items()
               for _b, rel, _f in INV._files_for(scope, dirs)}
    report = INV.build()
    manifested = {f for fs in report.values() for f in fs}
    assert manifested == yielded, sorted(yielded ^ manifested)
    zero = {f for fs in report.values() for f, rows in fs.items() if not rows}
    assert zero, 'expected at least one zero-row input to be retained'
    assert 'driver/core/__init__.py' in zero, sorted(zero)


_TWO_ON_ONE_LINE = (
    "def main():\n"
    "    AB = open('/abstain.jsonl', 'w'); SL = open('/sources_ledger.jsonl', 'w')\n"
)


def test_two_assignments_on_ONE_physical_line_are_TWO_rules(tmp_path):
    """SEQ 425. Keying a rule by LINE merged these into one row carrying
    bindings ['AB','SL'] and covered 4, which hid that they are two separate
    decisions. Statement identity splits them — and this fixture exists because
    that split was briefly mistaken for a dropped binding.

    Both bindings survive, both values survive, and raw coverage is exact:
    2 + 2 is the same 4 the merged row reported, so nothing was lost.
    """
    p = tmp_path / 'two.py'
    p.write_text(_TWO_ON_ONE_LINE)
    rows = INV.scan(str(p))
    report = {'proof_tools': {'two.py': rows}}
    rules = INV.decision_rules(report)

    assert len(rules) == 2, [r['bindings'] for r in rules]
    assert {r['stmt_id'] for r in rules}.__len__() == 2, 'ids must differ'
    by_binding = {tuple(r['bindings']): r for r in rules}
    assert set(by_binding) == {('AB',), ('SL',)}, sorted(by_binding)
    assert '/abstain.jsonl' in by_binding[('AB',)]['values']
    assert '/sources_ledger.jsonl' in by_binding[('SL',)]['values']
    # every rule reports the SAME physical line, which is what made the old
    # line-keyed grouping look reasonable
    for r in rules:
        assert r['lines'] == [2], r['lines']
    # COVERAGE IS EXACT: no literal was dropped by splitting the row
    assert sum(r['covered'] for r in rules) == len(rows) == 4


# ---------------------------------------------------------------------------
# SEQ 443: THE RULE CARRIES ITS OWN SOURCE.
#
# A mapper that wants the exact text of a rule had to re-find the statement
# from `(file, owner, stmt_id)`. I wrote that second lookup and it disagreed
# with this file in 27 of 3,529 mandatory rules — every one a `FunctionDef:`
# row — because I recomputed the owner by walking a node's parents to the
# enclosing def, while `scan` takes the owner from the LINE MAP at the
# LITERAL's line. Two walkers, two owner models, one of them wrong.
#
# The fix is not a better second walker. The traversal that mints the identity
# also records the source, so there is nothing left to re-derive.
# ---------------------------------------------------------------------------
_HEADER_LITERAL = (
    "def outer():\n"
    "    pass\n"
    "\n"
    "\n"
    "@register('deco-lit')\n"
    "def target(mode='header-default'):\n"
    "    return mode\n"
)


def test_a_FUNCTION_HEADER_literal_carries_the_DEF_statement_source(tmp_path):
    """The 27 failures were exactly this shape. `'header-default'` sits on the
    `def` line, so the line map names the function ITSELF as owner, while a
    parent walk from the `FunctionDef` node reports the ENCLOSING scope. The
    row must carry the def statement's own source either way."""
    p = tmp_path / 'hdr.py'
    p.write_text(_HEADER_LITERAL)
    rows = INV.scan(str(p))
    hdr = [r for r in rows if _text(r) == 'header-default']
    assert len(hdr) == 1, rows
    assert hdr[0]['owner'] == 'target', hdr[0]['owner']
    assert hdr[0]['stmt_id'].startswith('FunctionDef:'), hdr[0]['stmt_id']
    assert hdr[0]['stmt_source'].startswith("@register('deco-lit')\ndef target("), \
        hdr[0]['stmt_source']


def test_a_DECORATOR_literal_belongs_to_the_def_under_the_ENCLOSING_owner(tmp_path):
    """The other half of the same disagreement, and the reason a per-node owner
    rule cannot work: `FunctionDef.lineno` is the `def` line, so a decorator
    literal sits ABOVE it and the line map names the enclosing scope — while
    the literal still belongs to the def statement. One statement therefore
    appears under two owners, and both rows are correct."""
    p = tmp_path / 'deco.py'
    p.write_text(_HEADER_LITERAL)
    rows = INV.scan(str(p))
    deco = [r for r in rows if _text(r) == 'deco-lit']
    assert len(deco) == 1, rows
    assert deco[0]['owner'] == '', deco[0]['owner']          # enclosing = module
    hdr = [r for r in rows if _text(r) == 'header-default'][0]
    assert deco[0]['stmt_id'] == hdr['stmt_id'], 'same def statement'
    assert deco[0]['owner'] != hdr['owner'], 'different owners, one statement'
    assert deco[0]['stmt_source'] == hdr['stmt_source'], 'one statement, one source'


def test_a_DECORATOR_edit_moves_the_id_AND_the_recorded_source(tmp_path):
    """Source must cover exactly what identity covers. Decorators are
    expressions, so `_shallow_dump` fingerprints them and editing one moves
    `stmt_id` — but `FunctionDef.lineno` is the `def` line, so the plain
    `ast.get_source_segment` starts BELOW them and would report identical text
    for a changed rule. A pin would then say 'unchanged' about a changed law."""
    def scan_one(text):
        p = tmp_path / f'dec{abs(hash(text))}.py'
        p.write_text(text)
        rows = [r for r in INV.scan(str(p)) if _text(r) == 'x']
        assert len(rows) == 1, rows
        return rows[0]

    a = scan_one("@register('AAA')\ndef t(m='x'):\n    return m\n")
    b = scan_one("@register('BBB')\ndef t(m='x'):\n    return m\n")
    assert a['stmt_id'] != b['stmt_id'], 'the decorator is part of the identity'
    assert a['stmt_source'] != b['stmt_source'], 'so it must be part of the source'
    assert a['stmt_source'].startswith("@register('AAA')"), a['stmt_source']


def test_EVERY_rule_in_the_LIVE_inventory_carries_its_exact_source(inventory):
    """The population control the synthetic cannot give: every rule the real
    scan produces carries nonempty source that is byte-identical to the text
    at its own place in the file on disk."""
    rules = INV.decision_rules(inventory)
    empty = [r for r in rules if not r.get('stmt_source')]
    assert not empty, [(r['file'], r['owner'], r['stmt_id']) for r in empty[:5]]
    wrong = []
    for r in rules:
        want = hashlib.sha256(r['stmt_source'].encode()).hexdigest()
        if want != r['stmt_source_sha256']:
            wrong.append((r['file'], r['owner']))
    assert not wrong, wrong[:5]
    # and the recorded text really is in the file it names
    seen = {}
    for r in rules:
        text = seen.setdefault(
            r['file'], open(os.path.join(INV.ROOT, r['file']),
                            encoding='utf-8').read())
        assert r['stmt_source'] in text, (r['file'], r['owner'], r['stmt_id'])


# ---------------------------------------------------------------------------
# SEQ 444: PRODUCTION SCOPE IS AN IMPORT CLOSURE, NOT TWO DIRECTORY NAMES.
#
# `driver/xml_names.py` holds two production functions and is imported by four
# scanned production modules, and the audit never saw it — because the scope
# was `driver/core` + `driver/relocation` and that file sits one level up. Law
# was moved OUT of `inline_html.py` INTO it during this very audit (its own
# docstring records the move), so the inventory reported those rules gone from
# the source and nothing reported them arrived anywhere.
#
# A filename patch would fix this file and leave the hole. The scope is now
# derived the way `seed_route_a` already derives its own.
# ---------------------------------------------------------------------------
def _tree(tmp_path, files):
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return str(tmp_path)


def test_CLOSURE_reaches_a_helper_OUTSIDE_the_root_directories(tmp_path):
    """The exact live shape: a production root imports a module that lives one
    directory up, so a directory-shaped scope cannot see it."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': 'from pkg.helper import thing\n',
        'pkg/helper.py': 'X = "outside the root dirs"\n',
    })
    files, held, _sub = INV.production_closure(root=root,
                                               dirs=[os.path.join('pkg', 'core')])
    assert 'pkg/helper.py'.replace('/', os.sep) in files, sorted(files)
    assert not held, held


def test_CLOSURE_is_TRANSITIVE(tmp_path):
    """A helper's own helper is production too, or the hole simply moves."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': 'from pkg.one import x\n',
        'pkg/one.py': 'from pkg.two import y\n',
        'pkg/two.py': 'DEEP = "reached only transitively"\n',
    })
    files, _h, _sub = INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])
    assert os.path.join('pkg', 'two.py') in files, sorted(files)


def test_CLOSURE_survives_a_CYCLE_and_the_alias_and_from_forms(tmp_path):
    """Import spellings must not change the answer, and a cycle must terminate
    at a fixed point without duplicating or losing a file."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': ('import pkg.plain\n'
                          'import pkg.aliased as al\n'
                          'from pkg.fromform import name\n'),
        'pkg/plain.py': 'P = "plain"\n',
        'pkg/aliased.py': 'A = "aliased"\n',
        'pkg/fromform.py': 'from pkg.cycle_a import z\n',
        'pkg/cycle_a.py': 'from pkg.cycle_b import z\nZ = "a"\n',
        'pkg/cycle_b.py': 'from pkg.cycle_a import Z\nz = "b"\n',
    })
    files, _h, _sub = INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])
    for rel in ('pkg/plain.py', 'pkg/aliased.py', 'pkg/fromform.py',
                'pkg/cycle_a.py', 'pkg/cycle_b.py'):
        assert rel.replace('/', os.sep) in files, (rel, sorted(files))
    assert len(files) == len(set(files)), 'a file was reached twice'


def test_CLOSURE_does_not_swallow_third_party_or_tests(tmp_path):
    """Only repo-local modules join. A third-party name has no repo path, and
    a test module is evidence, never production."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': ('import os\nfrom lxml import etree\n'
                          'from pkg.real import r\n'),
        'pkg/real.py': 'R = "real"\n',
        'pkg/core/test_a.py': 'from pkg.only_tests_use_me import q\n',
        'pkg/only_tests_use_me.py': 'Q = "test-only"\n',
    })
    files, _h, _sub = INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])
    assert os.path.join('pkg', 'real.py') in files
    assert not any('only_tests_use_me' in f for f in files), sorted(files)
    assert not any(f in ('os.py', 'lxml.py') for f in files), sorted(files)


def test_CLOSURE_FAILS_CLOSED_on_a_repo_local_edge_it_cannot_place(tmp_path):
    """Silently dropping an unplaceable repo-local edge is how a scope claims
    coverage it does not have. `pkg/` exists, so `pkg.missing` is repo-local —
    and it must raise rather than vanish."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': 'from pkg.missing import gone\n',
        'pkg/__init__.py': '',
    })
    with pytest.raises(AssertionError, match='cannot be placed'):
        INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])


def test_CLOSURE_FAILS_CLOSED_when_production_depends_on_a_test_module(tmp_path):
    """SEQ 445 A2. A file's NAME does not decide what it is. Once production
    imports `test_helper`, that module is a production dependency, and quietly
    filing it under `held` dropped it from the scanned set entirely — the same
    silent-omission defect the closure exists to remove. The live held set is
    empty, so failing closed costs nothing and forbids the hole."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': 'from pkg.test_helper import x\n',
        'pkg/test_helper.py': 'X = "reached only from production"\n',
    })
    with pytest.raises(AssertionError, match='test'):
        INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])


def test_CLOSURE_resolves_the_ORDINARY_PACKAGED_relative_form(tmp_path):
    """SEQ 445 A3. I implemented relative imports and never controlled them."""
    root = _tree(tmp_path, {
        'pkg/__init__.py': '',
        'pkg/core/__init__.py': '',
        'pkg/core/a.py': 'from .sib import s\nfrom ..helper import h\n',
        'pkg/core/sib.py': 'S = "sibling"\n',
        'pkg/helper.py': 'H = "one level up"\n',
    })
    files, _h, _sub = INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])
    assert os.path.join('pkg', 'core', 'sib.py') in files, sorted(files)
    assert os.path.join('pkg', 'helper.py') in files, sorted(files)


def test_CLOSURE_handles_a_NAMESPACE_package_directory(tmp_path):
    """SEQ 445 A3. `from .. import helper` where the parent has no
    `__init__.py` is ordinary Python. The package DIRECTORY is not a module
    file, so there is nothing to scan for it — but it is placeable, and
    raising 'cannot be placed' on it was wrong."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': 'from .. import helper\n',
        'pkg/helper.py': 'H = "namespace parent"\n',
    })
    files, _h, _sub = INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])
    assert os.path.join('pkg', 'helper.py') in files, sorted(files)


def test_ONE_SNAPSHOT_binds_rules_and_hashes_to_the_SAME_bytes(tmp_path):
    """SEQ 445 B1. Rules and manifest used to come from separate reads, so a
    file could change between them and the run would pair B's rules with A's
    hash. One read, both derived from it."""
    snap = INV.snapshot()
    assert snap, 'empty snapshot'
    rel, (bucket, text, sha) = sorted(snap.items())[0]
    assert hashlib.sha256(text.encode('utf-8')).hexdigest() == sha, rel
    # the rules really are built from the snapshot's text, not a re-read
    fake = dict(snap)
    victim = os.path.join('driver', 'core', 'driver_ids.py')
    assert victim in fake, sorted(fake)[:3]
    b, _t, _s = fake[victim]
    marker = 'SEQ445_SNAPSHOT_ONLY_MARKER'
    fake[victim] = (b, f'X = "{marker}"\n',
                    hashlib.sha256(f'X = "{marker}"\n'.encode()).hexdigest())
    rules = INV.decision_rules(INV.build(snap=fake))
    got = [r for r in rules if r['file'] == victim]
    assert len(got) == 1 and marker in got[0]['values'][0], got[:2]


def test_the_RAW_view_carries_no_duplicated_source(tmp_path):
    """SEQ 445 C. Source on every raw occurrence duplicated it 18x — 28.7M
    characters against 1.5M at rule level. The rule keeps the exact source;
    the serialized raw view must not repeat it."""
    p = tmp_path / 'dup.py'
    p.write_text('def f():\n    a, b = "one", "two"\n')
    rows = INV.scan(str(p))
    assert len(rows) == 2, rows
    rules = INV.decision_rules({'production': {'dup.py': rows}})
    assert all(r['stmt_source'].strip() for r in rules), rules
    for row in INV.raw_view(rows):
        assert 'stmt_source' not in row, row
        assert 'stmt_source_sha256' not in row, row
        assert row['stmt_id'], 'identity must survive the strip'


# ---------------------------------------------------------------------------
# SEQ 446: THE SECOND SCOPE CLASS — sys.path, not packages.
#
# `driver/core/driver_period_resolver.py` inserts
# `.claude/skills/earnings-orchestrator/scripts` into `sys.path` and then
# imports `fiscal_math` and `guidance_ids` by bare name; `unit_resolver.py`
# does the same for `guidance_ids`. A package walk finds no such module and
# files all three under "third party" — three REPO files, silently foreign.
#
# They are shared substrate under the frozen Core/Fiscal boundary: recorded and
# hash-bound, never scanned, edited or staged as #827 work.
# ---------------------------------------------------------------------------
def test_A_REPO_FILE_IS_NEVER_SILENTLY_THIRD_PARTY(tmp_path):
    """The general rule, not the three filenames. A name that matches a real
    file anywhere in the repo must be placed or declared held — never assumed
    foreign because an ordinary package walk missed it."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': ('import sys\n'
                          'sys.path.insert(0, "elsewhere")\n'
                          'import sneaky\n'),
        'elsewhere/sneaky.py': 'S = "reached only via sys.path"\n',
    })
    with pytest.raises(AssertionError, match='classified third party'):
        INV.production_closure(root=root, dirs=[os.path.join('pkg', 'core')])


def test_a_BARE_ENTRYPOINT_PATH_import_is_followed_not_called_third_party(tmp_path):
    """Found BY the check above, on the live tree: `import exact_numbers` in
    `driver/relocation/locator.py` was classified third party.

    CORRECTED (SEQ 447): my first explanation was wrong. Python does NOT put an
    imported module's own directory on `sys.path` — only the __main__ script's.
    `import driver.relocation.locator` from the repo root really does fail on
    that bare import. It resolves because the ACTIVE Route-A entry points
    insert the directory themselves (`run_code_tier.py:28`,
    `wp3_compliant_packet.py:17` add `driver/relocation`), which is the same
    class as the held Fiscal substrate: a search path an entry point creates.

    The closure resolves the bare name for that active route. The file it
    reaches today sits inside a root directory and was scanned by luck; one
    directory over it would have vanished exactly as `xml_names` did.
    """
    root = _tree(tmp_path, {
        'pkg/core/a.py': 'import neighbour\n',
        'pkg/core/neighbour.py': 'from pkg.faraway import deep\n',
        'pkg/faraway.py': 'DEEP = "reached only through the sibling"\n',
    })
    files, _h, sub = INV.production_closure(root=root,
                                            dirs=[os.path.join('pkg', 'core')])
    assert os.path.join('pkg', 'core', 'neighbour.py') in files, sorted(files)
    assert os.path.join('pkg', 'faraway.py') in files, sorted(files)
    assert not sub, sub


def test_a_ZERO_RULE_production_file_stays_in_the_CLOSURE(tmp_path):
    """SEQ 447 #2, synthetic half. A file that declares no literal is still an
    input: it is imported, it can gain a rule tomorrow, and its hash pins the
    run. Membership must not depend on row count."""
    root = _tree(tmp_path, {
        'pkg/core/a.py': 'from pkg.empty import nothing\n',
        'pkg/empty.py': 'def nothing():\n    pass\n',      # zero literals
    })
    files, _h, _s = INV.production_closure(root=root,
                                           dirs=[os.path.join('pkg', 'core')])
    assert os.path.join('pkg', 'empty.py') in files, sorted(files)
    assert not INV.scan(os.path.join(root, 'pkg', 'empty.py')), 'fixture must be zero-rule'


def test_a_ZERO_RULE_input_survives_into_the_SNAPSHOT_and_MANIFEST():
    """SEQ 447 #2, live half — the real guarantee, on real state.
    `driver/core/__init__.py` detects no literal at all, and it must still be
    read, hashed and manifested like every other input."""
    snap = INV.snapshot()
    victim = os.path.join('driver', 'core', '__init__.py')
    assert victim in snap, 'a zero-rule input vanished from the snapshot'
    _bucket, text, sha = snap[victim]
    assert hashlib.sha256(text.encode('utf-8')).hexdigest() == sha
    report = INV.build(snap)
    present = {f for fs in report.values() for f in fs}
    assert victim in present, 'a zero-rule input vanished from the report'
    assert report['production'][victim] == [], 'fixture must be zero-rule'


def test_a_GENUINELY_third_party_name_is_still_allowed(tmp_path):
    """The check must not turn every stdlib import into a failure."""
    root = _tree(tmp_path, {'pkg/core/a.py': 'import os\nfrom lxml import etree\n'})
    files, _h, sub = INV.production_closure(root=root,
                                            dirs=[os.path.join('pkg', 'core')])
    assert files and not sub, (sorted(files), sub)


def test_the_HELD_shared_substrate_is_named_bound_and_really_imported():
    """SEQ 446 points 1-3. Each held path exists, is hash-bound, and is reached
    by a real import edge from current production — a boundary map that
    outlived its edges would record ownership of nothing."""
    _files, _held, sub = INV.production_closure()
    expected = set(INV.HELD_SHARED_SUBSTRATE.values())
    assert set(sub) == expected, (sorted(sub), sorted(expected))
    for path, importers in sub.items():
        assert os.path.isfile(os.path.join(INV.ROOT, path)), path
        assert importers, path
        for imp in importers:
            assert imp.startswith(os.path.join('driver', 'core')), (path, imp)
    man = INV.held_substrate_manifest()
    assert set(man) == expected, sorted(man)
    for path, entry in man.items():
        with open(os.path.join(INV.ROOT, path), 'rb') as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == entry['sha256'], path
        # importer evidence is DERIVED from the closure, never hand-copied
        assert entry['imported_by'] == sorted(sub[path]), path
        assert entry['imported_by'], path


def test_the_HELD_substrate_is_NEVER_SCANNED_as_827_work(inventory):
    """Recorded is not the same as owned. Fiscal migration is held, so these
    files must not appear in any scanned bucket or contribute a single rule."""
    scanned = {f for fs in inventory.values() for f in fs}
    for path in INV.HELD_SHARED_SUBSTRATE.values():
        assert path not in scanned, f'held substrate was scanned: {path}'
    rules = INV.decision_rules(inventory)
    assert not [r for r in rules
                if r['file'] in set(INV.HELD_SHARED_SUBSTRATE.values())]


def test_CLOSURE_adds_xml_names_to_the_LIVE_production_scope():
    """The live consequence, stated as an identity rather than a count: the
    closure adds exactly the module the census found, and nothing unexplained."""
    dirs = INV.SCOPES['production']
    closed, _held, _sub = INV.production_closure()
    directory_only = set()
    for d in dirs:
        for dirpath, _dn, names in os.walk(os.path.join(INV.ROOT, d)):
            for n in sorted(names):
                if n.endswith('.py'):
                    directory_only.add(os.path.relpath(
                        os.path.join(dirpath, n), INV.ROOT))
    added = set(closed) - directory_only
    assert added == {os.path.join('driver', 'xml_names.py')}, sorted(added)


def test_the_INVENTORY_scans_the_closed_set_and_reaches_xml_names(inventory):
    """One closure, reused. The inventory's own production bucket must contain
    the reached module — deriving the set twice is how the two drift apart."""
    prod = set(inventory.get('production', {}))
    assert os.path.join('driver', 'xml_names.py') in prod, sorted(prod)[:5]
    rules = INV.decision_rules(inventory)
    reached = [r for r in rules
               if r['file'] == os.path.join('driver', 'xml_names.py')]
    assert reached, 'the module is scanned but contributes no rule'
    assert all(r['bucket'] == 'production' for r in reached), reached
    assert all(r['stmt_source'].strip() for r in reached), reached


def test_ONE_identity_never_carries_TWO_different_sources(inventory):
    """`(file, owner, stmt_id)` is the mapping key, so it must name exactly one
    statement. If two distinct statements ever folded into one key, a pin would
    silently describe the wrong code."""
    rules = INV.decision_rules(inventory)
    keys = [(r['file'], r['owner'], r['stmt_id']) for r in rules]
    assert len(keys) == len(set(keys)), 'the fold itself lost a rule'
