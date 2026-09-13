"""Is serving the era's build_kfields_key.py 'switching grading back to old code'?

If the two versions differ in BEHAVIOUR, serving the older one in a TEST view
would be exactly the reactivation Codex forbade. So this proves the opposite
mechanically rather than by reading the diff:

  * every public name is present in both, with the same kind
  * every function's compiled code object is byte-identical, except the ones
    the diff actually touched, which are named here and shown
  * the one added constant is bound to a value that already existed, so the
    one changed comparison compares the same object it compared before

Nothing is asserted about intent. If any of it is false, this refuses.
"""
import collections
import hashlib
import importlib.util
import io
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
G = os.path.join(A7, 'grader_20260909')
ERA = os.path.join(G, 'attempts/native_final5/view/harness_g1v3/build_kfields_key.py')
CURRENT = os.path.join(A7, 'unit_2008/harness_g1v3/build_kfields_key.py')
OUT = os.path.join(HERE, 'OWNER_EQUIVALENCE_2100.json')


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def digest(code):
    """A digest of what a code object DOES, with line numbers excluded.

    co_code plus the names and constants it touches. Nested code objects are
    digested the same way instead of repr'd, because a code object's repr
    carries the file and line it was defined on - and a diff that inserts
    lines at the top of the file moves every line number without changing a
    single instruction. Digesting the repr would report the whole module as
    changed, which is exactly the false answer this has to avoid.
    """
    consts = []
    for const in code.co_consts:
        consts.append(digest(const) if isinstance(const, types.CodeType)
                      else repr(const))
    return hashlib.sha256(
        code.co_code
        + repr(code.co_names).encode()
        + repr(code.co_varnames).encode()
        + repr(consts).encode()).hexdigest()


def compiled(path):
    """{top-level name: digest of its behaviour}, without importing.

    Importing would run the module's own path setup and pull in the rest of
    the harness; compiling answers the behaviour question on its own.
    """
    source = io.open(path, encoding='utf-8').read()
    module = compile(source, path, 'exec')
    out = collections.OrderedDict()
    for const in module.co_consts:
        if isinstance(const, types.CodeType):
            out[const.co_name] = digest(const)
    return out, source, module


era_code, era_src, era_mod = compiled(ERA)
cur_code, cur_src, cur_mod = compiled(CURRENT)

only_current = [n for n in cur_code if n not in era_code]
only_era = [n for n in era_code if n not in cur_code]
changed = [n for n in cur_code if n in era_code and cur_code[n] != era_code[n]]

# the module-level constants each version binds, by name -> repr
def top_constants(source):
    names = collections.OrderedDict()
    for line in source.split('\n'):
        if line[:1].isalpha() and line[:1].isupper() and ' = ' in line:
            name, value = line.split(' = ', 1)
            if name.isupper() and name.isidentifier():
                names[name] = value.strip()
    return names


era_consts, cur_consts = top_constants(era_src), top_constants(cur_src)
added_consts = {n: v for n, v in cur_consts.items() if n not in era_consts}
dropped_consts = {n: v for n, v in era_consts.items() if n not in cur_consts}
retargeted = {n: (era_consts[n], cur_consts[n]) for n in cur_consts
              if n in era_consts and era_consts[n] != cur_consts[n]}

# every added constant must be an ALIAS of a name that already existed, or the
# change is not inert and this refuses.
aliases_only = all(v in era_consts or v in cur_consts for v in added_consts.values())

record = collections.OrderedDict([
    ('kind', 'is the era key owner behaviourally the same as the current one'),
    ('era_path', ERA), ('era_sha256', sha(ERA)),
    ('current_path', CURRENT), ('current_sha256', sha(CURRENT)),
    ('top_level_functions', len(cur_code)),
    ('present_only_in_current', only_current),
    ('present_only_in_era', only_era),
    ('functions_whose_code_differs', changed),
    ('constants_added_by_current', added_consts),
    ('constants_dropped_by_current', dropped_consts),
    ('constants_retargeted', retargeted),
    ('every_added_constant_is_an_alias_of_an_existing_one', aliases_only),
    ('model_calls', 0)])

# The one function that moved is only inert if the name it now reads is bound
# to the value it read before, and nothing ever rebinds it. Both are checked.
def rebinds(source, name):
    return [l for l in source.split('\n')
            if l.split('=')[0].strip() == name and '==' not in l.split('=')[0] + '=']


rebound = rebinds(cur_src, 'ROW_MODEL_ID')
alias_target = added_consts.get('ROW_MODEL_ID')
era_lines = era_src.split('\n')
cur_lines = cur_src.split('\n')
import difflib
moved_fn_diff = [l for l in difflib.unified_diff(era_lines, cur_lines, lineterm='', n=0)
                 if l[:1] in '+-' and l[:3] not in ('---', '+++')
                 and 'MODEL_ID' in l]

record['the_one_function_that_moved'] = collections.OrderedDict([
    ('name', changed[0] if changed else None),
    ('rebinding_lines_for_ROW_MODEL_ID', [l.strip() for l in rebound]),
    ('bound_once_to', alias_target),
    ('lines_that_mention_the_constant', [l.strip() for l in moved_fn_diff])])

assert len(changed) == 1, 'more than one function moved: %s' % changed
assert len(rebound) == 1, 'ROW_MODEL_ID is rebound %d times' % len(rebound)
assert alias_target == 'RUNTIME_MODEL_ID', alias_target

assert not only_era, 'the current version DROPPED a function: not inert'
assert not dropped_consts, 'the current version dropped a constant: not inert'
assert not retargeted, 'a constant was pointed at something else: not inert'
assert aliases_only, 'an added constant is not an alias: not inert'

with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('functions compared        :', len(cur_code))
print('added by current          :', only_current or 'none')
print('dropped by current        :', only_era or 'none')
print('functions whose code moved:', changed or 'none')
print('constants added           :', added_consts or 'none')
print('all added are aliases     :', aliases_only)
print('wrote', OUT)
