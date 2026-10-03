"""Heading pre-step (PrepareStep.md P7, an allowed small adapter): before an HTML tool runs, wrap the lines that the
labellers' guide calls headings — a short line standing alone, not a sentence, styled apart (bold, underline, capitals)
— in <h2> tags, so the tool's own outline works. Visible characters are never changed; the linker anchors the tool's
output to the ORIGINAL bytes, never to this copy. Rules are the guide's, with no words or names of any filing."""
from html.parser import HTMLParser
import re

from benchmarks.prepare.grader.anchor import Visible, norm

BLOCK = {'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th', 'span', 'font', 'b', 'strong', 'u', 'i', 'em', 'a', 'sup', 'sub', 'br', 'table', 'tr'}
WRAP = ('p', 'div')  # block lines a heading can be; table cells are left to the table rules
MAX_CHARS = 120      # a heading is a short line (guide 2.1); the key's longest heading is well under this
_BOLD = re.compile(r'font-weight\s*:\s*(bold|[6-9]00)', re.I)
_UNDER = re.compile(r'text-decoration\s*:[^;"\']*underline', re.I)


class _Blocks(HTMLParser):
    """Byte spans of <p>/<div> elements that contain no other block element (leaf lines) and their style clues."""

    def __init__(self, text):
        super().__init__(convert_charrefs=False); self.text = text; self.stack = []; self.leaves = []
        self.line_starts = [0]
        for i, ch in enumerate(text):
            if ch == '\n': self.line_starts.append(i + 1)

    def _pos(self):  # HTMLParser already owns an attribute named offset
        line, col = self.getpos(); return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs); style = a.get('style') or ''
        clue = tag in ('b', 'strong') or bool(_BOLD.search(style)) or tag == 'u' or bool(_UNDER.search(style))
        for frame in self.stack: frame['clue'] |= clue and tag not in ('p', 'div')  # styling inside the line counts for the line
        if tag in ('p', 'div') or tag in ('table', 'li', 'tr', 'td', 'th') or tag.startswith('h'):
            for frame in self.stack: frame['leaf'] = False  # a block inside: the outer one is not a line
        in_table = any(f['tag'] in ('table', 'td', 'th') for f in self.stack)  # table cells keep their own rules: never wrapped
        self.stack.append({'tag': tag, 'start': self._pos(), 'clue': clue, 'leaf': not in_table})

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                frame = self.stack.pop(i); end = self._pos()
                if tag in WRAP and frame['leaf']:
                    open_end = self.text.index('>', frame['start']) + 1
                    self.leaves.append((open_end, end, frame['clue']))
                del self.stack[i:]
                break


def mark_headings(raw):
    """Return a copy of the HTML with guide-style heading lines wrapped in <h2>…</h2>; bytes of visible text unchanged."""
    try: text = raw.decode('utf-8'); enc = 'utf-8'
    except UnicodeDecodeError: text = raw.decode('cp1252', 'replace'); enc = 'cp1252'
    p = _Blocks(text); p.feed(text)
    edits = []
    for open_end, end, clue in p.leaves:
        inner = text[open_end:end]; shown = norm(Visible(inner.encode(enc, 'replace')).text)
        if not shown or len(shown) > MAX_CHARS: continue
        letters = [c for c in shown if c.isalpha()]
        caps = len(letters) >= 2 and all(c.isupper() for c in letters)
        sentence = shown.endswith(('.', ';', ',')) and not re.fullmatch(r'(part|item)\b.*', shown, re.I)
        if (clue or caps) and not sentence and not shown.endswith(':') or (caps and shown.endswith(':') and len(shown) < 40):
            edits.append((open_end, end))
    out, pos = [], 0
    for a, b in edits:
        out.append(text[pos:a]); out.append('<h2>' + text[a:b] + '</h2>'); pos = b
    out.append(text[pos:])
    return ''.join(out).encode(enc, 'replace')
