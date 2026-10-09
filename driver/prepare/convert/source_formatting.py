"""Source-formatting step (a declared small route step, like the screen step): the original's own strike-through — <s>, <del>,
<strike> and CSS `text-decoration: line-through`, inherited by descendants — is written onto the route's units and cells as `struck`
phrases, found through their byte anchors. It changes no text and no anchor. Why: the key keeps struck evidence struck (key README,
E10); Docling maps only the three tags and EdgarTools reports no strikes, so redlines marked with CSS became active text."""

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


def step(raw, route):
    """The step on one document's route (the caller's bytes): the source's struck text written onto its units and cells (`apply`), the route record
    naming the step. Returns `apply`'s count, None where nothing can be certified. Bytes that are not the route's source (its SHA-256) raise ValueError
    before the route is touched."""
    anchor.check_source(raw, route.get('sha256'))
    return _step(Visible(raw), route)


def _step(vis, route):  # `step` on a reading already made of the route's own bytes (html_route.prepare, which checked them)
    n = _apply(vis, route['units']); route['route'] = dict(route['route'], name=route['route']['name'] + '+source-formatting', settings=dict(route['route'].get('settings') or {}, source_formatting=True))
    return n
