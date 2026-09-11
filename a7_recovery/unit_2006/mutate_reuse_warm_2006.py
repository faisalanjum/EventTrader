"""Remove only the warm evaluation guard; its behavioral test must detect it."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('check_reuse_warm_2006.py')),
               run_name='__main__', init_globals={'remove_warm_guard': True})
