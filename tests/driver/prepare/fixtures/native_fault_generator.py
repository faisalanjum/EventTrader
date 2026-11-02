"""Test-only generator: unchanged document.main with a fault at a native call."""
from contextlib import nullcontext
import json
from pathlib import Path
import sys
from unittest.mock import patch

plan=json.loads(Path(sys.argv[1]).read_bytes())
sys.path.insert(0,plan['runtime_root'])
from driver.prepare import document
from driver.prepare.convert import edgartools_html
from driver.prepare.get.acquire import StorageError
import lxml.html

spec=plan['audit_fault']
kind={'OSError':OSError,'StorageError':StorageError,'ImportError':ImportError,'MemoryError':MemoryError,'ValueError':ValueError}.get(spec['kind'])
boundary=spec['boundary']
fault=kind('controlled native '+spec['kind']) if kind else None
thrown=fault
for n in range(spec['depth']):
    wrapper=RuntimeError('explicit intermediate wrapper '+str(n))
    wrapper.__cause__=thrown
    thrown=wrapper
native=lxml.html.fromstring
def inject(*args,**kwargs):
    if boundary=='inline_only' and 'data-prepare-fact-' not in str(args[0]): return native(*args,**kwargs)
    raise thrown
context=nullcontext() if kind is None else patch.object(edgartools_html,'parse',side_effect=inject) if boundary=='direct' else patch.object(lxml.html,'fromstring',side_effect=inject)
with context:
    document.main()
