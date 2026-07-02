"""
unit_extract.py — STANDALONE wrapper that IMPORTS THE REAL guidance unit code.

This module does NOT re-implement any canonicalization logic. It imports the
real functions from the production guidance_ids.py and exposes a thin
extract_unit() wrapper so a DriverUpdate-style caller can run V1 or V2.

V1 = canonicalize_unit(unit_raw, slug(driver_name)) + canonicalize_value
V2 = build_guidance_ids(..., resolution_mode='v2') reading the resolved_* fields

Run directly to print IMPORT PROOF:
    /usr/bin/python3 unit_extract.py
"""

import sys

# The real code lives here (stdlib + fiscal_math sibling only — cleanly importable).
_SCRIPTS_DIR = '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts'
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Import the REAL functions — never re-implement.
from guidance_ids import (  # noqa: E402
    canonicalize_unit,
    canonicalize_value,
    slug,
    build_guidance_ids,
)
import guidance_ids  # noqa: E402  (for __file__ / __module__ proof)


def import_proof() -> dict:
    """Return concrete proof that the REAL guidance_ids module was imported."""
    return {
        'canonicalize_unit.__module__': canonicalize_unit.__module__,
        'guidance_ids.__file__': guidance_ids.__file__,
        'slug.__module__': slug.__module__,
        'build_guidance_ids.__module__': build_guidance_ids.__module__,
    }


def extract_unit(driver_name, unit_raw, value=None, quote=None, mode='v1',
                 unit_kind_hint=None, money_mode_hint=None, xbrl_qname=None):
    """
    Canonicalize a DriverUpdate unit using the REAL guidance code.

    Args:
        driver_name: free-text driver name (e.g. 'same_store_sales'); slugged internally.
        unit_raw:    raw unit string as stated in source (e.g. '$', 'billion', '%', 'bps').
        value:       optional numeric value to scale (float-castable).
        quote:       optional surrounding text (V2 reads it for YoY context only).
        mode:        'v1' or 'v2'.
        unit_kind_hint / money_mode_hint / xbrl_qname: optional V2 evidence hints
                     (left None by default so we measure the label-only borrow).

    Returns:
        {'canonical_unit': str, 'scaled_value': float|None,
         'resolved_kind': str|None, 'resolved_money_mode': str|None,
         'resolved_ratio_subtype': str|None, 'error': str|None}
    """
    label_slug = slug(driver_name)
    val = None
    if value is not None and value != '':
        try:
            val = float(value)
        except (TypeError, ValueError):
            val = None  # range strings like '94-97' can't scale to a single float

    out = {
        'canonical_unit': None,
        'scaled_value': None,
        'resolved_kind': None,
        'resolved_money_mode': None,
        'resolved_ratio_subtype': None,
        'error': None,
    }

    if mode == 'v1':
        # V1 = the literal 'extract a unit' entry point named in the mission.
        try:
            cu = canonicalize_unit(unit_raw if unit_raw is not None else '', label_slug)
            out['canonical_unit'] = cu
            if val is not None:
                try:
                    out['scaled_value'] = canonicalize_value(
                        val, unit_raw if unit_raw is not None else '', cu, label_slug)
                except ValueError as e:
                    out['scaled_value'] = None
                    out['error'] = f'value-scale: {e}'
        except Exception as e:  # noqa: BLE001
            out['error'] = f'v1: {type(e).__name__}: {e}'
        return out

    if mode == 'v2':
        # V2 = the production evidence resolver via build_guidance_ids.
        # build_guidance_ids requires label/source_id/period_u_id/basis_norm.
        try:
            res = build_guidance_ids(
                label=driver_name,
                source_id='PROBE_SRC',
                period_u_id='FY2025',
                basis_norm='unknown',
                low=val,
                unit_raw=unit_raw if unit_raw is not None else 'unknown',
                quote=quote,
                unit_kind_hint=unit_kind_hint,
                money_mode_hint=money_mode_hint,
                xbrl_qname=xbrl_qname,
                resolution_mode='v2',
            )
            out['canonical_unit'] = res.get('canonical_unit')
            out['scaled_value'] = res.get('canonical_low')
            out['resolved_kind'] = res.get('resolved_kind')
            out['resolved_money_mode'] = res.get('resolved_money_mode')
            out['resolved_ratio_subtype'] = res.get('resolved_ratio_subtype')
        except ValueError as e:
            # Could be a scaling guard (e.g. pre-scaled) — still try to recover the unit.
            out['error'] = f'v2: {e}'
            try:
                res = build_guidance_ids(
                    label=driver_name, source_id='PROBE_SRC', period_u_id='FY2025',
                    basis_norm='unknown', low=None,
                    unit_raw=unit_raw if unit_raw is not None else 'unknown',
                    quote=quote, unit_kind_hint=unit_kind_hint,
                    money_mode_hint=money_mode_hint, xbrl_qname=xbrl_qname,
                    resolution_mode='v2',
                )
                out['canonical_unit'] = res.get('canonical_unit')
                out['resolved_kind'] = res.get('resolved_kind')
                out['resolved_money_mode'] = res.get('resolved_money_mode')
                out['resolved_ratio_subtype'] = res.get('resolved_ratio_subtype')
            except Exception as e2:  # noqa: BLE001
                out['error'] += f' | recover: {type(e2).__name__}: {e2}'
        except Exception as e:  # noqa: BLE001
            out['error'] = f'v2: {type(e).__name__}: {e}'
        return out

    out['error'] = f'unknown mode {mode!r}'
    return out


if __name__ == '__main__':
    print('=== IMPORT PROOF ===')
    for k, v in import_proof().items():
        print(f'  {k} = {v}')
    print()
    print('=== smoke test ===')
    print("v1 same_store_sales '%':", extract_unit('same_store_sales', '%', '3', mode='v1'))
    print("v2 same_store_sales '%':", extract_unit('same_store_sales', '%', '3', mode='v2'))
