"""Source-formatting step (a declared small route step, like the screen step): the original's own strike-through — <s>, <del>,
<strike> and CSS `text-decoration: line-through`, inherited by descendants — is written onto the route's units and cells as `struck`
phrases, found through their byte anchors. It changes no text and no anchor. Why: the key keeps struck evidence struck (key README,
E10); Docling maps only the three tags and EdgarTools reports no strikes, so redlines marked with CSS became active text."""

from bisect import bisect_left, bisect_right

from driver.prepare.convert import anchor
from driver.prepare.convert.anchor import Visible, norm


def apply(raw, units):
    """Set `struck` on every unit and cell with byte anchors from the source's struck runs; returns how many items carry struck text.
    Only resolved decoration is certified: a struck run is written when no stylesheet rule touches decorations (`struck_certain`); a
    converter's claim is dropped only where nothing is struck and no sheet rule could add a strike (`plain_certain`); anywhere else the
    converter's own claim stands. When neither can be certified nothing is changed and None is returned. Beside the phrases, `struck_at`: the
    exact places of the struck characters in the item's text (`anchor.struck_at`), written only where both readings are certain and the text is the
    source's at its place — a phrase that stands twice in the text is placed by it; a redline printed as one run (`TheExcept`) keeps its two words."""
    return _apply(Visible(raw), units)


def _apply(vis, units):  # `apply` on a reading already made of the same bytes: the source as written, never the browser-qualified one (html_route.prepare)
    if vis.paged: raise ValueError('formatting reads the source as written, not a browser-qualified reading')
    if not vis.struck_certain and not vis.plain_certain: return None
    runs = vis.struck_runs(); n = 0
    for u in units:
        for x in (u.get('cells') or []) if u.get('kind') == 'table' else [u]:
            byte = [a for a in anchor.spans(x.get('anchor')) if 'byte_start' in a]
            if not byte: continue
            phrases = [norm(vis.at(max(s, a['byte_start']), min(e, a['byte_end_exclusive']))) for a in byte for s, e in runs if s < a['byte_end_exclusive'] and a['byte_start'] < e]
            phrases = [p for p in phrases if p and anchor.squash(p) in anchor.squash(x.get('text', ''))]  # only text the item carries: an anchor may span text the tool dropped
            if phrases and vis.struck_certain: x['struck'] = phrases; n += 1  # a struck run the scanner resolved in full
            elif not phrases and vis.plain_certain: x.pop('struck', None)  # nothing struck here and no sheet rule could add one: a tool's own claim is dropped
            # otherwise the converter's own claim stands: the source's decoration here was not resolved
            at = anchor.struck_at(vis, x)
            if at: x['struck_at'] = at
            else: x.pop('struck_at', None)  # nothing struck, or no exact answer: no claim of places
    return n


def rendered(vis, route, runs):
    """The step for a source whose strike-through the scanner cannot certify (not `struck_certain` of the source as written; `plain_certain` may hold), run
    after the screen step on the route's reading `vis` (the visibility authority) from that render's own verdict per source text run (`runs`,
    `screen_grid.decorations`): a struck run is written onto the units and cells whose anchors hold it (`vis.at`, as `apply`); a converter's claim is
    dropped only where every run an item holds is proved unstruck or hidden; an item holding an unresolved run is not qualified whole: it keeps the
    converter's reading as it is, proved runs included, and gets no places. Places (`struck_at`) come from the runs' own bytes, never from a phrase search among repeated words. Returns (items carrying struck text, the
    unresolved runs [[start, end, why]]), or (None, None) with no verdict at all (`runs` None: the render's answer failed): every item then stays as converted."""
    route['route'] = dict(route['route'], settings=dict(route['route'].get('settings') or {}, source_formatting='rendered'))  # the step already named itself; its result now comes from the render
    if runs is None: return None, None
    mask = bytearray(len(vis.flat))
    for s, e, verdict in runs:
        if verdict == 'struck': lo, hi = bisect_left(vis.s, s), bisect_left(vis.s, e); mask[lo:hi] = b'\x01' * (hi - lo)
    mask, firsts, ends, n = bytes(mask), [r[0] for r in runs], [r[1] for r in runs], 0  # runs: in source order, never overlapping
    for u in route['units']:
        for x in (u.get('cells') or []) if u.get('kind') == 'table' else [u]:
            byte = [a for a in anchor.spans(x.get('anchor')) if 'byte_start' in a]
            if not byte: continue
            held = [(a, r) for a in byte for r in runs[bisect_right(ends, a['byte_start']):bisect_left(firsts, a['byte_end_exclusive'])]]
            phrases = [norm(vis.at(max(r[0], a['byte_start']), min(r[1], a['byte_end_exclusive']))) for a, r in held if r[2] == 'struck']
            phrases = [p for p in phrases if p and anchor.squash(p) in anchor.squash(x.get('text', ''))]  # only text the item carries
            whole = bool(held) and not any(r[2].startswith('unresolved') for _, r in held)
            if not whole:  # a run here has no verdict: the item is not qualified whole - the converter's reading stays as it is, and no places are claimed over unknown text
                x.pop('struck_at', None); continue
            if phrases: x['struck'] = phrases; n += 1
            else: x.pop('struck', None)  # every run here proved unstruck (or hidden): a converter's claim is dropped
            at = anchor.struck_at(vis, x, mask)
            if at: x['struck_at'] = at
            else: x.pop('struck_at', None)
    return n, [r for r in runs if r[2].startswith('unresolved')]


def step(raw, route):
    """The step on one document's route (the caller's bytes): the source's struck text written onto its units and cells (`apply`), the route record
    naming the step. Returns `apply`'s count, None where nothing can be certified. Bytes that are not the route's source (its SHA-256) raise ValueError
    before the route is touched."""
    anchor.check_source(raw, route.get('sha256'))
    return _step(Visible(raw), route)


def _step(vis, route):  # `step` on a reading already made of the route's own bytes (html_route.prepare, which checked them)
    n = _apply(vis, route['units']); route['route'] = dict(route['route'], name=route['route']['name'] + '+source-formatting', settings=dict(route['route'].get('settings') or {}, source_formatting=True))
    return n
