"""Independent candidate/rules identity check in the existing native TEST view."""
import copy
from pathlib import Path

import pytest

from test_correction_native_2118 import base, _current_candidate
from test_a7_input_binding import run, inputs, g1
import test_correction_native_2118 as T


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_candidate_rules_are_the_actual_corrected_prompt_rules(base, kind):
    full = T.LC._required_populations()[kind]
    group = sorted(full)[0]
    subset = {group: copy.deepcopy(full[group])}
    out = base['tmp'] / ('codex_rules_' + kind)
    out.mkdir()
    # a G3 correction now needs the matched-pair inventory its comparison
    # records come from (Core SEQ 2121); every assertion below is unchanged.
    path, sha, doc, pin = T.PREP.prepare(
        str(out), kind, full, subset, base['gold'], base['arms'], T.LC.RUN,
        base['inputs'], T.LC._approved_g1(), T.G.live_key()[1],
        matched_pairs=T._matched(base) if kind == 'G3' else None)
    written = T.G._read(path)
    actual_rules = (T.V.meaning_rules if kind == 'G2' else T.V.extras_rules)()
    old_rules = T.R.KIND_RULES[kind]()
    assert actual_rules != old_rules
    assert written['input_correction_sha256'] == pin == T.G._sha_file(T.V.__file__)
    assert T.G._sha_file(path) == sha
    for row in written['batch_rows']:
        prompt = (Path(out) / row['prompt_path']).read_text(encoding='utf-8')
        assert prompt.startswith(actual_rules), 'positive control: corrected bytes are served'
        assert T.G._sha(prompt) == row['prompt_sha256']
    assert written['rules_block_sha256'] == T.G._sha(actual_rules), (
        kind, 'candidate rules pin does not name its actual corrected prompt rules',
        written['rules_block_sha256'], T.G._sha(actual_rules), T.G._sha(old_rules))
