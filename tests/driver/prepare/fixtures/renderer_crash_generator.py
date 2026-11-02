"""Test-only generator: unchanged document.main; on the first run (no marker file yet) the first page the step makes crashes its renderer
right after creation (the native chrome://crash navigation) and the marker is written; every later run is untouched (test_renderer_crash)."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

plan = json.loads(Path(sys.argv[1]).read_bytes())
sys.path.insert(0, plan['runtime_root'])
from driver.prepare import document
from driver.prepare.convert import screen_grid

marker = Path(plan['renderer_crash_once']); real = screen_grid.watch
def crash_once(page):
    page = real(page)
    if not marker.exists():
        marker.write_text('crashed once\n')
        try: page.goto('chrome://crash')
        except Exception: pass
    return page
with patch.object(screen_grid, 'watch', crash_once):
    document.main()
