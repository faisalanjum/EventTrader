"""The preparation seam a question-scoped correction candidate needs.

Four things the existing runner cannot express, and nothing else:
  * a candidate whose ENTIRE population is an independently approved subset;
  * the input version that produced its packets, on the candidate itself,
    BEFORE the root freeze;
  * a rules pin that names the instructions the prompts ACTUALLY carry;
  * for G3, the matched-pair inventory its comparison records come from,
    bound to the candidate so the consumer can check it rather than trust it.

Everything else is the existing owner's: `B.pack_batches` groups, the frozen
renderer builds the packets, `R._rows_and_prompts` does the real bound-script
fitting, and `R.write_kind` writes. The only new mechanism is one scope that
serves the writer its own two missing inputs - the corrected kind-to-rules
mapping and the version - and restores both in a finally. The rules hash is
still computed by `kind_candidate`; nothing here re-hashes it.

No lifecycle, matcher, scorer or schema is copied, and no existing candidate,
completion or judgment is read for writing.
"""
import collections
from contextlib import contextmanager

import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as R
import a7_grading_input_correction_2114 as V


def approved_subset(full, subset):
    """-> the subset, or a refusal. Compared INDEPENDENTLY against the full
    population through the one canonical owner - never trusted because some
    candidate declares it.

    Refuses an empty subset, an unknown group, a group that is not exactly one
    of the full group's own rows, a repeated row and an extra row.
    """
    if not isinstance(subset, dict) or not subset:
        raise ValueError('the correction subset is empty')
    if not isinstance(full, dict) or not full:
        raise ValueError('the full population is empty')
    for group, rows in subset.items():
        if group not in full:
            raise ValueError('the correction subset names an unknown group: %r'
                             % (group,))
        if not isinstance(rows, list) or not rows:
            raise ValueError('the correction subset group %r is empty' % (group,))
        offered = [G._plain(row) for row in full[group]]
        seen = set()
        for row in rows:
            key = G._plain(row)
            if key not in offered:
                raise ValueError('the correction subset names a question the '
                                 'full population does not: %r' % (row,))
            if key in seen:
                raise ValueError('the correction subset repeats a question')
            seen.add(key)
    return subset


#: the corrected instructions, per kind, from the FROZEN renderer. The writer
#: already knows how to hash whatever mapping it is given; serving it the right
#: one is the whole fix (Codex SEQ 2118 item 1).
CORRECTED_RULES = {'G2': V.meaning_rules, 'G3': V.extras_rules}


@contextmanager
def versioned_candidate(pin, matched_population=None):
    """Serve the EXISTING writer its missing inputs, and restore them all.

    `kind_candidate` reads `R.KIND_RULES[kind]` and hashes the result itself,
    so the corrected mapping goes in there rather than being re-hashed here:
    the candidate's rules pin then names the very instructions its prompt
    bytes carry. Restored on any exit, including a refusal.
    """
    if not isinstance(pin, str) or len(pin) != 64:
        raise ValueError('the input version must be a sha256')
    original, original_rules = R.kind_candidate, R.KIND_RULES

    def versioned(kind, doc, rows, identity):
        built = original(kind, doc, rows, identity)
        built['input_correction_sha256'] = pin
        if matched_population is not None:
            # THE INVENTORY THE G3 COMPARISON RECORDS CAME FROM, carried so the
            # consumer compares it with its OWN required G2 population instead
            # of taking this candidate's word for it.
            built['matched_population'] = matched_population
        return built

    try:
        R.kind_candidate = versioned
        R.KIND_RULES = dict(CORRECTED_RULES)
        yield
    finally:
        R.kind_candidate = original
        R.KIND_RULES = original_rules


def _packet_builder(kind, gold, arms, producer, inputs, matched_pairs):
    """The SAME grouping the runner does, through the FROZEN renderer."""
    def g2(_batch_id, batch):
        return V.batch_packet('G2', [
            V.meaning_packet(key.split('|', 1)[0], key.split('|', 1)[1], [pair],
                             gold[key.split('|', 1)[1]],
                             arms[key.split('|', 1)[0]][
                                 key.split('|', 1)[1]]['facts'],
                             producer, inputs=inputs)
            for key, pair in batch])

    def g3(_batch_id, batch):
        packets = []
        for key, produced_idx in batch:
            leg, sid = key.split('|', 1)
            srcs = [(gi, gold[sid][gi]) for gi in G.accepted_positions(gold[sid])]
            packets.append(V.extras_packet(leg, sid, [produced_idx],
                                           arms[leg][sid]['facts'], srcs,
                                           producer, inputs=inputs,
                                           matched_pairs=matched_pairs))
        return V.batch_packet('G3', packets)

    return g2 if kind == 'G2' else g3


def prepare(out_dir, kind, full_population, subset, gold, arms, producer,
            inputs, g1, identity, matched_pairs=None):
    """-> (path, sha256, doc, pin). A NEW correction candidate whose whole
    population is the approved subset, which names its input version, and -
    for G3 - which names the matched-pair inventory its comparison records
    were drawn from."""
    if kind not in ('G2', 'G3'):
        raise ValueError('a correction candidate is G2 or G3, not %r' % (kind,))
    if kind == 'G3' and not isinstance(matched_pairs, dict):
        raise ValueError('a G3 correction needs the matched-pair inventory')
    approved_subset(full_population, subset)
    # THE EXPLICIT VIEW for rendering, the CANONICAL inventory for binding.
    # The frozen G2 population is sparse by design, so a legitimately
    # unmatched group must be shown as an explicit empty pool rather than
    # refused as an absence (Codex SEQ 2121).
    view = (V.matched_inventory(matched_pairs, full_population)
            if kind == 'G3' else None)
    rows, prompts, _of = R._rows_and_prompts(
        kind, B.pack_batches(subset),
        _packet_builder(kind, gold, arms, producer, inputs, view))
    if not rows:
        raise ValueError('the approved subset fitted no call')
    counts = collections.OrderedDict([
        ('questions', sum(len(v) for v in subset.values())),
        ('batches', len(rows)),
        ('largest_batch', max(r['items'] for r in rows))])
    doc = collections.OrderedDict([
        ('producer_identity', producer),
        ('g1_identity', B.g1_identity(g1)),
        ('g2_pairs', subset if kind == 'G2' else {}),
        ('g3_idxs', subset if kind == 'G3' else {}),
        ('g2', counts if kind == 'G2' else None),
        ('g3', counts if kind == 'G3' else None),
        ('batching', collections.OrderedDict([('rows', rows)]))])
    pin = G._sha_file(V.__file__)
    with versioned_candidate(pin, matched_pairs if kind == 'G3' else None):
        path, sha = R.write_kind(out_dir, kind, doc, prompts, identity)
    return path, sha, doc, pin
