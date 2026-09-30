"""SEC heading rule on top of Docling's heading levels: PART = 1, Item = 2, other headings under an Item = 3+
(kept relative to Docling's own level for that Item, clamped to 3..6). Headings before the first PART/Item keep Docling's level."""
import re
from docling_core.types.doc import DocItemLabel
ITEM = re.compile(r'^\s*item\s+(\d{1,2}(?:\.\d{2})?[a-c]?)\b\.?', re.I)
PART = re.compile(r'^\s*part\s+(iv|i{1,3})\b', re.I)
ITEM_ANY = re.compile(r'\bitem\s+(\d{1,2}(?:\.\d{2})?[a-c]?)\b', re.I)
def headers(doc):
    return [it for it, _ in doc.iterate_items() if it.label == DocItemLabel.SECTION_HEADER]
def apply_sec_levels(doc):
    anchor_seen = False; item_lvl = None
    for h in headers(doc):
        t = h.text.strip(); old = h.level
        if PART.match(t) and not ITEM.match(re.sub(PART, '', t).strip() or 'x'):
            h.level = 1; anchor_seen = True; item_lvl = None
        elif PART.match(t):              # "PART II - OTHER INFORMATION Item 1. Legal Proceedings." merged into one header
            h.level = 1; anchor_seen = True; item_lvl = old
        elif ITEM.match(t):
            h.level = 2; anchor_seen = True; item_lvl = old
        elif anchor_seen and item_lvl is not None:
            h.level = min(6, max(3, 2 + (old - item_lvl)))
        elif anchor_seen:
            h.level = min(6, max(2, old))
    return doc
def item_ids(texts):
    out = []
    for t in texts:
        m = ITEM.match(t.strip()) or (PART.match(t.strip()) and ITEM_ANY.search(t))
        if m: out.append(m.group(1).upper())
    return out
if __name__ == '__main__':   # self-check
    class H:                  # minimal stand-in
        def __init__(s, t, l): s.text, s.level, s.label = t, l, DocItemLabel.SECTION_HEADER
    class D:
        def __init__(s, hs): s.hs = hs
        def iterate_items(s): return [(h, 0) for h in s.hs]
    hs = [H('FORM 10-Q', 2), H('PART I - FINANCIAL INFORMATION', 3), H('Item 1. Financial Statements.', 6), H('NOTE 1 - BASIS', 5),
          H('Item 2. MD&A', 6), H('Overview', 6), H('PART II - OTHER INFORMATION Item 1. Legal Proceedings.', 4), H('Item 1A. Risk Factors.', 6)]
    apply_sec_levels(D(hs))
    assert [h.level for h in hs] == [2, 1, 2, 3, 2, 3, 1, 2], [h.level for h in hs]
    assert item_ids(['Item 1A. Risk Factors', 'PART II Item 1. Legal', 'Item 2.02 Results']) == ['1A', '1', '2.02']
    print('sec_headings self-check OK')
