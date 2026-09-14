"""Measure the served source-only prefix around the approved anchor. Read-only."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E


def probe(_producer, _inputs):
    G = E.G
    sys.path.insert(0, str(E.A7 / 'unit_2063_source_closeout'))
    import a4_source_taskv2 as V2
    bound = G._approved_bound()
    base = V2.served_prefix(bound)
    anchor = 'Interpret those targets only.'
    print('served prefix chars', len(base), 'sha', E.K._sha(base), flush=True)
    print('anchor count', base.count(anchor), flush=True)
    i = base.index(anchor)
    print('--- context ---', flush=True)
    print(repr(base[max(0, i-420):i+300]), flush=True)
    lines = base[:i].split('\n')
    print('--- paragraph line widths ---',
          [len(l) for l in base[max(0,i-420):i+300].split('\n')], flush=True)
    print('clarification already present:',
          'The target fixes which fact you review' in base, flush=True)
    return {}


E.with_prepared_inputs(probe)
