"""Run just the changed retry boundary and its format dependency tests."""
from pathlib import Path
import pytest

here = Path(__file__).resolve().parent
raise SystemExit(pytest.main([str(here / 'test_meaning_retry_plan_2107.py'),
                             str(here / 'test_meaning_format_2105.py'),
                             '-q', '-p', 'no:cacheprovider']))
