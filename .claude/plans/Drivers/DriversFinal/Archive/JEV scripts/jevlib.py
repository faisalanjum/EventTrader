"""Shared input builder for the Jev fact-type tests (v3b). Reads only; nothing here writes to the repo or Neo4j."""
import re

SENT_END = re.compile(r"(?<=[.!?])[\"”’)]?\s+(?=[A-Z“\"(•\[])")
PARA = re.compile(r"\n\s*\n")
FURNITURE = re.compile(r"##TABLE_START\s*[^|\n#]{0,90}\|[^\n#]{0,90}##TABLE_END\s*")   # page header/footer boxes such as "Company | 2025 Form 10-K"

PARTS = {"mdna": "Management's Discussion and Analysis", "business": "Business section",
         "risk": "Risk Factors section", "RiskFactors": "Risk Factors section", "OtherEvents": "Other Events item",
         "exhibit_99_1": "earnings press release (Exhibit 99.1)",
         "EX-99.1": "earnings press release (Exhibit 99.1)", "EX-99.2": "press release exhibit (Exhibit 99.2)"}
DOCS = {"10k": "an annual report (10-K)", "10q": "a quarterly report (10-Q)", "8k": "a current report (8-K)"}


def where(src_type, part):
    p = PARTS.get(part)
    if p is None and part and str(part).startswith("Management"):
        p = "Management's Discussion and Analysis"
    p = p or str(part)
    if p.endswith(")") and src_type == "8k":            # press-release exhibits already name the document
        return p
    return f"{p} of {DOCS[src_type]}"


def _tidy(t):
    t = FURNITURE.sub("", t)
    t = re.sub(r"(?m)^[^\n|]{0,80}\|\s*(?:Q\d\s+)?20\d\d Form 10-[KQ]\s*$", "", t)     # running page header/footer line
    t = t.replace("##TABLE_START", "[Table]").replace("##TABLE_END", "[End of table]")
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"^(\[End of table\]\s*)+", "", t.strip())      # tail of a page-furniture table cut by the window
    t = re.sub(r"(\s*\[Table\])+\s*$", "", t)                # a table that opens right at the window edge
    return t.strip()


def _is_heading(block):
    b = block.strip()
    return 0 < len(b) < 90 and not re.search(r"[.!?:;]$", b) and "|" not in b


def _bounds(text):
    """Positions just after each sentence end and each paragraph break."""
    pos = {m.end() for m in SENT_END.finditer(text)} | {m.end() for m in PARA.finditer(text)}
    return sorted(pos)


def _left(text, s, want, hard):
    """Start index so that text[i:s] begins cleanly (sentence/paragraph start), preferring the farthest start within `want`
    characters, but never cutting inside the quote's own sentence (up to `hard`)."""
    lo = max(0, s - hard)
    b = _bounds(text[lo:s])
    cands = [lo + p for p in b]
    if lo == 0: cands = [0] + cands
    near = [c for c in cands if s - c <= want]
    if near: return min(near)
    return max(cands) if cands else s


def _right(text, e, want, hard):
    hi = min(len(text), e + hard)
    ends = [e + p for p in _bounds(text[e:hi])]
    if hi == len(text): ends.append(len(text))
    ok = [x for x in ends if x - e <= want]
    if ok: return max(ok)
    return min(ends) if ends else e


def build_state(text, s, e, src_type, part, driver_name, before_want=520, after_want=260):
    # paragraph structure present? (a paragraph around the quote shorter than ~1500 chars means real line breaks exist)
    ps = max(text.rfind("\n\n", 0, s), 0); pe = text.find("\n\n", e); pe = len(text) if pe < 0 else pe
    structured = (pe - ps) < 1500 and text.count("\n") > 20
    b0 = _left(text, s, before_want, 1300)
    a1 = _right(text, e, after_want, 900)
    if structured:
        # keep any heading lines directly above the window start
        blocks_above = text[max(0, b0 - 400):b0]
        hs = []
        for blk in reversed(PARA.split(blocks_above)[:-1] if PARA.search(blocks_above) else []):
            if _is_heading(blk): hs.append(blk.strip())
            else: break
            if len(hs) == 3: break
        head = "\n\n".join(reversed(hs))
        # a quote inside a table: bring in the table start (title and column headers) and end
        ts, te = text.rfind("##TABLE_START", 0, s), text.rfind("##TABLE_END", 0, s)
        if ts > te and s - ts <= 1600: b0 = min(b0, ts); head = ""
        nte = text.find("##TABLE_END", e)
        if ts > te and 0 <= nte - e <= 1200: a1 = max(a1, nte + len("##TABLE_END"))
        before = (head + "\n\n" if head else "") + text[b0:s]
    else:
        before = text[b0:s]
    after = text[e:a1]
    # cut off a table that opens but does not close inside the window
    k = after.rfind("##TABLE_START")
    if k >= 0 and "##TABLE_END" not in after[k:]: after = after[:k]
    # drop trailing heading-only lines (the next section's title) from the text after the quote
    parts = [p for p in PARA.split(after) if p.strip()]
    while parts and _is_heading(parts[-1]): parts.pop()
    after = "\n\n".join(parts).lstrip(" .;,")
    return {"where_it_appears": where(src_type, part),
            "driver_name": driver_name.replace("_", " "),
            "text_before_quote": _tidy(before), "quote": text[s:e].strip(), "text_after_quote": _tidy(after)}


def find_quote(text, quote):
    pat = r"\s+".join(re.escape(w) for w in quote.split())
    m = re.search(pat, text)
    return (m.start(), m.end()) if m else None
