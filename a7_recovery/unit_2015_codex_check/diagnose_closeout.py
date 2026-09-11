"""Read-only diagnosis: report the exact differing fields, then refuse."""
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2009/owner'))
import a4_review_composite as R

original = R._existing


def compared(path, text):
    try:
        return original(path, text)
    except ValueError:
        before, now = json.loads(Path(path).read_text()), json.loads(text)
        print(json.dumps({'path': path, 'differences': {
            k: {'stored': before.get(k), 'live': now.get(k)}
            for k in sorted(set(before) | set(now)) if before.get(k) != now.get(k)
        }}, indent=1), flush=True)
        raise


with R._using(R, _existing=compared):
    old, stage = R.old_readings()
    print(json.dumps({'matched': True, 'labels': len(old),
                      'outcomes': dict(Counter(v[0] for v in old.values()))}, indent=1))
