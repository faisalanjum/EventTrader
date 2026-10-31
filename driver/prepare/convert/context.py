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
import hashlib, json, os, posixpath, re, time, urllib.parse
from pathlib import Path
from playwright.sync_api import Error as PlaywrightError  # the pinned library's public typed error; Request.frame raises it for a navigation request whose frame does not exist yet
from . import anchor, edgartools_html, overlay, screen_grid as sg
from ..get.acquire import StorageError
from ..get import acquisition  # OCR's frozen selection module (one settle rule, one serializer, the native node key)
from .. import compare  # the shared comparison form (compare._WS), the scanner's own search form

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
OBSERVATION = ('startup', 'parse_order', 'scope', 'pre_selection_nodes', 'scope_activated', 'scope_origin', 'selection', 'selection_settle', 'control_located', 'action', 'action_settle', 'effects', 'probe', 'proof', 'origin_in_selected_child', 'target', 'bridge',
               'after_bridge_settle', 'after_bridge', 'observe', 'inner', 'final_controls', 'refused', 'selection_inputs', 'viewer_before', 'viewer_actions', 'viewer_unsupported', 'viewer_start_sha256')  # one attempt's own observation fields
FINAL_CONTROL = 'function () { return {label: this.textContent, shown: this.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})}; }'  # each acted control's own retained node, read once after all actions
class Refused(RuntimeError):
    """An observation refusal: a property of what this attempt observed (kept with the attempt), not a fault."""

CTL_FIND = """([p, runKeys, linkIndex, nLinks, hrefs]) => { const re = new RegExp('^' + p + 's:([0-9]+)$'), w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT), found = []; let c;
  while ((c = w.nextNode())) { const m = re.exec(c.data); if (m && runKeys.includes(+m[1])) found.push(c); }
  if (found.length) { const els = new Set(); for (const k of found) { let el = null; for (let n = k.nextSibling; n; n = n.nextSibling) { if (n.nodeType === 3) { el = n.parentElement; break; } if (n.nodeType !== 8) break; } els.add(el && el.closest('a[href]')); }
    if (found.length !== runKeys.length) return {how: 'own run marks', ok: false, why: found.length + ' run marks for ' + runKeys.length + ' control runs'};
    if (els.size !== 1 || els.has(null)) return {how: 'own run marks', ok: false, why: 'run marks resolve to ' + els.size + ' anchors'}; return [{how: 'own run marks', ok: true}, [...els][0]]; }
  return {how: 'inserted-child link order', fallback: true}; }"""  # no own run mark: decided in the isolated world (Scope.pick), the node carried by native identity
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
    return [{how: 'own run marks in the copy', ok: true}, [...els][0]]; }
  const as = Array.from(copy.querySelectorAll('a[href]')); if (as.length !== hrefs.length || as.some((a, i) => a.getAttribute('href') !== hrefs[i])) return {how: 'copy link order', ok: false, why: as.length + ' copy anchors for ' + hrefs.length + ' target source links'};
  return [{how: 'copy link order', ok: true}, as[k]]; }"""  # [reading, the node itself]: the caller retains the node (Scope.locate)
REPLACED = "([p]) => { " + COMMON + """ const rs = roots(); const r = rs.length === 1 ? rs[0] : null;
  return {same_origin: !!r && window.__lineage.origin.get(r) === window.__hiddenOrigin, old_removed: !!window.__copy && !window.__copy.isConnected,
          parent_kept: !!window.__copyParent && window.__copyParent.isConnected, same_parent: !!r && r.parentNode === window.__copyParent}; }"""  # Root CONTEXT_EXACT_STATE_REPLACEMENT_DECISION_20261022
ADOPT = "([p]) => { " + COMMON + """ const rs = roots(); window.__copy = rs[0]; return true; }"""  # the proved new instance is the copy from now on
ISO_WORLD = 'context_source_scope'  # the isolated world's name (CDP worldName); page scripts cannot reach its realm
ISO_INIT = """(() => { const has = Set.prototype.has, add = Set.prototype.add; let parse = null, snap = null, pre = null, origin = null;
  const all = () => { const s = new Set(), w = document.createTreeWalker(document, NodeFilter.SHOW_ALL); let n; while ((n = w.nextNode())) add.call(s, n); return s; };
  document.addEventListener('DOMContentLoaded', () => { parse = all(); }, {once: true});
  const outside = n => pre === null ? null : (has.call(pre, n) || (!!origin && origin.contains(n)));
  window.__sourceScope = {outside, useParse: () => { pre = parse; return parse !== null; }, takeNow: () => { snap = all(); return snap.size; }, useNow: () => { pre = snap; return snap !== null; },
    setOrigin: n => { origin = n || null; return !!origin; }, isOrigin: n => !!origin && n === origin, notPre: n => pre === null ? null : !has.call(pre, n),
    pick: (nLinks, hrefs, k) => { if (pre === null) return 'source scope unknown'; const anchors = Array.from(document.querySelectorAll('a[href]')).filter(a => !has.call(pre, a));
      if (anchors.length !== nLinks) return anchors.length + ' inserted anchors for ' + nLinks + ' source links';
      for (let i = 0; i < nLinks; i++) if (anchors[i].getAttribute('href') !== hrefs[i]) return 'href differs at link ' + i;
      return anchors[k]; }}; })();"""  # pick: the inserted-child link order rule, whole, in this realm; returns the node itself  # parse/pre/origin: this realm only
ORIGIN_NODE = "([p]) => { " + COMMON + """ const rs = roots(); return rs.length === 1 ? (window.__lineage.origin.get(rs[0]) || null) : null; }"""  # the one new root's native copy origin (main-world clone instrumentation, as PROVE reads it)
# Optional report controls of an initial-only view (Root order root-fable-p5-native-control-20261028T005238Z). Their "not attempted" deficit becomes a
# warning only where the page's executable code is completely known and each control can only reveal content the attempt's own typed source reading
# holds: every main-world script the browser parsed is exact reviewed bytes, the viewer template with only its three data slots, a control's own
# declared attribute or the viewer menu's; no other listener sits on a source node, a control or any ancestor (owner policy: the exact identified
# sec.gov-injected bot-detection artifacts are website infrastructure); each Show.showAR resolves, in the DOM, to one source-scope id (a following
# TABLE branch is unsupported); each Show.toggleNext that changes anything (its own DOM walk) has its control and DIV inside a DOM-unique source element the reading
# holds whole (Show.hideAR only hides Show.LastAR, which only Show.showAR sets).
# Anything else keeps the deficit. Reviewed public bytes: P/FABLE_P5_REPORT_CONTROL_EVIDENCE_20261028T002140Z.
KNOWN_CODE = {'2e4e3855abccb781a7086a1720be0114500d5e252ab21bf2094ea557b6d94901': 'renderer Show.js',
              '55e5cd7e99fb2aecfd86f64e3daf9c88c4878111d6a79dbeb2eaba58a34aafa8': 'renderer report helper (toggleNextSibling definition)',
              'fc9a93dd241f6b045cbff0481cf4e1901becd0e12fb45166a8f17f95823f0b1a': 'viewer jQuery v3.7.1',
              '2fb11b7660e3be6710a60743c252c4bde9286c70064d8e032c0a20927ea378e9': 'viewer accordionMenu.js'}
INFRASTRUCTURE = {'0f23ad013f05888115512f5dc6493ac6d6af23358424253090bf565fe81a36ee': 'sec.gov-injected bot detection (AMG campaign, initiator-identified 10-22)',
                  '39f3dc5b34f614a78075f1824407dc3de33cffcb5e5e3c5fd59a1356d3385d97': 'sec.gov-injected bot detection (CCL campaign, initiator-identified 10-22)'}


def qualified_version(evidence, h, url=None):
    """Owner single-version policy: exact inserted-script bytes count as website infrastructure (reviewed versions included, no grandfathering) only
    when (1) THIS file's own acquisition proved them its one server-inserted script (evidence['inserted_script']: bound address and recorded response
    sha256; the address too where the script has one) and (2) the producer's record for those bytes (qualify_version) passed, was made by this runtime
    (manifest pin) and still holds its chain: the producer's schema and fields, every named evidence file re-hashing to its pin, every required role
    present, the WITHOUT result holding exactly one verified row for the qualifying file. A record or flag alone never admits. -> (True, None) or (False, why)"""
    ins, q = evidence.get('inserted_script') or {}, evidence.get('qualifications') or {}
    if not ins.get('href') or ins.get('response_sha256') != h or (url and url != ins['href']): return False, "not this file's proved inserted script"
    if not q.get('folder') or not q.get('runtime_manifest_sha256'): return False, 'no qualification store'
    try: rec = json.loads((Path(q['folder']) / (h + '.json')).read_bytes())
    except (OSError, ValueError): return False, 'no qualification record'
    if rec.get('schema') != QUALIFY_SCHEMA or rec.get('script_sha256') != h or rec.get('outcome') != 'passed' or rec.get('reasons') != [] or (rec.get('comparison') or {}).get('all_equal') is not True or not rec.get('file_id') or not rec.get('states'):
        return False, 'record not passed for these bytes'
    if rec.get('runtime_manifest_sha256') != q['runtime_manifest_sha256']: return False, 'record made by another runtime'
    roles = {}
    for e in rec.get('evidence') or []:
        try: b = Path(e['path']).read_bytes()
        except (OSError, KeyError, TypeError): return False, 'record evidence missing'
        if hashlib.sha256(b).hexdigest() != e.get('sha256'): return False, 'record evidence changed after recording'
        roles[e.get('role')] = b
    if not QUALIFY_ROLES <= set(roles): return False, 'record lacks the producer evidence chain'
    try: rows = [r for r in json.loads(roles['without_result'])['rows'] if r.get('file_id') == rec['file_id']]
    except (ValueError, TypeError, AttributeError, KeyError): rows = []
    return (True, None) if len(rows) == 1 and rows[0].get('outcome') == 'verified_saved_output' else (False, 'record evidence has no verified WITHOUT row for its file')

from ..job import QUALIFY_ROUTE, QUALIFY_SCHEMA, QUALIFY_ROLES, QUALIFY_PLAN_KEYS, compare_views, claim_version, qualify_version  # noqa: E402,F401 the producer lives with
# the batch owner (job.py runs -I -S, without Playwright); qualified_version below is its consumer


TOOLING = {'764405f9d392d5881909d5d98e159ed8c1fc1a8320a3fc47736a6688e0fcf767': 'pinned Playwright 1.59.0 injected script',  # the run's own instrumentation, exact
           '6853be72f0e1a5eb5512aebe8549f7efd3342fb57e51395edf5140f427241065': 'pinned Playwright 1.59.0 handle preview',
           '9e22374178d30310bf36b9ad25aeb7e094195c70fae675a5d8e48cad46b77308': 'pinned Playwright 1.59.0 service-worker block (init script)',
           '12e3bee590e0ccbe3a221b7a19dc098cbe5e66ce06cbe24ecff98e76eef4b4fc': 'pinned Playwright 1.59.0 main-world utility script (server/javascript.js utilityScript(), not under test)',
           'a3c74b2aecbdd0b615e6a2eed4788a374366e25d5fdcd45dca45d55fbb119046': 'pinned Playwright 1.59.0 evaluate wrapper (server/javascript.js evaluateExpression, as Runtime.callFunctionOn compiles it)'}
UTILITY_WORLD = '__playwright_utility_world_'  # pinned Playwright 1.59.0: its own isolated world in this page's main frame (name + page guid)
INIT_WRAP = ('(() => {\n      ', '\n    })();')  # pinned Playwright 1.59.0: how add_init_script wraps this runtime's own init scripts (exact)
OWN_SNIPPETS = ('() => window.__m', 'e => e.click()', 'e => e.checkVisibility()')  # inline evaluations of acquisition.py (l.50/130/132/194) and context.py (Context.page selection click)
VIEWER_TEMPLATE = '0f8f0dc5ee025f233eec8c14df146e5e4333bc1f0c6fed39c3781a0412780a9f'  # the viewer's inline script, its data slots blanked, byte-exact elsewhere
VIEWER_SLOTS = ((re.compile(r'^[ \t]*reports\[\d+\] = ("[^"\n]*"|\'[^\'\n]*\');\r?\n', re.M), ''), (re.compile(r'var reports = new Array\(\d+\);'), 'var reports = new Array(<N>);'),
                (re.compile(r'var url_path = "/Archives/edgar/data/\d+/\d+/";'), 'var url_path = "<FOLDER>";'))
VIEWER_ATTRIBUTES = frozenset(('javascript:highlight(this);',))  # the viewer menu's own handler
VIEWER_NAVIGATION = re.compile(r'loadReport\(\d+\);')  # the only viewer menu javascript: code admitted: the pinned template's own loadReport(n) (the selection's click)
ACTION = re.compile(r"(?:top\.)?Show\.(?:showAR\( this, '(?P<id>[^'\\\r\n  ]+)', window \);|hideAR\(\);|toggleNext\( this \);)")  # the renderer's three control forms, exact; the id literal has no escape or line terminator, so it IS the runtime argument
LIFECYCLE = frozenset(('load', 'DOMContentLoaded'))  # fire once at load, already past at the initial state
CODE_NODE = """function () { const s = window.__sourceScope; if (!s) return null; const src = Array.from(document.querySelectorAll('a[href]')).filter(a => s.outside(a) === false);
  return {outside: s.outside(this), ancestor: src.some(a => a !== this && this.contains(a)), attributes: this.getAttributeNames ? this.getAttributeNames().filter(n => n.toLowerCase().startsWith('on')).map(n => this.getAttribute(n)) : []}; }"""
CODE_ACTIONS = """(() => { const s = window.__sourceScope; if (!s) return null; const actions = [], ids = {}, texts = {}, TOGGLE = /^(?:top\\.)?Show\\.toggleNext\\( this \\);$/;
  for (const a of document.querySelectorAll('[onclick]')) { if (s.outside(a) !== false) continue; let e = a; while (e && e.nodeName !== 'TABLE') e = e.nextSibling; const v = a.getAttribute('onclick');
    let d = a; while (d && d.nodeName !== 'DIV') d = d.nextSibling; const t = TOGGLE.test(v || ''), shown = t && d && d.style.display, h = [];
    for (let p = a.parentElement; p; p = p.parentElement) if (p.hasAttribute('id') && (!d || p.contains(d))) { const k = p.getAttribute('id'); h.push(k); if (shown) texts[k] = p.textContent; }
    actions.push([v, !!e, t ? {div: !!d, display: d ? d.style.display : null, holders: h} : null]); }
  for (const n of document.querySelectorAll('[id]')) { const k = n.getAttribute('id'), v = ids[k] || (ids[k] = [0, 0]); v[0]++; if (s.outside(n) === false) v[1]++; }
  const prof = el => { const tg = new Set(), dc = []; for (const e of [el, ...el.querySelectorAll('*')]) { tg.add(e.localName); const st = e.style;  // SHARED GUARD: what a reveal would show - its elements, and each declaration as the browser's own CSSStyleDeclaration lists it (name, value, priority)
      if (st) for (let i = 0; i < st.length; i++) { const n = st.item(i); dc.push([n, st.getPropertyValue(n), st.getPropertyPriority(n)]); } } return {tags: Array.from(tg).sort(), decls: dc}; };
  const reveal = {targets: {}, toggles: [], source_styles: Array.from(document.querySelectorAll('style')).filter(e => s.outside(e) === false).length}, AR = /^(?:top\\.)?Show\\.showAR\\( this, '([^']+)', window \\);$/;  // source <style>: it can style what a reveal shows (Codex T2)
  for (const a of document.querySelectorAll('[onclick]')) { if (s.outside(a) !== false) continue; const v = a.getAttribute('onclick') || '', m = AR.exec(v);
    if (m && !reveal.targets[m[1]]) { const tt = document.getElementById(m[1]); if (tt) reveal.targets[m[1]] = prof(tt); }
    if (TOGGLE.test(v)) { let d = a; while (d && d.nodeName !== 'DIV') d = d.nextSibling; if (d) reveal.toggles.push(prof(d)); } }  // toggleNext's own DIV, wherever it is
  const cls = new Set(), all = new Map(), ctx = new Set(); for (const e of document.querySelectorAll('*')) { if (s.outside(e) !== false) continue; for (const c of e.classList) cls.add(c); }  // SOURCE-WIDE: every source class (a sheet may style any of them)
  const up = e => { for (let p = e; p; p = p.parentElement) ctx.add(p); };  // REVEAL CONTEXT: what a reveal can inherit - the ancestors (inclusive) of every source-scope control (showAR's clone goes there), showAR target and toggleNext DIV
  for (const a of document.querySelectorAll('[onclick]')) { if (s.outside(a) !== false) continue; const v = a.getAttribute('onclick') || '', m = AR.exec(v), tt = m && document.getElementById(m[1]); up(a); if (tt) up(tt);
    if (TOGGLE.test(v)) { let d = a; while (d && d.nodeName !== 'DIV') d = d.nextSibling; if (d) up(d); } }  // visible content elsewhere (e.g. an XBRL text block's own formatting) is read by the ordinary carriers, as on any HTML page
  for (const e of ctx) { if (s.outside(e) !== false) continue; const st = e.style;  // each reveal-context inline declaration, as the browser's own CSSStyleDeclaration lists it
    if (st) for (let i = 0; i < st.length; i++) { const n = st.item(i), v = st.getPropertyValue(n), q = st.getPropertyPriority(n); all.set(n + '|' + v + '|' + q, [n, v, q]); } }
  reveal.classes = Array.from(cls).sort(); reveal.decls = Array.from(all.values());
  reveal.sheets = Array.from(document.styleSheets).map(x => { let rules = null, imports = 0; try { imports = Array.from(x.cssRules).filter(r => r.type === 3).length; rules = Array.from(x.cssRules).map(r => r.cssText).join('\\n'); } catch (e) {}  // EFFECTIVE STYLES: every sheet as the page applies it NOW: the browser's own cssText, no normalization
    return [x.href, x.disabled, x.media.mediaText, x.ownerNode ? x.ownerNode.localName : null, x.href ? null : (x.ownerNode ? x.ownerNode.textContent : null), rules, imports]; });  // [href, disabled, media, owner, inline text, the browser's own serialization of its current rules (after any script insertRule/deleteRule), @import count]
  reveal.adopted = (document.adoptedStyleSheets || []).length;  // constructed sheets a script adopted: never reviewed
  return {actions, ids, texts, reveal}; })()"""  # Show.showAR's own walk: a following sibling TABLE is shown instead of the named target


def viewer_template(text):
    for rx, to in VIEWER_SLOTS: text = rx.sub(to, text)
    return hashlib.sha256(text.encode()).hexdigest()


class Scope:
    """The Context-owned source scope of one owned Page: ONE CDP session, the isolated world named ISO_WORLD registered for every new document of the
    page (so each navigation/attempt rebuilds it), that world's context id tracked from the session's own Runtime events. Every ownership question
    is answered in that world: (value, None) or (None, why); no context, a destroyed one or a failed resolution is unknown (None), never outside."""
    def __init__(self, page, lifetime=False):  # lifetime: record every script the page parses from before its first navigation (Scope.code)
        self.cdp = page.context.new_cdp_session(page); self.ids = {}; self.seen = []; self.attached = {}; self.frame = self.cdp.send('Page.getFrameTree')['frameTree']['frame']['id']
        def made(e):
            c = e['context']; aux = c.get('auxData') or {}
            self.seen.append({'own_frame': aux.get('frameId') == self.frame, 'frame': aux.get('frameId'), 'default': aux.get('isDefault') is True, 'name': c.get('name') or '', 'type': aux.get('type')})  # every context this page ever ran (Scope.code)
            if aux.get('frameId') != self.frame: return
            if c.get('name') == ISO_WORLD: self.ids['iso'] = c['id']
            elif aux.get('isDefault'): self.ids['main'] = c['id']
        self.cdp.on('Runtime.executionContextCreated', made)
        self.cdp.on('Page.frameAttached', lambda e: self.attached.setdefault(e['frameId'], [f.get('url') or '' for f in ((e.get('stack') or {}).get('callFrames') or [])]))  # the script stack that attached a frame (none: not script-initiated)
        self.cdp.on('Runtime.executionContextDestroyed', lambda e: [self.ids.pop(k) for k, v in list(self.ids.items()) if v == e['executionContextId']])
        self.cdp.on('Runtime.executionContextsCleared', lambda e: self.ids.clear())
        self.cdp.send('Page.enable'); self.cdp.send('Page.addScriptToEvaluateOnNewDocument', {'source': ISO_INIT, 'worldName': ISO_WORLD}); self.cdp.send('Runtime.enable')
        self.parsed = None
        if lifetime:  # a late Debugger.enable reports only "known and uncollected" scripts (pinned protocol): enable before any page script runs, keep every one
            self.parsed = {}; self.cdp.on('Debugger.scriptParsed', lambda e: self.parsed.setdefault(e['scriptId'], e))
            self.cdp.send('Debugger.enable'); self.cdp.send('Debugger.setSkipAllPauses', {'skip': True})  # never pause the page (a page `debugger;` statement)
    def _result(self, r):
        if r.get('exceptionDetails'): return None, repr((r['exceptionDetails'].get('exception') or {}).get('description') or r['exceptionDetails'].get('text'))[:200]
        return r['result'].get('value'), None
    def function_sources(self, expression):
        """The browser's actual script sources for retained functions, not a page's toString claim. Uses the same native source API as code()."""
        obj, why = self.obj(expression)
        if why: return None
        self.cdp.send('Debugger.enable'); self.cdp.send('Debugger.setSkipAllPauses', {'skip': True})
        functions = [p.get('value') or {} for p in self.cdp.send('Runtime.getProperties', {'objectId': obj, 'ownProperties': True})['result'] if p['name'].isdigit()]
        sources, out = {}, []
        for f in functions:
            if f.get('type') != 'function': return None
            props = self.cdp.send('Runtime.getProperties', {'objectId': f['objectId'], 'ownProperties': True})
            location = next((p['value'].get('value') for p in props.get('internalProperties') or [] if p['name'] == '[[FunctionLocation]]'), None)
            if not location: return None
            sid = location['scriptId']
            if sid not in sources: sources[sid] = hashlib.sha256(self.cdp.send('Debugger.getScriptSource', {'scriptId': sid})['scriptSource'].encode()).hexdigest()
            out.append(sources[sid])
        return out
    def call(self, expr):  # an expression in the isolated world, by value
        if 'iso' not in self.ids: return None, 'no isolated scope context'
        try: return self._result(self.cdp.send('Runtime.evaluate', {'expression': expr, 'contextId': self.ids['iso'], 'returnByValue': True}))
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: return None, repr(e)[:200]
    def node(self, backend, fn):  # fn called on that node as the isolated world resolves it (DOM.resolveNode by backendNodeId)
        if 'iso' not in self.ids: return None, 'no isolated scope context'
        try:
            obj = self.cdp.send('DOM.resolveNode', {'backendNodeId': backend, 'executionContextId': self.ids['iso']})['object']['objectId']
            return self._result(self.cdp.send('Runtime.callFunctionOn', {'objectId': obj, 'returnByValue': True, 'functionDeclaration': fn}))
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: return None, repr(e)[:200]
    def code(self):
        """This state's executable code and listeners exactly as the pinned browser reports them (no click, no page function called): every main-world
        script it had parsed (Debugger.scriptParsed on enable; the exact source's sha256), every listener of the document subtree and the window
        (DOMDebugger.getEventListeners) with its script and its node's source-scope relation, and each source onclick's Show.showAR facts. A failure
        is recorded, never a guess (the decision fails closed)."""
        if 'main' not in self.ids or 'iso' not in self.ids: return {'unknown': 'no scope context'}
        if self.parsed is None: return {'unknown': 'no lifetime script record (the debugger was not enabled before page execution)'}
        t0, cdp, parsed = time.monotonic(), self.cdp, self.parsed
        try:
            root = cdp.send('DOM.getDocument', {'depth': 0})['root']  # a round trip on this session first: every scriptParsed sent before it is delivered
            existing = set(parsed)  # every script this page parsed in its lifetime so far, collected or not
            doc = cdp.send('DOM.resolveNode', {'backendNodeId': root['backendNodeId'], 'executionContextId': self.ids['main']})['object']['objectId']
            win = cdp.send('Runtime.evaluate', {'expression': 'window', 'contextId': self.ids['main']})['result']['objectId']  # our own: parsed after `existing`
            listeners = []
            for obj in (doc, win):
                for l in cdp.send('DOMDebugger.getEventListeners', {'objectId': obj, 'depth': -1, 'pierce': True})['listeners']:
                    node = l.get('backendNodeId'); rel, why = ({'outside': True, 'ancestor': True, 'attributes': []}, None) if node is None else self.node(node, CODE_NODE)
                    listeners.append({'type': l['type'], 'script_id': l.get('scriptId'), 'window': node is None, 'relation': rel, **({'why': why} if why else {})})
            actions, why_a = self.call(CODE_ACTIONS)
            def nested(t): return sum(1 + nested(c) for c in t.get('childFrames') or [])
            frames = nested(cdp.send('Page.getFrameTree')['frameTree'])  # child frames run code this inventory does not read: the decision fails closed on any
            me = cdp.send('Target.getTargetInfo')['targetInfo']  # other active contexts of this page (workers, out-of-process frames, opened windows)
            contexts = sorted(t['type'] for t in cdp.send('Target.getTargets')['targetInfos'] if t.get('browserContextId') == me.get('browserContextId')
                              and t['targetId'] != me['targetId'] and (t['type'] != 'page' or t.get('openerId') == me['targetId']))
            wanted = existing | {l['script_id'] for l in listeners}  # attribute handlers are compiled on demand: their scripts are the listeners' own
            scripts = {}
            for sid in sorted(wanted, key=str):
                e = parsed.get(sid)
                if e is None or e.get('executionContextId') != self.ids['main']: continue
                text = cdp.send('Debugger.getScriptSource', {'scriptId': sid})['scriptSource']
                scripts[sid] = {'url': e.get('url') or '', 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'bytes': len(text.encode()),
                                **({'text': text} if len(text) <= 300 else {}), **({'template': viewer_template(text)} if e.get('url') else {})}
            for l in listeners: l['script'] = scripts.get(l.pop('script_id'))
            return {'scripts': sorted(scripts.values(), key=lambda s: (s['url'], s['sha256'])), 'listeners': listeners,
                    'actions': actions if why_a is None else {'unknown': why_a}, 'frames': frames, 'contexts': contexts,
                    'executed_contexts': [dict(x, creator=self.attached.get(x['frame'])) for x in self.seen if not (x['own_frame'] and (x['default'] or x['name'] == ISO_WORLD or x['name'].startswith(UTILITY_WORLD)))],
                    'seconds': round(time.monotonic() - t0, 3)}
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: return {'unknown': repr(e)[:200]}
    def to_main(self, expr, fn):  # a node the isolated world's own query returns (or its reason, a string), carried into the main world by native identity
        if 'iso' not in self.ids or 'main' not in self.ids: return None, 'no scope context'
        try:
            r = self.cdp.send('Runtime.evaluate', {'expression': expr, 'contextId': self.ids['iso'], 'returnByValue': False})
            if r.get('exceptionDetails'): return self._result(r)
            got = r['result']
            if got.get('type') == 'string': return None, got.get('value')
            if got.get('subtype') != 'node' or not got.get('objectId'): return None, 'no node'
            backend = self.cdp.send('DOM.describeNode', {'objectId': got['objectId']})['node']['backendNodeId']
            obj = self.cdp.send('DOM.resolveNode', {'backendNodeId': backend, 'executionContextId': self.ids['main']})['object']['objectId']
            if fn is None: return obj, None  # the node itself, retained (its main-world remote object)
            return self._result(self.cdp.send('Runtime.callFunctionOn', {'objectId': obj, 'returnByValue': True, 'functionDeclaration': fn}))
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: return None, repr(e)[:200]
    ctl = outer = None; acted = ()  # the retained located control, the outer control, the acted controls (CDP remote object ids of this document)
    def obj(self, expr):  # a main-world expression's result kept as a remote object (never by value): (objectId, None) or (None, why)
        if 'main' not in self.ids: return None, 'no main context'
        try:
            r = self.cdp.send('Runtime.evaluate', {'expression': expr, 'contextId': self.ids['main'], 'returnByValue': False})
            if r.get('exceptionDetails'): return None, self._result(r)[1]
            return r['result'].get('objectId'), (None if r['result'].get('objectId') else 'no object')
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: return None, repr(e)[:200]
    def on(self, obj, fn, *args, by_value=True):  # fn with `this` = a retained object; args: values, or ('obj', id) for retained objects: (result, None); a null node: (None, 'no object')
        # the ONE native error boundary of every retained-control read: a native exception or an absent/invalid/destroyed retained object refuses (Refused, cause kept)
        if obj is None: raise Refused('control handle: no retained object')
        try:
            r = self.cdp.send('Runtime.callFunctionOn', {'objectId': obj, 'functionDeclaration': fn, 'returnByValue': by_value,
                                                          'arguments': [{'objectId': a[1]} if isinstance(a, tuple) else {'value': a} for a in args]})
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: raise Refused('control handle: ' + repr(e)[:200])
        if r.get('exceptionDetails'): raise Refused('control handle: native exception: ' + str(self._result(r)[1]))
        if by_value: return r['result'].get('value'), None
        return r['result'].get('objectId'), (None if r['result'].get('objectId') else 'no object')
    def locate(self, js, args):  # a main-world locator returning [reading, node] or a reading alone: (reading, the node retained as a remote object, or None)
        arr, why = self.obj('(' + js + ')(' + json.dumps(args) + ')')
        if arr is None: return {'ok': False, 'why': why}, None
        loc, why = self.on(arr, 'function () { return Array.isArray(this) ? this[0] : this; }')
        el, _ = self.on(arr, 'function () { return Array.isArray(this) ? this[1] : null; }', by_value=False)
        return (loc if isinstance(loc, dict) else {'ok': False, 'why': why or 'no reading'}), el
    def from_main(self, js, args, fn):  # a node the main world's proof code returns (a native object, never a page name), asked in the isolated world
        if 'main' not in self.ids: return None, 'no main context'
        try:
            r = self.cdp.send('Runtime.evaluate', {'expression': '(' + js + ')(' + json.dumps(args) + ')', 'contextId': self.ids['main'], 'returnByValue': False})
            if r.get('exceptionDetails') or not r['result'].get('objectId'): return None, 'no node from the proof code'
            return self.node(self.cdp.send('DOM.describeNode', {'objectId': r['result']['objectId']})['node']['backendNodeId'], fn)
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e: return None, repr(e)[:200]
COPY_SIG = """function (p, ...acted) { const re = new RegExp('^' + p), c = window.__copy.cloneNode(true);
  const skip = new Set(); const pair = (a, b) => { if (acted.includes(a)) skip.add(b); for (let i = 0; i < a.childNodes.length && i < b.childNodes.length; i++) pair(a.childNodes[i], b.childNodes[i]); }; pair(window.__copy, c);  // paired while the clone is still identical
  const w = document.createTreeWalker(c, NodeFilter.SHOW_COMMENT), cs = []; let n; while ((n = w.nextNode())) if (re.test(n.nodeValue)) cs.push(n); cs.forEach(x => x.remove()); c.normalize();
  const shape = e => Array.from(e.children).map(c => '<' + c.localName + shape(c) + '>').join('');  // an acted control: its own text may change, its elements may not
  const out = []; const walk = e => { for (const x of e.childNodes) { if (skip.has(x)) { out.push('<acted ' + x.localName + shape(x) + '>'); continue; } if (x.nodeType === 1) { out.push('<' + x.localName); walk(x); out.push('>'); } else if (x.nodeType === 3) out.push(x.data); else if (x.nodeType === 8) out.push('!' + x.data); } }; walk(c); return out.join('\u0001'); }"""  # content and order, attributes left out
FX_TAKE_INNER = """function () { const ms = window.__fx.concat(window.__fxObs.takeRecords()); window.__fxObs.disconnect(); const copy = window.__copy;
  const ctl = this, inCtl = t => !!ctl && (t === ctl || ctl.contains(t));
  const roots = []; const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL); let n; while ((n = w.nextNode())) if (!window.__pre.has(n) && (!n.parentNode || window.__pre.has(n.parentNode)) && !inCtl(n)) roots.push(n);  // a control's own new label nodes are its observed state
  const path = e => { const c = []; let q = e && e.nodeType === 1 ? e : e && e.parentElement; while (q) { c.push(q.tagName.toLowerCase() + (q.id ? '#' + q.id : '')); q = q.parentElement; } return c.join('<'); };
  return {roots: roots.length, records: ms.map(m => ({where: inCtl(m.target) && m.type !== 'attributes' ? 'control label' : copy && copy.contains(m.target) ? (m.type === 'attributes' ? 'attribute inside the copy' : m.type + ' inside the copy') : 'outside the copy', type: m.type, target: path(m.target), attribute: m.attributeName, old: m.oldValue,
    now: m.type === 'attributes' ? m.target.getAttribute(m.attributeName) : m.type === 'characterData' ? m.target.data : null, added: m.addedNodes.length, removed: m.removedNodes.length}))}; }"""
EQUAL_UNMARKED = "([p]) => { " + COMMON + """ const rs = roots(); const r = rs[0], o = window.__lineage.origin.get(r); const u = unmarked(r), v = unmarked(o);
  return u.childNodes.length === v.childNodes.length && Array.from(v.childNodes).every((c, i) => c.isEqualNode(u.childNodes[i])); }"""  # both sides through Smart's own unmarked(): our comments dropped, text normalized
OBSERVE = """function (p) { const re = new RegExp('^' + p + 's:([0-9]+)$'), ctl = this, runs = [];
  const t = document.createTreeWalker(ctl, NodeFilter.SHOW_COMMENT); let c; while ((c = t.nextNode())) { const m = re.exec(c.nodeValue); if (m) runs.push(+m[1]); }
  const w = document.createTreeWalker(document, NodeFilter.SHOW_ALL), roots = []; let n; while ((n = w.nextNode())) if (!window.__pre.has(n) && (!n.parentNode || window.__pre.has(n.parentNode))) roots.push(n);
  const els = roots.filter(r => r.nodeType === 1); if (els.length !== 1) return {control_runs: runs, copy: null};
  const r = els[0], par = r.parentElement, prev = r.previousElementSibling; let depth = 0, q = ctl; while (q && q !== par) { q = q.parentElement; depth++; }
  return {control_runs: runs, copy: {previous_sibling_is_control: prev === ctl, parent_contains_control: !!(par && par.contains(ctl)), container_depth_above_control: q === par ? depth : null, last_child: r.nextSibling === null}}; }"""


def _settle(page, rec, seconds):  # the one settle rule: OCR's acquisition.quiet_settle (500 ms with nothing in flight and no new mutation, within the budget)
    if acquisition.quiet_settle(page, rec['inflight'], seconds): return {'settled': True, 'kind': 'bounded snapshot (acquisition.quiet_settle): 500 ms quiet; later timers not observed'}
    return {'settled': False, 'inflight': rec['inflight'][0]}


VIEWER_MENU = """() => { const jq = window.jQuery; if (!jq || typeof jq._data !== 'function') return null;
  return Array.from(document.querySelectorAll('a[href]')).flatMap((a, index) => {
    if (!a.matches('#menu > li > a[href="#"]')) return [];
    const ul = a.nextElementSibling, handlers = (jq._data(a, 'events') || {}).click || [];
    return [{index, closed: ul && getComputedStyle(ul).display === 'none',
      supported: !!ul && ul.tagName === 'UL' && a.onclick === null && !a.hasAttribute('onclick') && handlers.length === 1 &&
        Function.prototype.toString.call(handlers[0].handler) === "function(){$(this).next().slideToggle('normal')}"}];
  }); }"""  # the pinned accordion's own direct handler, through pinned jQuery's existing event-data helper
VIEWER_CLOSED = "e => !!e.nextElementSibling && getComputedStyle(e.nextElementSibling).display === 'none'"
VIEWER_HELPERS = 'window.$ === window.jQuery ? [window.jQuery, window.jQuery && window.jQuery._data, window.jQuery && window.jQuery.fn.next, window.jQuery && window.jQuery.fn.slideToggle] : []'
VIEWER_HANDLERS = "Array.from(document.querySelectorAll('#menu > li > a[href=\"#\"]')).map(a => jQuery._data(a, 'events').click[0].handler)"
VIEWER_ACT = "e => jQuery._data(e, 'events').click[0].handler.call(e)"  # the bound category callback only: no bubbling, default navigation or DOM0 handler


class Context:
    """One state of one document shown by its observed parent: `evidence` = {parent_url, target_url, observed (Source.observed shape: every recorded
    response, the parent and the target included), selection ({source_anchor}: OCR's recorded parent action), proof (overlay proof of the target
    response: {'form', 'inserted'}[, before, after])}; `control` = the source byte start of the activated source link record, None for the initial view."""
    inventory = False  # contextual_routes sets it for an initial-only view: each render then records Scope.code (optional_controls)
    def __init__(self, evidence, control=None, label='initial', settle_s=3.0, viewer_start=None):  # control: a source link start, or (outer, inner, ...) - an outer reveal then controls inside its proved target
        self.controls = [] if control is None else [control] if isinstance(control, int) else list(control)
        self.evidence, self.control, self.label, self.settle_s, self.records, self.reference, self.captures = evidence, (self.controls or [None])[0], label, settle_s, [], None, {}
        self.scopes = {}  # id(owned page) -> its Scope (the isolated-world source scope)  # reference: the state's first completed unmarked observation
        self.named_by = None  # a trial-named state (contextual_routes): the trial's own native record that named it; this extraction must be that observation
        self.viewer_start = json.dumps(viewer_start, sort_keys=True) if viewer_start is not None else None  # immutable value; committed only with the original completed unmarked observation
        self.parent_hrefs = [l['href'] for l in sg.Visible(evidence['observed'][evidence['parent_url']]['body']).links]

    def _viewer(self, page, raw, rec, got_in, refused_in, refuse):
        """Replay one originally observed parent start BEFORE target bytes and the entire source-action sequence. Unsupported parents keep the strict
        existing path. A supplied plan must match the parent, source, selection, received inputs and every native control; it is never replaced."""
        ev = self.evidence; plan = json.loads(self.viewer_start) if self.viewer_start is not None else None
        before_target = not any(r[1] == 'GET' and r[2] == ev['target_url'] for r in rec['requests'])
        if not before_target or 'native_node' not in ev['selection']:
            if plan is not None: refuse('viewer start: target already requested or no recorded native selection')
            return
        known = {h for _, status, h in got_in if status == 200}
        needed = {h for h, name in KNOWN_CODE.items() if name in ('viewer jQuery v3.7.1', 'viewer accordionMenu.js')}
        sc = self.scopes[id(page)]
        helpers = sc.function_sources(VIEWER_HELPERS) if needed <= known else None
        jq = next(h for h, name in KNOWN_CODE.items() if name == 'viewer jQuery v3.7.1')
        rows = page.evaluate(VIEWER_MENU) if helpers == [jq] * 4 else None
        if not rows or not all(r['supported'] for r in rows):
            if plan is not None: refuse('viewer start: recorded native category controls unavailable')
            return
        accordion = next(h for h, name in KNOWN_CODE.items() if name == 'viewer accordionMenu.js')
        if sc.function_sources(VIEWER_HANDLERS) != [accordion] * len(rows):
            if plan is not None: refuse('viewer start: category handler is not the recorded viewer code')
            return
        nodes = page.evaluate(acquisition.NODES)
        keys = [dict(zip(('path', 'tags', 'outer_html_sha256'), (nodes[r['index']][0], nodes[r['index']][1], acquisition.sha(nodes[r['index']][2].encode())))) for r in rows]
        before = {'parent_url': ev['parent_url'], 'target_url': ev['target_url'], 'parent_sha256': ev['observed'][ev['parent_url']]['sha256'],
                  'source_sha256': hashlib.sha256(raw).hexdigest(), 'selection': ev['selection']['native_node'],
                  'received': sorted(map(list, got_in), key=str), 'refused_get': sorted(map(list, refused_in), key=str),
                  'controls': [{'native_node': key, 'closed': r['closed']} for key, r in zip(keys, rows)]}
        try: handles = [self._native_node(page, {'native_node': key, 'state_inputs': ev['selection']['state_inputs']}, got_in, refused_in, refuse) for key in keys]
        except Refused:
            if plan is not None: raise
            rec['viewer_unsupported'] = rec.pop('refused'); return  # an ambiguous category does not impose a new prerequisite on the old path
        if any(r[1] == 'GET' and r[2] == ev['target_url'] for r in rec['requests']):
            if plan is not None: refuse('viewer start: target arrived before preparation')
            return
        rec['viewer_before'] = before
        if plan is None: return  # observation only; no changed reference or action in the original attempt
        # The comparison-only Source has already proved each withheld response. It is the existing input exception, never a general missing-input allowance.
        withheld = {u for u, _ in rec.get('withheld') or []}
        expected = dict(plan, received=[r for r in plan['received'] if r[0] not in withheld], controls=[dict(c, closed=r['closed']) for c, r in zip(plan['controls'], rows)])
        if expected != before or len(plan['controls']) != len(rows) or any(type(c['closed']) is not bool for c in plan['controls']): refuse('viewer start: original parent, input or control binding differs')
        rec['viewer_actions'] = []; rec['phase'] = 'viewer start'; rec['viewer_start_sha256'] = hashlib.sha256(self.viewer_start.encode()).hexdigest()
        for control, current, wanted in zip(handles, rows, plan['controls']):
            if current['closed'] == wanted['closed']: continue
            if any(r[1] == 'GET' and r[2] == ev['target_url'] for r in rec['requests']): refuse('viewer start: target arrived before preparation')
            action = {'native_node': wanted['native_node'], 'before_closed': current['closed'], 'after_closed': None}; rec['viewer_actions'].append(action)
            n0 = len(rec['requests']); control.evaluate(VIEWER_ACT); action['settle'] = _settle(page, rec, self.settle_s)
            if not action['settle']['settled']: refuse('viewer start: native category action did not settle')
            if any(r[1] == 'GET' and r[2] == ev['target_url'] for r in rec['requests']): refuse('viewer start: category action requested the target')
            if rec['pages'] or any(r[0] == 'viewer start' and r[3] == 'document' for r in rec['requests']) or any(e[0] == 'viewer start' for e in rec['errors']): refuse('viewer start: navigation, new page or script error')
            if rec['requests'][n0:]: refuse('viewer start: request during the category action')
            action['after_closed'] = control.evaluate(VIEWER_CLOSED)
            if action['after_closed'] != wanted['closed']: refuse('viewer start: native category action did not restore the observed state')

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
        scope = self.scopes[id(page)] = Scope(page, lifetime=self.inventory); page.on('close', lambda _: self.scopes.pop(id(page), None)); page.context.add_init_script(INIT); page.context.add_init_script(acquisition.INIT); rec['inflight'] = acquisition.count_requests(page); served = [False]; got_in, refused_in = set(), set()  # this render's received inputs (OCR facts: delivered identities, refused GETs)
        def answer(route):
            q = route.request; r4 = [rec['phase'], q.method, q.url, q.resource_type]; rec['requests'].append(r4)  # the four raw fields, recorded first and always
            try: r4.append(bool(q.is_navigation_request() and q.frame.parent_frame is None))  # fifth field: a main-frame navigation by the browser's own facts (Request.is_navigation_request, Frame.parent_frame); a child-frame document load is not one
            except PlaywrightError as e: r4.append({'frame': str(e)})  # the getter's own typed error (a new window's first request: its frame does not exist yet): kept raw, never counted as ordinary
            if q.method != 'GET': return route.abort('blockedbyclient')  # recorded, never answered
            if q.url == ev['parent_url'] and q.is_navigation_request() and not served[0]:
                served[0] = True; got_in.add((q.url, pv[0], o[q.url].get('sha256'))); return route.fulfill(status=pv[0], content_type=o[q.url].get('content_type') or 'text/html', body=pv[2])
            if q.url == ev['target_url'] and not q.is_navigation_request():
                if rec['phase'] == 'viewer start': return route.abort('blockedbyclient')  # no target measurement bytes may arrive during preparation; its recorded request refuses the attempt
                if measured is None: source._refuse(q.url, q.url, None, q.resource_type, 'target without a verified measurement body'); refused_in.add((q.url, q.resource_type)); return route.abort('failed')
                got_in.add((q.url, tv[0], t.get('sha256'))); return route.fulfill(status=tv[0], content_type=t.get('content_type') or 'text/html', body=measured)  # received: the original response's identity
            got = source.answer(q.url, q.resource_type, q.is_navigation_request())
            if got: got_in.add((q.url, got[0], source.observed[q.url].get('sha256') if q.url in source.observed else hashlib.sha256(got[2]).hexdigest())); return route.fulfill(status=got[0], content_type=got[1], body=got[2])
            if q.url in sg.WITHHELD and (q.url + '\x00withheld\x00' + q.resource_type) in source.records: rec.setdefault('withheld', []).append([q.url, q.resource_type]); return route.abort('aborted')  # COMPARISON-ONLY (plan.qualification_withhold): exactly where the Source booked it; never a received or refused input
            if not q.is_navigation_request(): refused_in.add((q.url, q.resource_type))
            if asked is not None and q.resource_type == 'stylesheet': asked.append(q.url)
            return route.abort('aborted')
        page.context.route('**/*', answer); page.context.on('page', lambda pg: rec.__setitem__('pages', rec['pages'] + 1))  # the context's route: popups and workers answer to the same rule
        page.on('pageerror', lambda e: rec['errors'].append([rec['phase'], str(e)[:200]]))
        page.on('domcontentloaded', lambda _: rec.setdefault('dcl_at', len(rec['requests'])))  # native lifecycle order: requests recorded before the main frame's DOMContentLoaded event (the parse-time snapshot)
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
            self._viewer(page, raw, rec, got_in, refused_in, refuse)
            if ev['selection'].get('initial'):  # the target is the parent's own initial selection (OCR's native outcome): no click
                if not any(r[2] == ev['target_url'] and r[1] == 'GET' for r in rec['requests']): refuse('initial selection: the parent did not request the target at startup')
                t_at = next(i for i, r in enumerate(rec['requests']) if r[2] == ev['target_url'] and r[1] == 'GET'); d_at = rec.get('dcl_at')
                rec['parse_order'] = {'target_request_index': t_at, 'domcontentloaded_index': d_at, 'target_after_parse_snapshot': d_at is not None and t_at >= d_at}  # observed order only
                rec['selection'] = 'initial (no action)'
                if rec['parse_order']['target_after_parse_snapshot']:  # the parse-time parent set holds no member node: a parent-only inference is sound
                    rec['scope_activated'] = list(scope.call('window.__sourceScope.useParse()'))
                    if rec['scope_activated'][0] is not True: refuse('initial selection: no parse-time snapshot of the parent in the source scope (%s)' % rec['scope_activated'][1])
                else: rec['scope'] = 'unknown: the target was not proved requested after the parse-time snapshot; no source scope (consumers fail closed)'
                if self.control is not None: self._activate(page, raw, p, rec, refuse)
                for inner in self.controls[1:]: self._activate_inner(page, raw, p, rec, refuse, inner)
                return res
            rec['pre_selection_nodes'] = list(scope.call('window.__sourceScope.takeNow()')); rec['phase'] = 'selection'; sel = ev['selection']
            if not isinstance(rec['pre_selection_nodes'][0], int): refuse('source scope: no parent snapshot before the selection (%s)' % rec['pre_selection_nodes'][1])  # the parent's nodes right before the selection, in the isolated world
            if 'native_node' in sel:
                rec['selection_inputs'] = {'received': sorted(map(list, got_in), key=str), 'refused_get': sorted(map(list, refused_in), key=str)}  # the exact sets _native_node compares next (no browser call between), kept even when it refuses
                el = self._native_node(page, sel, got_in, refused_in, refuse); rec['selection'] = 'native observed control (OCR NativeSelection key), not a raw-source anchor'
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
            rec['scope_activated'] = list(scope.call('window.__sourceScope.useNow()'))
            if rec['scope_activated'][0] is not True: refuse('source scope: not activated after the selection (%s)' % rec['scope_activated'][1])
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
                served[0] = False; got_in.clear(); refused_in.clear(); rec.pop('refused', None); rec.pop('dcl_at', None); scope.ctl = scope.outer = None; scope.acted = []; rec['phase'] = 'startup'; a = {'attempt': k}; rec['attempts'].append(a)
                try: res = observe(); n = snapshot(); rec['final_controls'] = [scope.on(a, FINAL_CONTROL)[0] for a in scope.acted]  # the final state's control readings, beside the canonical snapshot
                except Refused as e: rec.setdefault('refused', str(e)); a['outcome'] = 'not used: refused'; continue  # its reason is kept with the attempt (a boundary's own Refused: its message)
                except sg.CaptureError as e: a['outcome'] = 'failed: ' + str(e); refuse(str(e))  # a failed or incomplete native capture: refused, never retried
                a['native'] = n; ref = self.reference
                if ref is None and rec['marked']: a['outcome'] = 'not used: no state reference (no unmarked observation completed first)'; break  # nothing to match: no retry
                if ref is not None and n != ref: a['outcome'] = 'not used: differs from the state reference (' + ', '.join(x for x in ref if n.get(x) != ref[x]) + ')'; continue
                if ref is None and self.named_by is not None and n != self.named_by: a['outcome'] = 'not used: differs from the trial observation that named the state (' + ', '.join(x for x in self.named_by if n.get(x) != self.named_by.get(x)) + ')'; continue  # a trial-named state's reference is only its own observation of that state
                if ref is None: self.reference = n  # the first completed unmarked observation: fixed for this state, never changed afterwards
                if ref is None and not rec['marked'] and self.viewer_start is None and not self.controls and rec.get('viewer_before'):
                    rec['viewer_start'] = rec['viewer_before']; self.viewer_start = json.dumps(rec['viewer_start'], sort_keys=True)
                a['outcome'] = 'used' if ref is not None else 'used: the state reference'; rec['native'] = n; rec['phase'] = 'measurement'
                if self.inventory and not self.controls: rec['code'] = scope.code()  # an initial-only view's executable code and listeners (optional_controls reads them)
                return res
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
        sc = self.scopes[id(page)]; hrefs = [l['href'] for l in vis.links]; rec['phase'] = 'action'; loc, el = sc.locate(CTL_FIND, [p, ctl_runs, idx[0], len(vis.links), hrefs])
        if loc.get('fallback'):  # no own run mark in this render: the inserted-child link order rule, decided in the isolated world on its own scope
            el, why = sc.to_main('window.__sourceScope.pick(%d, %s, %d)' % (len(vis.links), json.dumps(hrefs), idx[0]), None)
            loc = {'how': 'inserted-child link order (isolated-world scope; node by native identity)', 'ok': el is not None, **({} if el is not None else {'why': why or 'not located'})}
        rec['control_located'] = loc
        if not loc['ok'] or el is None: refuse('control identity: ' + str(loc.get('why') or 'no located node'))
        sc.ctl = el  # retained: every later step acts on this node, never on a page-writable name
        page.evaluate(SNAP); n0, e0 = len(rec['requests']), len(rec['errors']); page.evaluate(FX_START)
        why = sc.on(sc.ctl, 'function () { this.click(); }')[1]
        if why: refuse('control handle: ' + why)
        rec['action'] = 'programmatic HTMLElement.click() (untrusted)'; rec['action_settle'] = _settle(page, rec, self.settle_s)
        fx = page.evaluate(FX_TAKE); rec['effects'] = fx; reqs = rec['requests'][n0:]; errs = rec['errors'][e0:]
        rec['probe'] = {'new_roots': fx['roots'], 'mutations': len(fx['records']), 'requests': len(reqs), 'errors': len(errs)}
        proof = page.evaluate(PROVE, [p, raw.decode('utf-8')]); rec['proof'] = proof
        other = [m for m in fx['records'] if not (m['where'] == 'copy inserted' or (m['where'] == 'inside the copy' and m['type'] == 'attributes'))]  # a reveal may set the copy's own properties; any content change or outside effect is held
        mut = f"{len(other)} mutation(s) other than the one copy insertion and attribute changes inside the copy (held)"
        why = [w for w, bad in (('incomplete observation after the action', not rec['action_settle']['settled']), ('script error', errs), ('non-GET request', any(r[1] != 'GET' for r in reqs)),
               ('navigation', any(r[3] == 'document' for r in reqs)), ('not exactly one new element root with native copy lineage', len(proof) != 1 or proof[0]['lineage'] is None),
               (mut, other)) if bad]
        cont = self.continuation(rec, list(why), reqs, other, {'non-GET request', mut}, inner=False)  # QUALIFICATION-ONLY diagnostic continuation (root-single-version-qualification): decided on the action-phase reasons only
        if len(proof) == 1 and proof[0]['lineage']:
            L = proof[0]['lineage']; ids = vis.ids.get(L['origin_id'], []) if L['origin_id'] is not None else []
            why += [w for w, bad in (('origin not present before the action', not L['origin_was_present']), ('origin moved', not L['origin_still_connected']), ('copy not shown', not proof[0]['shown']),
                    ('origin id not declared exactly once', len(ids) != 1 or ids[0]['end'] is None or L['inert_id_hits'] != 1), ('origin differs from the inert parse of the source', not L['origin_equals_source_parse']),
                    ('copy root not mapped', not L['copy_root_mapped']), ('copy children not an ordered native copy', not L['copy_children_ordered_identity']), ('copy children not node-equal', not L['copy_children_equal'])) if bad]
            v, why_o = self.scopes[id(page)].from_main(ORIGIN_NODE, [p], 'function () { return window.__sourceScope.notPre(this); }'); rec['origin_in_selected_child'] = v if why_o is None else {'unknown': why_o}  # the selected child's own node, never a parent one; a scope failure: its cause, never True
            if rec['origin_in_selected_child'] is not True: why.append('the origin is not a node of the selected child (a parent-owned equal target does not qualify)')
            if len(ids) == 1 and ids[0]['end'] is not None: rec['target'] = {'declared_id': L['origin_id'], 'source_extent': {'byte_start': ids[0]['start'], 'byte_end_exclusive': ids[0]['end']}}
        if why and not (cont and why == rec['diagnostic_continuation']['rejected']): refuse('; '.join(why))  # the lineage/origin reasons added above are never continued
        br = page.evaluate(BRIDGE, [p]); rec['bridge'] = br
        if not br['performed']: refuse('bridge: ' + br['why'])
        page.evaluate(SET_ORIGIN, [p]); rec['scope_origin'] = list(self.scopes[id(page)].from_main(ORIGIN_NODE, [p], 'function () { return window.__sourceScope.setOrigin(this); }'))
        if rec['scope_origin'][0] is not True: refuse('source scope: the proved origin was not transferred (%s)' % rec['scope_origin'][1])
        rec['after_bridge_settle'] = _settle(page, rec, self.settle_s); after = page.evaluate(AFTER, [p]); rec['after_bridge'] = after
        after['copy_equals_origin_both_unmarked'] = page.evaluate(EQUAL_UNMARKED, [p])  # AFTER's own field compares an unnormalized origin (our removed marks leave its text split)
        bad = [k for k in ('copy_still_shown', 'origin_still_connected', 'origin_still_not_displayed', 'copy_equals_origin_both_unmarked') if after.get(k) is not True]
        if not rec['after_bridge_settle']['settled'] or bad: refuse('after the bridge: ' + ', '.join(bad or ['not settled']))
        rec['observe'] = sc.on(sc.ctl, OBSERVE, p)[0]; sc.outer, sc.acted = sc.ctl, []

    def _activate_inner(self, page, raw, p, rec, refuse, start):
        """A source-owned control inside the proved target, after the outer reveal: accepted only as an in-place change - no new node, every mutation an
        attribute of a node inside the copy, the copy's content and order unchanged (attributes are the observed change, kept raw)."""
        vis = sg.Visible(raw); runs, _ = sg.symbol_runs(raw, vis); ext = (rec.get('target') or {}).get('source_extent')
        if not ext: refuse('inner control without a proved target')
        inner = [l for l in vis.links if ext['byte_start'] <= l['start'] < ext['byte_end_exclusive']]; k = [i for i, l in enumerate(inner) if l['start'] == start]
        one = {'control': start}; rec.setdefault('inner', []).append(one)
        sc = self.scopes[id(page)]
        if start == self.control: sc.ctl = sc.outer; one['located'] = {'how': 'the outer control element already proved', 'ok': sc.outer is not None}
        elif len(k) != 1: refuse('a later control is neither a source link inside the proved target nor the outer control')
        else:
            l = inner[k[0]]; ctl_runs = [j for j, (_, chars, _, ok) in enumerate(runs) if ok and l['tag_end'] <= chars[0][0] and chars[-1][1] <= l['end']]
            one['located'], sc.ctl = sc.locate(IN_COPY_FIND, [p, ctl_runs, k[0], [x['href'] for x in inner]])
        loc = one['located']
        if not loc['ok'] or sc.ctl is None: refuse('later control identity: ' + str(loc.get('why') or 'no located node'))
        if sc.on(sc.ctl, 'function (...acted) { return acted.includes(this); }', *[('obj', a) for a in sc.acted])[0] is not True: sc.acted.append(sc.ctl)  # its own label is observed action state, compared apart
        one['label_before'], why = sc.on(sc.ctl, 'function () { return this.textContent; }')
        if why: refuse('control handle: ' + why)
        page.evaluate('() => { window.__copyParent = window.__copy ? window.__copy.parentNode : null; }')  # where the proved copy stands before the action
        sig = lambda: sc.on(sc.ctl, COPY_SIG, p, *[('obj', a) for a in sc.acted])[0]
        before = sig(); page.evaluate(SNAP); n0, e0 = len(rec['requests']), len(rec['errors']); page.evaluate(FX_START)
        why = sc.on(sc.ctl, 'function () { this.click(); }')[1]
        if why: refuse('control handle: ' + why)
        one['settle'] = _settle(page, rec, self.settle_s); fx, why = sc.on(sc.ctl, FX_TAKE_INNER); one['effects'] = fx
        if fx is None: refuse('control handle: ' + str(why))
        reqs, errs = rec['requests'][n0:], rec['errors'][e0:]; rep = None
        if start == self.control and fx['roots'] == 1:  # the outer control again, one new root: a native replacement of the proved copy, every fact required
            proof = page.evaluate(PROVE, [p, raw.decode('utf-8')]); f = page.evaluate(REPLACED, [p]); so = self.scopes[id(page)].from_main(ORIGIN_NODE, [p], 'function () { return window.__sourceScope.isOrigin(this); }'); f['same_origin'] = so[0] is True; f['same_origin'] or one.__setitem__('replacement_origin_scope', list(so)); L = proof[0]['lineage'] if len(proof) == 1 else None; got = {q[2] for q in rec['requests'][:n0]}
            rep = one['replacement'] = {'same_origin': f['same_origin'], 'new_root_in_place': f['same_parent'], 'old_copy_removed_only': f['old_removed'] and f['parent_kept'] and sum(m['removed'] for m in fx['records']) == 1,
                'only_that_change': all(m['type'] == 'childList' for m in fx['records']) and sum(m['added'] for m in fx['records']) == 1, 'origin_equals_source_parse': bool(L and L['origin_equals_source_parse']),
                'children_ordered_identity': bool(L and L['copy_children_ordered_identity']), 'children_equal': bool(L and L['copy_children_equal']), 'inputs_already_received': all(q[1] == 'GET' and q[2] in got for q in reqs)}
        replaced = rep is not None and all(rep.values()) and one['settle']['settled'] and not errs
        if replaced: page.evaluate(ADOPT, [p])
        one['copy_shown_after'] = page.evaluate('() => !!window.__copy && window.__copy.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})'); one['label_after'] = sc.on(sc.ctl, 'function () { return this.textContent; }')[0]
        one['control_shown_after'] = sc.on(sc.ctl, 'function () { return this.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}); }')[0]  # native: the acted control itself is shown
        one['probe'] = {'new_roots': fx['roots'], 'mutations': len(fx['records']), 'requests': len(reqs), 'errors': len(errs)}
        why = [w for w, bad in (('incomplete observation after the inner action', not one['settle']['settled']), ('script error', errs), ('navigation by an ordinary link (no conditional state)', any(r[3] == 'document' for r in reqs)), ('request after the inner action', not replaced and [r for r in reqs if r[3] != 'document']),
               ('new nodes', not replaced and fx['roots']), ('a change other than an attribute inside the copy or the control\'s own label', not replaced and any(m['where'] not in ('attribute inside the copy', 'control label') for m in fx['records'])),
               ("the copy's content or order changed", not replaced and (before is None or sig() != before))) if bad]
        if rep is not None and not replaced: why.append('not a qualified replacement: ' + (', '.join(k for k, v in rep.items() if not v) or 'unsettled or script error'))
        if why and not self.continuation(one, list(why), reqs, [m for m in fx['records'] if m['where'] not in ('attribute inside the copy', 'control label')],
                                         {'request after the inner action', "a change other than an attribute inside the copy or the control's own label"}, inner=True): refuse('inner action: ' + '; '.join(why))

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

    def continuation(self, rec, why, reqs, records, allowed, inner):
        """QUALIFICATION-ONLY diagnostic continuation (root-single-version-qualification). Only where the caller's evidence names it ({'diagnostic_continuation': {'bound_href': the proved inserted
        script's address}} - never set by production settings): an action whose rejected reasons are ALL in `allowed` (its own two bound-script effect
        classes) and whose every non-GET request (inner action: every request) is a non-GET to that address is observed on instead of refused. Its full rejected reasons, requests and
        records stay in rec['diagnostic_continuation']; Context.gate keeps the state incomplete. Evidence for the pair comparison only, never a pass."""
        href = ((self.evidence or {}).get('diagnostic_continuation') or {}).get('bound_href')
        if not href or not why or not set(why) <= allowed or not all(r[1] != 'GET' and r[2] == href for r in reqs if r[3] != 'document' and (inner or r[1] != 'GET')): return False
        rec['diagnostic_continuation'] = {'rejected': why, 'requests': [list(r) for r in reqs], 'records': records, 'bound_href': href}; return True

    def diagnostics(self):  # the gate reasons that come only from the qualification-only diagnostic continuation
        return [f"render {i}: diagnostic continuation (qualification only, never a native success): {c['rejected']}" for i, r in enumerate(self.records)
                for c in [r.get('diagnostic_continuation')] + [x.get('diagnostic_continuation') for x in r.get('inner') or []] if c]

    def gate(self):
        """Why this state is not complete ([] when every render reached it and all agree on the target occurrence and its placement)."""
        cont = self.diagnostics()
        why = cont + [f"render {i} ({'marked' if r.get('marked') else 'unmarked'}): {r['refused']}" for i, r in enumerate(self.records) if r.get('refused')]
        why += [f"render {i} ({'marked' if r.get('marked') else 'unmarked'}): attempted, but no completed native record" for i, r in enumerate(self.records) if not r.get('refused') and not r.get('native')]
        ref = next((r['native'] for r in self.records if not r.get('marked') and r.get('native')), None)  # OCR's strict rule, every attempted render and marker kind
        if ref is None: why.append('neutrality: no unmarked reference render of this state')
        else: why += [f"neutrality: render {i} ({'marked' if r.get('marked') else 'unmarked'}) differs from the unmarked reference ({', '.join(k for k in ref if r['native'].get(k) != ref[k])})"
                      for i, r in enumerate(self.records) if r.get('native') and r['native'] != ref]
        if self.named_by is not None and ref is not None and ref != self.named_by: why.append("state identity: this extraction's reference differs from the trial observation that named the state")
        if self.control is not None and not why:
            seen = {json.dumps([r.get('target'), (r.get('observe') or {}).get('copy'), [(i['control'], [(m['target'], m['attribute'], m['now']) for m in i['effects']['records']]) for i in r.get('inner') or []]], sort_keys=True) for r in self.records}
            if len(seen) != 1: why.append(f'neutrality: renders disagree on the target occurrence or its placement ({len(seen)} distinct readings across {len(self.records)} renders)')
        return why


def text_proof(route, ctx):
    """Why this state's text is not proved for its local labels and target runs ([] when it is): the native state gate, read now (after every render,
    the caller's picture step too), and the route's own affirmative text proof (`text_proved`, html_route; missing is false: no status fallback).
    Aggregate status, error and unknowns are untouched."""
    return ctx.gate() + ([] if route.get('text_proved') is True else ['state route text not proved'])


def observed_controls(raw, route, ctx):
    """OBSERVED_CONTROLS_CONTRACT_v2_20261022: one record per acted control whose label an action replaced in this state, by the existing owner text
    slices (screen_grid._owners); bound to its exact final action occurrence (lineage.action_index, lineage.occurrences in action order)."""
    labels = ctx.observed_labels(raw) if ctx.records else {}
    if not labels: return
    pv = route.get('page_visibility'); vis = anchor.Visible(raw, page=pv) if pv else anchor.Visible(raw)
    owned = sg._owners(vis, route['units'], spaced=True); rendered = [k for k, r in enumerate(ctx.records) if r.get('native')]; diag = ctx.diagnostics()
    state = [w for w in ctx.gate() if w not in diag] + ([] if route.get('text_proved') is True or (diag and (route.get('diagnostic') or {}).get('text_proved_before_gate') is True) else ['state route text not proved'])  # text_proof, the QUALIFICATION-ONLY diagnostic gate kept apart (the route stays PARTIAL)
    for (x0, x1), o in sorted(labels.items()):
        owners, why = owned(x0, x1)  # each owner (unit, or a table cell by its anchor's first byte) with the label's own code-point ranges in its saved text
        reasons = [w for w, bad in (('control not shown in the final state', not o['shown']), ('no final native reading of the control', o['after'] is None), ('the label is not owned whole: ' + str(why), owners is None)) if bad] + state
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


def same_text(vis, a, b, dom):
    """True iff `dom` (an element's DOM textContent: CODE_ACTIONS) in the shared comparison form (compare._WS removed) is exactly the scanner's search
    characters (`vis.idx`, the characters the held/owners rule counts) in that element's bytes [a, b): no held character the parser moved in, out or
    out of order. White space is not held material in that contract (the scanner's own layout gaps are white space); its roles stay with the reading's gates."""
    return dom is not None and compare._WS.sub('', dom) == ''.join(vis.text[i] for i in vis.idx if a <= vis.starts[i] < b)


def _declared_controls(items):
    """(reasons, {action value: count}, {link start: showAR id}) for scripted source links given as (start, href, declarations): each must be exactly one
    renderer ACTION form on javascript:void(0); (optional_controls' own rule, shared with the SCRIPTLESS path)."""
    why, declared, targets = [], {}, {}
    for start, href, d in items:
        m = ACTION.fullmatch(d[0].get('value') or '') if len(d) == 1 and d[0].get('name') == 'onclick' else None
        if href != 'javascript:void(0);' or m is None: why.append(f"control at {start}: not one renderer action on javascript:void(0);"); continue
        declared[d[0]['value']] = declared.get(d[0]['value'], 0) + 1
        if m.group('id'): targets[start] = m.group('id')
        # Show.hideAR only hides Show.LastAR, which only Show.showAR sets (pinned Show.js): it reveals nothing. Show.toggleNext: its own DOM walk (CODE_ACTIONS), below
    return why, declared, targets


REVIEWED_SHEETS = {'cb242530100cd884d71f96f5fb2f780c23b21027e81be3b8a778b7bbd9282ca8': 'viewer /include/report.css', '53ad2e099685b3b0f9f313352e126db79eaeb28a2168ee5fda02a2aaf845ba33': 'viewer /include/interactive2.css',
                   'd85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede': 'viewer bootstrap.min.css', '711700a13fac17a9e5a6a23b654c3449285396a7e003aab5679183dcae91d88e': 'viewer /include/xbrlViewerStyle.css',
                   '5b47d0695976e1c83253163f36e080b11531d3c136c794a9338eaae963420074': 'viewer /include/print.css', 'c564d6d00dc81a734bd958995c968a220c4e3de896cd48ac52b82a641a40e26f': 'package report.css',
                   '9e1daf3fc7e3573457b340ee45f8f5e9dd6b47ccd913c9cfee43a63a0ede7722': 'viewer inline <style> (li.accordion menu)'}  # reviewed 10-30 (VIEWER_SHEETS_REVIEW.txt): no text-adding rule reaches Renderer classes/reveal tags


REVIEWED_CSSOM = {'cb242530100cd884d71f96f5fb2f780c23b21027e81be3b8a778b7bbd9282ca8': ('d8054541f7687020e49468a068416a9debfebe28bae7797f08e79eea7129a237',),
                  '53ad2e099685b3b0f9f313352e126db79eaeb28a2168ee5fda02a2aaf845ba33': ('9319d1e321c0f0bbd2dfac32bcaac6ee40dd3f499db7fa534b21d83b1a3a4228',),
                  'd85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede': ('9a2c34104ad5859d7e39c23f1b473d6f231b1342699c1a3f7ecdbc2eda2d1f28', '12bc2d0664a9f99be2ec87373e57618244dafc11235eff4f1c73a2bce4e2572c'),
                  '711700a13fac17a9e5a6a23b654c3449285396a7e003aab5679183dcae91d88e': ('0b5ef6ad519292cf1f0cb2cead1d7ec6e004e6cec9d8f4d15a39a6cfaac7d506',),
                  '5b47d0695976e1c83253163f36e080b11531d3c136c794a9338eaae963420074': ('3d2270c0d30f8a4ff748afde8da05ab68bf2f1e092592c678f44a80bd2e5c5cf',),
                  'c564d6d00dc81a734bd958995c968a220c4e3de896cd48ac52b82a641a40e26f': ('d8054541f7687020e49468a068416a9debfebe28bae7797f08e79eea7129a237',),
                  '9e1daf3fc7e3573457b340ee45f8f5e9dd6b47ccd913c9cfee43a63a0ede7722': ('5cff2d47979a1171507a2f4f6779903d531ebf917b081935dd094dad210602b4',)}  # each reviewed sheet's DEMONSTRATED raw native cssRules[].cssText digests (joined by newline), pinned Chromium 147: the clean <link> parse (REVIEWED_CSSOM_DERIVATION_LINK.txt); for bootstrap ALSO the same-DOM JS-disabled parse that equals the live viewer exactly (Codex S0b: six navbar-collapse rules serialize display/flex-basis in the other order). Any other current text: unknown, deficit kept


RENDERER_REVEAL_TAGS = frozenset(('table', 'tbody', 'tr', 'td', 'div', 'a', 'p', 'strong', 'br'))  # SHARED GUARD positive profile: inside every definition on the 4 reviewed public Renderer pages (tbody: the parser's own)
RENDERER_REVEAL_ANY = frozenset(('color', 'width', 'text-wrap-mode'))  # with any padding-* longhand
RENDERER_REVEAL_BORDERS = frozenset(f'border-{side}-{part}' for side in ('top', 'right', 'bottom', 'left') for part in ('width', 'style', 'color'))  # exactly what the per-cell carrier records; border-image-* is NOT admitted (no demonstrated need; it can add image content)  # by EFFECT: paint, spacing, line breaking - none adds, removes or reorders text
RENDERER_CLASSES = frozenset(('a', 'authRefData', 'big', 'body', 'fn', 'hide', 'more', 'note', 'num', 'nump', 'outerFootnotes', 'pl', 'rc', 're', 'report', 'reu', 'rh', 'ro', 'rou', 'small', 'text', 'void',  # every class selector of the reviewed report.css c564d6d0
                              'th', 'tl', 'custom', 'outerFootnote'))  # + Renderer markup classes NO reviewed or recorded viewer sheet styles (inert on both routes); bootstrap styles only 'small' (font size). Any other class: unproved
# outerFootnote (the Renderer's footnote ROW class; .outerFootnotes is its table): 0 class-token and 0 [class] attribute selectors in package report.css c564d6d0 and the
# recorded viewer sheets cb242530, 53ad2e09, d85327d9, 711700a1, 5b47d069 (KNOWN_00D_R4_ASSESSMENT, static read 6:31 PM)
RENDERER_REVEAL_VALUES = {'display': ('none', 'block'), 'white-space-collapse': ('collapse',)}  # hide/show only (what the reveal toggles); default white-space collapsing only. Any priority (!important) or other declaration: unproved


def _dom_action_reasons(acts, declared, targets, toggles, unknown_classes_inert=False):
    """optional_controls' DOM-action conditions on one CODE_ACTIONS reading (appends each qualifying toggleNext's holders to `toggles`)."""
    r = []
    if not isinstance(acts, dict) or 'unknown' in acts: return ['the DOM control facts are unknown']
    seen = {}
    for v, table, *walk in acts['actions']:
        seen[v] = seen.get(v, 0) + 1; m = ACTION.fullmatch(v or '')
        if table and m and m.group('id'): r.append(f'Show.showAR {m.group("id")!r}: a following TABLE is shown instead (branch unsupported)')
        if m and 'toggleNext' in m.group(0):  # pinned Show.toggleNext: the first DIV from the control along its following siblings; no DIV throws, no inline display is a no-op
            t = walk[0] if walk else None
            if not isinstance(t, dict): r.append('Show.toggleNext: its DOM walk facts are unknown')
            elif t['div'] and t['display']:  # it shows or hides that DIV and rewrites the control's own first character: both must lie in an element the reading holds whole
                u = [k for k in t.get('holders') or [] if acts['ids'].get(k) == [1, 1]]  # DOM ancestors enclosing control and DIV, one element per id, in the source scope
                if u: toggles.append(tuple((k, (acts.get('texts') or {}).get(k)) for k in sorted(u)))  # with the DOM's own text of each
                else: r.append('Show.toggleNext: no DOM-unique source-scope element encloses the control and its DIV')
    if seen != declared: r.append('the source-scope onclick controls in the DOM differ from the native declarations')
    for t in sorted(set(targets.values())):
        if acts['ids'].get(t) != [1, 1]: r.append(f'Show.showAR target {t!r}: {acts["ids"].get(t)} [document, source-scope] elements, not one source-scope id')
    rv = acts.get('reveal')  # SHARED GUARD (Codex T2/T3): what any reveal shows must lie within the reviewed Renderer profile; unknown or outside keeps the deficit
    if not (isinstance(rv, dict) and {'targets', 'toggles', 'source_styles', 'classes', 'decls', 'sheets', 'adopted'} <= set(rv)): r.append('reveal profile facts unknown (shared guard)'); return r
    if set(rv['classes']) - RENDERER_CLASSES and not unknown_classes_inert: r.append(f"source classes outside the reviewed Renderer profile: {sorted(set(rv['classes']) - RENDERER_CLASSES)} (another sheet may style them)")  # e.g. a viewer-only utility class
    if rv['source_styles'] != 0: r.append(f"source <style> elements: {rv['source_styles']} (only the reviewed Renderer stylesheet may style a reveal)")
    def odd(decls): return [f"{n}: {v}" + (f" !{q}" if q else '') for n, v, q in decls or [] if q or not (n in RENDERER_REVEAL_ANY or n.startswith('padding-') or n in RENDERER_REVEAL_BORDERS or v in RENDERER_REVEAL_VALUES.get(n, ()))]
    def outside(f): return sorted(set(f.get('tags') or []) - RENDERER_REVEAL_TAGS) + odd(f.get('decls'))
    if odd(rv['decls']): r.append(f"source inline declarations outside the effect profile: {odd(rv['decls'])[:6]}")  # the ancestor/insertion context of every reveal (CODE_ACTIONS REVEAL CONTEXT)
    for t in sorted(set(targets.values())):
        f = rv['targets'].get(t)
        if f is None: r.append(f'Show.showAR target {t!r}: reveal profile facts unknown (shared guard)'); continue
        if outside(f): r.append(f'Show.showAR target {t!r}: content outside the supported reveal profile {outside(f)} (its CSS/source program is not proved reveal-only)')
    for k, f in enumerate(rv['toggles']):
        if outside(f): r.append(f'Show.toggleNext DIV {k}: content outside the supported reveal profile {outside(f)}')
    return r


def _reading_reasons(raw, route, child, targets, toggles):
    """optional_controls' source-reading conditions: every showAR target and every toggleNext holder held by the OK typed source reading (one run-to-owner rule)."""
    why, ids = [], {}
    for r in (route.get('source_ids') or {}).get('records') or []:
        if r.get('by') == 'id': ids.setdefault(r['value'], []).append((r['start'], r['end']))
    vis = anchor.Visible(raw, page=route.get('page_visibility'), source=True)  # the source reading's own stream (html_route.source_reading)
    held, owners = edgartools_html._holders(child.get('units') or [], vis)[0], sg._owners(vis, child.get('units') or [])  # the one run-to-owner rule
    for t in sorted(set(targets.values())):
        if len(ids.get(t) or []) != 1: why.append(f'target {t!r}: {len(ids.get(t) or [])} native id records'); continue
        (a, b), = ids[t]; _, n, _ = held(a, b); _, bad = owners(a, b)
        if n == 0 or bad: why.append(f'target {t!r}: {bad or "no character"} (source reading, one run-to-owner rule)')  # every character held, each owner's text the source's own at its places, every character read
    whole = lambda a, b: b is not None and held(a, b)[1] > 0 and owners(a, b)[1] is None  # the targets' rule, on that element's one native id record
    for u in sorted(set(toggles), key=str):
        if not any(len(ids.get(k) or []) == 1 and whole(*ids[k][0]) and same_text(vis, *ids[k][0], dom) for k, dom in u):
            why.append(f'Show.toggleNext: none of its {len(u)} enclosing DOM-unique element(s) is held whole by the source reading with exactly its own source text in the DOM')
    return why


RENDERER_SCRIPTS = {'37b4bcd336d85afa83ee0d5af7fd0c4ca43b0f4388eda9f2ed7e7c9be40999c8': 'package Show.js (the viewer 2e4e3855 with CRLF -> LF)',
                    '2e4e3855abccb781a7086a1720be0114500d5e252ab21bf2094ea557b6d94901': 'renderer Show.js'}  # SCRIPTLESS: reviewed Show.js bytes
RENDERER_HELPER = '55e5cd7e99fb2aecfd86f64e3daf9c88c4878111d6a79dbeb2eaba58a34aafa8'  # KNOWN_CODE's inline toggleNextSibling definition (never called by a control)
RENDERER_UNVALIDATED = ()  # Root 10:24 PM: every c564 role effect has an existing carrier (rc background stack, note font_style+weight, more hidden run, fn sup lift) - ROLE_GUARD proof. Was: SCRIPTLESS scope: report.css roles not yet shown preserved on this path (hidden more, notes, calendars). fn (footnote reference cell) admitted Root 10:07 PM: FN_PROOF 3 pages, 170 cells/52 sup markers kept vs independent original. Totals (reu/rou) admitted: their underline is now kept by source_style 'borders' (Codex T1 P/N, B1)
RENDERER_DOM = """(() => { const sheets = Array.from(document.querySelectorAll('link')).filter(l => /stylesheet/i.test(l.rel || '')).map(l => l.href);
  const scripts = Array.from(document.scripts).map(s => s.hasAttribute('src') ? [s.src, null] : [null, s.text]);
  const classes = new Set(); for (const e of document.querySelectorAll('[class]')) for (const c of e.classList) classes.add(c);
  const applied = Array.from(document.styleSheets).map(x => { let n = null; try { n = x.cssRules.length; } catch (e) {} return [x.href, x.disabled, x.media.mediaText, n, x.ownerNode ? x.ownerNode.localName : null]; });  // what the page actually applies: every sheet, enabled or not, its media and rule count
  const links = Array.from(document.querySelectorAll('link')).filter(l => /stylesheet/i.test(l.rel || '')).map(l => [l.href, (l.getAttribute('rel') || '').toLowerCase().split(/\\s+/).filter(Boolean), l.getAttribute('media'), l.hasAttribute('title'), l.hasAttribute('disabled')]);  // each sheet link as written: an alternate or titled sheet can report enabled yet not apply
  return {top: window.top === window, sheets, applied, links, scripts, classes: Array.from(classes).sort(), sup: document.querySelectorAll('sup').length, styles: document.querySelectorAll('style').length, frames: document.querySelectorAll('iframe,frame,object,embed').length}; })()"""


def renderer_eligible(raw, vis, links, outside, browser, source):
    """SCRIPTLESS: may this Renderer report page skip the viewer? (reasons, facts). From the native declarations first (no render), then ONE read of the
    owner's JS-disabled page (screen_grid._document; no page script runs): exact plain Show.* forms, no other handler, the page's scripts bound to their
    own references (the browser resolves each src against the document's address; Source's path rule names the member) and only reviewed bytes, its
    one stylesheet the include/report.css the bundle binds, no frame, no role outside the validated set, and optional_controls' DOM-action conditions.
    Any reason: the caller keeps today's route (viewer where configured)."""
    why, facts = [], {}
    items = [(l['start'], l.get('href'), l.get('declarations') or []) for l in vis.links if l['start'] in links]
    w0, declared, targets = _declared_controls(items); why += w0
    if outside: why.append(f'{len(outside)} declared event handler(s) outside the supported link path')
    if getattr(source, 'renderer_css', None) is None: why.append('no Renderer bundle binding')
    if why: return why, dict(facts, stage='declarations')
    page, address, _ = sg._document(browser, raw, raw, source)
    try:
        dom = page.evaluate(RENDERER_DOM); page.evaluate("window.__sourceScope = {outside: () => false}; true"); acts = page.evaluate(CODE_ACTIONS)  # a standalone page holds only the document's own nodes
    finally: page.close()
    member = lambda url: (urllib.parse.unquote(urllib.parse.urlsplit(url).path)[len(urllib.parse.urlsplit(source.root).path):] if source.root and url.startswith(source.root) else None)
    want_js = posixpath.join(posixpath.dirname(source.path), 'Show.js'); want_css = posixpath.join(posixpath.dirname(source.path), sg.RENDERER_CSS_REF)
    srcs, inline = [u for u, _ in dom['scripts'] if u is not None], [t for u, t in dom['scripts'] if u is None]
    if [member(u) for u in srcs] != [want_js]: why.append(f'scripts by reference: {[member(u) or u for u in srcs]}, not exactly the bundle member {want_js}')
    elif hashlib.sha256(source.members.get(want_js, b'')).hexdigest() not in RENDERER_SCRIPTS: why.append(f'{want_js}: bytes not a reviewed Show.js')
    if [hashlib.sha256(t.encode()).hexdigest() for t in inline] != [RENDERER_HELPER]: why.append(f'inline scripts: {len(inline)}, not exactly the reviewed helper')
    if [member(u) for u in dom['sheets']] != [want_css]: why.append(f'stylesheets by reference: {[member(u) or u for u in dom["sheets"]]}, not exactly {want_css}')
    else:  # both, each on its own: the sheet the page APPLIES on screen, and the bytes this render actually USED for it (Source's own record: an exact member or recorded answer wins over the remap), never the URL alone
        plain = len(dom['links']) == 1 and dom['links'][0][1] == ['stylesheet'] and dom['links'][0][2] in (None, '', 'all', 'screen') and not dom['links'][0][3] and not dom['links'][0][4]  # exactly rel=stylesheet, screen media, no title, not disabled
        if not (plain and len(dom['applied']) == 1 and dom['applied'][0][0] == dom['sheets'][0] and dom['applied'][0][1] is False and dom['applied'][0][2] in ('', 'all', 'screen') and (dom['applied'][0][3] or 0) > 0):
            why.append(f"stylesheet {want_css} is not the one sheet applied on screen: links {dom['links']}, applied {dom['applied']}")  # fetched is not applied: disabled/alternate, print-only media, no rules
        from .html_route import RENDERER_CSS
        rec = source.records.get(dom['sheets'][0]) or source.records.get(want_css) or {}
        used = rec.get('status') in ('renderer-remap', 200) and rec.get('sha256') in RENDERER_CSS
        if not used: why.append(f"effective stylesheet for {want_css} is not the reviewed Renderer CSS: status {rec.get('status')}, sha256 {rec.get('sha256')}")
    if dom['frames']: why.append(f"{dom['frames']} frame/object element(s)")
    if dom.get('top') is not True: why.append('the page is not its own top window (top.Show would not be its own Show)')  # the top.Show forms are Show here only when top === window
    exact = not why  # Root 9:57 PM: every check above passed - exact bound reviewed report.css (RENDERER_CSS c564d6d0: all 22 class selectors in RENDERER_CLASSES, 0 attribute selectors) applied alone, reviewed Show.js + helper only, no other handler/frame: a class that sheet does not name styles nothing here
    roles = sorted(set(dom['classes']) & set(RENDERER_UNVALIDATED))  # <sup> admitted: screen_grid's lift records every sup BY TAG (text, raise, owner) on either route; one inside a reveal stays refused (RENDERER_REVEAL_TAGS)
    if roles: why.append(f'roles not yet validated on the script-free path: {roles}')
    toggles = []; why += _dom_action_reasons(acts, declared, targets, toggles, unknown_classes_inert=exact)  # the shared default (viewer path, late fallback) stays conservative
    return why, {'stage': 'dom', 'controls': sum(declared.values()), 'targets': len(set(targets.values())), 'toggles': len(set(toggles)), 'scripts': [member(u) or u for u in srcs] + ['inline'] * len(inline),
                 'sheets': [member(u) or u for u in dom['sheets']], 'classes': dom['classes'], '_targets': targets, '_toggles': toggles}


def renderer_controls(raw, route, child, browser, source, pre=None):
    """SCRIPTLESS: the declared Renderer controls of a script-free route decided by the existing content rule: renderer_eligible (or its earlier result
    `pre`) and optional_controls' source-reading conditions on the attempt's own typed source reading. (reasons, facts); [] -> a recorded warning."""
    if pre is None:
        from . import html_route  # no cycle: html_route never imports context
        vis = sg.Visible(raw); links, outside = html_route.declarations(vis, browser); pre = renderer_eligible(raw, vis, links, outside, browser, source)
    why, facts = list(pre[0]), {k: v for k, v in pre[1].items() if not k.startswith('_')}
    if not why:
        if child is None or child.get('status') != 'OK': why.append('the attempt has no OK typed source reading')
        else: why += _reading_reasons(raw, route, child, pre[1]['_targets'], pre[1]['_toggles'])
    return why, dict(facts, by='context.renderer_controls (script-free path)')


def _effective_sheet_reasons(rv, observed, answered):
    """EFFECTIVE STYLES (old route): every sheet the page applies on screen is reviewed bytes (an external one by its recorded response, an inline one by its
    text) AND its CURRENT rules - the browser's own cssText after any script - equal those bytes' own native parse; no @import, no adopted sheet. Missing facts are
    reported by _dom_action_reasons ('reveal profile facts unknown'). A recorded non-200 answer that applies no rules is no style."""
    r = []
    for href, _, media, _, text, rules, imports in (rv or {}).get('sheets') or []:
        if media == 'print': continue
        if href and isinstance(answered.get(href), int) and answered[href] != 200 and rules == '': continue  # e.g. the R page's own include/report.css 404 inside the viewer
        h = observed.get(href) if href else hashlib.sha256((text or '').encode()).hexdigest()
        cur = hashlib.sha256(rules.encode()).hexdigest() if isinstance(rules, str) else None
        if h not in REVIEWED_SHEETS or imports or cur not in REVIEWED_CSSOM.get(h, ()): r.append(f"stylesheet {href or '(inline)'} {(h or 'unrecorded')[:12]}: not reviewed bytes with their own unchanged rules (current rules {(cur or 'unreadable')[:12]}, imports {imports})")
    if (rv or {}).get('adopted'): r.append(f"{rv['adopted']} adopted (script-constructed) stylesheet(s): never reviewed")
    return r


def optional_controls(raw, route, records, evidence, child):
    """(why the initial-only view's declared controls stay a deficit - [] means a truthful warning instead, facts). EVERY initial render actually
    made must carry its own code inventory (Scope.code) and pass every condition on its own - no render certifies another, a missing or unknown
    inventory fails; then the route's native declarations and ids and the attempt's own typed source reading `child` (one run-to-owner rule).
    No click is claimed; unknown code, listeners or active contexts, a following-TABLE branch, an escaped or unresolved or ambiguous id, or a
    target the reading does not hold keeps the deficit."""
    why, observed = [], {u: o.get('sha256') for u, o in (evidence.get('observed') or {}).items() if o.get('status') == 200}
    answered = {u: o.get('status') for u, o in (evidence.get('observed') or {}).items()}  # every recorded status (EFFECTIVE STYLES)
    mine = [v for m in (acquisition, sg) for v in vars(m).values() if isinstance(v, str)] + [v for v in list(globals().values()) + list(OWN_SNIPPETS) if isinstance(v, str)]
    own = {hashlib.sha256(x.encode()).hexdigest() for v in mine for x in (v, INIT_WRAP[0] + v + INIT_WRAP[1])} | set(TOOLING)  # this runtime's own evaluated code, exact (as written or as its init script)
    parent = ((evidence.get('observed') or {}).get(evidence.get('parent_url')) or {}).get('body') or b''  # the recorded viewer page: its own javascript: links
    checked, mine_ins = {}, [0]  # mine_ins: objections whose subject is exactly this file's proved inserted script (a typed count, for the producer's eligibility)
    ins_h, ins_u = (evidence.get('inserted_script') or {}).get('response_sha256'), (evidence.get('inserted_script') or {}).get('href')
    proved = lambda h, url: bool(ins_u) and h == ins_h and (not url or url == ins_u)  # this file's own proof that these bytes are its one server-inserted script
    def held_ins(r, h, url, why):  # an objection made about the proved inserted bytes is counted as such; every other objection is not
        r.append(why); mine_ins[0] += 1 if h and h == ins_h and (not url or url == ins_u) else 0
    def ok(h, url=None):  # a version outside the reviewed lists admitted by its own record and this file's insertion proof (qualified_version), decided once per call
        if (h, url) not in checked: checked[(h, url)] = bool(h) and qualified_version(evidence, h, url)[0]  # reviewed bytes too: their own record and this file's proof (no grandfathering)
        return checked[(h, url)]
    toggles = []; w0, declared, targets = _declared_controls((l['tag']['byte_start'], l.get('href'), l.get('declarations') or []) for l in route.get('source_links') or [] if l.get('script_action')); why += w0
        # Show.hideAR only hides Show.LastAR, which only Show.showAR sets (pinned Show.js): it reveals nothing. Show.toggleNext: its own DOM walk (CODE_ACTIONS), below
    def one(g):  # one render's own inventory: every condition, nothing borrowed from another render
        r = []
        if g.get('frames') != 0 or g.get('contexts') != []: r.append(f"unsupported active context: {g.get('frames')} child frame(s), other targets {g.get('contexts')}")
        infra = {u for u, h in observed.items() if ok(h, u)}  # the exact identified (or qualified) bot artifacts' own recorded addresses (owner policy)
        foreign = [x for x in g.get('executed_contexts') if not (not x.get('own_frame') and x.get('creator') and all(u in infra for u in x['creator']))] if isinstance(g.get('executed_contexts'), list) else None
        if foreign != []:
            w = f"unqualified executed context(s) in this page's lifetime (a child frame not attached by the identified infrastructure, or a foreign world, gone or not): {foreign}"
            only = ins_u and isinstance(foreign, list) and all(not x.get('own_frame') and x.get('creator') and set(x['creator']) == {ins_u} and observed.get(ins_u) == ins_h for x in foreign)
            held_ins(r, ins_h if only else None, None, w)
        r += _dom_action_reasons(g.get('actions'), declared, targets, toggles)
        rv = g['actions'].get('reveal') if isinstance(g.get('actions'), dict) else None
        r += _effective_sheet_reasons(rv, observed, answered)
        for s in g.get('scripts') or []:
            url, h = s['url'], s['sha256']
            if h in KNOWN_CODE or ok(h, url or None):  # exact reviewed (or qualified) bytes; a fetched one must also be the recorded response at its own address
                if url and observed.get(url) != h: r.append(f'known code at {url} is not the recorded response')
                continue
            if url == evidence.get('parent_url') and s.get('template') == VIEWER_TEMPLATE: continue
            if s.get('text') is not None and (s['text'] in declared or s['text'] in VIEWER_ATTRIBUTES): continue  # an attribute handler; its node is checked below
            if not url and h in own: continue  # this runtime's own instrumentation (its module code, inline evaluations, the pinned Playwright's)
            if not url and VIEWER_NAVIGATION.fullmatch(s.get('text') or '') and b'href="javascript:' + s['text'].encode() + b'"' in parent: continue  # the selection's click on a recorded viewer menu link: the template's loadReport(n) only, never arbitrary link code
            held_ins(r, h, url, f"unknown executable code: {url or '(no url)'} {h[:12]} ({s['bytes']} bytes)")
        for l in g.get('listeners') or []:
            s, rel = l.get('script') or {}, l.get('relation')
            if not isinstance(rel, dict) or rel.get('outside') is None: r.append(f"listener {l['type']}: node scope unknown"); continue
            if l.get('window') or rel.get('ancestor'):  # the window, the document or a container of source content (checked first: the document is in no snapshot)
                if not (ok(s.get('sha256'), s.get('url') or None) or (not s.get('url') and s.get('sha256') in TOOLING) or (l['type'] in LIFECYCLE and (s.get('template') == VIEWER_TEMPLATE or s.get('sha256') in KNOWN_CODE))):
                    held_ins(r, s.get('sha256'), s.get('url') or None, f"listener {l['type']} on an ancestor of source content from {s.get('url') or '(no url)'} {(s.get('sha256') or '')[:12]}")
            elif rel['outside'] is False:  # a source node: only its own declared renderer action
                if not (s.get('text') in declared and s.get('text') in (rel.get('attributes') or [])): r.append(f"listener {l['type']} on a source node is not its own declared action")
            elif not (s.get('sha256') in KNOWN_CODE or s.get('text') in VIEWER_ATTRIBUTES):  # the viewer's own controls (its menu): known code only
                r.append(f"listener {l['type']} on a viewer node from unknown code")
        return r
    if not records: why.append('no initial render was recorded')
    done = []
    for i, rec in enumerate(records):
        g = rec.get('code')
        if not isinstance(g, dict): why.append(f'render {i}: no code inventory'); continue
        if 'unknown' in g: why.append(f"render {i}: code inventory unknown: {g['unknown']}"); continue
        why += [f'render {i}: {w}' for w in one(g)]; done.append(g)
    page_code = lambda g: sorted((s['url'], s['sha256']) for s in g.get('scripts') or [] if s['url'] or s['sha256'] not in own)  # this runtime's own code runs once per its own call
    if len({json.dumps(page_code(g)) for g in done}) > 1: why.append('the initial renders disagree on the executable code')  # in addition to each render's own pass
    sr = (route.get('facts') or {}).get('source_reading') or {}
    if not (sr.get('made') is True and sr.get('status') == 'OK' and child is not None and child.get('status') == 'OK'):
        why.append('the attempt has no OK typed source reading')
    else: why += _reading_reasons(raw, route, child, targets, toggles)
    facts = {'controls': sum(declared.values()), 'targets': len(set(targets.values())), 'renders': len(records), 'renders_inventoried': len(done),
             'scripts': [len(g.get('scripts') or []) for g in done], 'listeners': [len(g.get('listeners') or []) for g in done],
             'infrastructure': sorted({INFRASTRUCTURE[s['sha256']] for g in done for s in g.get('scripts') or [] if s['sha256'] in INFRASTRUCTURE}),
             'inventory_seconds': [g.get('seconds') for g in done], 'qualified_versions': sorted({h for (h, _), v in checked.items() if v}),
             'inserted_version_objections': mine_ins[0], 'other_objections': len(why) - mine_ins[0]}  # typed: held only by the proved inserted bytes iff other_objections == 0 < inserted_version_objections
    return why, facts


def contextual_routes(raw, file_id, sha256, browser, source, evidence, parse=None, prepare=None, max_states=32, max_transitions=128, explore=True, viewer_start=None):
    """The initial route, then each source-owned action once (finite): a trial render first; only an action that proves a useful state (an outer reveal
    of one proved target, or an in-place change inside it, or the same control reopening it) gets full per-state extraction. Every trial keeps its
    whole native record. Each acting link record of the initial route carries labelled activations: complete or not with reasons, or `refused` (no state
    built) with the trial's reasons; ordinary links keep their href and attempted outcome. Participants and coverage use the one ownership rule
    (`edgartools_html._holders`); `coverage_across_states` counts a target run as shown only where a state route whose text is proved (`text_proof`) holds every visible character
    of it and its verdict is neither hidden nor unbound; unknowns stay listed. `prepare(route, source, label)` adds a caller's per-state step;
    `parse(label)` gives the tool call per state. `explore=False`: the initial view only - no source control is tried and no state is built (the
    ceilings above bound only each proved target's own graph, never the outer trials); each declared scripted action stays unresolved (PARTIAL)."""
    if not isinstance(explore, bool): raise TypeError(f'explore must be True or False, not {explore!r}')  # never a silently different path
    from . import html_route
    vis0 = sg.Visible(raw); runs0, _ = sg.symbol_runs(raw, vis0)
    def one(ctx):
        src = state_source(source, evidence, ctx)
        route, facts = html_route.prepare(raw, file_id, sha256, browser, src, **({} if parse is None else {'parse': parse(ctx.label)})); route['facts'] = facts
        if prepare: prepare(route, src, ctx.label)  # the caller's per-state step; its renders are gated by the same state gate there
        g = ctx.gate()
        if route.get('text_proved') is True and g:  # a later render failed the state gate: the prepare-time proof no longer holds
            if len(ctx.diagnostics()) == len(g): route['diagnostic'] = {'text_proved_before_gate': True, 'gate': g}  # QUALIFICATION-ONLY: the native proof kept apart; status stays diagnostic
            route['text_proved'] = False
        observed_controls(raw, route, ctx)
        return route, src
    def trial(controls, label):  # one unmarked render: the whole native record, or why it was refused
        t = Context(evidence, control=controls, label=label, viewer_start=viewer_start); why = None
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
    start = Context(evidence, viewer_start=viewer_start); start.inventory = not explore; initial, src0 = one(start)  # the initial view: its reference is the 'back to the start' identity; its code inventory only where optional_controls needs it
    viewer_start = json.loads(start.viewer_start) if start.viewer_start is not None else None
    out = {'initial': initial, 'states': [], 'trials': [], 'trial_captures': {}}  # trial captures: the caller keeps them once by digest
    unknown, deficits = [], []  # refused source-owned actions (ordinary navigation excepted); the document's required deficits
    for l in vis0.links:  # every source link record shown in the initial reading, once; one hidden there is reachable only inside a revealed target
        if l['hidden']: out['trials'].append({'label': None, 'controls': [l['start']], 'skipped': 'hidden in the initial reading'}); continue
        if not explore: out['trials'].append({'label': None, 'controls': [l['start']], 'skipped': 'not attempted: report-control exploration disabled'}); continue
        r, probe, why = trial(l['start'], f"trial@{l['start']}")
        if probe and not any(probe.values()): continue  # located, clicked, nothing happened: a no-op, no state
        if why: refused(l['start'], f"trial@{l['start']}", r, why); continue  # an attempted action that proved no target state: its record kept, no extraction
        label = f"activated@{l['start']}"; ctx = Context(evidence, control=l['start'], label=label, viewer_start=viewer_start); ctx.named_by = r.get('native') or {}; route, _ = one(ctx)  # named by its trial (none: unproved)
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
        proved = r.get('native') == ctx.reference  # its own trial and extraction agree: only then enrolled and expanded (else held by its own gate)
        seen = {k: v for k, v in ((ident(start.reference), 'initial'), (ident(r.get('native')) if proved else None, label)) if k}
        graph = {'states': [label], 'edges': [], 'noops': 0, 'refused': 0, 'transitions': 0, 'frontier': [], 'unexpanded': [] if proved else [label], 'ceilings': {'states': max_states, 'transitions': max_transitions}}
        queue = [((l['start'],), label)] if proved else []  # never a traversal from an unproved state
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
                ilabel = 'activated@' + '+'.join(map(str, seq)); ictx = Context(evidence, control=seq, label=ilabel, viewer_start=viewer_start); ictx.named_by = r2.get('native') or {}; iroute, _ = one(ictx)
                out['states'].append({'label': ilabel, 'control': list(seq), 'route': iroute, 'records': ictx.records}); attach(c, activation(ictx, iroute, ilabel, act['target'])); family.append((ilabel, iroute, ictx))
                ok = r2.get('native') == ictx.reference  # enrolled and expanded only when its own trial and extraction agree (else held by its gate, never an edge target)
                if key and ok: seen[key] = ilabel
                graph['states'].append(ilabel); graph['edges'].append({'from': at, 'control': c, 'to': ilabel, 'kind': 'new state', 'trial': tl, 'lineage': lineage(r2)})
                if ok: queue.append((seq, ilabel))
                else: graph['unexpanded'].append(ilabel)
        act['state_graph'] = graph
        if graph['frontier']: act['status'] = 'incomplete'; act['reasons'] = act['reasons'] + [f"state graph: {len(graph['frontier'])} transition(s) left unexplored at the ceiling"]
        target_runs = [(chars[0][0], chars[-1][1]) for _, chars, _, ok in runs0 if ok and x0 <= chars[0][0] and chars[-1][1] <= x1 and sg._glyphs(raw, chars)[1]]  # white space only: nothing to show
        def shown(rt, cx, a, b):  # affirmative: an OK state route holds every visible character of the run, and its verdict is neither hidden nor unbound there
            if text_proof(rt, cx) or (rt.get('page_visibility') or {}).get('unproven'): return False  # the state's gate and text proof, read now
            pv = rt.get('page_visibility') or {}
            if any(h0 <= a and b <= h1 for k in ('hidden', 'unbound') for h0, h1 in (pv.get(k) or [])): return False
            _, m, u = edgartools_html._holders(rt['units'], anchor.Visible(raw, page=rt.get('page_visibility')) if rt.get('page_visibility') else anchor.Visible(raw))[0](a, b)
            return m > 0 and u == 0
        labels = {s_ for _, _, cx in family for s_ in cx.label_spans(raw)}
        never = [list(rn) for rn in target_runs if not any(a <= rn[0] and rn[1] <= b for a, b in labels) and not any(shown(rt, cx, *rn) for _, rt, cx in family)]
        act['coverage_across_states'] = {'states': [lb for lb, _, _ in family], 'target_runs': len(target_runs), 'never_affirmatively_shown_runs': never, 'observed_control_label_runs': sorted(labels)}
        if never: deficits.append(f"{label}: {len(never)} target run(s) never affirmatively shown in any observed state (coverage_across_states)")
        if graph['frontier']: deficits.append(f"{label}: {len(graph['frontier'])} transition(s) left unexplored at the state ceiling")
    if not explore:  # a context route's declared actions count as qualified only by their activations (html_route): none was attempted, each stays unresolved
        scripted = sum(1 for r in initial.get('source_links') or [] if r.get('script_action'))
        if scripted:  # optional report controls: a warning only where optional_controls proves every one reveals content the source reading holds
            why, facts = optional_controls(raw, initial, start.records, evidence, getattr(src0, 'source_reading_route', None))
            initial['facts']['optional_controls'] = dict(facts, reasons=why, outcome='deficit kept' if why else
                                                         f'warning: {scripted} declared report control(s) not opened (initial view only); each in-page target is held by the source reading')
            if why: deficits.append(f'{scripted} declared script action(s) not attempted (report-control exploration disabled)')
        elif skipped := sum(1 for l in vis0.links if not l['hidden']):  # no inline declaration is no proof of no action (a parent/delegated listener): each skipped visible link stays unresolved
            deficits.append(f'{skipped} visible source link(s) not attempted, action unresolved (report-control exploration disabled)')
    reached = {c for t in out['trials'] for c in t.get('controls', [])[1:]}
    out['unreached_links'] = [l['start'] for l in vis0.links if l['hidden'] and l['start'] not in reached]  # hidden, and inside no proved target: no observed state reaches them
    deficits += [f'{tl}: source-owned action refused, its state unknown (CONTEXT_TRIALS)' for tl in unknown]
    if deficits:  # the existing route-status policy (the caller's render gate uses the same form): automatic output incomplete, reasons listed
        initial['status'] = 'PARTIAL'; initial['error'] = '; '.join(filter(None, [initial.get('error')] + ['context: ' + d for d in deficits]))
    return out
