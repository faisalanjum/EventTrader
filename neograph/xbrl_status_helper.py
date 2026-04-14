"""Post-processing status classifier for XBRL worker paths.

Used by both xbrl_worker_loop.py (K8s path) and mixins/xbrl.py (local path) to
decide final xbrl_status after process_report() returns.

Detects silent Arelle failures (e.g. SEC 503 on schema download) where the
processor returns without raising but built zero facts in memory. Such runs
would otherwise be marked COMPLETED — ghost bug.

Scope: narrow invariant — no run that builds zero in-memory facts becomes
COMPLETED. Does not address async edge-writer persistence failures.
"""
from typing import Optional, Tuple


def classify_xbrl_run(processor) -> Tuple[str, Optional[str]]:
    """Decide xbrl_status from THIS run's in-memory output.

    Uses processor.facts (current run state) — NOT a Neo4j count query —
    because stale facts from a prior partial/failed run could falsely satisfy
    a DB count check and produce a false COMPLETED.

    Returns:
        (status, error) — error is None on success, else a short diagnostic
        suitable for Report.xbrl_error.
    """
    facts_built = 0
    if processor is not None:
        try:
            facts_built = len(processor.facts) if processor.facts else 0
        except Exception:
            facts_built = 0

    if facts_built > 0:
        return "COMPLETED", None
    return "FAILED", "Zero facts extracted after retries — likely persistent Arelle schema load failure"
