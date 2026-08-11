"""#827 Stage 3 — the fixed-value inventory, generated and DELIBERATELY UNFILTERED.

Records EVERY non-docstring literal — str, bytes, int, float — in the scoped
files, with its owning def/class and the AST context that uses it, so each can
be classified by hand against the permanent rule:

    every remaining fixed XML/XBRL/SEC value must come from an official
    normative standard (named by URL, version/date and section), and every
    non-standard product value from the frozen owner-approved contract.

NO CLEVER CANDIDATE FILTER. The first version of this file scored literals with
a regex for prefix- and regex-shaped text and called the result complete. That
filter WAS the classification it claimed not to perform: it silently dropped
plain semantic words (`segment`, `shares`, outcome and storage keys), every
numeric threshold and cap, and every byte literal — the exact rows this audit
exists to find. A list that certifies its own blind spots is worse than a long
one, so the only exclusion left is a docstring.

Manual classification is the point; this guarantees only that the candidate set
is complete and reproducible.

Read-only: parses files, writes one JSON receipt, touches no tracked source.
"""
import ast
import base64
import hashlib
import json
import os
import sys


def _repo_root(start):
    """Walk up to the directory that really holds `driver/` — counting `..`
    levels pointed one short and scanned an empty tree instead of failing."""
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, 'driver', 'core')):
            return d
        d = os.path.dirname(d)
    raise SystemExit('cannot find the repo root above ' + start)


ROOT = _repo_root(os.path.dirname(__file__))
_HERE = os.path.relpath(os.path.dirname(__file__), ROOT)

#: EVERY SCOPE THE REVIEWER NAMED. `production` and `seed_route_a` state rules
#: the product applies; `proof_tools` can encode a false law just as easily —
#: the false-green history is the reason they are audited, not trusted; and
#: `evidence` (fixtures/tests) is INCLUDED BUT LABELLED, never silently
#: dropped, because a fixture literal is what a filing said, not a rule.
SCOPES = {
    'production': [os.path.join('driver', 'core'),
                   os.path.join('driver', 'relocation')],
    'seed_route_a': [os.path.join('scripts', 'driver_seed')],
    'proof_tools': [_HERE],
}

#: THE ACTIVE SEED ROOTS, named by the #827 contract (reviewer ruling
#: 2026-08-02). This is the ONLY hand-written list, and it is an authority
#: statement rather than a scope: what gets scanned is DERIVED from it below.
#:
#: The scope used to BE a hand-written filename set, and its own coverage test
#: rebuilt the expected set from that same constant — so it proved the list
#: agreed with itself. It omitted `public_contract.py`,
#: `wp3_compliant_packet.py` and `build_packets.py` outright, and four more
#: files that the listed ones import directly.
SEED_ROOTS = (
    os.path.join('scripts', 'driver_seed', 'run_code_tier.py'),
    os.path.join('scripts', 'driver_seed', 'build_packets.py'),
    os.path.join('scripts', 'driver_seed', 'public_contract.py'),
    os.path.join('scripts', 'driver_seed', 'wp3_compliant_packet.py'),
    os.path.join('scripts', 'driver_seed', 'route_a_source.py'),
    os.path.join('scripts', 'driver_seed', 'locate.py'),
    os.path.join('scripts', 'driver_seed', 'relocate_probe', 'xbrl_lane.py'),
)


#: HELD SHARED SUBSTRATE — repo modules Core loads by inserting a directory
#: into `sys.path` at runtime, so an ordinary package walk cannot see them and
#: silently files them under "third party".
#:
#: `driver/core/driver_period_resolver.py` inserts
#: `.claude/skills/earnings-orchestrator/scripts` and imports `fiscal_math` and
#: `guidance_ids`; `driver/core/unit_resolver.py` locates the same directory
#: and imports `guidance_ids`.
#:
#: They are NOT Core-owned #827 work. The frozen Core/Fiscal boundary names
#: them read-only shared dependencies and Fiscal migration is held, so they are
#: RECORDED and HASH-BOUND, never scanned, edited or staged here. A frozen
#: map, not an environment resolver: this states ownership, not semantics.
HELD_SHARED_SUBSTRATE = {
    'fiscal_math': os.path.join(
        '.claude', 'skills', 'earnings-orchestrator', 'scripts', 'fiscal_math.py'),
    'guidance_ids': os.path.join(
        '.claude', 'skills', 'earnings-orchestrator', 'scripts', 'guidance_ids.py'),
    'guidance_write_cli': os.path.join(
        '.claude', 'skills', 'earnings-orchestrator', 'scripts',
        'guidance_write_cli.py'),
}

#: Directories that are not this repository's own source.
_NOT_SOURCE = {'.git', '__pycache__', 'node_modules', 'venv', '.venv',
               'site-packages', '.mypy_cache', '.pytest_cache'}


def _repo_py_index(root):
    """{basename without .py: [repo-relative paths]} for the whole repository.

    Exists for ONE question: was a name called "third party" while a file of
    that name sits in this repo? Answering it is what turns a silent
    misclassification into a failure.
    """
    index = {}
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _NOT_SOURCE]
        for n in names:
            if n.endswith('.py'):
                index.setdefault(n[:-3], []).append(
                    os.path.relpath(os.path.join(dirpath, n), root))
    return index


def _import_targets(root, rel):
    """Every module path one file imports, as REPO-RELATIVE dotted names.

    Unlike `_local_imports` this keeps the FULL dotted path, because that is
    what names a file: `from driver.xml_names import graph_qname_parts` points
    at `driver/xml_names.py`, and truncating to the first component (`driver`)
    loses exactly the module that escaped this audit's scope.

    Relative imports are resolved against the importing file's own package so
    nothing has to be imported or executed to place them.
    """
    try:
        tree = ast.parse(open(os.path.join(root, rel), encoding='utf-8').read())
    except (OSError, SyntaxError):
        return set()
    here = os.path.dirname(rel).split(os.sep) if os.path.dirname(rel) else []
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}          # alias is irrelevant
        elif isinstance(node, ast.ImportFrom):
            if node.level:                               # `from .x import y`
                base = here[:len(here) - node.level + 1]
                parts = base + (node.module.split('.') if node.module else [])
                out.add('.'.join(parts))
                out |= {'.'.join(parts + [a.name]) for a in node.names}
            elif node.module:
                out.add(node.module)
                # `from pkg import mod` may name a SUBMODULE, not an attribute
                out |= {node.module + '.' + a.name for a in node.names}
    return {m for m in out if m}


def _place(root, dotted):
    """The repo file a dotted name refers to, '' if it is not repo-local, or
    None if it LOOKS repo-local and cannot be placed.

    The three-way answer is the point. Returning '' for both "third party" and
    "repo module I could not find" is what lets a scope quietly shed an edge.
    """
    parts = dotted.split('.')
    for cand in (os.path.join(*parts) + '.py',
                 os.path.join(*parts, '__init__.py')):
        if os.path.isfile(os.path.join(root, cand)):
            return cand
    head = parts[0]
    if (os.path.isdir(os.path.join(root, head))
            or os.path.isfile(os.path.join(root, head + '.py'))):
        # A PACKAGE DIRECTORY IS PLACEABLE AND HAS NOTHING TO SCAN. `from ..
        # import helper` in a namespace package (no `__init__.py`) names the
        # parent DIRECTORY, which is ordinary Python; raising "cannot be
        # placed" on it treated a standard form as corruption. Its submodules
        # are named separately and are followed on their own.
        if os.path.isdir(os.path.join(root, *parts)):
            return ''
        # `from pkg import some_name` where the name is an ATTRIBUTE of an
        # already-placed module, not a module — the parent carries it.
        if len(parts) > 1:
            for cand in (os.path.join(*parts[:-1]) + '.py',
                         os.path.join(*parts[:-1], '__init__.py')):
                if os.path.isfile(os.path.join(root, cand)):
                    return ''
        return None                                      # repo-local, unplaced
    return ''                                            # third party


def production_closure(root=None, dirs=None):
    """(files, held) — the production roots' transitive repo-local closure.

    THE SCOPE USED TO BE TWO DIRECTORY NAMES, and `driver/xml_names.py` proved
    what that costs: two production functions, imported by four scanned
    production modules, one directory up and therefore invisible. Law had been
    moved there OUT of an audited file DURING the audit, so the inventory
    recorded the rules as gone and nothing recorded them as arrived.

    Derived, like `seed_closure`, so a future move cannot escape. Test files
    are evidence, never production, so they are neither roots nor followed.
    """
    root = ROOT if root is None else root
    dirs = SCOPES['production'] if dirs is None else dirs
    stack, files = [], set()
    for d in dirs:
        for dirpath, _dn, names in os.walk(os.path.join(root, d)):
            for name in sorted(names):
                if name.endswith('.py') and not name.startswith('test_'):
                    stack.append(os.path.relpath(
                        os.path.join(dirpath, name), root))
    held, substrate, index = {}, {}, _repo_py_index(root)
    while stack:                                    # fixed point; cycles fine
        rel = stack.pop()
        if rel in files:
            continue
        files.add(rel)
        for dotted in sorted(_import_targets(root, rel)):
            placed = _place(root, dotted)
            assert placed is not None, (
                f'repo-local import {dotted!r} in {rel} cannot be placed — '
                f'refusing to claim a scope that silently drops an edge')
            if placed == '':
                # A BARE NAME RESOLVED BY AN ENTRY POINT'S SEARCH PATH.
                #
                # CORRECTED (SEQ 447): this is NOT general Python behaviour.
                # Python puts the __main__ SCRIPT's directory on `sys.path`,
                # not an imported module's own directory — `import
                # driver.relocation.locator` from the repo root really does
                # fail on its bare `import exact_numbers`. It works because
                # the active Route-A entry points insert that directory
                # themselves: `scripts/driver_seed/run_code_tier.py:28` and
                # `wp3_compliant_packet.py:17` add `driver/relocation`.
                #
                # So this is the same class as the held substrate above — a
                # search path an entry point creates — and it is resolved for
                # the active route only, never as a general resolver. The file
                # it reaches today sits inside a root directory and so was
                # scanned by luck, not by the closure.
                sibling = os.path.join(os.path.dirname(rel),
                                       *dotted.split('.')) + '.py'
                if os.path.isfile(os.path.join(root, sibling)):
                    if sibling not in files:
                        stack.append(sibling)
                    continue
                # NOT-PLACED IS NOT THE SAME AS NOT-OURS. Core adds a local
                # directory to `sys.path` and imports repo modules by bare
                # name, so a package walk calls them third party. Any name
                # that matches a real file in this repository must be either
                # placed or explicitly HELD — never assumed foreign.
                if dotted in HELD_SHARED_SUBSTRATE:
                    substrate.setdefault(HELD_SHARED_SUBSTRATE[dotted],
                                         set()).add(rel)
                elif dotted in index:
                    raise AssertionError(
                        f'{dotted!r} imported by {rel} was classified third '
                        f'party, but this repo holds {index[dotted]} — place '
                        f'it or declare it held; do not guess')
                continue
            if placed not in files:
                if os.path.basename(placed).startswith('test_'):
                    held.setdefault(placed, set()).add(rel)
                else:
                    stack.append(placed)
    # A FILENAME DOES NOT DECIDE WHAT A FILE IS. Once production imports a
    # `test_*` module it IS a production dependency, and filing it under `held`
    # dropped it from the scanned set silently — the very omission this closure
    # replaced a directory scope to prevent. The live held set is empty, so
    # refusing costs nothing today and forbids the hole tomorrow.
    assert not held, (
        f'production depends on test modules, which cannot be silently '
        f'omitted: {sorted(held)}')
    # Every declared held path must EXIST and be really imported — a boundary
    # map that outlived its edges would record ownership of nothing.
    for path, importers in substrate.items():
        assert os.path.isfile(os.path.join(root, path)), \
            f'held shared-substrate path is missing: {path}'
        assert importers, f'held path with no importer: {path}'
    return files, held, substrate


def held_substrate_manifest(root=None):
    """{path: {sha256, imported_by}} for the held shared substrate.

    BOUND BUT NEVER SCANNED. These files are read-only shared dependencies
    under the frozen Core/Fiscal boundary, so the proof records exactly which
    bytes it saw and which production files put them in the boundary — and the
    importer evidence is DERIVED from the closure, never hand-copied, so a map
    that outlived its edges cannot look healthy.
    """
    root = ROOT if root is None else root
    _f, _h, substrate = production_closure(root=root)
    man = {}
    for path in sorted(substrate):
        with open(os.path.join(root, path), 'rb') as fh:
            man[path] = {'sha256': hashlib.sha256(fh.read()).hexdigest(),
                         'imported_by': sorted(substrate[path])}
    return man


def _local_imports(rel):
    """The module names one file imports, whatever their origin."""
    try:
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding='utf-8').read())
    except (OSError, SyntaxError):
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            names.add(node.module.split('.')[0])
    return names


def seed_closure():
    """(scanned, held) — the seed roots' repo-local import closure, and every
    edge that leaves the seed tree.

    A closure that stopped silently at a directory boundary would be the same
    defect as the hand-written list: it would report a scope it had not
    justified. So an import that resolves OUTSIDE the seed tree is not dropped
    — it is returned in `held`, named, for the reviewer to place. `held` edges
    are NOT followed: they belong to another owner's scope, not this one.
    """
    seed_base = os.path.join(ROOT, 'scripts', 'driver_seed')
    index = {}
    for dirpath, _d, names in os.walk(seed_base):
        for name in names:
            if name.endswith('.py'):
                index.setdefault(name[:-3], []).append(
                    os.path.relpath(os.path.join(dirpath, name), ROOT))
    scanned, held, stack = set(), {}, list(SEED_ROOTS)
    while stack:
        rel = stack.pop()
        if rel in scanned or not os.path.exists(os.path.join(ROOT, rel)):
            continue
        scanned.add(rel)
        here = os.path.dirname(rel)
        for mod in _local_imports(rel):
            hits = index.get(mod)
            if not hits:
                # Not in the seed tree. Repo-local or third-party is decided by
                # whether the repo holds a module of that name at all.
                for cand in (os.path.join('driver', 'core', mod + '.py'),
                             os.path.join('driver', 'relocation', mod + '.py'),
                             os.path.join('scripts', 'earnings', mod + '.py')):
                    if os.path.exists(os.path.join(ROOT, cand)):
                        held.setdefault(cand, set()).add(rel)
                        break
                continue
            # prefer a sibling; an unambiguous name resolves anywhere
            for cand in hits:
                if os.path.dirname(cand) == here or len(hits) == 1:
                    stack.append(cand)
    return scanned, held


#: Derived once at import: what the scanner covers, and what it deliberately
#: does not follow.
SEED_FILES, HELD_DEPENDENCIES = seed_closure()


def _docstring_nodes(tree):
    """The Constant nodes that are docstrings — the one lawful exclusion."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, 'body', None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def _binding(node):
    """The NEAREST enclosing assignment target — the rule that owns this
    literal — walking out through any expression at all.

    Distinct from the immediate use, and both are kept. `_table_name` only
    escaped collection literals, so a pattern inside `re.compile(...)` or a
    literal inside a call inside a table reported no owning rule; a grammar
    with no name attached cannot be classified, only guessed at.
    """
    # UNBOUNDED, to the definition or module boundary. Both this and the
    # deleted `_table_name` carried arbitrary depth caps (40 and 8), which
    # could silently miss exactly the deeply nested literal a tool that
    # promises never to miss one must reach. Parent links form a finite tree,
    # so the walk terminates on its own; the caps bought nothing and risked
    # the tool's only claim.
    while node is not None:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            return names[0] if names else ''
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            return node.target.id
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Module)):
            return ''                          # never cross a definition
        node = getattr(node, '_parent', None)
    return ''


def _stmt_line(node):
    """The line of the nearest enclosing STATEMENT.

    An unassigned comparison or call has no name to group under, but it does
    have one statement that owns it — that statement is the decision, and all
    the literals inside it are its members.
    """
    while node is not None:
        if isinstance(node, ast.stmt):
            return node.lineno
        node = getattr(node, '_parent', None)
    return 0


def _owner_label(node):
    """The owner's SIMPLE NAME — the same label the folded rule key carries.
    SEQ 284: scoping the duplicate ordinal by the owning AST *object* while
    the rule key held only this name let two same-named functions with one
    identical statement merge into a single rule (7 merged keys / 8 lost
    rules in the live scope). The ordinal scope must equal the key's own
    owner label."""
    node = getattr(node, '_parent', None)
    while node is not None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            return node.name
        node = getattr(node, '_parent', None)
    return ''


def _shallow_dump(root):
    """SEQ 281: the fingerprint text of ONE statement — the statement ITSELF
    with every DESCENDANT statement omitted. A compound `if`/`for`/`try` keeps
    its header expressions, names, operators and literals, but its body
    statements are their own rules; including them made a child edit move the
    unchanged parent's id. Generic recursion, no body-field allowlist; no
    line/column attributes anywhere."""
    def ser(x):
        if isinstance(x, ast.AST):
            if isinstance(x, ast.stmt) and x is not root:
                return None                    # a descendant rule, not ours
            fields = ', '.join(f'{name}={ser(value)}'
                               for name, value in ast.iter_fields(x))
            return f'{type(x).__name__}({fields})'
        if isinstance(x, list):
            kept = [s for s in (ser(i) for i in x) if s is not None]
            return '[' + ', '.join(kept) + ']'
        return repr(x)
    return ser(root)


def _stable_stmt_ids(tree):
    """SEQ 278 §2 + SEQ 281: THE one statement identity — the FULL 64-hex
    SHA-256 of the normalized shallow statement dump (no line/column
    attributes, no descendant statement bodies), plus an occurrence ordinal
    ONLY to keep fingerprint-identical statements under one owner LABEL
    distinct — the exact label the rule key carries (SEQ 284). Ordinals count
    in deterministic tree order within (owner label, digest), so an edit
    elsewhere never renumbers a neighbour.
    `stmt_line` stays DISPLAY metadata on the row, never identity: one import
    shift renumbered 1,595 rules under the line identity and buried the real
    packet delta."""
    ids, counts = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            h = hashlib.sha256(_shallow_dump(node).encode()).hexdigest()
            key = (_owner_label(node), h)
            n = counts.get(key, 0)
            counts[key] = n + 1
            ids[id(node)] = f'{type(node).__name__}:{h}:{n}'
    return ids


def _stmt_node(node):
    """The nearest enclosing statement NODE.

    SEQ 443: THE ONLY WALKER. A mapper that wanted a rule's exact text used to
    re-find this statement from `(file, owner, stmt_id)` with its own walk, and
    the two disagreed on 27 of 3,529 mandatory rules — every one a function
    header, where this file takes the owner from the LINE MAP at the literal's
    line while the other walk climbed parents to the enclosing def. Identity
    and source now come from one traversal, so there is nothing to re-derive
    and nothing to disagree with.
    """
    while node is not None:
        if isinstance(node, ast.stmt):
            return node
        node = getattr(node, '_parent', None)
    return None


def _stmt_identity(node, stable_ids):
    """The nearest enclosing statement's stable id from `_stable_stmt_ids`."""
    stmt = _stmt_node(node)
    return stable_ids[id(stmt)] if stmt is not None else ''


def _stmt_source(src, stmt):
    """The statement's own source, INCLUDING its decorators.

    THE RECORDED SOURCE MUST COVER EXACTLY WHAT THE IDENTITY COVERS.
    `_shallow_dump` fingerprints `decorator_list` — decorators are expressions,
    not descendant statements — so editing `@register('A')` to `@register('B')`
    moves `stmt_id`. But `FunctionDef.lineno` is the `def` line, so
    `ast.get_source_segment` starts BELOW the decorators and would report
    unchanged text for a changed rule. Measured, not assumed: the id moves and
    the plain segment does not contain the decorator.

    A decorator is required to sit at the statement's own indentation, so the
    statement's `col_offset` is exactly where its `@` begins.
    """
    decs = getattr(stmt, 'decorator_list', None) or []
    if not decs:
        return ast.get_source_segment(src, stmt) or ''
    lines = src.splitlines(keepends=True)
    chunk = lines[min(d.lineno for d in decs) - 1:stmt.end_lineno]
    chunk[-1] = chunk[-1][:stmt.end_col_offset]
    chunk[0] = chunk[0][stmt.col_offset:]
    return ''.join(chunk)


def _use_context(parent, node, binding):
    """How the literal is USED — the thing that turns a string into a rule.
    A bare value list cannot show that `"segment"` is a `startswith` test or a
    membership table, and that is precisely what has to be classified."""
    if parent is None:
        return 'module'
    if isinstance(parent, ast.Compare):
        return 'compare'
    if isinstance(parent, ast.Call):
        fn = parent.func
        if isinstance(fn, ast.Attribute):
            return f'call:{fn.attr}'          # startswith, split, partition...
        if isinstance(fn, ast.Name):
            return f'call:{fn.id}'
        return 'call'
    if isinstance(parent, (ast.Set, ast.List, ast.Tuple, ast.Dict)):
        if isinstance(parent, ast.Dict):
            kind = ('dict-key' if any(k is node for k in parent.keys)
                    else 'dict-value')
        else:
            kind = 'membership-table'
        # ONE ancestry algorithm, not two: the table's name IS its binding.
        return f'{kind}:{binding}' if binding else kind
    if isinstance(parent, (ast.Subscript, ast.Slice)):
        return 'index'
    if isinstance(parent, ast.Assign):
        names = [t.id for t in parent.targets if isinstance(t, ast.Name)]
        return f'assign:{names[0]}' if names else 'assign'
    if isinstance(parent, ast.keyword):
        return f'kwarg:{parent.arg}'
    if isinstance(parent, ast.BinOp):
        return 'binop'
    if isinstance(parent, (ast.JoinedStr, ast.FormattedValue)):
        return 'fstring'
    if isinstance(parent, ast.Return):
        return 'return'
    return type(parent).__name__.lower()


def _owner_map(tree, n_lines):
    owner = [''] * (n_lines + 2)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            end = getattr(node, 'end_lineno', node.lineno)
            for ln in range(node.lineno, min(end, n_lines) + 1):
                owner[ln] = node.name          # inner defs overwrite outer
    return owner


def scan(path):
    """Convenience: read the file and scan it. The proof path uses
    `snapshot()` + `scan_source` so rules and hashes come from ONE read."""
    return scan_source(open(path, encoding='utf-8').read(), path)


def scan_source(src, path):
    tree = ast.parse(src, filename=path)
    owner, docs = _owner_map(tree, src.count('\n') + 1), _docstring_nodes(tree)
    for parent in ast.walk(tree):            # one parent link pass
        for child in ast.iter_child_nodes(parent):
            child._parent = parent
    stable_ids = _stable_stmt_ids(tree)      # SEQ 278 §2: content identity
    # A SIGNED NUMBER IS NOT A `Constant`. Python parses `-4` as `USub` applied
    # to `4`, so walking constants alone reported the MAGNITUDE and named the
    # use after the wrapper (`unaryop`) instead of the statement that owns the
    # decision — `decimals="-4"`-class rules were being classified from the
    # wrong number. Here the wrapper IS the literal: it carries the value, the
    # line and the owning statement, and the constant inside it is replaced
    # rather than added, so one rule can never be counted twice.
    # `bool` is deliberately excluded: `-True` is an integer expression, and
    # this inventory keeps booleans as booleans.
    signed = {id(n.operand): n for n in ast.walk(tree)
              if isinstance(n, ast.UnaryOp)
              and isinstance(n.op, (ast.USub, ast.UAdd))
              and isinstance(n.operand, ast.Constant)
              and isinstance(n.operand.value, (int, float))
              and not isinstance(n.operand.value, bool)}
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or id(node) in docs:
            continue
        # BOOLEANS ARE FIXED DECISION VALUES TOO, and some of the most
        # consequential ones in this tree: `recover=False` decides whether a
        # malformed filing is repaired, `no_network=True` decides whether
        # parsing can reach the network, and a divide flag decides which unit
        # branch a fact enters. I excluded them and then described the result
        # as an inventory of every fixed decision value — it could not be both.
        #
        # `None` stays out, and only `None`: it is the language's absence
        # marker, not a decision, and admitting it would bury the worklist in
        # thousands of default arguments that state nothing.
        if node.value is None or not isinstance(
                node.value, (str, bytes, int, float, bool)):
            continue
        wrap = signed.get(id(node))
        if wrap is None:
            value = node.value
        else:
            value = -node.value if isinstance(wrap.op, ast.USub) else node.value
            node = wrap                      # the wrapper is the literal now
        parent = getattr(node, '_parent', None)
        binding = _binding(parent)
        # SEQ 443: the rule carries its own text, minted by the SAME walk that
        # mints its identity. A consumer never re-finds the statement, so it
        # can never re-find a different one.
        stmt = _stmt_node(parent)
        stmt_src = _stmt_source(src, stmt) if stmt is not None else ''
        row = {
            'line': node.lineno,
            'owner': owner[node.lineno] if node.lineno < len(owner) else '',
            'type': type(value).__name__,
            'use': _use_context(parent, node, binding),
            # THE RULE THIS LITERAL BELONGS TO, not just the shape around it.
            'binding': binding,
            # ...and, when it has no name, the statement that owns it —
            # by CONTENT identity; stmt_line is display metadata only.
            'stmt_line': _stmt_line(parent),
            'stmt_id': _stmt_identity(parent, stable_ids),
            'stmt_source': stmt_src,
            'stmt_source_sha256': hashlib.sha256(stmt_src.encode()).hexdigest(),
            'length': len(value) if isinstance(value, (str, bytes)) else None,
        }
        # EXACT AND LOSSLESS. The previous `[:160]` was a silent cap that could
        # cut away the very substring under classification, and bytes were
        # decoded latin-1 and presented as if they were the source text — a
        # byte pattern is not text and must not be shown as one.
        if isinstance(value, bytes):
            row['value_b64'] = base64.b64encode(value).decode('ascii')
        else:
            row['value'] = value if isinstance(value, str) else repr(value)
        rows.append(row)
    return rows


def _files_for(scope, dirs):
    # SEQ 444: production is an import CLOSURE, not a directory walk, and this
    # is the ONE place the set is produced. Deriving it again downstream is how
    # the manifest and the inventory would come to disagree.
    if scope == 'production':
        closed, _held, _substrate = production_closure()
        for rel in sorted(closed):
            name = os.path.basename(rel)
            bucket = 'evidence' if name.startswith('test_') else scope
            yield bucket, rel, os.path.join(ROOT, rel)
        # the roots' own test files are evidence and still belong to the record
        for d in dirs:
            for dirpath, _dn, names in os.walk(os.path.join(ROOT, d)):
                for name in sorted(names):
                    if name.endswith('.py') and name.startswith('test_'):
                        full = os.path.join(dirpath, name)
                        yield 'evidence', os.path.relpath(full, ROOT), full
        return
    for d in dirs:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirnames, names in os.walk(base):
            for name in sorted(names):
                if not name.endswith('.py'):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, ROOT)
                if scope == 'seed_route_a' and rel not in SEED_FILES:
                    # DERIVED, not declared: `SEED_FILES` is the import closure
                    # of the contract's named roots. A file in the seed tree
                    # that no active root reaches is history, and history is not
                    # this inventory's subject.
                    continue
                # EVIDENCE IS SPLIT OUT, NOT DROPPED.
                bucket = 'evidence' if name.startswith('test_') else scope
                yield bucket, rel, full


#: Fields the RULE carries and the raw occurrence must not repeat.
_SOURCE_FIELDS = ('stmt_source', 'stmt_source_sha256')


def raw_view(rows):
    """The raw occurrences WITHOUT the duplicated source.

    SEQ 445 C, measured: the exact source on every occurrence was 28.7M
    characters across 31,449 rows against 1.5M at rule level — the same text
    18 times over. The rule is where a statement's source belongs, because the
    rule IS the statement; an occurrence only points at one. Identity stays on
    the row, so nothing is lost and the receipt sheds ~29MB.
    """
    return [{k: v for k, v in row.items() if k not in _SOURCE_FIELDS}
            for row in rows]


def snapshot():
    """{rel: (bucket, text, sha256)} — every input read EXACTLY ONCE.

    SEQ 445 B1: the manifest and the rules used to come from separate walks,
    so a file edited between them produced rules from one version paired with
    the hash of another, and nothing could detect it. Both now derive from
    these bytes. (Verified: no input uses CRLF, so decoding the bytes is
    text-identical to a newline-translating text read.)
    """
    snap = {}
    for scope, dirs in SCOPES.items():
        for bucket, rel, full in _files_for(scope, dirs):
            with open(full, 'rb') as fh:
                data = fh.read()
            snap[rel] = (bucket, data.decode('utf-8'),
                         hashlib.sha256(data).hexdigest())
    return snap


def build(snap=None):
    # EVERY YIELDED FILE IS RETAINED, including one that scans to zero rows.
    # Dropping empties made `report` a record of files WITH literals rather
    # than files SCANNED, so the manifest derived from it silently omitted
    # `driver/core/__init__.py` — 104 inputs, 103 listed. An input that
    # contributed nothing is still an input, and its hash still pins the run.
    snap = snapshot() if snap is None else snap
    report = {}
    for rel, (bucket, text, _sha) in snap.items():
        report.setdefault(bucket, {})[rel] = scan_source(
            text, os.path.join(ROOT, rel))
    return report


def decision_rules(report):
    """THE CLASSIFICATION VIEW: one row per RULE, built from the raw rows.

    Every member of `_CANDIDATE_EXACT` is not eight adjudications, it is one.
    So a row is keyed by the thing that OWNS the decision:

      * a named assignment/table  -> the name, carrying all member values;
      * anything unnamed          -> its nearest STATEMENT (owner + stable
                                     content id), carrying every literal in
                                     that statement.

    EVERY VALUE IS KEPT. An earlier draft capped members at 40 — the same
    silent-truncation defect this audit had just removed from the raw view,
    reintroduced one layer up, where it would have hidden members of exactly
    the big tables most needing classification.

    `covered` counts the raw deciding rows folded into each row, so the view
    is mechanically checkable against the raw record and cannot lose a member.
    """
    rules = {}
    for bucket, files in report.items():
        for rel, rows in files.items():
            for r in rows:
                # THE STATEMENT IS THE IDENTITY. `binding` is only a label:
                # two functions may each bind a local `d`, and one function may
                # reassign `key` twice, so keying on the name would silently
                # merge unrelated rules into one adjudication.
                key = (bucket, rel, r['owner'], r['stmt_id'])
                rule = rules.setdefault(key, {
                    'bucket': bucket, 'file': rel,
                    'owner': r['owner'] or '<module>',
                    'stmt_id': r['stmt_id'],
                    'stmt_line': r['stmt_line'],
                    'stmt_source': r['stmt_source'],
                    'stmt_source_sha256': r['stmt_source_sha256'],
                    'bindings': set(), 'uses': set(),
                    'values': [], 'lines': [], 'covered': 0})
                # ONE IDENTITY, ONE STATEMENT. If two different statements ever
                # folded into a single key, every pin naming that key would
                # describe the wrong code — silently. It is cheap to check and
                # unrecoverable to miss, so it raises instead of being counted.
                if rule['stmt_source_sha256'] != r['stmt_source_sha256']:
                    raise AssertionError(
                        f'one rule key holds two different statements: '
                        f'{rel} {r["owner"]!r} {r["stmt_id"]}')
                if r['binding']:
                    rule['bindings'].add(r['binding'])
                rule['uses'].add(r['use'])
                # EXPLICIT, not `dict.get(k, default)`: the default expression
                # is evaluated even when the key is present, so the b64 lookup
                # raised on every ordinary string row.
                rule['values'].append(r['value'] if 'value' in r
                                      else 'b64:' + r['value_b64'])
                rule['lines'].append(r['line'])
                rule['covered'] += 1
    out = []
    for rule in rules.values():
        rule['uses'] = sorted(rule['uses'])
        rule['bindings'] = sorted(rule['bindings'])
        rule['lines'] = sorted(set(rule['lines']))
        rule['values'] = sorted(set(rule['values']))       # complete, uncapped
        out.append(rule)
    return sorted(out, key=lambda r: (r['bucket'], r['file'], r['lines'][0]))


def main():
    snap = snapshot()                 # ONE read; rules and hashes share it
    report = build(snap)
    totals = {b: sum(len(r) for r in fs.values()) for b, fs in report.items()}
    rules = decision_rules(report)
    # COVERAGE, PER BUCKET AND OVERALL. Every raw occurrence must fold into
    # exactly one rule. This is the whole guarantee: with no prefilter left,
    # equality here means the rule view cannot hide a literal from review.
    per_bucket = {}
    for r in rules:
        per_bucket[r['bucket']] = per_bucket.get(r['bucket'], 0) + r['covered']
    assert per_bucket == totals, f'coverage mismatch {per_bucket} != {totals}'

    # THE MANIFEST IS DERIVED FROM WHAT WAS ACTUALLY SCANNED, not from a
    # re-walk that could disagree: `report` is keyed by the very files these
    # counts came from. Without it, a later reader cannot tell whether a
    # changed total means changed code or a changed file set — which is exactly
    # the ambiguity that made a +5,977 delta unreadable.
    here = os.path.dirname(__file__)
    # SEQ 445 B1: the hashes come from THE SAME READ the rules came from.
    # Re-opening each file here was a second walk, so a file changed between
    # the two produced rules from one version stamped with another's hash.
    manifest = {rel: sha for rel, (_b, _t, sha) in snap.items()}
    assert set(manifest) == {f for fs in report.values() for f in fs}, \
        'manifest and report disagree about what was scanned'
    with open(os.path.abspath(__file__), 'rb') as fh:
        generator_sha = hashlib.sha256(fh.read()).hexdigest()

    inv_path = os.path.join(here, '21_hardcoding_inventory.json')
    with open(inv_path, 'w', encoding='utf-8') as fh:
        json.dump({'buckets': sorted(report), 'totals': totals,
                   'occurrences': sum(totals.values()),
                   'generator': os.path.basename(__file__),
                   'generator_sha256': generator_sha,
                   'scanned_files': len(manifest),
                   'input_manifest_sha256': manifest,
                   # SEQ 447: the held shared substrate is RECORDED by the
                   # proof, not merely by a test. Unscanned and unowned, but
                   # its exact bytes and the production files that reach it
                   # are on the record, so "we did not audit these" is a
                   # verifiable statement rather than an omission.
                   'held_shared_substrate': held_substrate_manifest(),
                   # SEQ 445 C: the raw view points AT statements; the rule
                   # view IS the statement and carries its exact source once.
                   'by_bucket': {b: {rel: raw_view(rows)
                                     for rel, rows in fs.items()}
                                 for b, fs in report.items()}},
                  fh, indent=1, sort_keys=True)
    # 22 BINDS TO 21 BY HASH rather than repeating the manifest: one copy, and
    # a mismatch is detectable instead of two lists drifting apart silently.
    with open(inv_path, 'rb') as fh:
        inventory_sha = hashlib.sha256(fh.read()).hexdigest()
    with open(os.path.join(here, '22_decision_rules.json'), 'w',
              encoding='utf-8') as fh:
        json.dump({'rules': len(rules),
                   'occurrences': sum(totals.values()),
                   'covered': sum(r['covered'] for r in rules),
                   'generator': os.path.basename(__file__),
                   'generator_sha256': generator_sha,
                   'derived_from': '21_hardcoding_inventory.json',
                   'derived_from_sha256': inventory_sha,
                   'coverage_by_bucket': per_bucket,
                   'rules_by_bucket': {
                       b: sum(1 for r in rules if r['bucket'] == b)
                       for b in sorted(report)},
                   'worklist': rules}, fh, indent=1, sort_keys=True)
    audit = [r for r in rules if r['bucket'] != 'evidence']
    print(f'occurrences {sum(totals.values())} (all covered)'
          f' -> statement rules {len(rules)}'
          f'   to adjudicate, excluding evidence: {len(audit)}')
    for b in sorted(report):
        print(f'   {b:14} {totals[b]:6d} literals'
              f'  {sum(1 for r in rules if r["bucket"] == b):5d} rules')
    return 0


if __name__ == '__main__':
    sys.exit(main())
