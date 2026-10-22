"""Shared source fixtures and calls; all addresses/selectors below are test data."""
import hashlib
from pathlib import Path
from driver.prepare.convert import context, screen_grid as sg
T = Path(__file__).with_name('fixtures'); V1, V2 = T / 'public_parent_reference_controls_v1', T / 'public_parent_reference_controls_v2'
ROOT = 'https://museum.invalid'; PARENT, TARGET = ROOT + '/portal/select.html', ROOT + '/bundle/item.html'
CHILD0, PANELS, CSS, PARENT_UI, JQ = ((V1 / 'child.html').read_bytes(), (V1 / 'panels.js').read_bytes(), (V1 / 'frame.css').read_bytes(), (V2 / 'parent_ui.html').read_bytes(), (V2 / 'jquery.min.js').read_bytes())
WELCOME = b'<section id="welcome-panel"><p>Welcome panel of the portal.</p></section>'
AMBER = b'<aside class="museum-note" id="note-amber"><p>Use the east stair.</p></aside>'; INDIGO = b'<aside class="museum-note" id="note-indigo"><p>Keep paper dry.</p></aside>'
RICH = (b'<aside class="museum-note" id="note-amber"><!-- authored note --><p>Use the <b>east</b> stair.</p>\n<p>Lifts are closed on Mondays; <a href="#native-note">see access</a>.</p>\n'
        b'<ul><li>Level 1: maps</li><li>Level 2: prints</li></ul>\n<table><tr><th>Day</th><th>Hours</th></tr><tr><td>Sat</td><td>9-5</td></tr></table>\n<img src="plan.png" alt="floor plan"></aside>')
PNG = (T / 'plan.png').read_bytes()
CLONE = b'const copy = target.cloneNode(true);'
def rep(b, old, new): assert b.count(old) == 1, old; return b.replace(old, new)
CHILD = rep(CHILD0, AMBER, RICH)
ANON = rep(rep(CHILD, b'<a id="map-link" ', b'<a '), b'<a id="label-link" ', b'<a ')
BUTTON = 'context: 1 declared event handler(s) outside the supported link path (not activated)'
def obs(body, ctype, status=200): return {'status': status, 'content_type': ctype, 'observed_at': 'invented test evidence', 'sha256': hashlib.sha256(body).hexdigest(), 'body': body}
def evidence(child=CHILD, panels=PANELS, css=CSS, parent=PARENT_UI, drop=()):
    o = {PARENT: obs(parent, 'text/html'), ROOT + '/shared/frame.css': obs(css, 'text/css'), ROOT + '/vendor/jquery.min.js': obs(JQ, 'application/javascript'),
         ROOT + '/shared/panels.js': obs(panels, 'application/javascript'), ROOT + '/bundle/welcome.html': obs(WELCOME, 'text/html'), TARGET: obs(child, 'text/html'),
         ROOT + '/portal/theme/leaf.css': obs(b'invented fixture: absent', 'text/plain', 404), ROOT + '/portal/actions.js': obs(b'invented fixture: absent', 'text/plain', 404),
         ROOT + '/portal/plan.png': obs(PNG, 'image/png')}
    for u in drop: o.pop(u)
    return {'parent_url': PARENT, 'target_url': TARGET, 'observed': o, 'selection': {'source_anchor': 1}, 'proof': {'form': 'equal', 'inserted': []}}  # selection: test setup (the caller takes it from OCR's automatic Selection)

def run(browser, child=CHILD, **kw):
    sha = hashlib.sha256(child).hexdigest(); members = {'child.html': child, 'plan.png': PNG}
    return context.contextual_routes(child, 'invented/child.html', sha, browser, sg.Source('child.html', members), evidence(child=child, **kw))  # the caller's own Source (review item 2)
def link_at(route, start): return next(l for l in route['source_links'] if l['tag']['byte_start'] == start)
def controls(child): return [l['start'] for l in sg.Visible(child).links if l['href'].startswith('javascript:')]
def activations(res, start): return link_at(res['initial'], start).get('activations') or []
def state(res, label): return next(s for s in res['states'] if s['label'] == label)
def units_in(route, ext): return [u for u in route['units'] if u.get('anchor') and ext['byte_start'] <= u['anchor']['byte_start'] < ext['byte_end_exclusive']]
