"""Completed primary and retry calls for the active A4 candidate owners."""
import os
import build_kfields_key as K


def finalized_scheduled(run):
    """Count only finalized attempts; an offered but unrun retry adds zero."""
    total = 0
    for base in (run, os.path.join(run, 'retry')):
        fin = os.path.join(base, K.FINALIZATION_NAME)
        if os.path.isfile(fin):
            total += K._load(fin)['ledger']['scheduled']
    return total
