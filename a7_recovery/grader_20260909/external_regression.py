"""Record the existing pure production-dependency tests; no model or graph calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
repo = here.parents[1]
out = here / "attempts" / sys.argv[1]
out.mkdir()  # Existing attempts are evidence, never replaced.
selection = json.loads((here / "EXTERNAL_TESTS.json").read_text())
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
for name in ("RUN_NEO4J_ROUNDTRIP_PROBE", "ENABLE_DRIVER_WRITES", "S4_REHEARSAL_OUT",
             "PYTEST_ADDOPTS"):
    env.pop(name, None)
command = [sys.executable, "-B", "-m", "pytest", "-q", "-ra", "-p", "no:cacheprovider",
           "-m", selection["marker"], "--basetemp", str(out / "pytest")] + selection["modules"]
record = {"command": command, "selection": selection,
          "test_sha256": {p: hashlib.sha256((repo / p).read_bytes()).hexdigest()
                          for p in selection["modules"]}}
for label, extra in (("collection", ["--collect-only"]),
                     ("regression", ["--junitxml", str(out / "JUNIT.xml")])):
    actual = command + extra
    result = subprocess.run(actual, cwd=repo, env=env, capture_output=True, text=True)
    (out / (label + ".stdout.txt")).write_text(result.stdout)
    (out / (label + ".stderr.txt")).write_text(result.stderr)
    record[label] = {"command": actual, "exit": result.returncode}
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(label, result.returncode, result.stdout.splitlines()[-1:], flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
