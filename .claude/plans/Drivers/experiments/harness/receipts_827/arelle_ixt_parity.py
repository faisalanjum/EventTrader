"""#827 Stage 3 — Arelle transformation-registry PARITY, complete and fail-closed.

Answers one question with evidence instead of preference: does the inline-XBRL
transformation behaviour this product depends on differ between `arelle-release`
2.35.0 (the `requirements.txt` pin, and what production runs) and 2.38.20 (what
this development environment happens to have)?

WHAT CHANGED AND WHY, because the first version of this file was not evidence:

  * IT COMPARED SEVEN HAND-PICKED NAMES. Seven names I chose cannot show that
    two libraries agree; they show that two libraries agree ON MY SHORTLIST,
    which is a claim about me. The comparison is now the SUPPORTED-registry
    function tables in full, and behaviour on the occurrences the scanner
    actually read from the manifest-bound corpus. Registries the product
    refuses are RECORDED, not compared. (A previous version of this bullet
    said "the COMPLETE matrix the library exposes: every namespace, every
    function, every input" — which was both wider than the gate and, on the
    inputs, simply untrue.)

  * IT INSTALLED NOTHING. It put an unpacked distribution on `PYTHONPATH` and
    imported it beside whatever else the ambient interpreter could see. That is
    not an isolated 2.35.0; it is 2.35.0's source files with this machine's
    dependency graph behind them. Each version now gets its OWN virtualenv, a
    real install, and a probe run with `-E -s` so no `PYTHON*` variable and no
    user site directory can reach in.

  * IT COULD ONLY SUCCEED. `run()` returned `{'error': ...}` and `main()`
    returned 0 regardless, so an install failure, an import failure and a clean
    parity pass were the same exit status. Every failure mode now exits 1.

  * IT RECORDED NO PROVENANCE. "2.35.0" was a string I typed. The install
    report now pins the exact artifact URL and its sha256, and the probe hashes
    the `FunctionIxt.py` it actually imported.

WHAT THIS PROVES, AND WHAT IT DOES NOT. An earlier draft called every function
Arelle exposes with fifteen inputs I made up, and described that as the
complete matrix with "nothing selected by hand". The function list was
complete; the INPUTS were entirely my choice, so the sentence was false and the
claim was too large. This file now proves exactly two things and names them as
such:

  (A) SUPPORTED FUNCTION-TABLE COMPATIBILITY — the transformations the two
      versions expose under TR3, TR4 and TR5 are the same set, under the same
      namespace URIs.
  (B) FROZEN-CORPUS BEHAVIOURAL PARITY — every transform occurrence THE
      SCANNER WAS ABLE TO READ from the manifest-bound filing corpus, replayed
      through both versions with the text the filing actually printed, agrees.
      A manifest file that is neither parsed nor named as standards-invalid is
      UNACCOUNTED and fails the gate. A file proven not to be a well-formed
      Inline XBRL report, bound by name and hash to an exact manifest row,
      stays named in the receipt and closes the lawful-scope partition — it has
      no lawful transform occurrence to replay, so its exclusion is the
      standard being applied, not coverage being missed.

Neither is universal parity and this receipt never uses that phrase. Inputs no
filing produced are not evidence about filings.

SCOPE OF THE GATE. The product admits TR3, TR4 and TR5 and REFUSES the 2008
namespace, TR1, TR2 and the WGWD draft alias. Arelle implements those refused
registries too, but a difference there cannot affect this product and must not
be able to block it, so they are recorded and excluded from the gate. The SEC's
own registry `http://www.sec.gov/inlineXBRL/transformation/2015-08-31` is a
separate, truthful boundary: Arelle does not implement it at all — verified
below by `sec_registry_implemented` rather than assumed — so no Arelle-based
parity statement about it is possible.

NO STANDING DIFFERENCE ALLOWLIST. Any difference fails and returns for a fresh
evidence-based ruling. A permanent allowlist would let a real regression be
inherited silently by every later run.

Usage:  python arelle_ixt_parity.py
Reads the scanner's `01c_ix_transform_occurrences.json` (manifest-bound) and
writes `24_arelle_ixt_parity.json` beside this file. Exit 0 only on proof.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

#: The requirements pin first, the environment's drift second.
VERSIONS = ('2.35.0', '2.38.20')

#: THE REGISTRIES THE PRODUCT ADMITS, and therefore the whole gate. A
#: difference under a registry the product refuses cannot reach the product, so
#: including it could only produce a false block.
SUPPORTED = (
    'http://www.xbrl.org/inlineXBRL/transformation/2015-02-26',   # TR3
    'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12',   # TR4
    'http://www.xbrl.org/inlineXBRL/transformation/2022-02-16',   # TR5
)

#: NO HAND-WRITTEN OUTSIDE LIST. A second registry inventory maintained here
#: would be one more thing to get wrong and to keep in step with Arelle. The
#: recorded outside set is DERIVED per version: whatever that installation
#: implements, minus the registries the product supports. Only `SUPPORTED` and
#: the SEC boundary are stated, and both are cited.

SEC_REGISTRY = 'http://www.sec.gov/inlineXBRL/transformation/2015-08-31'

#: The scanner's manifest-bound occurrence file. THE ONLY SOURCE OF INPUTS: it
#: records what filings actually printed, so no case here was chosen by me.
OCCURRENCES = '01c_ix_transform_occurrences.json'

PROBE = r'''
import gettext, hashlib, json, sys
import importlib.metadata as md
import arelle.FunctionIxt as F
from arelle.formula import XPathContext

# THE CASES ARRIVE AS A FILE, not embedded in this source. The corpus yields
# ~255,000 distinct occurrences; inlining them would build a multi-megabyte
# `python -c` argument and die on ARG_MAX long before Arelle was even imported.
with open(OCCURRENCES_PATH, encoding='utf-8') as _fh:
    OCCURRENCES = json.load(_fh)

# THE TRANSLATOR IS ARMED FIRST, as production does. Arelle raises its refusal
# THROUGH `XPathContext`, whose `_` gettext name is unbound until something
# initialises it — so an invalid input surfaced as `NameError` and the first
# version of this probe recorded that accident as if it were the library's
# answer. Only this module attribute is set: a process-wide `builtins` install
# would change behaviour for every other consumer.
if getattr(XPathContext, '_', None) is None:
    XPathContext._ = gettext.gettext

with open(F.__file__, 'rb') as fh:
    digest = hashlib.sha256(fh.read()).hexdigest()

# NO `function_ixt_file`. It was an absolute path inside a random
# `TemporaryDirectory` that is deleted before anyone reads the receipt — not
# durable, not deterministic, and flatly against the rule two lines away that
# only what outlives the temp directory is recorded. The imported file's HASH,
# the package version and the full distribution provenance carry the evidence.
out = {'installed_version': md.version('arelle-release'),
       'python': sys.version.split()[0],
       'function_ixt_sha256': digest,
       'namespaces': dict(sorted(F.ixtNamespaces.items())),
       'sec_registry_implemented': SEC_REGISTRY in F.ixtNamespaceFunctions,
       'function_table': {},
       'out_of_scope_table': {},
       'results': {}}

for ns, fns in sorted(F.ixtNamespaceFunctions.items()):
    if ns in SUPPORTED:
        out['function_table'][ns] = sorted(fns)
    else:
        # RECORDED, NOT COMPARED. The product refuses these, so a difference
        # here cannot reach it — and putting it in the gate could only block
        # this product for a reason that does not apply to it.
        out['out_of_scope_table'][ns] = sorted(fns)

# EVERY INPUT COMES FROM THE FROZEN CORPUS. Each occurrence is (registry URI,
# local name, the exact text the filing printed) as read by the manifest-bound
# namespace-aware scanner. Nothing here was invented for the test.
for ns, name, value in OCCURRENCES:
    key = '%s|%s|%r' % (ns, name, value)
    if key in out['results']:
        continue
    fns = F.ixtNamespaceFunctions.get(ns) or {}
    fn = fns.get(name)
    if fn is None:
        out['results'][key] = ['absent', 'no such transform in this version']
        continue
    try:
        out['results'][key] = ['ok', str(fn(value))]
    except XPathContext.FunctionArgType:
        # THE DECLARED REFUSAL, AND ONLY IT. A broad `except Exception`
        # recorded `NameError` — our own missing setup — as though the
        # transform had rejected the input, which is a false parity result in
        # the most convincing possible shape: a green one. Anything else
        # propagates and fails the whole run on purpose.
        out['results'][key] = ['refused', 'FunctionArgType']

print(json.dumps(out))
'''


class Failure(Exception):
    """A stage that did not prove what it exists to prove."""


def _sh(argv, **kw):
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=900,
                          **kw)
    if proc.returncode != 0:
        raise Failure(f'{argv[0]} exited {proc.returncode}\n'
                      f'{proc.stderr.strip()[-1500:]}')
    return proc.stdout


def build(version, root):
    """A CLEAN venv, a REAL install, and the exact artifact that was installed.

    `--no-cache-dir` so the recorded hash belongs to a download that actually
    happened this run rather than to whatever a previous run left behind.
    """
    home = os.path.join(root, version)
    _sh([sys.executable, '-m', 'venv', home])
    py = os.path.join(home, 'bin', 'python')
    report = os.path.join(root, f'install-{version}.json')
    _sh([py, '-m', 'pip', 'install', '--no-cache-dir', '--disable-pip-version-check',
         '--report', report, f'arelle-release=={version}'])

    with open(report, encoding='utf-8') as fh:
        installed = json.load(fh)['install']
    picked = [p for p in installed
              if p['metadata']['name'].lower() == 'arelle-release']
    if len(picked) != 1:
        raise Failure(f'{version}: install report names {len(picked)} '
                      'arelle-release artifacts, expected exactly 1')
    info = picked[0]['download_info']
    resolved = picked[0]['metadata']['version']

    # EVERY DISTRIBUTION BY NAME, VERSION AND VALIDATED HASH. The receipt used
    # to record `dependency_count: 12` and `21` — a number nobody can
    # reproduce or audit an environment from. Arelle's behaviour depends on
    # what is installed beneath it, and 12 versus 21 packages is precisely the
    # kind of difference that would explain a divergence if one ever appeared.
    environment = []
    for pkg in sorted(installed, key=lambda p: p['metadata']['name'].lower()):
        digest = (pkg.get('download_info', {}).get('archive_info', {})
                  .get('hashes', {}).get('sha256'))
        if not _is_sha256(digest):
            raise Failure(
                f'{version}: {pkg["metadata"]["name"]} '
                f'{pkg["metadata"]["version"]} carries no usable sha256 '
                f'({digest!r}); the environment would be named but not pinned')
        environment.append({'name': pkg['metadata']['name'],
                            'version': pkg['metadata']['version'],
                            'sha256': digest})
    if resolved != version:
        raise Failure(f'requested arelle-release {version} but pip resolved '
                      f'{resolved}; the receipt would name a version that was '
                      'never installed')
    digest = info.get('archive_info', {}).get('hashes', {}).get('sha256')
    if not _is_sha256(digest):
        raise Failure(f'{version}: install report carries no usable sha256 '
                      f'({digest!r}); provenance would be a claim, not a fact')
    # Only what OUTLIVES the temp directory is recorded: a path under a
    # directory that is about to be deleted proves nothing to a later reader.
    return py, {'requested': version, 'resolved': resolved,
                'url': info['url'], 'sha256': digest,
                'environment': environment,
                'distributions_installed': len(environment)}


def _is_sha256(value):
    """A hash is provenance only if it IS one. `None`, a truncated value or an
    upper-case variant would all still print convincingly in a receipt."""
    return (isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value))


def _is_basename(value):
    """ONE plain file name sitting beside the receipt.

    `input_manifest_file: "../01b.txt"` was accepted whenever a file of that
    name happened to exist one directory up, so the receipt could bind itself
    to a manifest outside its own folder. A name is a name, not a route.
    """
    return (isinstance(value, str) and value not in ('', '.', '..')
            and os.path.basename(value) == value)


def probe(py, occurrences):
    """`-E -s`: no `PYTHON*` variable and no user site dir reaches this
    interpreter, so the only Arelle it can find is the one just installed.
    `-B` keeps it from writing bytecode anywhere."""
    handle, path = tempfile.mkstemp(suffix='.json', prefix='ixt-cases-')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as fh:
            json.dump(occurrences, fh)
        src = (f'OCCURRENCES_PATH = {path!r}\nSUPPORTED = {SUPPORTED!r}\n'
               f'SEC_REGISTRY = {SEC_REGISTRY!r}\n' + PROBE)
        return json.loads(_sh([py, '-B', '-E', '-s', '-c', src]))
    finally:
        os.unlink(path)


def load_occurrences(path):
    """The scanner's manifest-bound occurrences, restricted to the registries
    the product admits. Refuses rather than inventing inputs when absent."""
    if not os.path.exists(path):
        raise Failure(
            f'{os.path.basename(path)} is missing. This gate replays what the '
            'frozen corpus actually printed; without it there is nothing to '
            'replay, and substituting inputs of my own is exactly the false '
            'claim this file was rewritten to remove. Run the scanner first.')
    with open(path, 'rb') as fh:
        raw = fh.read()
    doc = json.loads(raw.decode('utf-8'))

    # PROOF-INPUT VALIDATION, not a second scanner. This gate trusts `01c` for
    # its entire population; if that file is malformed the whole receipt is
    # built on it silently. These checks read only what is already there.
    #
    # TYPES, NOT TRUTHINESS. Presence plus `bool(value)` accepted a receipt
    # saying `supported_scope_complete: "false"` — a non-empty STRING, therefore
    # true — alongside `n_files_parsed: 1` of `9` and an empty invalid list, and
    # reported complete scope. Every field below is checked for what it IS.
    for field in ('input_manifest_file', 'input_manifest_sha256',
                  'supported_scope_complete', 'n_files_in_manifest',
                  'n_files_parsed', 'files_not_well_formed', 'eligible_facts',
                  'occurrences'):
        if field not in doc:
            raise Failure(f'the occurrence file has no `{field}`; its scope '
                          'cannot be read, only assumed')
    if not isinstance(doc['supported_scope_complete'], bool):
        raise Failure(f'`supported_scope_complete` is '
                      f'{doc["supported_scope_complete"]!r}, not a JSON '
                      'boolean; truthy text would read as complete')
    for field in ('n_files_in_manifest', 'n_files_parsed', 'eligible_facts'):
        value = doc[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise Failure(f'`{field}` is {value!r}; a count must be a '
                          'non-negative integer and `True` is not one')
    if not _is_sha256(doc['input_manifest_sha256']):
        raise Failure(f'`input_manifest_sha256` is '
                      f'{doc["input_manifest_sha256"]!r}, not a lowercase '
                      'sha256')
    if not _is_basename(doc['input_manifest_file']):
        raise Failure(f'`input_manifest_file` is '
                      f'{doc["input_manifest_file"]!r}; it must be one plain '
                      'file name beside the receipt, not a path')

    # THE MANIFEST IS VERIFIED AND PARSED FIRST, because everything below is
    # checked AGAINST it.
    #
    # The binding used to be COPIED, not enforced: `input_manifest_sha256` was
    # lifted from the receipt and printed without comparing it to the manifest
    # on disk. Even once the whole-file hash was compared, the invalid-file
    # list stayed unbound to the ROWS — so a made-up name with a well-shaped
    # hash, plus a correspondingly reduced parsed count, satisfied the
    # partition equation and reported complete supported scope. A file the
    # corpus does not contain cannot be excluded from it.
    manifest = os.path.join(os.path.dirname(os.path.abspath(path)),
                            doc['input_manifest_file'])
    if not os.path.exists(manifest):
        raise Failure(f'{doc["input_manifest_file"]} is named by the occurrence '
                      'file but is not on disk; the corpus binding cannot be '
                      'checked, only believed')
    with open(manifest, 'rb') as fh:
        manifest_bytes = fh.read()
    on_disk = hashlib.sha256(manifest_bytes).hexdigest()
    if on_disk != doc['input_manifest_sha256']:
        raise Failure(
            f'the occurrence file was built against manifest '
            f'{doc["input_manifest_sha256"][:16]}… but the manifest on disk is '
            f'{on_disk[:16]}…; these replay inputs do not belong to this corpus')
    pinned = {}
    for line in manifest_bytes.decode('utf-8').splitlines():
        name, _, digest = line.partition(' ')
        if not _is_basename(name) or not _is_sha256(digest):
            raise Failure(f'manifest row is not `<name> <sha256>`: '
                          f'{line[:120]!r}')
        if name in pinned:
            raise Failure(f'{name} appears twice in the manifest; the corpus '
                          'membership is ambiguous')
        pinned[name] = digest
    if len(pinned) != doc['n_files_in_manifest']:
        raise Failure(
            f'the manifest holds {len(pinned)} rows but the receipt says '
            f'{doc["n_files_in_manifest"]} files; they do not describe the '
            'same corpus')

    unread = doc['files_not_well_formed']
    if not isinstance(unread, list):
        raise Failure(f'`files_not_well_formed` is {type(unread).__name__}, '
                      'not a list')
    # EVERY ENTRY IS CHECKED FOR BEING A RECORD FIRST. Calling `.get` on a bare
    # string raised `AttributeError` straight out of this loader — a crash
    # instead of the tool's own truthful refusal, which is the difference
    # between "your input is malformed" and "the gate is broken".
    unread_names = []
    for u in unread:
        if not isinstance(u, dict):
            raise Failure(f'unread entry {u!r} is {type(u).__name__}, not a '
                          'record')
        if not _is_basename(u.get('file')) or not _is_sha256(u.get('sha256')):
            raise Failure(f'unread entry {u!r} lacks a plain file name and a '
                          'lowercase sha256; an excluded file must still be '
                          'identified')
        if u['file'] not in pinned:
            raise Failure(f'{u["file"]} is excluded as standards-invalid but '
                          'is not in the frozen manifest; a file the corpus '
                          'does not contain cannot be excluded from it')
        if pinned[u['file']] != u['sha256']:
            raise Failure(
                f'{u["file"]} is excluded with sha256 {u["sha256"][:16]}… but '
                f'the manifest pins {pinned[u["file"]][:16]}…; that is a '
                'different file')
        unread_names.append(u['file'])
    if len(set(unread_names)) != len(unread_names):
        raise Failure('the same file is listed unread more than once; the '
                      'scope equation would count it twice')

    # THE SCOPE EQUATION, so the three numbers cannot disagree quietly.
    # THE PARTITION, not a coverage count. A file that is not a well-formed
    # Inline XBRL report has no lawful transform occurrence to replay, so
    # excluding it is the standard being applied rather than coverage being
    # missed. What must hold is that every manifest file is ACCOUNTED FOR.
    if doc['n_files_parsed'] + len(unread) != doc['n_files_in_manifest']:
        raise Failure(
            f'scope does not add up: {doc["n_files_parsed"]} parsed + '
            f'{len(unread)} standards-invalid != '
            f'{doc["n_files_in_manifest"]} in manifest')
    complete = doc['n_files_parsed'] + len(unread) == doc['n_files_in_manifest']
    if doc['supported_scope_complete'] != complete:
        raise Failure(
            f'`supported_scope_complete` says '
            f'{doc["supported_scope_complete"]} but the counts say {complete}; '
            'it is not a field to be asserted independently of the files')

    if not isinstance(doc['occurrences'], list):
        raise Failure(f'`occurrences` is {type(doc["occurrences"]).__name__}, '
                      'not a list')
    # A RECEIPT CANNOT REPORT FACTS FROM NO FILES. `0` in the manifest, `0`
    # read and one eligible fact satisfied every equation above — zero equals
    # zero — and was accepted as COMPLETE coverage of nothing.
    if (doc['occurrences'] or doc['eligible_facts']) and (
            doc['n_files_in_manifest'] < 1 or doc['n_files_parsed'] < 1):
        raise Failure(
            f'the receipt carries {doc["eligible_facts"]} eligible fact(s) '
            f'from {doc["n_files_parsed"]} of {doc["n_files_in_manifest"]} '
            'files; facts cannot come from no corpus')

    seen, total = set(), 0
    for o in doc['occurrences']:
        if not isinstance(o, dict):
            raise Failure(f'occurrence row {o!r} is {type(o).__name__}, not a '
                          'record')
        for field in ('registry', 'local', 'text'):
            if not isinstance(o.get(field), str):
                raise Failure(f'occurrence row {o!r} has a non-string '
                              f'`{field}`; it does not identify an input')
        triple = (o['registry'], o['local'], o['text'])
        if triple in seen:
            raise Failure(f'duplicate occurrence row {triple!r}; the '
                          'multiplicities would double-count')
        seen.add(triple)
        if not isinstance(o.get('count'), int) or isinstance(o['count'], bool) \
                or o['count'] < 1:
            raise Failure(f'occurrence {triple!r} has count {o.get("count")!r}; '
                          'a multiplicity must be a positive integer')
        total += o['count']
    if total != doc['eligible_facts']:
        raise Failure(f'occurrence multiplicities sum to {total} but the file '
                      f'states {doc["eligible_facts"]} eligible facts; the '
                      'replay set is not the population it claims')

    cases = [(o['registry'], o['local'], o['text'])
             for o in doc['occurrences'] if o['registry'] in SUPPORTED]
    if not cases:
        raise Failure('the corpus carries no occurrence under any supported '
                      'registry; there is no behavioural claim to make')

    # THE SCOPE TRAVELS WITH THE INPUTS, and the invalid files stay named. The
    # scanner records which manifest files are not valid Inline XBRL reports;
    # if that stopped here, this gate would go on to talk about "the corpus"
    # without saying what it actually replayed.
    binding = {'occurrence_file': os.path.basename(path),
               'occurrence_file_sha256': hashlib.sha256(raw).hexdigest(),
               'input_manifest_file': doc['input_manifest_file'],
               'input_manifest_sha256': on_disk,
               'supported_scope_complete': doc['supported_scope_complete'],
               'files_in_manifest': doc['n_files_in_manifest'],
               'files_parsed': doc['n_files_parsed'],
               'files_not_valid_inline_xbrl': [
                   {'file': u['file'], 'sha256': u['sha256']}
                   for u in doc['files_not_well_formed']],
               # BOTH numbers, because they answer different questions: how
               # many DISTINCT inputs were replayed, and how many FACTS those
               # stand for.
               'distinct_triples_total': len(doc['occurrences']),
               'distinct_triples_replayed': len(cases),
               'fact_multiplicity_total': total,
               'fact_multiplicity_replayed': sum(
                   o['count'] for o in doc['occurrences']
                   if o['registry'] in SUPPORTED),
               'occurrences_total': len(doc['occurrences']),
               'occurrences_in_supported_registries': len(cases)}
    return cases, binding


def compare(a, b, names):
    """Every way these two can disagree, as a list of failure sentences."""
    bad = []
    for label, tag in ((a, names[0]), (b, names[1])):
        missing = [ns for ns in SUPPORTED if ns not in label['function_table']]
        if missing:
            bad.append(f'{tag} does not implement supported registries: '
                       + ', '.join(missing))
        if label['sec_registry_implemented']:
            bad.append(f'{tag} claims to implement {SEC_REGISTRY}; this '
                       'receipt was written on the recorded fact that Arelle '
                       'does not. Re-read the scope note before trusting it.')
    if a['function_table'] != b['function_table']:
        bad.append('the supported function tables differ between versions')

    # AGREEMENT ON ABSENCE IS NOT AGREEMENT ON BEHAVIOUR. If a corpus
    # occurrence names a transform NEITHER version implements, both sides
    # record `absent`, the two agree, and the case slides into the pass count
    # having exercised nothing. It is counted and reported as its own number so
    # the behavioural population is the population that actually ran.
    absent = sorted(k for k in set(a['results']) & set(b['results'])
                    if a['results'][k][0] == 'absent'
                    and b['results'][k][0] == 'absent')
    if absent:
        bad.append(f'{len(absent)} corpus occurrence(s) name a transform '
                   f'neither version implements, e.g. {absent[0]}; they cannot '
                   'support a behavioural claim and must not be counted as one')

    # NO ALLOWLIST. Any difference fails and goes back for a fresh ruling; a
    # standing exception list would let one accepted difference silently carry
    # a later, unrelated regression through every future run.
    keys = sorted(set(a['results']) | set(b['results']))
    diffs = [{'case': k, names[0]: a['results'].get(k),
              names[1]: b['results'].get(k)}
             for k in keys if a['results'].get(k) != b['results'].get(k)]
    if diffs:
        bad.append(f'{len(diffs)} behavioural differences on frozen-corpus '
                   'occurrences')
    return keys, diffs, bad


def main(dest=None, occurrences=None):
    # `dest` exists so the fail-closed proofs can drive the RED path without
    # overwriting the real receipt with a deliberately broken one;
    # `occurrences` so they can supply a tiny corpus instead of the frozen one.
    dest = dest or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '24_arelle_ixt_parity.json')
    report = {
        'versions': list(VERSIONS),
        'supported_registries': list(SUPPORTED),
        'claim': 'supported (TR3/TR4/TR5) function-table compatibility, plus '
                 'behavioural agreement on every transform occurrence THE '
                 'SCANNER WAS ABLE TO READ from the manifest-bound frozen '
                 'corpus — see `corpus_binding.files_parsed` of '
                 '`files_in_manifest`, which is the population this covers and '
                 'the only one it covers. Files listed in '
                 '`files_not_valid_inline_xbrl` are not valid Inline XBRL '
                 'reports (Inline XBRL 1.1 §3.1 / SEC EDGAR XBRL Guide June '
                 '2026 §11.2) and have no lawful transform occurrence to '
                 'replay. NOT universal parity: inputs no filing produced are '
                 'not evidence about filings.',
        'sec_registry_note': f'{SEC_REGISTRY} is not implemented by Arelle; '
                             'parity for it is not testable here'}
    failures = []
    try:
        cases, binding = load_occurrences(
            occurrences or os.path.join(os.path.dirname(os.path.abspath(
                __file__)), OCCURRENCES))
        report['corpus_binding'] = binding
        if not binding['supported_scope_complete']:
            # THE PARTITION IS BROKEN, which is a different fault from the two
            # versions disagreeing. A manifest file that is neither parsed nor
            # named as standards-invalid is unexplained, and this receipt is
            # not entitled to describe a population it cannot account for.
            failures_from_scope = [
                f'the manifest partition is INCOMPLETE: '
                f'{binding["files_parsed"]} parsed + '
                f'{len(binding["files_not_valid_inline_xbrl"])} '
                f'standards-invalid does not account for '
                f'{binding["files_in_manifest"]} manifest files.']
        else:
            failures_from_scope = []
        with tempfile.TemporaryDirectory(prefix='ixt-parity-') as root:
            got, prov = {}, {}
            for v in VERSIONS:
                py, prov[v] = build(v, root)
                got[v] = probe(py, cases)
            report['provenance'] = prov
            report['per_version'] = {
                v: {k: got[v][k] for k in got[v] if k != 'results'}
                for v in VERSIONS}
            keys, diffs, version_failures = compare(got[VERSIONS[0]],
                                                    got[VERSIONS[1]], VERSIONS)
            report['compared_cases'] = len(keys)
            report['functions_compared'] = sum(
                len(t) for t in got[VERSIONS[0]]['function_table'].values())
            report['differences'] = diffs
            # TWO SEPARATE FACTS, and an earlier draft had only one name for
            # both. "The versions agree" and "we looked at the whole corpus"
            # can differ, and collapsing them lets either one be read as the
            # other. The gate passes only when both hold.
            report['version_parity_proven'] = not version_failures
            failures = failures_from_scope + version_failures
    except Failure as exc:
        failures = [str(exc)]
    report['failures'] = failures
    report['supported_scope_complete'] = (
        report.get('corpus_binding', {}).get('supported_scope_complete')
        is True)
    # EXACTLY the reviewer's definition, and only these two facts.
    report['gate_passed'] = (report.get('version_parity_proven') is True
                             and report['supported_scope_complete']
                             and not failures)

    with open(dest, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1, sort_keys=True)

    for v in report.get('provenance', {}):
        p = report['provenance'][v]
        print(f"  {v}: resolved {p['resolved']}  sha256 {p['sha256']}")
    if 'corpus_binding' in report:
        b = report['corpus_binding']
        print(f"  corpus occurrences : {b['occurrences_in_supported_registries']}"
              f" of {b['occurrences_total']}"
              f"  (manifest {b['input_manifest_sha256'][:16]}…)")
        invalid = b['files_not_valid_inline_xbrl']
        print(f"  manifest partition : {b['files_parsed']} parsed + "
              f"{len(invalid)} standards-invalid = {b['files_in_manifest']}"
              f"{'' if b['supported_scope_complete'] else '  <-- UNACCOUNTED'}")
        for f in invalid:
            print(f"     NOT valid Inline XBRL, no lawful occurrence to "
                  f"replay: {f['file']}  sha256 {f['sha256'][:16]}…")
    if 'compared_cases' in report:
        print(f"  functions compared : {report['functions_compared']}")
        print(f"  cases compared     : {report['compared_cases']}")
        for d in report['differences'][:10]:
            print(f"     {d['case']}  {d[VERSIONS[0]]} vs {d[VERSIONS[1]]}")
    for f in failures:
        print(f'  FAIL: {f}')
    print(f"  version parity     : {report.get('version_parity_proven')}")
    print(f"  scope complete     : {report['supported_scope_complete']}")
    print(f"  GATE PASSED        : {report['gate_passed']}")
    return 0 if report['gate_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
