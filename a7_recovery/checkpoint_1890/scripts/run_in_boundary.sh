#!/bin/bash
# run_in_boundary.sh <payload> <tag> [limit_seconds]
#
# Runs a payload inside the recovery boundary and RETURNS ITS REAL EXIT CODE.
# <payload> is a .py in ledger/: the boundary always execs it with python.
#
# EVERY attempt owns a fresh durable directory logs/attempt_<tag>/, created
# with an ordinary exclusive mkdir. Its stdout, stderr, exit code and any test
# artifact live only there, so a later attempt can never overwrite an earlier
# trace (Codex SEQ 1877). A repeated tag stops here, before anything runs.
#
# `timeout` is one process that signals and exits, leaving nothing to orphan;
# `setsid --wait` keeps the handle and returns the payload's own status. ORDER
# MATTERS: setsid OUTSIDE so the job gets its own session, `timeout` INSIDE so
# the signal reaches the boundary within that session.
set -u
PAYLOAD="$1"; TAG="$2"; LIMIT="${3:-2400}"
R=/home/faisal/EventMarketDB-driver-recovery
A=$R/a7_recovery
U=$A/unit_1881
BND=$R/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher/boundary.py
PY=/home/faisal/EventMarketDB/venv/bin/python3

ATT="$U/logs/attempt_$TAG"
mkdir "$ATT" || { echo "REFUSE: $ATT already exists - that attempt is evidence"; exit 5; }

"$PY" -B "$U/ledger/repin_1881.py" > "$ATT/repin.txt" 2>&1 || {
  echo "REPIN FAILED"; cat "$ATT/repin.txt"; exit 4; }

# THE PRODUCER, LIFECYCLE AND CANDIDATE ARE NAMED HERE, never defaulted in the
# test. They are exactly the three the verified native run used.
export A7_PRODUCER_IDENTITY="$A/unit_1849/logs/PREFLIGHT_1851_historical.json"
export A7_G1_PINS="$A/unit_1871/logs/G1_PINS_1871.json"
export A7_G23_CANDIDATE="$A/unit_1871/out/native/g23_candidate"
# THE APPROVED RECOVERY driver_validators, pinned. The test binds the
# recovery package in native_1876's own import order and proves THIS hash
# inside the pytest child; a separate probe is not sufficient (SEQ 1878/1879).
export A7_DRIVER_VALIDATORS_SHA="${A7_DRIVER_VALIDATORS_SHA:-$(sha256sum "$R/driver/core/driver_validators.py" | cut -d" " -f1)}"
export A7_ATTEMPT_DIR="/tmp/a7_logs_1781/attempt_$TAG"

cd "$R" || exit 2
setsid --wait timeout --signal=TERM --kill-after=20 "$LIMIT" \
  env PYTHONDONTWRITEBYTECODE=1 \
      A7_PRODUCER_IDENTITY="$A7_PRODUCER_IDENTITY" \
      A7_G1_PINS="$A7_G1_PINS" \
      A7_G23_CANDIDATE="$A7_G23_CANDIDATE" \
      A7_DRIVER_VALIDATORS_SHA="$A7_DRIVER_VALIDATORS_SHA" \
      A7_ATTEMPT_DIR="$A7_ATTEMPT_DIR" \
      A7_TAG="$TAG" \
      A7_PYTEST_ARGS="${A7_PYTEST_ARGS:-}" \
    "$PY" -B "$BND" --host "$U/a7_map_1881b.tsv" "$U/ledger/$PAYLOAD" \
    > "$ATT/stdout.txt" 2> "$ATT/stderr.txt" < /dev/null
RC=$?

echo "$RC" > "$ATT/exit"
cat "$ATT/stdout.txt"
echo "--- stderr tail ---"; tail -8 "$ATT/stderr.txt"
echo "raw exit $RC"
exit "$RC"
