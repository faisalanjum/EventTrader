"""Route adapter: edgartools `parse_html` -> the common route format, anchored by the shared linker.
edgartools keeps no source positions, so the linker places every block. Under its own environment the adapter first
dumps the parsed node tree to plain JSON (kept as the raw output); `to_units` works on that dump, so it is testable
without the package. Shape rules only, no document-specific logic.

    <edgartools python> -m benchmarks.prepare.grader.adapters.edgartools_html --key <key package> --split development --out <run dir> [--catalog CSV]"""
import argparse
import json
import re
from dataclasses import asdict
import time
from pathlib import Path

from benchmarks.prepare.grader import anchor, grade
from benchmarks.prepare.grader.adapters import cache

NAME = 'edgartools-html'  # the tool's heading nodes nested inside paragraphs are kept as headings
KIND = {'HeadingNode': 'heading', 'ParagraphNode': 'text', 'TextNode': 'text', 'ListItemNode': 'list_item', 'ImageNode': 'image'}
BRANCH = ('DocumentNode', 'ContainerNode', 'SectionNode', 'ListNode')
BLOCKY = ('HeadingNode', 'ParagraphNode', 'ContainerNode', 'SectionNode', 'ListNode', 'TableNode', 'ListItemNode', 'ImageNode')  # children that make their parent a branch; a picture has no text to merge into a run: flattened with its paragraph it was lost (Codex's worktree)


def dump(node):
    """Plain-dict copy of an edgartools node tree (run under the edgartools environment)."""
    kind = type(node).__name__
    d = {'type': kind}
    if kind == 'HeadingNode':  # the tool's own evidence for its heading claim, kept as a claim: a style or a confidence certifies no heading (Codex's worktree)
        native = {'metadata': dict(getattr(node, 'metadata', None) or {})}
        if getattr(node, 'style', None) is not None: native['style'] = asdict(node.style)
        for key in ('semantic_type', 'semantic_role'):
            value = getattr(node, key, None)
            if value is not None: native[key] = getattr(value, 'value', value)
        d['native'] = native
    if kind == 'TableNode':
        rows = list(node.headers or []) + [getattr(r, 'cells', r) for r in node.rows or []]
        d['caption'] = node.caption
        d['rows'] = [[{'text': (c.text() if callable(c.text) else c.text) or '', 'colspan': c.colspan or 1, 'rowspan': c.rowspan or 1, 'is_header': bool(c.is_header)} for c in row] for row in rows]
        return d
    kids = list(getattr(node, 'children', None) or [])
    if kind in BRANCH or any(type(k).__name__ in BLOCKY and type(k).__name__ != 'HeadingNode' for k in kids):  # a paragraph that holds blocks (a heading child alone keeps the run-in handling below) (a note emitted as one 60,000-character node) is a branch: its own inline runs become units, its blocks are walked
        children, run = [], []
        def flush():
            if run: children.append({'type': 'TextNode', 'text': ''.join(t + (' ' if (getattr(k, 'metadata', None) or {}).get('has_tail_whitespace') else '') for k, t in run).strip(), 'links': [{'text': (l.text() if callable(l.text) else l.text) or '', 'href': l.href} for k, _ in run for l in ([k] if type(k).__name__ == 'LinkNode' else (k.walk() if hasattr(k, 'walk') else [])) if type(l).__name__ == 'LinkNode']}); run.clear()
        for k in kids:
            if type(k).__name__ in BLOCKY: flush(); children.append(dump(k))
            else: run.append((k, (k.text() if callable(getattr(k, 'text', None)) else getattr(k, 'text', '')) or ''))
        flush(); d['children'] = [c for c in children if c.get('type') != 'TextNode' or c.get('text')]; d['type'] = kind if kind in BRANCH else 'ContainerNode'; return d
    text = node.text() if callable(getattr(node, 'text', None)) else getattr(node, 'text', '')
    heads = [k for k in kids if type(k).__name__ == 'HeadingNode']
    if heads:  # the tool's heading claim inside a paragraph: kept when its text is the paragraph's start or end (the parser's own text, no new joins)
        ht = (heads[0].text() or '').strip(); pt = (text or '').strip()
        if ht and pt.startswith(ht): d['heading'] = dict(dump(heads[0]), text=ht); d['rest'] = pt[len(ht):].strip(); d['order'] = 'head_first'
        elif ht and pt.endswith(ht): d['heading'] = dict(dump(heads[0]), text=ht); d['rest'] = pt[:-len(ht)].strip(); d['order'] = 'head_last'
    d['text'] = text or ''
    for k in ('level', 'src', 'href'):
        if getattr(node, k, None) is not None: d[k] = getattr(node, k)
    links = [{'text': (l.text() if callable(l.text) else l.text) or '', 'href': l.href} for l in node.walk() if type(l).__name__ == 'LinkNode'] if hasattr(node, 'walk') else []
    if links: d['links'] = links
    return d


def codes(raw, vis):
    """One code for every picture tag that writes a `src`, shown or hidden: the source's own SHA-256 (its first 16 hex digits) and the tag's first byte — letters
    and digits the tool's cleaning cannot touch, and nothing a name written in any source can impersonate — with what it stands for: {code: (tag start, the name
    as the parser reads it)}. EdgarTools rewrites the file's text before it parses it (runs of spaces, a space after a point before a capital, `&amp;amp;`,
    zero-width characters), and a name that reached the linker changed stood at another picture's tag; two tags that name one resource, one of them hidden,
    stood for each other (Codex G3-C2)."""
    sha = grade.sha256(raw)[:16]
    return {sha + str(start): (start, name) for start, (_, name) in vis.picture_names.items()}


_A_OPEN, _A_CLOSE = re.compile(r'<a(?=[\s/>])', re.I), re.compile(r'</a\s*>', re.I)
_IX = re.compile(r'</?ix:', re.I)


def without_empty_anchors(text):
    """The text without its anchors that hold nothing — an <a> start tag, comments only, then </a> — by the scanner's own tokens (anchor._TOKEN): a tag is a tag
    only where the tokenizer makes one (not inside a script, a title or a quoted attribute), and a comment ends at its own `-->`, so no text between two
    comments can be taken for emptiness (Codex C1). White space inside is content and stays; so does every other anchor."""
    toks = [m.group() for m in anchor._TOKEN.finditer(text)]; out, i = [], 0
    while i < len(toks):
        if _A_OPEN.match(toks[i]) and anchor._TAG.fullmatch(toks[i]):
            j = i + 1
            while j < len(toks) and toks[j].startswith('<!--'): j += 1
            if j < len(toks) and _A_CLOSE.fullmatch(toks[j]): i = j + 1; continue
        if _IX.match(toks[i]): i += 1; continue  # an inline-XBRL wrapper, opening or closing, however written: it presents nothing, and it is the inline element that cuts a heading-like <div> short
        out.append(toks[i]); i += 1
    return ''.join(out)


def named(raw, vis, codes):
    """The source as the tool gets it, decoded: each picture's name replaced by its code, the text the page hides left out (where the scanner's reading is
    certain), and the anchors that hold nothing removed — the tool reads a <div> it takes for a heading only up to its first inline element, so `Item 1A.
    <a name="x"></a>Risk Factors` came back as `Item 1A.` and `For the quarterly period ended <ix:nonNumeric …>December 28, 2024</ix:nonNumeric>` lost its
    date (run 36's coverage check: one title and two cover facts lost in 60 files; the class reproduced on named anchors, empty links, with and without a
    comment inside, and on the iXBRL wrappers) — and the inline-XBRL wrappers themselves, which present nothing (`without_empty_anchors`). Nothing else changes."""
    edits = [(vis.picture_names[start][0], code.encode()) for code, (start, _) in codes.items()]
    if vis.certain: edits += [(span, b'') for span in vis.hidden]  # text the page hides (display:none, visibility:hidden, …): the tool read it as text — a hidden "%" put beside "8.2" for alignment became "8.2 %" and its visible "%" cell a copy, and a whole table's cells were placed out of order (Codex C4); the scanner's reading of what hides must be certain
    out, at = [], 0
    for (a, b), piece in sorted(edits):
        out += [raw[at:a], piece]; at = b
    given = b''.join(out) + raw[at:]
    try: text = given.decode('utf-8')
    except UnicodeDecodeError: text = given.decode('cp1252', 'replace')
    return without_empty_anchors(text)


def to_units(tree, codes=None):
    """The units of the tool's tree. With `codes` (this source's, from `codes`), every picture names the tag it came from (`tag`, for the linker: a `src` that is no
    code of this source — the tool's own, from a tag the scanner does not list — names no tag) and keeps its code as `src` until `route_for` gives the name back."""
    units = []

    def table_unit(t):
        cells, until = [], {}  # until[column] = the first row at which that column is free again: a rowspan expires by row, whatever later rows hold
        for r, row in enumerate(t.get('rows') or []):
            c = 0
            for cell in row:
                while until.get(c, 0) > r: c += 1
                cs, rs = cell.get('colspan') or 1, cell.get('rowspan') or 1
                if (cell.get('text') or '').strip():
                    cells.append({'r': r, 'c': c, 'rs': rs, 'cs': cs, 'text': cell['text'], 'header': bool(cell.get('is_header'))})
                for k in range(c, c + cs): until[k] = r + rs
                c += cs
        units.append({'id': f't{len(units)}', 'kind': 'table', 'cells': cells, 'caption': [t['caption']] if t.get('caption') else []})

    def walk(n):
        kind = n['type']
        if kind == 'TableNode': table_unit(n)
        elif kind in BRANCH:
            for k in n.get('children') or []: walk(k)
        elif n.get('heading'):  # a paragraph the tool marks as (or starting/ending with) a heading
            parts = [('heading', n['heading']['text'], n['heading'].get('level')), ('text', n.get('rest') or '', None)]
            if n.get('order') == 'head_last': parts.reverse()
            for kind2, text2, level in parts:
                if not anchor.squash(text2): continue
                u = {'id': f'u{len(units)}', 'kind': kind2, 'text': text2}
                if level is not None: u['level'] = level
                if kind2 == 'heading' and n['heading'].get('native') is not None: u['native_heading'] = n['heading']['native']
                units.append(u)
        elif kind == 'ImageNode': units.append({'id': f'u{len(units)}', 'kind': 'image', 'text': '', 'src': n.get('src'), **({'tag': codes.get(n.get('src'), (None,))[0]} if codes is not None else {})})
        else:
            if not anchor.squash(n.get('text') or ''): return  # whitespace or control characters only: not a block
            u = {'id': f'u{len(units)}', 'kind': KIND.get(kind, 'other'), 'text': n.get('text') or ''}
            if n.get('level') is not None: u['level'] = n['level']
            if n.get('native') is not None: u['native_heading'] = n['native']  # (only a heading's dump carries it)
            if n.get('links'): u['links'] = [{'text': l['text'], 'href': l['href'], 'to': None} for l in n['links']]
            units.append(u)
    walk(tree)
    return units


def route_for(tree, raw, file_id, sha256, seconds, version, settings=None, vis=None):
    vis = anchor.Visible(raw) if vis is None else vis; known = codes(raw, vis); linked = anchor.link(raw, to_units(tree, known), vis=vis)
    for u in linked['units']:
        if u.get('src') in known: u['src'] = known[u['src']][1]  # the name back, now that the tag has decided the place; a src that is no code stays the tool's own
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'seconds': seconds,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': settings or {'parse_html': 'defaults'}, 'adapter': 'benchmarks/prepare/grader/adapters/edgartools_html.py',
                      'linker': 'benchmarks/prepare/grader/anchor.py'}, 'units': linked['units'], 'uncovered': linked['uncovered']}


def unsupported(file_id, sha256, version, status='UNSUPPORTED', error='not an HTML file'):
    return {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': status, 'error': error, 'seconds': 0,
            'route': {'name': NAME, 'tool': 'edgartools', 'version': version, 'settings': {}, 'adapter': 'benchmarks/prepare/grader/adapters/edgartools_html.py', 'linker': None}, 'units': []}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt the saved node dump again instead of parsing')
    a = ap.parse_args(argv)
    from edgar.documents import parse_html  # only here: the grader package stays standard-library
    import importlib.metadata as md
    version = f"edgartools {md.version('edgartools')}"
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files = {}
    for src in grade.load_sources(a.key, a.catalog):  # sources only: converters never read answers
        if src['split'] == a.split: files.setdefault(src['file_id'], (src['path'], src['sha256']))
    facts, settings = {}, {'parse_html': 'defaults', 'retain_pictures': True, 'retain_native_heading_evidence': True, 'picture_names': 'codes', 'empty_anchors': 'removed', 'hidden_text': 'left out', 'inline_xbrl_tags': 'left out'}  # what the saved parse keeps: one saved before pictures were kept answers to other settings and is not reused
    for fid, (path, sha) in sorted(files.items()):
        (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() not in ('.htm', '.html'):
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
        raw = path.read_bytes(); t0 = time.time(); vis = anchor.Visible(raw); scanned = time.time() - t0; t0 = time.time(); rawjson = out / 'raw' / (fid + '.edgartools.json'); metajson = out / 'raw' / (fid + '.meta.json'); ver = version
        try:
            if a.reuse_raw and rawjson.exists():  # a saved parse is reused only whole: its record names the source bytes, settings, producing version and output (adapters/cache.py; Codex R13 C1, R15-5)
                meta = cache.reuse(metajson, sha, settings)
                if meta.get('status') != 'OK': raise RuntimeError('cache refused: the cached run did not succeed')
                tree, dt, ver = json.loads(rawjson.read_text()), meta.get('tool_seconds', 0), meta['version']
            else:
                cache.begin(metajson)  # from here the old record vouches for nothing: a crash below leaves no record
                tree = dump(parse_html(named(raw, vis, codes(raw, vis))).root); dt = time.time() - t0  # the tool reads the source with the pictures' names as codes and no empty anchor
                rawjson.write_text(json.dumps(tree, ensure_ascii=False)); cache.save(metajson, [rawjson], sha256=sha, version=version, settings=settings, status='OK', tool_seconds=round(dt, 2))
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 2)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version, 'FAILED', repr(e)[:300]))); continue
        t1 = time.time(); route = route_for(tree, raw, fid, sha, round(dt, 2), ver, settings, vis)
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': 'OK', 'version': ver, 'tool_seconds': round(dt, 2), 'adapter_seconds': round(time.time() - t1 + scanned, 2), 'items': len(flat),
                      'unanchored': sum(1 for x in flat if not x.get('anchor')), 'uncovered_spans': len(route['uncovered']),
                      'uncovered_chars': sum(len(anchor.squash(s['text'])) for s in route['uncovered'])}
        (out / 'route' / (fid + '.json')).write_text(json.dumps(route, ensure_ascii=False))
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': NAME, 'version': version, 'split': a.split, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
