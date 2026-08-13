"""MACHINE-ENFORCED GATE — mechanical patterns allowed, meaning-based ones fail.

The rule (owner, P0): keep in CODE only what is provably correct across ALL
unseen input. A regex that checks the SHAPE of a string we generate is
mechanical and fine. A regex, fuzzy matcher, or keyword list that decides what
source text MEANS is not — it passes our samples and misfires silently on the
universe, which is how `_NUMY`, `PERSHARE_HINT` and the 20-char `_overlap`
window got in.

THE SCOPE IS DERIVED, NEVER HAND-WRITTEN. An earlier version of this gate listed
files by hand and gave a FALSE CLEAN twice over: it omitted `fact16_checks`
(which `score_exp5` imported at the time, so `_NUMY` was live while the gate
reported "zero exam patterns" — that module is now DELETED, but the lesson is
the hand-written list, not the file), and it walked imports with the heuristic
`if "driver" in name`,
which silently dropped `guidance_ids` (imported by `driver_period_resolver`).
A gate that reports clean while a semantic pattern is reachable is worse than no
gate — so the closure below is computed by FOLLOWING ACTUAL IMPORTS from the real
entry points and resolving each to a file in this repo.

Run: venv/bin/python -m pytest harness/test_no_semantic_patterns.py -q
"""
import ast
import os

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))

# The real entry points. Everything they reach, transitively, is in scope.
ENTRY_PRODUCTION = [os.path.join(_REPO, "driver", "core", "driver_write_cli.py")]
ENTRY_EXAM = [os.path.join(_HERE, "kf_lint.py"),
              os.path.join(_HERE, "raw_transport.py"),
              os.path.join(_HERE, "scorers", "score_exp5.py")]

# Where an imported module name may resolve to a file (the roots the code itself
# puts on sys.path). Ordered; first hit wins.
_SEARCH_ROOTS = [
    os.path.join(_REPO, "driver", "core"),
    _HERE,
    os.path.join(_HERE, "scorers"),
    os.path.join(_REPO, ".claude", "skills", "earnings-orchestrator", "scripts"),
    _REPO,
]

_RE_FUNCS = ("compile", "search", "match", "findall", "sub", "fullmatch",
             "finditer", "split", "subn")
FUZZY_TOKENS = ("difflib", "SequenceMatcher", "fuzz", "levenshtein",
                "jaro", "soundex", "get_close_matches")


def _resolve(modname, rel_roots=None):
    """Module name -> file in THIS repo, or None if stdlib/third-party.
    `rel_roots` resolves RELATIVE imports against the importing package dir —
    an earlier version ignored `from .utils` entirely."""
    tail = modname.split(".")[-1]
    for root in (rel_roots or []) + _SEARCH_ROOTS:
        for cand in (os.path.join(root, *modname.split(".")) + ".py",
                     os.path.join(root, tail + ".py")):
            if os.path.exists(cand) and "worktrees" not in cand:
                return os.path.realpath(cand)
    return None


def closure(entries):
    """Transitive import closure by FOLLOWING REAL IMPORTS (no name heuristics,
    no hand-written lists). Returns {realpath: module_basename}."""
    seen, stack = {}, list(entries)
    while stack:
        path = os.path.realpath(stack.pop())
        if path in seen or not os.path.exists(path):
            continue
        seen[path] = os.path.basename(path)[:-3]
        pkg = os.path.dirname(path)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            names, rel_roots = [], None
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:                      # RELATIVE: from .utils / from . import x
                    base = pkg
                    for _ in range(node.level - 1):
                        base = os.path.dirname(base)
                    rel_roots = [base]
                    names = ([node.module] if node.module
                             else [a.name for a in node.names])   # `from . import x`
                elif node.module:
                    names = [node.module]
            elif isinstance(node, ast.Call):        # literal dynamic import
                f = node.func
                nm = (f.id if isinstance(f, ast.Name) else
                      f.attr if isinstance(f, ast.Attribute) else None)
                if nm in ("import_module", "__import__") and node.args:
                    a0 = node.args[0]
                    if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                        names = [a0.value]
            for n in names:
                dep = _resolve(n, rel_roots)
                if dep and dep not in seen:
                    stack.append(dep)
    return seen


def regex_patterns(path):
    """Every regex call site as a [function, operation, pattern] triple.

    Approval is PER SITE, not per module: a module blessed as "mechanical"
    (e.g. guidance_ids) could otherwise absorb a NEW semantic regex silently.
    The OPERATION is part of the freeze because pattern text alone gave a
    FALSE GREEN (reviewer-proven): `re.sub` swapped to `re.search` keeps the
    pattern byte-identical while changing a rewrite into a meaning probe.
    The enclosing FUNCTION pins where the site lives; the pattern record (not
    line numbers) keeps the freeze stable under edits above it.

    THE PATTERN RECORD IS NOT ALWAYS LITERAL TEXT. A literal argument is
    recorded verbatim; a dynamic one is recorded as its location-free argument
    AST. So this tool pins the expression SHAPE of a dynamic pattern — a
    changed literal, referenced name or operator moves the record, a line move
    does not. It deliberately does NOT resolve names or evaluate anything, so
    the VALUE a referenced constant holds is out of scope here and owned by the
    hardcoding inventory."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    re_names, direct = set(), {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "re" or a.name.startswith("re."):
                    re_names.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module == "re":
            for a in node.names:
                direct[a.asname or a.name] = a.name
    out = []

    def visit(node, func):
        for child in ast.iter_child_nodes(node):
            child_func = func
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                child_func = child.name
            if isinstance(child, ast.Call):
                f = child.func
                op = None
                if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                        and f.value.id in re_names and f.attr in _RE_FUNCS):
                    op = f.attr
                elif isinstance(f, ast.Name) and f.id in direct:
                    op = direct[f.id]
                if op:
                    a0 = child.args[0] if child.args else None
                    if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                        pat = a0.value
                    elif a0 is None:
                        pat = "<no-argument>"
                    else:
                        # A SHARED "<non-literal>" TOKEN COLLIDED: two different
                        # dynamic expressions produced byte-identical records, so
                        # editing either could leave this freeze unchanged while
                        # the tool claimed per-site coverage. The location-free
                        # dump freezes the EXPRESSION SHAPE; it deliberately does
                        # not resolve names or evaluate anything — the referenced
                        # constant's VALUE is the hardcoding inventory's job, not
                        # this tool's.
                        pat = "<expr>" + ast.dump(a0, include_attributes=False)
                    out.append([func, op, pat])
            visit(child, child_func)

    visit(tree, "<module>")
    return sorted(out)


def keyword_lists(path, min_len=3):
    """KNOWN-SHAPE TRIPWIRE, deliberately NOT exhaustive: module-level
    tuples/sets/lists (incl. frozenset()/set()/tuple() over a literal) of >=3
    string literals — the shape of a hidden keyword list
    (`_XBRL_PER_SHARE_MARKERS`, YoY token sets).

    HONEST SCOPE (reviewer-proven escapes, accepted): inline sets in
    expressions, startswith/endswith tuples, dict keyword tables, and
    runtime-built lists are NOT detected — chasing every encoding of a word
    list is unwinnable. The LOAD-BEARING defense is structural, not this scan:
    meaning-deciding code receives structured fields (never free prose), every
    regex SITE is frozen as (function, operation, pattern), and hidden grading
    attacks the semantic gaps. This tripwire only catches the common shape
    cheaply; it must never be described as proof of absence."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        v = node.value
        # frozenset({...}) / set([...]) / tuple((...)) wrap a literal in a Call —
        # the scan MISSED those entirely (reviewer-demonstrated); unwrap them.
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) \
                and v.func.id in ("frozenset", "set", "tuple", "list") \
                and len(v.args) == 1 and not v.keywords \
                and isinstance(v.args[0], (ast.Tuple, ast.List, ast.Set)):
            v = v.args[0]
        if not isinstance(v, (ast.Tuple, ast.List, ast.Set)):
            continue
        vals = [e.value for e in v.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        if len(vals) >= min_len and len(vals) == len(v.elts):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    found[t.id] = sorted(vals)
    return found


# ---------------------------------------------------------------------------
# CLASSIFICATION — every module reaching a regex must appear in exactly one bucket.
#   MECHANICAL    : shape of a string we generate / parsing our own format.
#   GOVERNING_LAW : implements a written law and is exact (not a meaning guess).
#   SEMANTIC_DEBT : guesses what source text MEANS. Each entry is a DEBT with a
#                   disposition — never an approval. The set is frozen; a NEW one
#                   fails the gate until a human classifies it.
# ---------------------------------------------------------------------------
MECHANICAL = {
    "guidance_ids": "slugify/whitespace normalisers, a numeric-token splitter "
                    "(`^([+-]?\\d+\\.?\\d*)\\s*([a-zA-Z]*)$` on an ALREADY-"
                    "isolated value string) and an XBRL count matcher on "
                    "declared qnames — shape work on our own/declared strings, "
                    "not judgments about prose.",
    # Reached only because guidance_ids imports the shared XBRL stack at module
    # level. Included because they ARE import-reachable (scope is derived, not
    # trimmed to make the gate pass) — and both are pure markup/encoding work.
    "utils": "XML entity escaping: `&` -> `&amp;` unless already an entity. "
             "Character-level encoding, no judgment about content.",
    "xbrl_reporting": "`<[^>]+>` strips markup tags. Structural text cleanup, "
                      "not a decision about what the text means.",
}
GOVERNING_LAW = {
    # RECLASSIFIED (#827): the old MECHANICAL note said "all check strings WE
    # emit", which is not true of this module. These shapes are imposed from
    # outside and cited, so widening or narrowing one is a contract change, not
    # a formatting preference:
    #   * source-id charset and NAME-05 driver-name shape — the owner-approved
    #     S3.1 ID law (FINAL_DESIGN §5.1, OD-8/OD-21);
    #   * the `gp_` period-id grammar — dated ids only, sentinels owned by
    #     PERIOD_SENTINEL_SCOPE (FINAL_DESIGN §6.2, PER-01..21);
    #   * the sha-256 shape — OD-8;
    #   * the CIK spelling — SEC: EDGAR Filer Manual (Volume II) v77 §7.3.3.2
    #     and the EDGAR API's 10-digit, leading-zero form;
    #   * the unknown-axis sentinel — FINAL_DESIGN line 174;
    #   * `norm`'s normalizer class — the one canonical value law.
    "driver_ids": "governing-contract shapes, not self-emitted formatting: "
                  "S3.1 ID law (source_id, NAME-05, OD-8 hash), FINAL_DESIGN "
                  "§6.2 period-id grammar, FINAL_DESIGN:174 unknown-axis "
                  "sentinel, and the SEC CIK spelling (EFM Vol II v77 §7.3.3.2 "
                  "+ EDGAR API 10-digit). Each is cited; each edit is a "
                  "contract change.",
}
SEMANTIC_DEBT = {
    "driver_validators": "_VALUE_TEXT_NUMERIC — 'does this prose hide a "
                         "number?'. OWNER RULING 2026-07-25: Option A approved "
                         "— code enforces numeric-slot/value_text MUTUAL "
                         "EXCLUSION; the MODEL decides whether prose is "
                         "genuinely numberless; hidden grading attacks numeric "
                         "prose in value_text; uncertainty ABSTAINS. The "
                         "structural check alone does NOT prove numberlessness. "
                         "Removal lands with that implementation.",
}


# ONE MODULE, THREE DIFFERENT DISPOSITIONS. inline_html is the only file in either
# closure whose regex sites do NOT share a class. Every table above blesses a
# whole MODULE, so putting inline_html in any one of them would let any of its
# three sites silently absorb a new pattern of a different kind — the exact
# false-green this gate exists to prevent. The disposition is therefore recorded
# PER SITE, keyed by the same [function, operation, pattern] identity the freeze
# uses, and such a module counts as classified ONLY while EVERY live site carries
# one. A fifth site added tomorrow is UNCLASSIFIED and fails.
SITE_DISPOSITION = {
    "inline_html": {
        ("<module>", "compile", "[ \t\n\x0c\r]+"):
            "MECHANICAL — the CSS white-space character set (CSS Text 3 §4.1.1). "
            "Collapsing runs of those five characters is markup mechanics on a "
            "string we already parsed; it judges no prose.",
        ("_sec_cik", "fullmatch",
         "<expr>Name(id='_SEC_CIK_10_PATTERN', ctx=Load())"):
            "GOVERNING_LAW — the SEC 10-digit CIK spelling, IMPORTED from "
            "driver_ids (line 26) where the identical rule is already frozen. "
            "The law keeps ONE owner; this site references it, never restates it.",
        # The fourth site, `_evidence_from` search '\\d', is GONE (EU-094,
        # #827). It was carried here as SEMANTIC_DEBT on the strength of a
        # fail-closed claim that measurement disproved — discarding a
        # digit-bearing candidate could leave exactly one candidate where the
        # row had two, turning ambiguity into acceptance. Having no standards or
        # frozen-contract authority, it was removed rather than retained, so it
        # has no disposition and must not reappear in this table.
        ("_words", "findall", "[A-Za-z][A-Za-z’'-]*"):
            "OWNER_SCOPE — ASCII label words. Owner-supported MEASURED scope, "
            "never a standard: the production owner at inline_html.py:130-141 "
            "records that NO spec owns what a label word is, so the scope is "
            "the owner's under the 2026-08-05 routing (rule bf3881d879cb3e3a) "
            "and its recall cost is measured rather than assumed. It is NOT a "
            "declared alphabet or a contract.",
    },
}


# A debt entry covers a MODULE, so adding ANOTHER semantic pattern inside an
# already-debted file would slip through (proven by mutation-testing this gate).
# Freezing the site COUNT closes that: growth inside a debted module fails too.
# PER-SITE FREEZE (measured, never guessed). Approval is per REGEX, not per
# module: a module blessed "mechanical" (guidance_ids) could otherwise absorb a
# NEW semantic regex silently — proven by mutation-testing this gate.
# Each site = [enclosing function, re-operation, literal pattern]. The
# OPERATION is frozen because pattern-text-only froze gave a FALSE GREEN
# (re.sub -> re.search, byte-identical pattern \u2014 reviewer-proven on temp copies).
FROZEN_PATTERNS = {
    # GOVERNING_LAW, not mechanical: source-id, NAME-05, the period-id grammar,
    # the OD-8 hash, the SEC CIK spelling, the unknown-axis sentinel and the
    # normalizer all come from cited frozen contracts or the official SEC rule.
    # They are not merely strings this program happens to emit.
    "driver_ids": [
        ["<module>", "compile",
         "<expr>BinOp(left=BinOp(left=Constant(value='^'), op=Add(), "
         "right=Name(id='_UNKNOWN_AXIS_VALUE_PREFIX', ctx=Load())), op=Add(), "
         "right=Constant(value='([0-9a-f]+)__([a-z0-9_]+)$'))"],
        ["<module>", "compile", "<expr>Name(id='SEC_CIK_10_PATTERN', ctx=Load())"],
        ["<module>", "compile", "^[0-9a-f]{64}$"],
        ["<module>", "compile", "^[A-Za-z0-9._\\-]+$"],
        ["<module>", "compile", "^[a-z][a-z0-9_]*$"],
        ["<module>", "compile", "^gp_([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{4}-[0-9]{2}-[0-9]{2})$"],
        ["norm", "sub", "[^a-z0-9]+"],
    ],
    # REMOVED, row T2, card action "value_text born complete; delete the
    # heuristic". `_VALUE_TEXT_NUMERIC` asked prose "does this hide a
    # number?" — a meaning guess, wrong in both directions. The owner
    # ruled Option A (2026-07-25); the compile site is gone and only a
    # tombstone comment survives at driver_validators.py:95, so the
    # module now contributes NO regex site and a frozen entry was stale.
    # THREE sites, THREE dispositions — see SITE_DISPOSITION. Frozen per site here
    # so growth inside the module still fails even though the sites are
    # separately dispositioned rather than sharing one module class.
    "inline_html": [
        ["<module>", "compile", "[ \t\n\x0c\r]+"],
        ["_sec_cik", "fullmatch",
         "<expr>Name(id='_SEC_CIK_10_PATTERN', ctx=Load())"],
        ["_words", "findall", "[A-Za-z][A-Za-z’'-]*"],
    ],
    "guidance_ids": [
        ["<module>", "compile", "SharesOutstanding|ShareCount|WeightedAverage\\w*Shares|NumberOf\\w*Shares"],
        ["_normalize_text", "sub", "\\s+"],
        ["_normalize_unit_text", "sub", "\\s+"],
        ["_parse_numeric_with_scale", "match", "^([+-]?\\d+\\.?\\d*)\\s*([a-zA-Z]*)\\s*$"],
        ["normalize_for_member_match", "sub", "[^a-z0-9]"],
        ["slug", "sub", "[^a-z0-9]+"],
        ["slug", "sub", "_+"],
    ],
    "utils": [
        ["clean_xml_entities", "sub", "&(?!amp;|lt;|gt;|quot;|apos;|#\\d+;|#x[0-9a-fA-F]+;)"],
    ],
    "xbrl_reporting": [
        ["<module>", "compile", "<[^>]+>"],
    ],
}

# Keyword lists = closed vocabularies FROM LAW (legitimate) vs meaning guesses.
LEGIT_VOCAB = {
    "LANES", "BASELINES", "SOURCE_TYPES", "PERIOD_SCOPES",
    "SHAPES", "CANONICAL_UNITS", "VALID_UNIT_KIND_HINTS",
    "VALID_MONEY_MODE_HINTS", "valid_bases", "__all__", "EXPECT_BASE",
    "MEANING_FIELDS", "CODE_FIELDS", "OD_RULES", "ARMS", "SOURCE_OWNED",
    "ITEM_KEYS", "DOC_KEYS", "FACT_KEYS", "NUMERIC", "STRINGY", "FUZZY_TOKENS",
    "_RE_FUNCS", "_POLARITY_BASES", "_PROOF_KEYS", "_NUMERIC_FIELDS",
    "ENTRY_PRODUCTION", "ENTRY_EXAM", "_SEARCH_ROOTS", "RUN_EVENT_CLOSURE",
    "EXAM_FILES", "LEGIT_VOCAB", "KEYWORD_DEBT",
    # B-16 closed vocabularies, both STRUCTURAL and both owner-fixed:
    #   GRADER_OWNED   — the WorkOrder §649 meaning fields, excluded from direct
    #                    code accuracy because a qualified grader owns them.
    #   EXTRAS_BUCKETS — the Addendum-A extras classes. Exactly three, by owner
    #                    ruling; nothing infers a bucket from text.
    # Neither RECOGNISES meaning in a document — they name which owner scores
    # which field, so a closed set is the point rather than a smell.
    "GRADER_OWNED", "EXTRAS_BUCKETS",
    # prepared_fact groups FIELD NAMES by declared type — schema structure,
    # not a judgment about source text.
    "_NUMERIC", "_STR", "_INT",
    # Uncovered by the frozenset unwrap (2026-07-26) and individually judged
    # LAW ENUMS / schema structure, not meaning guesses:
    # T7 moved the numeric-slot field list to the SHARED schema owner and
    # dropped the leading underscore, so the already-classified
    # `_NUMERIC_FIELDS` reappeared under a new name. It is a static tuple of
    # SLOT NAMES — schema structure, never a judgement about source text.
    # Owner row recorded at receipts_827/28_pc4_row_and_pc1_denominator.md:
    # "NUMERIC_FIELDS | T7 | static tuple literal".
    "NUMERIC_FIELDS",
    # kf_lint — the three GOLD-ONLY review fields. A closed vocabulary from law
    # (WorkOrder 620 defines du_worthy as the internal name of the official fact
    # gate; step2 §7 limits gold additions to the review fields), attached AFTER
    # the model answers. The checker uses it to REFUSE these names at the model
    # door — the opposite of a guess about source text.
    "GOLD_ONLY",
    "_SLICE_KINDS",       # driver_ids — the FS-05 slice-kind enum
    "_SURPRISE_TYPES",    # driver_ids — the OD-21 surprise-type enum
    "_SENTINEL_SCOPES",   # driver_units — the PER sentinel-horizon enum
    "_ALLOWED_FIELDS",    # driver_validators — the schema field-name list
    "_VALID_SHAPES",      # driver_validators — the shape enum
}
# Keyword lists that INFER MEANING from a name/label/prose — same class as the
# forbidden PERSHARE_HINT. Each is a DEBT with a disposition, never an approval.
KEYWORD_DEBT = {
    "_XBRL_PER_SHARE_MARKERS": "guidance_ids — matches XBRL concept NAMES "
        "('PerShare','PerUnit',...) to infer per-share-ness. Identical class to "
        "the PERSHARE_HINT the register FORBIDS. OWNER ITEM: use the declared "
        "XBRL unit (numerator/denominator) instead of a name guess.",
    "PER_SHARE_LABELS": "guidance_ids — infers per-share from a label slug "
        "('eps','dps'). Same class. OWNER ITEM: declared unit, not the label.",
    # Uncovered by the frozenset unwrap (2026-07-26) — the scan could not see
    # frozenset(...) assignments at all, so these three label→meaning lists sat
    # invisible in an import-reachable module:
    "_COUNT_LABEL_PRIORS": "guidance_ids — infers unit-kind COUNT from a label "
        "slug ('headcount','share_count'). Label→meaning guess; same owner "
        "disposition as PER_SHARE_LABELS.",
    "_PRICE_LIKE_LABEL_PRIORS": "guidance_ids — infers money_mode price_like "
        "from a label slug ('arpu','asp','adr'). Same class, same disposition.",
    "KNOWN_INSTANT_LABELS": "guidance_ids — infers instant-vs-duration from a "
        "label slug. Documented HINT-ONLY (FACT-18: time_type stays "
        "authoritative), still a label→meaning list; rides the same owner item.",
}


def _classified(path_map):
    # reuses regex_patterns (one alias-aware AST walk — the parallel
    # regex_sites() duplicate was deleted, reviewer sweep 2026-07-26)
    unknown = {}
    for path, mod in path_map.items():
        hits = regex_patterns(path)
        if not hits or mod in MECHANICAL or mod in GOVERNING_LAW \
                or mod in SEMANTIC_DEBT:
            continue
        per_site = SITE_DISPOSITION.get(mod)
        if per_site is None:
            unknown[mod] = hits
            continue
        # classified only while EVERY live site carries its own disposition
        undisposed = [h for h in hits if tuple(h) not in per_site]
        if undisposed:
            unknown[mod] = undisposed
    return unknown


def test_production_closure_is_derived_not_handwritten():
    """The run_event closure must be reached by following imports — and must
    include shared code whose NAME does not contain 'driver' (guidance_ids was
    missed by exactly that heuristic)."""
    mods = set(closure(ENTRY_PRODUCTION).values())
    assert "guidance_ids" in mods, (
        "guidance_ids is imported by driver_period_resolver but missing from "
        "the closure — the walker is using a name heuristic again")
    assert {"driver_validators", "driver_units", "prepared_fact"} <= mods


def test_exam_closure_includes_everything_it_imports():
    """The exam closure must contain fact16_checks while score_exp5 imports it —
    the hand-written list omitted it and reported a FALSE CLEAN."""
    mods = set(closure(ENTRY_EXAM).values())
    src = open(os.path.join(_HERE, "scorers", "score_exp5.py"),
               encoding="utf-8").read()
    if "from fact16_checks import" in src:
        assert "fact16_checks" in mods, "gate is blind to a live exam import"


def test_no_unclassified_regex_in_the_production_path():
    unknown = _classified(closure(ENTRY_PRODUCTION))
    assert not unknown, (
        f"UNCLASSIFIED regex in the run_event path: {unknown}. Classify it: "
        f"mechanical / governing-law / semantic-debt (semantic must go to the "
        f"model).")


def test_no_unclassified_regex_in_the_exam_path():
    unknown = _classified(closure(ENTRY_EXAM))
    assert not unknown, f"UNCLASSIFIED regex in the exam path: {unknown}"


def test_every_regex_site_is_frozen_individually():
    """PER-SITE freeze. Approving a whole module lets a new semantic regex slip
    in beside an approved one, so each site is pinned individually: a literal
    pattern by its exact text, a dynamic one by its argument AST. The AST form
    pins the expression SHAPE, not the value a referenced constant holds —
    that value belongs to the hardcoding inventory."""
    live = {}
    for path, mod in {**closure(ENTRY_PRODUCTION), **closure(ENTRY_EXAM)}.items():
        pats = regex_patterns(path)
        if pats:
            live[mod] = pats
    assert live == FROZEN_PATTERNS, (
        "regex SITES changed. Added one? it needs classification (mechanical / "
        "governing law / semantic debt) before the freeze is updated. Removed "
        "one? update FROZEN_PATTERNS.\n"
        f"only-live={ {k: [x for x in v if x not in FROZEN_PATTERNS.get(k, [])] for k, v in live.items() if v != FROZEN_PATTERNS.get(k)} }")


def test_keyword_lists_are_classified():
    """Every KNOWN-SHAPE keyword list must be a law vocabulary or a declared
    debt. This is a tripwire, NOT an exhaustive scan (see keyword_lists's
    honest-scope note): inline sets, startswith tuples, and dict tables escape
    it by design — the structural fences carry the real guarantee."""
    unknown = {}
    for path, mod in {**closure(ENTRY_PRODUCTION), **closure(ENTRY_EXAM)}.items():
        if mod not in ("guidance_ids", "driver_validators", "driver_units",
                       "unit_resolver", "fact16_checks", "prepared_fact",
                       "kf_lint", "score_exp5", "raw_transport", "driver_ids"):
            continue                      # Driver-relevant modules only
        for name in keyword_lists(path):
            if name not in LEGIT_VOCAB and name not in KEYWORD_DEBT:
                unknown.setdefault(mod, []).append(name)
    assert not unknown, (
        f"UNCLASSIFIED keyword list(s): {unknown}. A closed vocabulary from law "
        f"-> LEGIT_VOCAB; a guess about a name/label/prose -> KEYWORD_DEBT with "
        f"an owner disposition.")


def test_keyword_debt_is_frozen():
    """The two known meaning-guessing lists must not multiply."""
    found = set()
    for path, mod in {**closure(ENTRY_PRODUCTION), **closure(ENTRY_EXAM)}.items():
        found |= set(keyword_lists(path)) & set(KEYWORD_DEBT)
    assert found == set(KEYWORD_DEBT), f"{found} vs {set(KEYWORD_DEBT)}"


def test_no_fuzzy_matching_anywhere_in_either_path():
    """No similarity scoring, edit distance, or nearest-match. Identity must be
    EXACT. Scans the AST, not the text: prose like 'never a fuzzy near-match' is
    a COMMENT asserting the opposite (an earlier version flagged exactly that)."""
    paths = list(closure(ENTRY_PRODUCTION)) + list(closure(ENTRY_EXAM))
    bad = []
    for path in paths:
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                name = " ".join(a.name for a in node.names) + " " + \
                       (getattr(node, "module", "") or "")
            if not name:
                continue
            for tok in FUZZY_TOKENS:
                if tok.lower() in name.lower():
                    bad.append(f"{os.path.basename(path)}:{node.lineno}:{tok}")
    assert not bad, f"fuzzy matching found in CODE: {bad} — identity must be EXACT"


def test_the_deleted_fuzzy_matcher_stays_deleted():
    src = open(os.path.join(_HERE, "scorers", "score_exp5.py"),
               encoding="utf-8").read()
    assert "def _overlap" not in src, "the fuzzy sliding-window matcher is back"
    assert "def _ev_key" in src, "exact evidence identity is missing"


# ---------------------------------------------------------------------------
# MUTATION TESTS — the gate must FAIL on each known evasion route, and it must
# fail ON THE RIGHT DETECTOR. Rebuilt 2026-07-26 after the reviewer showed two
# holes in the old versions: (a) they appended to LIVE project files (a crash
# between write and restore leaves the tree mutated); (b) they asserted only
# "some gate test failed", so an unrelated pre-existing failure could green a
# mutation that actually slipped through. Now: every mutation happens in a TEMP
# copy of the whole derived closure, and every test asserts the SPECIFIC
# detector + the mutated module's name in its message. A baseline test proves
# the temp copy itself is GREEN, so a failure can only come from the mutation.
# ---------------------------------------------------------------------------
import json
import shutil
import subprocess
import sys
import tempfile

_REL_HARNESS = os.path.relpath(_HERE, _REPO)
_DETECTORS = ["test_every_regex_site_is_frozen_individually",
              "test_no_unclassified_regex_in_the_exam_path",
              "test_no_unclassified_regex_in_the_production_path",
              "test_keyword_lists_are_classified",
              "test_no_fuzzy_matching_anywhere_in_either_path"]


def _temp_repo():
    """Copy the ENTIRE derived closure (+ this gate file) into a temp repo
    skeleton, preserving repo-relative paths. Live files are never written."""
    tmp = tempfile.mkdtemp(prefix="nsp_gate_")
    files = set(closure(ENTRY_PRODUCTION)) | set(closure(ENTRY_EXAM))
    files.update(os.path.realpath(p) for p in ENTRY_PRODUCTION + ENTRY_EXAM)
    files.add(os.path.join(_HERE, "test_no_semantic_patterns.py"))
    for src in files:
        rel = os.path.relpath(src, _REPO)
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    return tmp


def _gate_failures(tmp):
    """Run the five detectors inside the TEMP repo; {detector: message}."""
    code = (
        "import json\n"
        "import test_no_semantic_patterns as g\n"
        "out = {}\n"
        f"for n in {_DETECTORS!r}:\n"
        "    try:\n"
        "        getattr(g, n)()\n"
        "    except AssertionError as e:\n"
        "        out[n] = str(e)[:400]\n"
        "print(json.dumps(out))\n")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, cwd=os.path.join(tmp, _REL_HARNESS))
    assert r.returncode == 0, f"gate crashed in the temp repo: {r.stderr[:400]}"
    return json.loads(r.stdout.strip())


def _mutated_failures(target_rel, extra="", replace=None):
    """APPEND `extra`, and/or REPLACE one exact snippet. Replacement exists
    because per-SITE dispositions must be provable by ALTERING a site, not only
    by adding one: an append-only harness can never show that changing an
    existing frozen site is caught."""
    tmp = _temp_repo()
    try:
        path = os.path.join(tmp, target_rel)
        if replace is not None:
            old, new = replace
            src = open(path, encoding="utf-8").read()
            assert old in src, f"mutation anchor absent in {target_rel}: {old!r}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(src.replace(old, new, 1))
        if extra:
            with open(path, "a", encoding="utf-8") as f:
                f.write(extra)
        return _gate_failures(tmp)
    finally:
        shutil.rmtree(tmp)


_INLINE_HTML_REL = "driver/relocation/inline_html.py"

# B-17: the sites carry SEPARATE dispositions, so each must be shown
# to be caught ON ITS OWN. A single module-level proof would not distinguish
# them — that is precisely the uniform-class blessing this row forbids.
@pytest.mark.parametrize("disposition,old,new", [
    ("MECHANICAL css whitespace",
     "_CSS_WS = re.compile('[ \\t\\n\\x0c\\r]+')",
     "_CSS_WS = re.compile('[ \\t\\n]+')"),
    ("GOVERNING_LAW sec cik",
     "re.fullmatch(_SEC_CIK_10_PATTERN, digits)",
     "re.search(_SEC_CIK_10_PATTERN, digits)"),
    ("OWNER_SCOPE ascii words",
     're.findall(r"[A-Za-z][A-Za-z’\'-]*", value)',
     're.findall(r"[A-Za-z]+", value)'),
])
def test_MUTATION_each_inline_html_site_is_individually_caught(disposition, old,
                                                              new):
    """Change ONE dispositioned site; the per-site freeze must fail."""
    failures = _mutated_failures(_INLINE_HTML_REL, replace=(old, new))
    assert "test_every_regex_site_is_frozen_individually" in failures, \
        f"{disposition}: altering this site did NOT fail the freeze — {failures}"


def test_MUTATION_a_fifth_inline_html_site_is_unclassified():
    """A NEW site in the same module has no disposition, so the module stops
    counting as classified even though its other four are dispositioned."""
    failures = _mutated_failures(
        _INLINE_HTML_REL,
        extra="\n\ndef _added_probe(s):\n    return re.search(r'profit', s)\n")
    assert "test_no_unclassified_regex_in_the_production_path" in failures, \
        f"a fifth undispositioned site was tolerated — {failures}"


def test_MUTATION_baseline_temp_repo_is_green():
    """No mutation → zero detector failures in the temp copy. This is what
    makes every assertion below attributable to its mutation alone."""
    tmp = _temp_repo()
    try:
        assert _gate_failures(tmp) == {}
    finally:
        shutil.rmtree(tmp)


def test_MUTATION_aliased_regex_import_is_caught():
    """`import re as _re` — the alias an earlier gate missed entirely."""
    fails = _mutated_failures(
        os.path.join(_REL_HARNESS, "kf_lint.py"),
        "\nimport re as _re\n_BAD = _re.compile(r'revenue|sales')\n")
    msg = fails.get("test_every_regex_site_is_frozen_individually", "")
    assert "kf_lint" in msg, f"wrong/missing detector: {fails}"


def test_MUTATION_from_re_import_form_is_caught():
    fails = _mutated_failures(
        os.path.join(_REL_HARNESS, "raw_transport.py"),
        "\nfrom re import compile as _c\n_B = _c(r'beat|miss')\n")
    msg = fails.get("test_every_regex_site_is_frozen_individually", "")
    assert "raw_transport" in msg, f"wrong/missing detector: {fails}"


def test_MUTATION_new_regex_inside_an_APPROVED_module_is_caught():
    """The per-site freeze exists for this: guidance_ids is blessed
    'mechanical' — it must not absorb a new semantic pattern silently."""
    fails = _mutated_failures(
        os.path.join(".claude", "skills", "earnings-orchestrator", "scripts",
                     "guidance_ids.py"),
        "\nimport re as _re2\n_X = _re2.compile(r'beats|misses|tops')\n")
    msg = fails.get("test_every_regex_site_is_frozen_individually", "")
    assert "guidance_ids" in msg, f"wrong/missing detector: {fails}"


def test_MUTATION_operation_swap_is_caught():
    """re.sub -> re.search with a BYTE-IDENTICAL pattern turns a rewrite into a
    meaning probe; the old pattern-text-only freeze stayed green on exactly
    this (reviewer-proven on temp copies). The operation is now frozen."""
    tmp = _temp_repo()
    try:
        target = os.path.join(tmp, ".claude", "skills", "earnings-orchestrator",
                              "scripts", "guidance_ids.py")
        src = open(target, encoding="utf-8").read()
        swapped = src.replace(".sub(", ".search(", 1)
        assert swapped != src
        open(target, "w", encoding="utf-8").write(swapped)
        fails = _gate_failures(tmp)
        msg = fails.get("test_every_regex_site_is_frozen_individually", "")
        assert "guidance_ids" in msg, f"wrong/missing detector: {fails}"
    finally:
        shutil.rmtree(tmp)


def test_MUTATION_new_keyword_list_is_caught():
    fails = _mutated_failures(
        os.path.join(_REL_HARNESS, "kf_lint.py"),
        "\n_GUESS_WORDS = ('beat', 'missed', 'topped')\n")
    msg = fails.get("test_keyword_lists_are_classified", "")
    assert "_GUESS_WORDS" in msg, f"wrong/missing detector: {fails}"


def test_MUTATION_frozenset_keyword_list_is_caught():
    """frozenset({...}) hid keyword lists from the scan entirely
    (reviewer-demonstrated). The unwrap fix must catch it."""
    fails = _mutated_failures(
        os.path.join(_REL_HARNESS, "kf_lint.py"),
        "\n_FS_WORDS = frozenset({'beat', 'missed', 'topped'})\n")
    msg = fails.get("test_keyword_lists_are_classified", "")
    assert "_FS_WORDS" in msg, f"wrong/missing detector: {fails}"


def test_MUTATION_fuzzy_import_is_caught():
    fails = _mutated_failures(
        os.path.join(_REL_HARNESS, "raw_transport.py"),
        "\nimport difflib  # noqa\n")
    msg = fails.get("test_no_fuzzy_matching_anywhere_in_either_path", "")
    assert "difflib" in msg, f"wrong/missing detector: {fails}"


# ---- SEQ 435: durable controls for the dynamic-expression record -----------
# These were run as scratch checks and reported as if they were repository
# proof. They are tests now. Each writes temporary source text and compares
# `regex_patterns` records — no repository file is read or written.

_DYN_BASE = 'import re\nP = "x"\nR = re.compile("^" + P + r"[0-9]+$")\n'
_DYN_MOVED = 'import re\nimport os\n\n\nP = "x"\nR = re.compile("^" + P + r"[0-9]+$")\n'
_DYN_LITERAL = 'import re\nP = "x"\nR = re.compile("^" + P + r"[0-9]{4}$")\n'
_DYN_NAME = 'import re\nZ = "x"\nR = re.compile("^" + Z + r"[0-9]+$")\n'
_DYN_OPERATOR = 'import re\nP = "x"\nR = re.compile("^" % P + r"[0-9]+$")\n'


def _sites(tmp_path, name, src):
    p = tmp_path / name
    p.write_text(src)
    return regex_patterns(str(p))


def test_DYNAMIC_a_line_only_move_keeps_the_same_frozen_record(tmp_path):
    """A dynamic pattern that merely moves down the file must not churn the
    freeze — otherwise every unrelated edit demands a re-review."""
    assert _sites(tmp_path, "a.py", _DYN_BASE) == \
        _sites(tmp_path, "b.py", _DYN_MOVED)


@pytest.mark.parametrize("src,what", [
    (_DYN_LITERAL, "the embedded literal"),
    (_DYN_NAME, "the referenced name"),
    (_DYN_OPERATOR, "the operator"),
])
def test_DYNAMIC_a_changed_expression_changes_the_frozen_record(tmp_path, src, what):
    """THE COLLISION THIS CLOSES: every dynamic pattern used to collapse to a
    shared `<non-literal>` token, so two different expressions produced
    byte-identical records and a change to either was invisible."""
    base = _sites(tmp_path, "base.py", _DYN_BASE)
    other = _sites(tmp_path, "other.py", src)
    assert base != other, what


def test_every_classified_module_sits_in_EXACTLY_ONE_bucket():
    """The file claims this; it did not enforce it. Moving `driver_ids` from
    MECHANICAL to GOVERNING_LAW must not be able to leave it in both."""
    buckets = {"MECHANICAL": set(MECHANICAL),
               "GOVERNING_LAW": set(GOVERNING_LAW),
               "SEMANTIC_DEBT": set(SEMANTIC_DEBT)}
    names = list(buckets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlap = buckets[a] & buckets[b]
            assert not overlap, f"{a} and {b} both classify {sorted(overlap)}"
    assert "driver_ids" in buckets["GOVERNING_LAW"], sorted(buckets["GOVERNING_LAW"])
