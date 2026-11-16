"""Matched generic label check: only 12 Locate instruction strings change.

Native Locate treats instructions as an extraction label. Test explicit labels
instead of references to task names; retain source, options and grouping exactly.
"""
import json
import pathlib
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/home/faisal/EventMarketDB')
from config import local_llm as L

ROOT = pathlib.Path('/tmp/decider_claude_review_20261115')
OUT = ROOT / 'prepared_record'
request = json.loads((OUT / 'request.json').read_text())
targets = json.loads((OUT / 'source_map.json').read_text())['targets']
for target in targets:
    address = f"forecast {target['text']!r} at [{target['tag']}]"
    request['questions'][target['tag'] + '_modifiers']['instructions'] = (
        f'Measurement qualifiers, approximation or strict-bound words, and growth/change words '
        f'applying to {address}; exact qualifying words only, not the number, measure, date or unit.')
    request['questions'][target['tag'] + '_conditions']['instructions'] = (
        f'Management\'s assumptions, dependencies and exclusions applying to {address}, '
        f'including their negations; not causes, actual results, measurement definitions or guidance movements.')
prior = json.loads((OUT / 'request.json').read_text())
assert request['state'] == prior['state']
assert list(request['questions']) == list(prior['questions'])
changed = [qid for qid, q in request['questions'].items() if q != prior['questions'][qid]]
assert len(changed) == 12 and all(request['questions'][q]['type'] == 'locate' for q in changed)
(OUT / 'label_check_request.json').write_text(json.dumps(request, indent=2))
t = time.perf_counter()
try:
    result = {'response': L.decide(**request, timeout=1800)}
except Exception as error:
    result = {'error': str(error)}
result.update(seconds=time.perf_counter() - t,
              finished_at=datetime.now(ZoneInfo('America/Toronto')).isoformat())
(OUT / 'label_check_result.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k: v for k, v in result.items() if k != 'response'}), flush=True)
with (ROOT / 'progress.md').open('a') as f:
    f.write('\nTest: Matched prepared-block request; replace only 12 indirect Locate task-name references with explicit generic extraction labels.\n')
    f.write(f'Result: {result["seconds"]:.2f}s; {result.get("response", {}).get("usage")}; error={result.get("error")}. Source, choice questions and grouping unchanged; copying requires review.\n')
    f.write('Next: Compare exact returned spans and complete meanings; keep only demonstrated improvements and stop bounded field-copy repairs.\n')
