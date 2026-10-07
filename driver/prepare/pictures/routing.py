# Selective Sonnet routing, version 5 (Oct 6, owner + Codex r6/r7: the validation candidate): Sonnet for any table in Chandra's reading
# (the second reader makes silent value, unit and heading errors visible: 157 "5.1%" for a printed 5.1x), a cut-off or failed reading, printed
# numbers both free tools see in a chart region, and words both free tools see outside every Chandra block. Word contradictions no longer
# call Sonnet: they stay as free-OCR conflict lines in the packet (070's colour-to-measure links are a known unresolved relationship).
# Version 4 (Oct 6, Codex development review: any word contradiction or missed word counts, not only numbers;
# a missing reading is routed; the length limit comes from the reader's configuration; table confirmation shared with table_choice).
# Version 3 (Oct 6: a table counts as confirmed only when every cell's text was found exactly - tiers 1-2 -
# never by an approximate or bracket-ignoring match; version 2 let 'Net Debt-to-EBITDA' pass for a printed 'EBITDAre'). Version 2 (after the owner's priorities in PrepareTools.md: a table or chart starts the existing
# local checks, not an automatic Sonnet call; no custom layout detector). Version 1 is kept as real336_dev/routing_v1_frozen.py.
# Development, measured on saved readings only. Chandra is the primary
# reading; a picture is sent to the second reader only when evidence available BEFORE Sonnet runs shows a material risk. Inputs:
# Chandra's reading and its run record, and the saved free OCR - never Sonnet's answer, picture-type labels or audit notes.
#   table      - a table in Chandra's reading (any block)
#   cut off    - Chandra stopped at its length limit, or wrote unreadable/uncertain marks ('[?]', data-uncertain)
#   chart text - both free tools read a number inside a region Chandra treats as a picture, chart or diagram
#   missed     - both free tools read any word or number outside every Chandra block
#   no reading - Chandra wrote nothing usable
#   no support - (version 6, Codex r10) a text block none of whose words either free tool reads at its place; no free OCR = no support
# Absence of a trigger is not a certificate: unrouted content is single-reader content.
import collections
from . import packets as p, free_evidence as E

NUM = lambda t: any(ch.isdigit() for ch in t)

def free_outside(words, blocks, w, h):  # one free tool's tokens that belong to no Chandra block (geometry alone)
    if not words: return collections.Counter()
    reach = sorted(max(b['box'][1::2]) - min(b['box'][1::2]) for b in words)[len(words) // 2]
    own = E.owner_of([b['box'] for b in blocks], w, h, reach)
    out = [b for b in words if own(sum(b['box'][0::2]) / len(b['box'][0::2]), sum(b['box'][1::2]) / len(b['box'][1::2])) is None]
    return collections.Counter(p.toks('\n'.join(p.rc.boxes_to_lines(out)), 'text')) if out else collections.Counter()

def route(html, generated_tokens, free, limit=None):  # (send to Sonnet?, the reasons); limit: the reader's configured output limit
    bl, why = p.blocks_of(html or ''), []
    if not any(p.toks(b['html'], 'html') for b in bl if b['label'] not in p.VISUAL) and not any(b['label'] in p.VISUAL for b in bl): return True, ['no reading']
    if any(p.rc.read(b['html'], 'html')[1] for b in bl): why.append('table')
    if (limit and (generated_tokens or 0) >= limit) or '[?]' in html or 'data-uncertain' in html: why.append('cut off')
    ft = [{}, {}]
    if free:
        ft = [E.free_tokens(free[t], bl, free['w'], free['h']) for t in ('pp', 'ox')]
        both = lambda i: collections.Counter(ft[0].get(i, [])) & collections.Counter(ft[1].get(i, []))
        if any(b['label'] in p.VISUAL and any(NUM(t) for t in both(i)) for i, b in enumerate(bl)): why.append('chart text')
        out = free_outside(free['pp'], bl, free['w'], free['h']) & free_outside(free['ox'], bl, free['w'], free['h'])
        if any(any(ch.isalnum() for ch in t) for t in out): why.append('missed')
    if any(b['label'] not in p.VISUAL
           and (words := {t for t in p.toks(b['html'], 'html') if any(c.isalnum() for c in t)})
           and not words.intersection(ft[0].get(i, []) + ft[1].get(i, [])) for i, b in enumerate(bl)):
        why.append('no support')
    return bool(why), why
