"""Guard the historical cached-resume test's two writable native locations.

The test mutates a real-shaped state and its child records. Only private
copies may be served there. This is TEST setup, not a native-evidence owner.
"""
import json
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
REC = UNIT.parents[1]
sys.path.insert(0, str(REC / 'a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher'))
import boundary as B


def native_targets():
    state = json.loads((UNIT.parent / 'unit_1814/out/run_1814/state.seg01.json').read_text())
    assert len(state['states']) == 1
    path = Path(state['states'][0])
    archive = UNIT.parent / 'unit_1778/evidence'
    return ((path, archive / 'g1_states' / path.name),
            (path.parent.parent / 'subagents/workflows' / path.stem,
             archive / 'g1_runs' / path.stem))


def check(rows):
    for logical, preserved in native_targets():
        matches = [r for r in rows if r['logical'] == str(logical)]
        assert len(matches) == 1, 'missing private native TEST binding: ' + str(logical)
        row = matches[0]
        source = Path(row['source']).resolve()
        relative = source.relative_to(UNIT)
        assert relative.parts[0].startswith('regression_ordinary_'), source
        assert row['mode'] == 'rw', 'mutation fixture must be a private writable copy'
        assert source != preserved.resolve()
        assert B.source_sha(str(source)) == B.source_sha(str(preserved)), source
    return True


if __name__ == '__main__':
    assert check(B.read_map(sys.argv[1]))
    print('Both native mutation locations are exact private TEST copies.')
