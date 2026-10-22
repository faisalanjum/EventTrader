"""A source document as an observed parent viewer shows it, one state per set of renders: the initial view, or the view after one source control's
native action. Every render of a contextual state is made here (screen_grid._offline_page hands page creation over when the Source carries a Context),
so visibility, geometry, style, generated content and picture preparation read the same qualified native state; with no context nothing changes.
Evidence only: the parent, its resources and the target response are recorded responses (Source.observed shape); the target is served as the
render's own body mapped onto its recorded response with exact inverses (overlay.measurement_body); every other request is answered by the existing
Source (exact recorded URL) or refused there, so refusals reach the existing readers; non-GET is blocked; service workers are blocked; the route is
the browser context's, so new pages are answered by the same rule and counted. The parent selection is OCR's: the parent's own initial selection, a source anchor (acquisition.LOCATE) or a native observed control (acquisition.NODES key).
Proof (Smart's reviewed scripts): native cloneNode lineage, the origin equal to the inert native parse of the source, an ordered one-to-one native
copy, a unique declared target id; then every mutation of the action phase must be that one copy insertion (native MutationObserver, uncapped),
and the bridge removes only our comments from the wholly not-displayed original. Native timers are untouched: an observation is a bounded snapshot
(500 ms with nothing in flight and no new mutation, OCR's rule), not proof that the page never changes again. Gate: every render of a state (the unmarked one included) must
select the same target occurrence and placement, and (OCR's strict rule, every marker kind, initial and activated views) equal the state's unmarked
reference render at measurement start: the whole native serialization without our comments and the received inputs; anything else leaves the
state incomplete with its reasons."""
import hashlib, json, re, time
from playwright.sync_api import Error as PlaywrightError  # the pinned library's public typed error; Request.frame raises it for a navigation request whose frame does not exist yet
from . import anchor, edgartools_html, overlay, screen_grid as sg
from ..get.acquire import StorageError
from ..get import acquisition  # OCR's frozen selection module (one settle rule, one serializer, the native node key)

# Smart's reviewed proof scripts, verbatim (bridge_helper_v3.py sha256 53a685d46bd577cf...; its timer-wrapping INIT and capped EFFECTS are not used)
SNAP = "() => { const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL); window.__pre = new Set(); let n; while ((n = w.nextNode())) window.__pre.add(n); return window.__pre.size; }"
COMMON = """const re = new RegExp('^' + p); const attrs = e => e.nodeType === 1 ? Array.from(e.attributes).map(a => [a.name, a.value]) : null;
  const ordered = (a, b) => { if (a.childNodes.length !== b.childNodes.length) return false; for (let i = 0; i < a.childNodes.length; i++) { if (window.__lineage.origin.get(b.childNodes[i]) !== a.childNodes[i] || !ordered(a.childNodes[i], b.childNodes[i])) return false; } return true; };
  const unmarked = root => { const t = root.cloneNode(true); const x = document.createTreeWalker(t, NodeFilter.SHOW_COMMENT), cs = []; let c; while ((c = x.nextNode())) if (re.test(c.nodeValue)) cs.push(c); cs.forEach(k => k.remove()); t.normalize(); return t; };
  const notDisplayed = e => { for (let x = e; x && x.nodeType === 1; x = x.parentElement) if (getComputedStyle(x).display === 'none') return true; return false; };
  const roots = () => { const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL), out = []; let n; while ((n = w.nextNode())) if (!window.__pre.has(n) && (!n.parentNode || window.__pre.has(n.parentNode)) && n.nodeType === 1) out.push(n); return out; };
  const allMarks = () => { const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT), out = []; let n; while ((n = w.nextNode())) if (re.test(n.nodeValue)) out.push(n.nodeValue); return out; };"""
PROVE = "([p, originalText]) => { " + COMMON + """ const inert = new DOMParser().parseFromString(originalText, 'text/html'); const rs = roots();
  return rs.map(r => { const o = window.__lineage.origin.get(r) || null; const rec = {node: r.tagName.toLowerCase(), shown: r.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}), under: (() => { const c = []; let e = r.parentElement; while (e) { c.push(e.tagName.toLowerCase()); e = e.parentElement; } return c.join('>'); })(), lineage: null};
    if (o === null || o.nodeType !== 1) return rec; const id = o.getAttribute('id'); const hits = id === null ? [] : Array.from(inert.querySelectorAll('[id]')).filter(e => e.getAttribute('id') === id); const inertEl = hits.length === 1 ? hits[0] : null;
    const competing = rs.filter(x => window.__lineage.origin.get(x) === o && x.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})).length;
    rec.lineage = {origin_was_present: window.__pre.has(o), origin_still_connected: o.isConnected, origin_tag: o.tagName.toLowerCase(), origin_id: id, inert_id_hits: hits.length, origin_equals_source_parse: inertEl !== null && unmarked(o).isEqualNode(unmarked(inertEl)),
      origin_not_displayed: notDisplayed(o), origin_check_visibility: o.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}), shown_copies_of_origin: competing, copy_root_mapped: window.__lineage.origin.get(r) === o, copy_children_ordered_identity: ordered(o, r),
      copy_children_equal: o.childNodes.length === r.childNodes.length && Array.from(o.childNodes).every((c, i) => c.isEqualNode(r.childNodes[i])), root_attribute_changes: JSON.stringify(attrs(o)) === JSON.stringify(attrs(r)) ? [] : [{origin: attrs(o), copy: attrs(r)}],
      origin_mark_values: (() => { const w = document.createTreeWalker(o, NodeFilter.SHOW_COMMENT), out = []; let n; while ((n = w.nextNode())) if (re.test(n.nodeValue)) out.push(n.nodeValue); return out; })(), copy_outer_unmarked: unmarked(r).outerHTML};
    return rec; }); }"""
BRIDGE = "([p]) => { " + COMMON + """ const rs = roots(); if (rs.length !== 1) return {performed: false, why: rs.length + ' new element roots'}; const r = rs[0], o = window.__lineage.origin.get(r);
  if (!o) return {performed: false, why: 'no native copy lineage'}; if (!notDisplayed(o)) return {performed: false, why: 'origin is displayed (no computed display:none on it or an ancestor): visible original plus copy'};
  const competing = rs.filter(x => window.__lineage.origin.get(x) === o && x.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})).length; if (competing !== 1) return {performed: false, why: competing + ' shown copies of the origin compete'};
  const before = allMarks(); const w = document.createTreeWalker(o, NodeFilter.SHOW_COMMENT), cs = []; let n; while ((n = w.nextNode())) if (re.test(n.nodeValue)) cs.push(n); const removed = cs.map(c => c.nodeValue); cs.forEach(c => c.remove());
  return {performed: true, operation: 'removed ' + removed.length + ' instrument comments from the hidden origin subtree only', removed_marks: removed, marks_before: before.length}; }"""
AFTER = "([p]) => { " + COMMON + """ const rs = roots(); const r = rs[0], o = window.__lineage.origin.get(r); const all = allMarks(); const dup = all.filter((v, i) => all.indexOf(v) !== i);
  return {copy_still_shown: r.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}), origin_still_connected: o.isConnected, origin_still_not_displayed: notDisplayed(o), copy_children_equal_unmarked_origin: (() => { const u = unmarked(r); return u.childNodes.length === o.childNodes.length && Array.from(o.childNodes).every((c, i) => c.isEqualNode(u.childNodes[i])); })(), root_attribute_changes: JSON.stringify(attrs(o)) === JSON.stringify(attrs(r)) ? [] : [{origin: attrs(o), copy: attrs(r)}], origin_marks_left: (() => { const w = document.createTreeWalker(o, NodeFilter.SHOW_COMMENT); let n, k = 0; while ((n = w.nextNode())) if (re.test(n.nodeValue)) k++; return k; })(), marks_total: all.length, duplicate_mark_keys: dup, origin_html_length: o.outerHTML.length}; }"""


INIT = """(() => { const origin = new WeakMap();
  const pairs = (a, b) => { origin.set(b, a); const ca = a.childNodes, cb = b.childNodes; if (ca.length === cb.length) for (let i = 0; i < ca.length; i++) pairs(ca[i], cb[i]); };
  const cn = Node.prototype.cloneNode; Node.prototype.cloneNode = function (deep) { const c = cn.call(this, deep); pairs(this, c); return c; };
  const im = Document.prototype.importNode; Document.prototype.importNode = function (n, deep) { const c = im.call(this, n, deep); pairs(n, c); return c; };
  let mutations = 0; new MutationObserver(ms => { mutations += ms.length; }).observe(document, {subtree: true, childList: true, characterData: true, attributes: true});
  document.addEventListener('DOMContentLoaded', () => { const s = new Set(), w = document.createTreeWalker(document, NodeFilter.SHOW_ALL); let n; while ((n = w.nextNode())) s.add(n); window.__preSelectAtParse = s; }, {once: true});
  window.__lineage = {origin, mutations: () => mutations}; })();"""  # native cloneNode/importNode results unchanged; timers untouched (not observed)
ATTEMPTS = 3  # Root CONTEXT_CANONICAL_STATE_DECISION_20261021: at most 3 observation attempts per logical reading
OBSERVATION = ('startup', 'selection', 'selection_settle', 'control_located', 'action', 'action_settle', 'effects', 'probe', 'proof', 'origin_in_selected_child', 'target', 'bridge',
               'after_bridge_settle', 'after_bridge', 'observe', 'inner', 'final_controls', 'refused')  # one attempt's own observation fields
FINAL_CONTROLS = '() => (window.__acted || []).map(e => ({label: e.textContent, shown: e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})}))'  # each acted control's own proved node, read once after all actions
class Refused(RuntimeError):
    """An observation refusal: a property of what this attempt observed (kept with the attempt), not a fault."""

PRESEL = "() => { window.__preSelect = new Set(); const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL); let n; while ((n = w.nextNode())) window.__preSelect.add(n); return window.__preSelect.size; }"
SCOPE = "() => { window.__sourceScope = {outside: n => window.__preSelect.has(n) || (!!window.__hiddenOrigin && window.__hiddenOrigin.contains(n))}; return true; }"  # proved parent nodes + the bridged hidden original, nothing else
CTL_FIND = """([p, runKeys, linkIndex, nLinks, hrefs]) => { const re = new RegExp('^' + p + 's:([0-9]+)$'), w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT), found = []; let c;
  while ((c = w.nextNode())) { const m = re.exec(c.data); if (m && runKeys.includes(+m[1])) found.push(c); }
  if (found.length) { const els = new Set(); for (const k of found) { let el = null; for (let n = k.nextSibling; n; n = n.nextSibling) { if (n.nodeType === 3) { el = n.parentElement; break; } if (n.nodeType !== 8) break; } els.add(el && el.closest('a[href]')); }
    if (found.length !== runKeys.length) return {how: 'own run marks', ok: false, why: found.length + ' run marks for ' + runKeys.length + ' control runs'};
    if (els.size !== 1 || els.has(null)) return {how: 'own run marks', ok: false, why: 'run marks resolve to ' + els.size + ' anchors'}; window.__ctl = [...els][0]; return {how: 'own run marks', ok: true}; }
  const anchors = Array.from(document.querySelectorAll('a[href]')).filter(a => !window.__preSelect.has(a));
  if (anchors.length !== nLinks) return {how: 'inserted-child link order', ok: false, why: anchors.length + ' inserted anchors for ' + nLinks + ' source links'};
  for (let i = 0; i < nLinks; i++) if (anchors[i].getAttribute('href') !== hrefs[i]) return {how: 'inserted-child link order', ok: false, why: 'href differs at link ' + i};
  window.__ctl = anchors[linkIndex]; return {how: 'inserted-child link order', ok: true}; }"""
FX_START = """() => { window.__fx = []; window.__fxObs = new MutationObserver(ms => { for (const m of ms) window.__fx.push(m); });
  window.__fxObs.observe(document, {subtree: true, childList: true, characterData: true, attributes: true, characterDataOldValue: true, attributeOldValue: true}); return true; }"""
FX_TAKE = """() => { const ms = window.__fx.concat(window.__fxObs.takeRecords()); window.__fxObs.disconnect();
  const roots = []; const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL); let n; while ((n = w.nextNode())) if (!window.__pre.has(n) && (!n.parentNode || window.__pre.has(n.parentNode))) roots.push(n);
  const copies = roots.filter(r => r.nodeType === 1 && window.__lineage.origin.get(r));
  const path = e => { const c = []; let q = e && e.nodeType === 1 ? e : e && e.parentElement; while (q) { c.push(q.tagName.toLowerCase() + (q.id ? '#' + q.id : '')); q = q.parentElement; } return c.join('<'); };
  const desc = x => x.nodeType === 1 ? x.tagName.toLowerCase() : x.nodeType === 3 ? '#text:' + x.data.slice(0, 60) : '#' + x.nodeName;
  return {roots: roots.length, records: ms.map(m => { const added = Array.from(m.addedNodes), removed = Array.from(m.removedNodes);
    const where = copies.length === 1 && m.type === 'childList' && added.length === 1 && added[0] === copies[0] && removed.length === 0 ? 'copy inserted' : copies.length === 1 && copies[0].contains(m.target) ? 'inside the copy' : 'outside the copy';
    return {where, type: m.type, target: path(m.target), attribute: m.attributeName, old: m.oldValue, now: m.type === 'characterData' ? m.target.data : m.type === 'attributes' ? m.target.getAttribute(m.attributeName) : null,
            added: added.map(desc), removed: removed.map(desc)}; })}; }"""
SET_ORIGIN = "([p]) => { " + COMMON + """ const rs = roots(); window.__hiddenOrigin = rs.length === 1 ? (window.__lineage.origin.get(rs[0]) || null) : null; window.__copy = rs.length === 1 ? rs[0] : null; return !!window.__hiddenOrigin; }"""
IN_COPY_FIND = """([p, runKeys, k, hrefs]) => { const copy = window.__copy; if (!copy) return {ok: false, why: 'no proved copy'}; const re = new RegExp('^' + p + 's:([0-9]+)$');
  const w = document.createTreeWalker(copy, NodeFilter.SHOW_COMMENT), found = []; let c; while ((c = w.nextNode())) { const m = re.exec(c.data); if (m && runKeys.includes(+m[1])) found.push(c); }
  if (found.length) { const els = new Set(); for (const x of found) { let el = null; for (let n = x.nextSibling; n; n = n.nextSibling) { if (n.nodeType === 3) { el = n.parentElement; break; } if (n.nodeType !== 8) break; } els.add(el && el.closest('a[href]')); }
    if (found.length !== runKeys.length || els.size !== 1 || els.has(null) || !copy.contains([...els][0])) return {how: 'own run marks in the copy', ok: false, why: found.length + ' marks resolve to ' + els.size + ' anchors'};
    window.__ctl = [...els][0]; return {how: 'own run marks in the copy', ok: true}; }
  const as = Array.from(copy.querySelectorAll('a[href]')); if (as.length !== hrefs.length || as.some((a, i) => a.getAttribute('href') !== hrefs[i])) return {how: 'copy link order', ok: false, why: as.length + ' copy anchors for ' + hrefs.length + ' target source links'};
  window.__ctl = as[k]; return {how: 'copy link order', ok: true}; }"""
REPLACED = "([p]) => { " + COMMON + """ const rs = roots(); const r = rs.length === 1 ? rs[0] : null;
  return {same_origin: !!r && window.__lineage.origin.get(r) === window.__hiddenOrigin, old_removed: !!window.__copy && !window.__copy.isConnected,
          parent_kept: !!window.__copyParent && window.__copyParent.isConnected, same_parent: !!r && r.parentNode === window.__copyParent}; }"""  # Root CONTEXT_EXACT_STATE_REPLACEMENT_DECISION_20261022
ADOPT = "([p]) => { " + COMMON + """ const rs = roots(); window.__copy = rs[0]; return true; }"""  # the proved new instance is the copy from now on
ORIGIN_SCOPE = "([p]) => { " + COMMON + """ const rs = roots(); if (rs.length !== 1) return null; const o = window.__lineage.origin.get(rs[0]); return o ? !window.__preSelect.has(o) : null; }"""  # the selected child's own node, never a parent one
COPY_SIG = """([p]) => { const re = new RegExp('^' + p), acted = window.__acted || [], c = window.__copy.cloneNode(true);
  const skip = new Set(); const pair = (a, b) => { if (acted.includes(a)) skip.add(b); for (let i = 0; i < a.childNodes.length && i < b.childNodes.length; i++) pair(a.childNodes[i], b.childNodes[i]); }; pair(window.__copy, c);  // paired while the clone is still identical
  const w = document.createTreeWalker(c, NodeFilter.SHOW_COMMENT), cs = []; let n; while ((n = w.nextNode())) if (re.test(n.nodeValue)) cs.push(n); cs.forEach(x => x.remove()); c.normalize();
  const shape = e => Array.from(e.children).map(c => '<' + c.localName + shape(c) + '>').join('');  // an acted control: its own text may change, its elements may not
  const out = []; const walk = e => { for (const x of e.childNodes) { if (skip.has(x)) { out.push('<acted ' + x.localName + shape(x) + '>'); continue; } if (x.nodeType === 1) { out.push('<' + x.localName); walk(x); out.push('>'); } else if (x.nodeType === 3) out.push(x.data); else if (x.nodeType === 8) out.push('!' + x.data); } }; walk(c); return out.join('\u0001'); }"""  # content and order, attributes left out
FX_TAKE_INNER = """() => { const ms = window.__fx.concat(window.__fxObs.takeRecords()); window.__fxObs.disconnect(); const copy = window.__copy;
  const ctl = window.__ctl, inCtl = t => !!ctl && (t === ctl || ctl.contains(t));
  const roots = []; const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL); let n; while ((n = w.nextNode())) if (!window.__pre.has(n) && (!n.parentNode || window.__pre.has(n.parentNode)) && !inCtl(n)) roots.push(n);  // a control's own new label nodes are its observed state
  const path = e => { const c = []; let q = e && e.nodeType === 1 ? e : e && e.parentElement; while (q) { c.push(q.tagName.toLowerCase() + (q.id ? '#' + q.id : '')); q = q.parentElement; } return c.join('<'); };
  return {roots: roots.length, records: ms.map(m => ({where: inCtl(m.target) && m.type !== 'attributes' ? 'control label' : copy && copy.contains(m.target) ? (m.type === 'attributes' ? 'attribute inside the copy' : m.type + ' inside the copy') : 'outside the copy', type: m.type, target: path(m.target), attribute: m.attributeName, old: m.oldValue,
    now: m.type === 'attributes' ? m.target.getAttribute(m.attributeName) : m.type === 'characterData' ? m.target.data : null, added: m.addedNodes.length, removed: m.removedNodes.length}))}; }"""
EQUAL_UNMARKED = "([p]) => { " + COMMON + """ const rs = roots(); const r = rs[0], o = window.__lineage.origin.get(r); const u = unmarked(r), v = unmarked(o);
  return u.childNodes.length === v.childNodes.length && Array.from(v.childNodes).every((c, i) => c.isEqualNode(u.childNodes[i])); }"""  # both sides through Smart's own unmarked(): our comments dropped, text normalized
OBSERVE = """([p]) => { const re = new RegExp('^' + p + 's:([0-9]+)$'), ctl = window.__ctl, runs = [];
  const t = document.createTreeWalker(ctl, NodeFilter.SHOW_COMMENT); let c; while ((c = t.nextNode())) { const m = re.exec(c.nodeValue); if (m) runs.push(+m[1]); }
  const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL), roots = []; let n; while ((n = w.nextNode())) if (!window.__pre.has(n) && (!n.parentNode || window.__pre.has(n.parentNode))) roots.push(n);
  const els = roots.filter(r => r.nodeType === 1); if (els.length !== 1) return {control_runs: runs, copy: null};
  const r = els[0], par = r.parentElement, prev = r.previousElementSibling; let depth = 0, q = ctl; while (q && q !== par) { q = q.parentElement; depth++; }
  return {control_runs: runs, copy: {previous_sibling_is_control: prev === ctl, parent_contains_control: !!(par && par.contains(ctl)), container_depth_above_control: q === par ? depth : null, last_child: r.nextSibling === null}}; }"""


def _settle(page, rec, seconds):  # the one settle rule: OCR's acquisition.quiet_settle (500 ms with nothing in flight and no new mutation, within the budget)
    if acquisition.quiet_settle(page, rec['inflight'], seconds): return {'settled': True, 'kind': 'bounded snapshot (acquisition.quiet_settle): 500 ms quiet; later timers not observed'}
    return {'settled': False, 'inflight': rec['inflight'][0]}


class Context:
    """One state of one document shown by its observed parent: `evidence` = {parent_url, target_url, observed (Source.observed shape: every recorded
    response, the parent and the target included), selection ({source_anchor}: OCR's recorded parent action), proof (overlay proof of the target
    response: {'form', 'inserted'}[, before, after])}; `control` = the source byte start of the activated source link record, None for the initial view."""
    def __init__(self, evidence, control=None, label='initial', settle_s=3.0):  # control: a source link start, or (outer, inner, ...) - an outer reveal then controls inside its proved target
        self.controls = [] if control is None else [control] if isinstance(control, int) else list(control)
        self.evidence, self.control, self.label, self.settle_s, self.records, self.reference, self.captures = evidence, (self.controls or [None])[0], label, settle_s, [], None, {}  # reference: the state's first completed unmarked observation
        self.parent_hrefs = [l['href'] for l in sg.Visible(evidence['observed'][evidence['parent_url']]['body']).links]

    def identity(self):
        o = self.evidence['observed']
        return {'state': self.label, 'parent_url': self.evidence['parent_url'], 'target_url': self.evidence['target_url'], 'selection': self.evidence['selection'],
                'control_source_link_tag_byte_start': self.control, 'controls': list(self.controls), 'responses': {u: {'status': v['status'], 'sha256': v.get('sha256')} for u, v in sorted(o.items())}}

    def page(self, browser, asked=None, document=None, source=None):
        ev, o = self.evidence, self.evidence['observed']; raw = source.members[source.path]; body = document[1] if document else raw; p = sg.marker_prefix(raw)
        rec = {'state': self.label, 'marked': body != raw, 'requests': [], 'errors': [], 'pages': 0, 'inflight': 0, 'phase': 'startup'}; self.records.append(rec)
        t = o[ev['target_url']]; pv = source.observation(ev['parent_url'], 'document')  # parent and target are observed responses (never package members), by the Source's own rule
        tv = source.observation(ev['target_url'], 'context target')  # the target's ORIGINAL published response (a verified 200); the measured body is derived from these checked bytes
        if tv is None or tv[0] != 200: measured, rec['overlay'] = None, {'refused': 'target response refused by the source rule (or not a 200)'}
        else: measured, rec['overlay'] = overlay.measurement_body(tv[2], raw, body, p, ev['proof'], ev.get('before', b''), ev.get('after', b''))
        if measured is not None: rec['target_measured_sha256'] = hashlib.sha256(measured).hexdigest()  # this render's measured body; the original identity stays in the Source record
        page = browser.new_page(viewport={'width': 1400, 'height': 1000}, service_workers='block', offline=True)  # native: an owned context; Page.close closes it
        if measured is not None and 'window' in rec['overlay']:  # an inserted run (SEC's server adds one to some pages): accepted only where it is node-level (OCR's native proof)
            cs = re.search(r'charset=([^;\s]+)', t.get('content_type') or '', re.I); rec['node_level'] = overlay.node_level(page, measured, rec['overlay'], cs.group(1) if cs else 'utf-8')
        page.context.add_init_script(INIT); page.context.add_init_script(acquisition.INIT); rec['inflight'] = acquisition.count_requests(page); served = [False]; got_in, refused_in = set(), set()  # this render's received inputs (OCR facts: delivered identities, refused GETs)
        def answer(route):
            q = route.request; r4 = [rec['phase'], q.method, q.url, q.resource_type]; rec['requests'].append(r4)  # the four raw fields, recorded first and always
            try: r4.append(bool(q.is_navigation_request() and q.frame.parent_frame is None))  # fifth field: a main-frame navigation by the browser's own facts (Request.is_navigation_request, Frame.parent_frame); a child-frame document load is not one
            except PlaywrightError as e: r4.append({'frame': str(e)})  # the getter's own typed error (a new window's first request: its frame does not exist yet): kept raw, never counted as ordinary
            if q.method != 'GET': return route.abort('blockedbyclient')  # recorded, never answered
            if q.url == ev['parent_url'] and q.is_navigation_request() and not served[0]:
                served[0] = True; got_in.add((q.url, pv[0], o[q.url].get('sha256'))); return route.fulfill(status=pv[0], content_type=o[q.url].get('content_type') or 'text/html', body=pv[2])
            if q.url == ev['target_url'] and not q.is_navigation_request():
                if measured is None: source._refuse(q.url, q.url, None, q.resource_type, 'target without a verified measurement body'); refused_in.add((q.url, q.resource_type)); return route.abort('failed')
                got_in.add((q.url, tv[0], t.get('sha256'))); return route.fulfill(status=tv[0], content_type=t.get('content_type') or 'text/html', body=measured)  # received: the original response's identity
            got = source.answer(q.url, q.resource_type, q.is_navigation_request())
            if got: got_in.add((q.url, got[0], source.observed[q.url].get('sha256') if q.url in source.observed else hashlib.sha256(got[2]).hexdigest())); return route.fulfill(status=got[0], content_type=got[1], body=got[2])
            if not q.is_navigation_request(): refused_in.add((q.url, q.resource_type))
            if asked is not None and q.resource_type == 'stylesheet': asked.append(q.url)
            return route.abort('aborted')
        page.context.route('**/*', answer); page.context.on('page', lambda pg: rec.__setitem__('pages', rec['pages'] + 1))  # the context's route: popups and workers answer to the same rule
        page.on('pageerror', lambda e: rec['errors'].append([rec['phase'], str(e)[:200]]))
        goto = page.goto
        def refuse(why): rec['refused'] = why; raise Refused(f'context {self.label}: refused: {why}')
        def snapshot():  # at measurement start (before the step's own scripts): the one shared native-state read (document + native full-page capture) and this attempt's received inputs
            st, png = sg.native_state(page, p); self.captures.setdefault(st['capture']['sha256'], png)  # each distinct capture once; the caller stores it by digest
            return dict(st, received=sorted(map(list, got_in), key=str), refused_get=sorted(map(list, refused_in), key=str))
        def keep(a):  # an unmatched attempt's own observation, kept whole in its attempt record; the next attempt starts clean
            a.update({x: rec.pop(x) for x in OBSERVATION if x in rec}); a['requests'], a['errors'] = rec['requests'], rec['errors']; rec['requests'], rec['errors'] = [], []
        def observe():  # one observation attempt in this Page: the parent loaded, the selection, the source-owned actions
            res = goto(ev['parent_url'], wait_until='load'); rec['startup'] = _settle(page, rec, self.settle_s)
            if not rec['startup']['settled']: refuse('incomplete observation before selection')
            if ev['selection'].get('initial'):  # the target is the parent's own initial selection (OCR's native outcome): no click
                if not any(r[2] == ev['target_url'] and r[1] == 'GET' for r in rec['requests']): refuse('initial selection: the parent did not request the target at startup')
                if not page.evaluate('() => { if (!window.__preSelectAtParse) return false; window.__preSelect = window.__preSelectAtParse; return true; }'): refuse('initial selection: no parse-time snapshot of the parent')
                rec['selection'] = 'initial (no action)'; page.evaluate(SCOPE)
                if self.control is not None: self._activate(page, raw, p, rec, refuse)
                for inner in self.controls[1:]: self._activate_inner(page, raw, p, rec, refuse, inner)
                return res
            page.evaluate(PRESEL); rec['phase'] = 'selection'; sel = ev['selection']
            if 'native_node' in sel: el = self._native_node(page, sel, got_in, refused_in, refuse); rec['selection'] = 'native observed control (OCR NativeSelection key), not a raw-source anchor'
            else:
                el = page.evaluate_handle(acquisition.LOCATE, [self.parent_hrefs, sel['source_anchor']]).as_element()
                if el is None: refuse('parent anchors do not correspond to the parent source anchors (a script-built menu needs the native-node selection)')
            try:  # native wait for the selection's own request of the target, then its response, then a quiet snapshot
                with page.expect_request(lambda q: q.url == ev['target_url'] and q.method == 'GET', timeout=int(self.settle_s * 1000)) as got: el.evaluate('e => e.click()')
                got.value.response()
            except (OSError, StorageError, ImportError, MemoryError): raise  # html_route's policy, inside the boundary too
            except Exception as e:
                if not browser.is_connected(): raise
                refuse('the selection did not request the target (' + type(e).__name__ + ')')
            rec['selection_settle'] = _settle(page, rec, self.settle_s)
            if not rec['selection_settle']['settled']: refuse('incomplete observation after selection')
            page.evaluate(SCOPE)
            if self.control is not None: self._activate(page, raw, p, rec, refuse)
            for inner in self.controls[1:]: self._activate_inner(page, raw, p, rec, refuse, inner)
            return res
        def stated(url, **kw):
            if pv is None: refuse('parent response refused by the source rule')  # source corruption is a failure: never retried
            if measured is None: refuse('target response: ' + str(rec['overlay'].get('refused') or rec['overlay'].get('unresolved')))
            if 'node_level' in rec and not rec['node_level']['node_level']: refuse('target response: the inserted run is not node-level (overlay.node_level)')
            rec['attempts'] = []
            for k in range(1, ATTEMPTS + 1):  # Root's canonical state: the same Page navigated afresh (no Page swapped under the caller); one attempt equal to the state reference is used
                if k > 1: keep(rec['attempts'][-1])
                served[0] = False; got_in.clear(); refused_in.clear(); rec.pop('refused', None); rec['phase'] = 'startup'; a = {'attempt': k}; rec['attempts'].append(a)
                try: res = observe(); n = snapshot(); rec['final_controls'] = page.evaluate(FINAL_CONTROLS)  # the final state's control readings, beside the canonical snapshot
                except Refused: a['outcome'] = 'not used: refused'; continue  # its reason is kept with the attempt
                except sg.CaptureError as e: a['outcome'] = 'failed: ' + str(e); refuse(str(e))  # a failed or incomplete native capture: refused, never retried
                a['native'] = n; ref = self.reference
                if ref is None and rec['marked']: a['outcome'] = 'not used: no state reference (no unmarked observation completed first)'; break  # nothing to match: no retry
                if ref is not None and n != ref: a['outcome'] = 'not used: differs from the state reference (' + ', '.join(x for x in ref if n.get(x) != ref[x]) + ')'; continue
                if ref is None: self.reference = n  # the first completed unmarked observation: fixed for this state, never changed afterwards
                a['outcome'] = 'used' if ref is not None else 'used: the state reference'; rec['native'] = n; rec['phase'] = 'measurement'; return res
            refuse('neutrality: no observation attempt equalled the state reference (' + '; '.join(f"attempt {x['attempt']} {x['outcome']}" + (f": {x['refused']}" if x.get('refused') else '') for x in rec['attempts'][:-1])
                   + ('; ' if len(rec['attempts']) > 1 else '') + f"attempt {a['attempt']} {a['outcome']}" + (f": {rec['refused']}" if rec.get('refused') else '') + '; its observation is this record\'s own)')
        page.goto = stated
        return page

    def _native_node(self, page, sel, got_in, refused_in, refuse):
        """OCR acquisition.NativeSelection's key, proved afresh in this attempt: the inputs received before the action equal the recorded parent state's
        (the parent's own recorded identity included, as there), and exactly one node with the recorded tag chain and outerHTML sha256 stands at the recorded path."""
        k, want = sel['native_node'], sel['state_inputs']
        if ({tuple(x) for x in got_in}, set(refused_in)) != ({tuple(x) for x in want['delivered']}, {tuple(x) for x in want['refused_get']}):  # the parent included on both sides
            refuse('native node: this attempt received different inputs than the recorded parent state')
        hits = [q for q, t, h in page.evaluate(acquisition.NODES) if (t, acquisition.sha(h.encode())) == (k['tags'], k['outer_html_sha256'])]
        if len(hits) != 1: refuse(f'native node key matches {len(hits)} nodes in this attempt' + (' (ambiguous)' if len(hits) > 1 else ''))
        if hits[0] != k['path']: refuse('native node found at another path')
        return page.evaluate_handle(acquisition.RESOLVE, k['path']).as_element()

    def _activate(self, page, raw, p, rec, refuse):
        vis = sg.Visible(raw); runs, _ = sg.symbol_runs(raw, vis)
        src = [l for l in vis.links if l['start'] == self.control]; idx = [i for i, l in enumerate(vis.links) if l['start'] == self.control]
        ctl_runs = [k for k, (_, chars, _, ok) in enumerate(runs) if ok and src and src[0]['tag_end'] <= chars[0][0] and chars[-1][1] <= src[0]['end']]
        if len(src) != 1 or not ctl_runs: refuse('no single source link record with text at the control position')
        rec['phase'] = 'action'; loc = page.evaluate(CTL_FIND, [p, ctl_runs, idx[0], len(vis.links), [l['href'] for l in vis.links]]); rec['control_located'] = loc
        if not loc['ok']: refuse('control identity: ' + loc['why'])
        page.evaluate(SNAP); n0, e0 = len(rec['requests']), len(rec['errors']); page.evaluate(FX_START)
        page.evaluate('() => window.__ctl.click()'); rec['action'] = 'programmatic HTMLElement.click() (untrusted)'; rec['action_settle'] = _settle(page, rec, self.settle_s)
        fx = page.evaluate(FX_TAKE); rec['effects'] = fx; reqs = rec['requests'][n0:]; errs = rec['errors'][e0:]
        rec['probe'] = {'new_roots': fx['roots'], 'mutations': len(fx['records']), 'requests': len(reqs), 'errors': len(errs)}
        proof = page.evaluate(PROVE, [p, raw.decode('utf-8')]); rec['proof'] = proof
        other = [m for m in fx['records'] if not (m['where'] == 'copy inserted' or (m['where'] == 'inside the copy' and m['type'] == 'attributes'))]  # a reveal may set the copy's own properties; any content change or outside effect is held
        why = [w for w, bad in (('incomplete observation after the action', not rec['action_settle']['settled']), ('script error', errs), ('non-GET request', any(r[1] != 'GET' for r in reqs)),
               ('navigation', any(r[3] == 'document' for r in reqs)), ('not exactly one new element root with native copy lineage', len(proof) != 1 or proof[0]['lineage'] is None),
               (f"{len(other)} mutation(s) other than the one copy insertion and attribute changes inside the copy (held)", other)) if bad]
        if len(proof) == 1 and proof[0]['lineage']:
            L = proof[0]['lineage']; ids = vis.ids.get(L['origin_id'], []) if L['origin_id'] is not None else []
            why += [w for w, bad in (('origin not present before the action', not L['origin_was_present']), ('origin moved', not L['origin_still_connected']), ('copy not shown', not proof[0]['shown']),
                    ('origin id not declared exactly once', len(ids) != 1 or ids[0]['end'] is None or L['inert_id_hits'] != 1), ('origin differs from the inert parse of the source', not L['origin_equals_source_parse']),
                    ('copy root not mapped', not L['copy_root_mapped']), ('copy children not an ordered native copy', not L['copy_children_ordered_identity']), ('copy children not node-equal', not L['copy_children_equal'])) if bad]
            rec['origin_in_selected_child'] = page.evaluate(ORIGIN_SCOPE, [p])
            if rec['origin_in_selected_child'] is not True: why.append('the origin is not a node of the selected child (a parent-owned equal target does not qualify)')
            if len(ids) == 1 and ids[0]['end'] is not None: rec['target'] = {'declared_id': L['origin_id'], 'source_extent': {'byte_start': ids[0]['start'], 'byte_end_exclusive': ids[0]['end']}}
        if why: refuse('; '.join(why))
        br = page.evaluate(BRIDGE, [p]); rec['bridge'] = br
        if not br['performed']: refuse('bridge: ' + br['why'])
        page.evaluate(SET_ORIGIN, [p]); rec['after_bridge_settle'] = _settle(page, rec, self.settle_s); after = page.evaluate(AFTER, [p]); rec['after_bridge'] = after
        after['copy_equals_origin_both_unmarked'] = page.evaluate(EQUAL_UNMARKED, [p])  # AFTER's own field compares an unnormalized origin (our removed marks leave its text split)
        bad = [k for k in ('copy_still_shown', 'origin_still_connected', 'origin_still_not_displayed', 'copy_equals_origin_both_unmarked') if after.get(k) is not True]
        if not rec['after_bridge_settle']['settled'] or bad: refuse('after the bridge: ' + ', '.join(bad or ['not settled']))
        rec['observe'] = page.evaluate(OBSERVE, [p]); page.evaluate('() => { window.__outerCtl = window.__ctl; window.__acted = []; }')

    def _activate_inner(self, page, raw, p, rec, refuse, start):
        """A source-owned control inside the proved target, after the outer reveal: accepted only as an in-place change - no new node, every mutation an
        attribute of a node inside the copy, the copy's content and order unchanged (attributes are the observed change, kept raw)."""
        vis = sg.Visible(raw); runs, _ = sg.symbol_runs(raw, vis); ext = (rec.get('target') or {}).get('source_extent')
        if not ext: refuse('inner control without a proved target')
        inner = [l for l in vis.links if ext['byte_start'] <= l['start'] < ext['byte_end_exclusive']]; k = [i for i, l in enumerate(inner) if l['start'] == start]
        one = {'control': start}; rec.setdefault('inner', []).append(one)
        if start == self.control: one['located'] = {'how': 'the outer control element already proved', 'ok': page.evaluate('() => { window.__ctl = window.__outerCtl; return !!window.__ctl; }')}
        elif len(k) != 1: refuse('a later control is neither a source link inside the proved target nor the outer control')
        else:
            l = inner[k[0]]; ctl_runs = [j for j, (_, chars, _, ok) in enumerate(runs) if ok and l['tag_end'] <= chars[0][0] and chars[-1][1] <= l['end']]
            one['located'] = page.evaluate(IN_COPY_FIND, [p, ctl_runs, k[0], [x['href'] for x in inner]])
        loc = one['located']
        if not loc['ok']: refuse('later control identity: ' + str(loc.get('why')))
        page.evaluate('() => { if (!window.__acted.includes(window.__ctl)) window.__acted.push(window.__ctl); }')  # its own label is observed action state, compared apart
        one['label_before'] = page.evaluate('() => window.__ctl.textContent')
        page.evaluate('() => { window.__copyParent = window.__copy ? window.__copy.parentNode : null; }')  # where the proved copy stands before the action
        before = page.evaluate(COPY_SIG, [p]); page.evaluate(SNAP); n0, e0 = len(rec['requests']), len(rec['errors']); page.evaluate(FX_START)
        page.evaluate('() => window.__ctl.click()'); one['settle'] = _settle(page, rec, self.settle_s); fx = page.evaluate(FX_TAKE_INNER); one['effects'] = fx
        reqs, errs = rec['requests'][n0:], rec['errors'][e0:]; rep = None
        if start == self.control and fx['roots'] == 1:  # the outer control again, one new root: a native replacement of the proved copy, every fact required
            proof = page.evaluate(PROVE, [p, raw.decode('utf-8')]); f = page.evaluate(REPLACED, [p]); L = proof[0]['lineage'] if len(proof) == 1 else None; got = {q[2] for q in rec['requests'][:n0]}
            rep = one['replacement'] = {'same_origin': f['same_origin'], 'new_root_in_place': f['same_parent'], 'old_copy_removed_only': f['old_removed'] and f['parent_kept'] and sum(m['removed'] for m in fx['records']) == 1,
                'only_that_change': all(m['type'] == 'childList' for m in fx['records']) and sum(m['added'] for m in fx['records']) == 1, 'origin_equals_source_parse': bool(L and L['origin_equals_source_parse']),
                'children_ordered_identity': bool(L and L['copy_children_ordered_identity']), 'children_equal': bool(L and L['copy_children_equal']), 'inputs_already_received': all(q[1] == 'GET' and q[2] in got for q in reqs)}
        replaced = rep is not None and all(rep.values()) and one['settle']['settled'] and not errs
        if replaced: page.evaluate(ADOPT, [p])
        one['copy_shown_after'] = page.evaluate('() => !!window.__copy && window.__copy.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})'); one['label_after'] = page.evaluate('() => window.__ctl.textContent')
        one['control_shown_after'] = page.evaluate('() => window.__ctl.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})')  # native: the acted control itself is shown
        one['probe'] = {'new_roots': fx['roots'], 'mutations': len(fx['records']), 'requests': len(reqs), 'errors': len(errs)}
        why = [w for w, bad in (('incomplete observation after the inner action', not one['settle']['settled']), ('script error', errs), ('navigation by an ordinary link (no conditional state)', any(r[3] == 'document' for r in reqs)), ('request after the inner action', not replaced and [r for r in reqs if r[3] != 'document']),
               ('new nodes', not replaced and fx['roots']), ('a change other than an attribute inside the copy or the control\'s own label', not replaced and any(m['where'] not in ('attribute inside the copy', 'control label') for m in fx['records'])),
               ("the copy's content or order changed", not replaced and page.evaluate(COPY_SIG, [p]) != before)) if bad]
        if rep is not None and not replaced: why.append('not a qualified replacement: ' + (', '.join(k for k, v in rep.items() if not v) or 'unsettled or script error'))
        if why: refuse('inner action: ' + '; '.join(why))

    def observed_labels(self, raw):
        """The acted controls whose own label an action replaced, as the render now being read observed them (its record): {(tag_end, end): {control,
        before (the first occurrence's: the source label), after and shown (the FINAL state's: its native textContent and checkVisibility read once after all
        actions, `final_controls`; None/False when that reading is missing), action_index (the final label-changing occurrence's exact place in the action
        sequence), occurrences: every label-changing occurrence in action order, its own readings kept as raw history}} by the source link record's own
        extent - never by text."""
        rec = next((r for r in reversed(self.records) if r.get('native')), {}); links = {l['start']: l for l in sg.Visible(raw).links}; out = {}
        acted = list(dict.fromkeys(i['control'] for i in rec.get('inner') or []))  # window.__acted's own order: each control once, at its first action
        fin = rec.get('final_controls'); final = dict(zip(acted, fin)) if isinstance(fin, list) and len(fin) == len(acted) else {}
        for n, i in enumerate(rec.get('inner') or []):  # inner[n] is the action self.controls[n + 1]
            l = links.get(i['control'])
            if l is None or l['end'] is None or not any(m['where'] == 'control label' for m in (i.get('effects') or {}).get('records', [])): continue
            occ = {'action_index': n + 1, 'before': i.get('label_before'), 'after': i.get('label_after'), 'shown': i.get('control_shown_after') is True}
            got = out.setdefault((l['tag_end'], l['end']), {'control': i['control'], 'before': occ['before'], 'occurrences': []}); got['occurrences'].append(occ)
            f = final.get(i['control']) or {}; got.update(after=f.get('label'), shown=f.get('shown') is True, action_index=occ['action_index'])
        return out

    def label_spans(self, raw):
        """Source text spans of later controls whose own label the action replaced (observed action state, kept distinct): their marks are gone by design."""
        starts = {i['control'] for r in self.records for i in r.get('inner') or [] if any(m['where'] == 'control label' for m in (i.get('effects') or {}).get('records', []))}
        return [(l['tag_end'], l['end']) for l in sg.Visible(raw).links if l['start'] in starts and l['end'] is not None]

    def gate(self):
        """Why this state is not complete ([] when every render reached it and all agree on the target occurrence and its placement)."""
        why = [f"render {i} ({'marked' if r.get('marked') else 'unmarked'}): {r['refused']}" for i, r in enumerate(self.records) if r.get('refused')]
        why += [f"render {i} ({'marked' if r.get('marked') else 'unmarked'}): attempted, but no completed native record" for i, r in enumerate(self.records) if not r.get('refused') and not r.get('native')]
        ref = next((r['native'] for r in self.records if not r.get('marked') and r.get('native')), None)  # OCR's strict rule, every attempted render and marker kind
        if ref is None: why.append('neutrality: no unmarked reference render of this state')
        else: why += [f"neutrality: render {i} ({'marked' if r.get('marked') else 'unmarked'}) differs from the unmarked reference ({', '.join(k for k in ref if r['native'].get(k) != ref[k])})"
                      for i, r in enumerate(self.records) if r.get('native') and r['native'] != ref]
        if self.control is not None and not why:
            seen = {json.dumps([r.get('target'), (r.get('observe') or {}).get('copy'), [(i['control'], [(m['target'], m['attribute'], m['now']) for m in i['effects']['records']]) for i in r.get('inner') or []]], sort_keys=True) for r in self.records}
            if len(seen) != 1: why.append(f'neutrality: renders disagree on the target occurrence or its placement ({len(seen)} distinct readings across {len(self.records)} renders)')
        return why


def observed_controls(raw, route, ctx):
    """OBSERVED_CONTROLS_CONTRACT_v2_20261022: one record per acted control whose label an action replaced in this state, by the existing owner text
    slices (screen_grid._owners); bound to its exact final action occurrence (lineage.action_index, lineage.occurrences in action order)."""
    labels = ctx.observed_labels(raw) if ctx.records else {}
    if not labels: return
    pv = route.get('page_visibility'); vis = anchor.Visible(raw, page=pv) if pv else anchor.Visible(raw)
    owned = sg._owners(vis, route['units'], spaced=True); rendered = [k for k, r in enumerate(ctx.records) if r.get('native')]
    for (x0, x1), o in sorted(labels.items()):
        owners, why = owned(x0, x1)  # each owner (unit, or a table cell by its anchor's first byte) with the label's own code-point ranges in its saved text
        reasons = [w for w, bad in (('control not shown in the final state', not o['shown']), ('no final native reading of the control', o['after'] is None), ('the label is not owned whole: ' + str(why), owners is None),
                                    ('state route not OK', route['status'] != 'OK')) if bad]
        ext = {'byte_start': o['control'], 'byte_end_exclusive': x1}  # the link record's own extent (edgartools_html: <a start .. label end); owners over the label text, as there
        lr = next((l for l in route.get('source_links') or [] if l['tag']['byte_start'] == o['control']), None)
        if not reasons and lr is not None and lr.get('extent') is None: lr.update(extent=ext, owners=owners, owners_by='action')  # action evidence; a page-proved record is never overwritten
        route.setdefault('observed_controls', []).append({'control': o['control'], 'extent': ext, 'state': ctx.label,
            'status': 'incomplete' if reasons else 'complete', 'reasons': reasons, 'owners': owners or [], 'owners_by': 'action',
            'original': {'label': o['before']}, 'observed': {'label': o['after'], 'shown': o['shown'], 'by': 'final state: native textContent and checkVisibility of the acted control, read once after all actions'},
            'lineage': {'controls': list(ctx.controls), 'action_index': o['action_index'], 'occurrences': o['occurrences'], 'render': rendered[-1] if rendered else None,
                        'state_capture_sha256': (ctx.reference or {}).get('capture', {}).get('sha256')}})


def state_source(source, evidence, ctx):
    """The caller's Source evidence unchanged (path, members, base, bundle, observations) for one state, the context's recorded responses added; a context
    record that differs from one the source already holds for the same URL is refused, never overwritten."""
    obs = {u: dict(o) for u, o in source.observed.items()}
    for u, o in evidence['observed'].items():
        if u in obs and obs[u] != o: raise ValueError('context evidence differs from the source observation for ' + u)
        obs[u] = o
    return sg.Source(source.path, dict(source.members), base=source.base, observed=obs, bundle=source.bundle, context=ctx)


def contextual_routes(raw, file_id, sha256, browser, source, evidence, parse=None, prepare=None, max_states=32, max_transitions=128):
    """The initial route, then each source-owned action once (finite): a trial render first; only an action that proves a useful state (an outer reveal
    of one proved target, or an in-place change inside it, or the same control reopening it) gets full per-state extraction. Every trial keeps its
    whole native record. Each acting link record of the initial route carries labelled activations: complete or not with reasons, or `refused` (no state
    built) with the trial's reasons; ordinary links keep their href and attempted outcome. Participants and coverage use the one ownership rule
    (`edgartools_html._holders`); `coverage_across_states` counts a target run as shown only where a state route that is OK holds every visible character
    of it and its verdict is neither hidden nor unbound; unknowns stay listed. `prepare(route, source, label)` adds a caller's per-state step;
    `parse(label)` gives the tool call per state."""
    from . import html_route
    vis0 = sg.Visible(raw); runs0, _ = sg.symbol_runs(raw, vis0)
    def one(ctx):
        src = state_source(source, evidence, ctx)
        route, facts = html_route.prepare(raw, file_id, sha256, browser, src, **({} if parse is None else {'parse': parse(ctx.label)})); route['facts'] = facts
        if prepare: prepare(route, src, ctx.label)  # the caller's per-state step; its renders are gated by the same state gate there
        observed_controls(raw, route, ctx)
        return route, src
    def trial(controls, label):  # one unmarked render: the whole native record, or why it was refused
        t = Context(evidence, control=controls, label=label); why = None
        try:
            pg = t.page(browser, None, ('http://trial.invalid/', raw), state_source(source, evidence, t))
            try: pg.goto('trial')
            finally: pg.close()
        except (OSError, StorageError, ImportError, MemoryError): raise  # html_route's policy: storage, dependency and resource faults propagate
        except Exception as e:
            if not browser.is_connected(): raise
            why = repr(e)[:300]
        r = t.records[0] if t.records else {'refused': why}; out['trial_captures'].update(t.captures)
        last = (r.get('inner') or [{}])[-1] if len(t.controls) > 1 else r  # the last action's own record
        probe = last.get('probe') or {}; settled = (last.get('settle' if len(t.controls) > 1 else 'action_settle') or {}).get('settled') is True
        out['trials'].append({'label': label, 'controls': list(t.controls), 'probe': probe, 'refused': r.get('refused') or why, 'record': r})
        known = probe if settled else {}  # an unsettled observation never proves a no-op (its raw probe is kept above)
        noop = bool(known) and not any(known.values())  # located, clicked, settled, nothing happened
        acted = [q for q in r.get('requests') or [] if q[0] == 'action']  # the action phase's own raw requests (each carries the fifth field from the one recording point above) and, below, its own page errors: no probe field, a fulfilled navigation destroys the document before the probe runs
        ordinary = any(q[3] == 'document' for q in acted) and all(q[4] is True for q in acted if q[3] == 'document') and all(q[1] == 'GET' for q in acted) and not [e for e in r.get('errors') or [] if e[0] == 'action']  # a link leaving the page: every document navigation observed is a main-frame one (a child-frame load or a new window whose frame the library could not give, alone or beside it, is not), GETs only, no script error (Root 03:27/03:40)
        if (r.get('refused') or why) and not noop and not ordinary: unknown.append(label)  # neither a no-op nor ordinary navigation: the state is unknown
        return r, known, r.get('refused') or why
    def coverage(route, tgt, skip):
        x0, x1 = tgt['source_extent']['byte_start'], tgt['source_extent']['byte_end_exclusive']; pv = route.get('page_visibility')
        vis = anchor.Visible(raw, page=pv) if pv else anchor.Visible(raw); held, _, _ = edgartools_html._holders(route['units'], vis)
        cuts = sorted(x for a, b in skip for x in (a, b) if x0 <= a and b <= x1); edges = [x0] + cuts + [x1]
        ranges = [(edges[k], edges[k + 1]) for k in range(0, len(edges) - 1, 2)]  # the target minus the acted controls' own labels
        got, n, unheld = {}, 0, 0
        for a, b in ranges:
            g, m, u = held(a, b); n += m; unheld += u
            for k, v in g.items(): got.setdefault(k, v)
        return got, n, unheld, vis, held
    def activation(ctx, route, label, tgt=None, rec=None):
        why = ctx.gate() + ([route.get('error') or 'route not OK'] if route['status'] != 'OK' else [])
        tgt = tgt or next((r['target'] for r in ctx.records if r.get('target')), None); obs = next(((r.get('observe') or {}).get('copy') for r in ctx.records if r.get('observe')), None)
        act = {'state': label, 'status': 'complete', 'reasons': why, 'target': tgt, 'placement': obs, 'action': 'programmatic HTMLElement.click() (untrusted)',
               'observation': 'bounded snapshot per render; native timers untouched (not observed)'}
        if len(ctx.controls) > 1:
            act['after'] = ctx.controls[:-1]; inner = next(((r.get('inner') or [{}])[-1] for r in ctx.records if r.get('inner')), {})
            act['inner_effects'] = [(m['target'], m['attribute'], m['old'], m['now']) for m in (inner.get('effects') or {}).get('records', []) if m['where'] == 'attribute inside the copy']
            act['control_label'] = {'before': inner.get('label_before'), 'after': inner.get('label_after')}; act['copy_shown_after'] = inner.get('copy_shown_after')
        pv = route.get('page_visibility'); skip = ctx.label_spans(raw)
        if tgt:
            x0, x1 = tgt['source_extent']['byte_start'], tgt['source_extent']['byte_end_exclusive']; inside = lambda a, b: x0 <= a and b <= x1
            got, n, unheld, vis, _ = coverage(route, tgt, skip)
            pics = [u for u in route['units'] if u.get('kind') == 'image' and any('byte_start' in a and inside(a['byte_start'], a['byte_end_exclusive']) for a in anchor.spans(u.get('anchor')))]
            act['participants'] = [{'state': label, 'unit': k[0], **({'cell': k[1]} if k[1] is not None else {})} for k in sorted(got, key=lambda k: got[k][0])] + [{'state': label, 'unit': u['id'], 'picture': True} for u in pics]
            outside = lambda s_: inside(*s_) and not any(a <= s_[0] and s_[1] <= b for a, b in skip)
            act['coverage'] = {'visible_characters': n, 'unheld_visible_characters': unheld, 'not_shown_in_state': {k: [s_ for s_ in ((pv or {}).get(k) or []) if outside(s_)] for k in ('hidden', 'unbound')},
                               'page_unproven_runs': (pv or {}).get('unproven', 0), 'observed_control_labels': [list(x) for x in skip]}
            if unheld: act['reasons'] = act['reasons'] + [f'{unheld} visible target character(s) no unit holds']
            if any(act['coverage']['not_shown_in_state'].values()) or act['coverage']['page_unproven_runs']: act['reasons'] = act['reasons'] + ['target descendants not shown or not proven in this state (listed in coverage)']
        if act['reasons'] or not tgt or not act.get('participants'): act['status'] = 'incomplete'
        return act
    def attach(start, act): next(r for r in initial['source_links'] if r['tag']['byte_start'] == start).setdefault('activations', []).append(act)
    def refused(start, label, r, why): attach(start, {'state': None, 'trial': label, 'status': 'refused', 'reasons': [why], 'target': r.get('target'), 'action': 'programmatic HTMLElement.click() (untrusted)'})
    start = Context(evidence); initial, _ = one(start)  # the initial view: its reference is the 'back to the start' identity
    out = {'initial': initial, 'states': [], 'trials': [], 'trial_captures': {}}  # trial captures: the caller keeps them once by digest
    unknown, deficits = [], []  # refused source-owned actions (ordinary navigation excepted); the document's required deficits
    for l in vis0.links:  # every source link record shown in the initial reading, once; one hidden there is reachable only inside a revealed target
        if l['hidden']: out['trials'].append({'label': None, 'controls': [l['start']], 'skipped': 'hidden in the initial reading'}); continue
        r, probe, why = trial(l['start'], f"trial@{l['start']}")
        if probe and not any(probe.values()): continue  # located, clicked, nothing happened: a no-op, no state
        if why: refused(l['start'], f"trial@{l['start']}", r, why); continue  # an attempted action that proved no target state: its record kept, no extraction
        label = f"activated@{l['start']}"; ctx = Context(evidence, control=l['start'], label=label); route, _ = one(ctx)
        act = activation(ctx, route, label); out['states'].append({'label': label, 'control': l['start'], 'route': route, 'records': ctx.records}); attach(l['start'], act)
        if not act['target']: continue
        x0, x1 = act['target']['source_extent']['byte_start'], act['target']['source_extent']['byte_end_exclusive']; family = [(label, route, ctx)]
        # the state loop (Root CONTEXT_RANGE_AND_STATE_IMPLEMENTATION_20261021): breadth first over the proved target's own source controls and the outer
        # control, from every new state; a state is its canonical native fingerprint (the trial's unmarked observation: document, inputs, capture);
        # an equal fingerprint is an edge, never another extracted copy; fixed ceilings, the rest saved as an unexplored frontier (incomplete)
        moves = [x['start'] for x in vis0.links if x0 <= x['start'] < x1] + [l['start']]
        ident = lambda native: json.dumps(native, sort_keys=True) if native else None
        def lineage(rec):  # the trial's actual node lineage: the first action's one observed copy, then each later action's located control and new roots;
            inner = rec.get('inner') or []; copy = (rec.get('observe') or {}).get('copy')  # same instance only by this observation, never by a matching hash
            return {'copy': copy, 'actions': [{'located': i.get('located'), 'new_roots': (i.get('probe') or {}).get('new_roots'), 'copy_shown_after': i.get('copy_shown_after')} for i in inner],
                    'same_instance': copy is not None and all((i.get('probe') or {}).get('new_roots') == 0 for i in inner), 'replacements': [i['replacement'] for i in inner if i.get('replacement')]}
        seen = {k: v for k, v in ((ident(start.reference), 'initial'), (ident(r.get('native')), label)) if k}
        graph = {'states': [label], 'edges': [], 'noops': 0, 'refused': 0, 'transitions': 0, 'frontier': [], 'ceilings': {'states': max_states, 'transitions': max_transitions}}
        queue = [((l['start'],), label)]
        while queue:
            base, at = queue.pop(0)
            for c in moves:
                seq = base + (c,)
                if graph['transitions'] >= max_transitions or len(graph['states']) >= max_states: graph['frontier'].append({'from': at, 'controls': list(seq)}); continue
                graph['transitions'] += 1; tl = 'trial@' + '+'.join(map(str, seq)); r2, probe, why = trial(seq, tl)
                if probe and not any(probe.values()): graph['noops'] += 1; graph['edges'].append({'from': at, 'control': c, 'to': at, 'kind': 'no-op', 'trial': tl}); continue
                if why: graph['refused'] += 1; refused(c, tl, r2, why); graph['edges'].append({'from': at, 'control': c, 'to': None, 'kind': 'refused', 'trial': tl}); continue
                key = ident(r2.get('native'))
                if key in seen: graph['edges'].append({'from': at, 'control': c, 'to': seen[key], 'kind': 'equal state', 'trial': tl, 'lineage': lineage(r2)}); continue
                if ((r2.get('inner') or [{}])[-1]).get('replacement'):  # a qualified replacement only ever reaches an already-qualified exact state; unmatched: unknown, never a new state
                    why = 'a replacement whose native state equals no already-qualified state'; graph['refused'] += 1; unknown.append(tl); refused(c, tl, r2, why)
                    graph['edges'].append({'from': at, 'control': c, 'to': None, 'kind': 'refused', 'trial': tl, 'lineage': lineage(r2)}); continue
                ilabel = 'activated@' + '+'.join(map(str, seq)); ictx = Context(evidence, control=seq, label=ilabel); iroute, _ = one(ictx)
                out['states'].append({'label': ilabel, 'control': list(seq), 'route': iroute, 'records': ictx.records}); attach(c, activation(ictx, iroute, ilabel, act['target'])); family.append((ilabel, iroute, ictx))
                if key: seen[key] = ilabel
                graph['states'].append(ilabel); graph['edges'].append({'from': at, 'control': c, 'to': ilabel, 'kind': 'new state', 'trial': tl, 'lineage': lineage(r2)}); queue.append((seq, ilabel))
        act['state_graph'] = graph
        if graph['frontier']: act['status'] = 'incomplete'; act['reasons'] = act['reasons'] + [f"state graph: {len(graph['frontier'])} transition(s) left unexplored at the ceiling"]
        target_runs = [(chars[0][0], chars[-1][1]) for _, chars, _, ok in runs0 if ok and x0 <= chars[0][0] and chars[-1][1] <= x1 and sg._glyphs(raw, chars)[1]]  # white space only: nothing to show
        def shown(rt, cx, a, b):  # affirmative: an OK state route holds every visible character of the run, and its verdict is neither hidden nor unbound there
            if rt['status'] != 'OK' or (rt.get('page_visibility') or {}).get('unproven'): return False
            pv = rt.get('page_visibility') or {}
            if any(h0 <= a and b <= h1 for k in ('hidden', 'unbound') for h0, h1 in (pv.get(k) or [])): return False
            _, m, u = edgartools_html._holders(rt['units'], anchor.Visible(raw, page=rt.get('page_visibility')) if rt.get('page_visibility') else anchor.Visible(raw))[0](a, b)
            return m > 0 and u == 0
        labels = {s_ for _, _, cx in family for s_ in cx.label_spans(raw)}
        never = [list(rn) for rn in target_runs if not any(a <= rn[0] and rn[1] <= b for a, b in labels) and not any(shown(rt, cx, *rn) for _, rt, cx in family)]
        act['coverage_across_states'] = {'states': [lb for lb, _, _ in family], 'target_runs': len(target_runs), 'never_affirmatively_shown_runs': never, 'observed_control_label_runs': sorted(labels)}
        if never: deficits.append(f"{label}: {len(never)} target run(s) never affirmatively shown in any observed state (coverage_across_states)")
        if graph['frontier']: deficits.append(f"{label}: {len(graph['frontier'])} transition(s) left unexplored at the state ceiling")
    reached = {c for t in out['trials'] for c in t.get('controls', [])[1:]}
    out['unreached_links'] = [l['start'] for l in vis0.links if l['hidden'] and l['start'] not in reached]  # hidden, and inside no proved target: no observed state reaches them
    deficits += [f'{tl}: source-owned action refused, its state unknown (CONTEXT_TRIALS)' for tl in unknown]
    if deficits:  # the existing route-status policy (the caller's render gate uses the same form): automatic output incomplete, reasons listed
        initial['status'] = 'PARTIAL'; initial['error'] = '; '.join(filter(None, [initial.get('error')] + ['context: ' + d for d in deficits]))
    return out
