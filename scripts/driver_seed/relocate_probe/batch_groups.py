#!/usr/bin/env python3
"""BATCHED reader input builder (#770): group frozen benchmark cases by (ticker, period_target),
merge + dedupe their candidate snippets, and write grouped batches — ONE reader call per group.

HARD CAPS (user requirement 2026-07-14): <=8 metrics per call and <=100KB merged candidates per
call; a group over either cap SPLITS into sub-groups. Quality bar: batched answers must be
IDENTICAL to the certified one-by-one answers (the A/B this feeds).

    venv/bin/python scripts/driver_seed/relocate_probe/batch_groups.py --set quarterly
"""
import os, sys, json, glob, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_CASES = 8
MAX_CHARS = 100_000


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--set', required=True); a = ap.parse_args()
    B = f'{HERE}/benchmark'
    batches = {}
    for f in glob.glob(f'{B}/batches_{a.set}/batch_*.json'):
        b = json.load(open(f)); batches[b['id']] = b
    groups = collections.defaultdict(list)
    for i, b in sorted(batches.items()):
        groups[(b['ticker'], b['period_target'])].append(i)
    odir = f'{HERE}/gbatches_{a.set}'; os.makedirs(odir, exist_ok=True)
    for f in glob.glob(f'{odir}/*.json'):
        os.remove(f)
    k = 0; singles = 0; case_tot = 0; vol_batched = 0
    vol_single = sum(sum(len(c['text']) for c in b['candidates']) for b in batches.values())

    def merged_cands(id_list):
        seen, out = set(), []
        for i in id_list:
            for c in batches[i]['candidates']:
                key = c['text'][:160]
                if key not in seen:
                    seen.add(key); out.append(c)
        return out

    def emit_chunks(id_list):
        """yield id-sublists each within BOTH caps (recursive halving; singleton = trim)."""
        if len(id_list) > MAX_CASES:
            h = len(id_list) // 2
            yield from emit_chunks(id_list[:h]); yield from emit_chunks(id_list[h:])
            return
        cands = merged_cands(id_list)
        if sum(len(c['text']) for c in cands) > MAX_CHARS and len(id_list) > 1:
            h = len(id_list) // 2
            yield from emit_chunks(id_list[:h]); yield from emit_chunks(id_list[h:])
            return
        yield id_list

    for (tk, per), ids in sorted(groups.items()):
        for chunk in emit_chunks(ids):
            cases = [{'id': i, 'kpi': batches[i]['kpi'], 'fmt': batches[i]['fmt'],
                      'period_type': batches[i]['period_type'], 'period_target': batches[i]['period_target'],
                      'address': batches[i]['address']} for i in chunk]
            cands = merged_cands(chunk)
            merged = sum(len(c['text']) for c in cands)
            if merged > MAX_CHARS:                              # singleton over cap: trim tail candidates
                cands = cands[:max(1, int(len(cands) * MAX_CHARS / merged))]
                merged = sum(len(c['text']) for c in cands)
            json.dump({'gid': k, 'ticker': tk, 'period_target': per, 'cases': cases,
                       'candidates': cands}, open(f'{odir}/gbatch_{k}.json', 'w'))
            vol_batched += merged; case_tot += len(cases)
            singles += (len(cases) == 1)
            k += 1
    print(f"[{a.set}] {case_tot} cases -> {k} calls ({singles} singletons) | "
          f"candidate volume {vol_single/1e6:.1f}MB -> {vol_batched/1e6:.1f}MB "
          f"({100*(1-vol_batched/max(vol_single,1)):.0f}% saved)")


if __name__ == '__main__':
    main()
