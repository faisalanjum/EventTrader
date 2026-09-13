"""How many of the map's harness file overlays the finished view still serves.

The active grading owners must stay CURRENT even while the source/key-era
owners come from their own era, so this counts the overlays whose served bytes
still equal the pin in map_g23_transport_2098.tsv. Reads only.
"""
import hashlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
MAP = os.path.join(A7, 'unit_2020_codex_check/map_g23_transport_2098.tsv')
VIEW = sys.argv[1]
ROOT = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')

matching = total = 0
for line in io.open(MAP, encoding='utf-8'):
    cells = line.rstrip('\n').split('\t')
    if len(cells) < 4 or not cells[0].startswith(ROOT + '/'):
        continue
    if cells[0].count('/') != ROOT.count('/') + 1 or not os.path.isfile(cells[1]):
        continue
    total += 1
    served = os.path.join(VIEW, os.path.basename(cells[0]))
    matching += hashlib.sha256(io.open(served, 'rb').read()).hexdigest() == cells[2]
assert total, 'the map names no harness file overlays'
print('%d/%d' % (matching, total))
