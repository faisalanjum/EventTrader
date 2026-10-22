"""Context selection (OCR's reviewed module, in the runtime; Fable owns this copy). Downloading is not here: Campaign does it (get/context_acquire.py).
  index_parent_candidates: native lxml iterlinks over the filing's OWN official index page; a candidate is an official https://www.sec.gov link that names
    this filing (accession, dashed or not) and is not a file of the filing's own Archives directory. No label, no guessed path.
  quiet_settle / count_requests: the one settle rule (500 ms, nothing in flight, no new mutation, within the bound), shared with convert.context.
  Every observation also takes the ONE runtime native-state read (screen_grid.native_state: document + full-page capture digest + environment), part
    of the canonical equality; a capture failure fails that reading, never retried (OCR's v9 change, applied here).
  Selection: automatic source-anchor selection on recorded responses (parent as observed, target as its verified measurement body via MeasuredSource):
    target GET after the action only, verified body, no non-GET, no navigation, no page error, settled, inclusion, clean no-action baseline, ambiguity;
    the canonical-state rule (one fixed unmarked reference, at most 3 observations per reading). NativeSelection: controls of the recorded native parent
    state (NODES key: path, tag chain, outerHTML sha256, plus that state's received inputs), never raw-source anchors.
  Prototypes cut from the runtime (no callers): the Recorder downloader, acquire_parent, QUIET, render_neutral and the test-only extra_init hook; they
    stay in ocr_handoff/ as first-attempt evidence."""
import time, re
from urllib.parse import urlsplit, unquote
import lxml.html
import hashlib
from driver.prepare.get.acquire import AcquisitionError
from driver.prepare.convert.overlay import MeasuredSource  # the runtime's own overlay owner (no copied measure module)
sha = lambda b: hashlib.sha256(b).hexdigest()
from driver.prepare.convert import screen_grid as sg

OFFICIAL = 'www.sec.gov'

def index_parent_candidates(index_html, index_url, accession):
    root = lxml.html.fromstring(index_html, base_url=index_url); root.make_links_absolute(index_url, resolve_base_href=True)
    own_dir = re.compile(r'/Archives/edgar/data/[0-9]+/' + accession.replace('-', '') + r'(/|$)')
    out, seen = [], {'kept': 0, 'filing_files': 0, 'other_filing_or_none': 0, 'not_official': 0}
    for el, attr, link, _ in root.iterlinks():
        if el.tag != 'a' or attr != 'href': continue
        s = urlsplit(link)
        if s.scheme != 'https' or s.netloc != OFFICIAL: seen['not_official'] += 1; continue
        if own_dir.match(s.path) and not s.query: seen['filing_files'] += 1; continue
        text = unquote(s.path + '?' + s.query)
        if accession not in text and accession.replace('-', '') not in text: seen['other_filing_or_none'] += 1; continue
        seen['kept'] += 1
        if link not in out: out.append(link)
    return out, seen

def quiet_settle(page, box, seconds):
    """The one bounded-snapshot settle rule: settled only after 500 ms with zero in-flight requests (`box[0]`, kept by the page's native request /
    requestfinished / requestfailed events) and no new MutationObserver record (window.__m), within `seconds`; else False. Never a quiescence claim."""
    end = time.time() + seconds; since, last = None, None
    while time.time() < end:
        m = page.evaluate('() => window.__m')
        if box[0] == 0 and m == last:
            since = since or time.time()
            if time.time() - since >= 0.5: return True
        else: since = None
        last = m; page.wait_for_timeout(50)
    return False

def count_requests(page):  # the in-flight counter quiet_settle reads
    box = [0]; page.on('request', lambda q: box.__setitem__(0, box[0] + 1)); page.on('requestfinished', lambda q: box.__setitem__(0, box[0] - 1)); page.on('requestfailed', lambda q: box.__setitem__(0, box[0] - 1)); return box

LOCATE = """([hrefs, i]) => { const as = Array.from(document.getElementsByTagName('a')).filter(a => a.hasAttribute('href'));
  if (as.length !== hrefs.length || as.some((a, k) => a.getAttribute('href') !== hrefs[k])) return null; return as[i]; }"""
SER = """(p) => { const c = document.documentElement.cloneNode(true), w = document.createTreeWalker(c, NodeFilter.SHOW_COMMENT), drop = []; let n;
  while ((n = w.nextNode())) if (n.nodeValue.startsWith(p)) drop.push(n); drop.forEach(x => x.remove()); return [c.outerHTML, window.__m]; }"""
INIT = "window.__m = 0; new MutationObserver(l => { window.__m += l.length; }).observe(document, {subtree: true, childList: true, characterData: true, attributes: true});"
READ = """(p) => { const re = new RegExp('^' + p + 's:([0-9]+)$'), w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT), marks = []; let n;
  while ((n = w.nextNode())) { const m = re.exec(n.nodeValue); if (m) { let t = n.nextSibling; while (t && t.nodeType === 8 && t.nodeValue.startsWith(p)) t = t.nextSibling; marks.push({n, run: +m[1], text: t && t.nodeType === 3 ? t.nodeValue : null}); } }
  let lca = null; if (marks.length) { lca = marks[0].n.parentNode; while (lca && !marks.every(x => lca.contains(x.n))) lca = lca.parentNode; }
  const el = lca && (lca.nodeType === 1 ? lca : lca.parentElement);
  return {marks: marks.map(x => [x.run, x.text]), shown: el ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) : null, url: location.href}; }"""

def facts(rec):
    """The state's received facts (Smart CONTEXT_REAL_SELECTION_DECISION sec. 1): delivered inputs {(url/member, status, observation sha256)} and refused
    GET dependencies {(url/member, kind)} from the Source's own records; outbound refused non-GET attempts as (method, url, count), recorded, not compared."""
    recs = rec['source'].records.values(); from collections import Counter
    delivered = sorted({(r.get('url') or r.get('member') or r.get('path'), r['status'], r.get('sha256')) for r in recs if r.get('status') != 'refused'}, key=str)
    refused = sorted({(r.get('url') or r.get('path'), r.get('kind')) for r in recs if r.get('status') == 'refused' and r.get('kind') != 'navigation'}, key=str)
    out = sorted(Counter((x[0], x[1]) for x in rec['log'] if x[0] != 'GET').items())
    navigations = sorted({u for u, k in rec['source'].refusals if k == 'navigation'})  # every navigation the Source refused, each time (a refused reload of an answered URL too): unknown, never absence
    return {'delivered': delivered, 'refused_get': refused, 'outbound_attempts_refused': [(m, u, c) for (m, u), c in out], 'refused_navigation': navigations}

def _same_inputs(a, b):  # marked vs unmarked: equal delivered inputs (observation identities) and equal refused GET sets; outbound counts excluded
    return a is not None and b is not None and a['delivered'] == b['delivered'] and a['refused_get'] == b['refused_get']

class Selection:
    """One parent (observed, immutable) and one target (member + the caller's marked body + its measurement body)."""
    def __init__(self, parent_url, observed, target_url, member, measured_body, prefix, settle_s=3.0, offline=False):
        self.offline = offline; self.parent_url, self.observed, self.target, self.member, self.body, self.prefix, self.settle_s = parent_url, observed, target_url, member, measured_body, prefix, settle_s
        vis = sg.Visible(member); self.runs = sg.symbol_runs(member, vis)[0]; self.expect = [k for k, r in enumerate(self.runs) if r[3]]
        self.hrefs = [l['href'] for l in sg.Visible(observed[parent_url]['body']).links]
    def _settle(self, page):
        return quiet_settle(page, self._inflight.get(id(page), [0]), self.settle_s)
    def _page(self, browser, marked, rec):
        src = MeasuredSource('target', {}, observed=self.observed, measured={self.target: self.body} if marked else {}, prefix=self.prefix); rec['source'] = src
        ctx = browser.new_context(viewport={'width': 1200, 'height': 850}, service_workers='block', offline=self.offline); ctx.add_init_script(INIT); page = None
        def answer(route):
            q = route.request; rec['log'].append((q.method, q.url, q.is_navigation_request()))
            if q.method != 'GET': return route.abort('failed')
            if q.url == self.parent_url and q.is_navigation_request() and page is not None and q.frame == page.main_frame and not rec.get('loaded'):
                rec['loaded'] = True; got = src.observation(self.parent_url, 'document')  # the parent by the Source's own rule (checked before navigation)
                return route.fulfill(status=got[0], content_type=self.observed[self.parent_url].get('content_type') or 'text/html', body=got[2]) if got else route.abort('failed')
            got = src.answer(q.url, q.resource_type, q.is_navigation_request())
            return route.fulfill(status=got[0], content_type=got[1], body=got[2]) if got else route.abort('aborted')
        rec['pages'] = []; ctx.route('**/*', answer); ctx.on('page', lambda p: rec['pages'].append(p.url))  # context boundary: popups/new windows answered by the same rule, and counted
        page = ctx.new_page(); page.on('pageerror', lambda e: rec['errors'].append(str(e)))
        self._inflight = getattr(self, '_inflight', {}); self._inflight[id(page)] = count_requests(page)
        if src.observation(self.parent_url, 'document') is None:  # a parent whose recorded bytes are not its recorded identity: a failure, never retried
            ctx.close(); raise AcquisitionError('parent response refused by the source rule: ' + str((src.records.get(self.parent_url) or {}).get('why')))
        page.goto(self.parent_url, wait_until='load'); rec['initial_settled'] = self._settle(page); return ctx, page
    def _included(self, got):
        why = []
        if [m[0] for m in got['marks']] != self.expect: why.append(f"{len(got['marks'])} run marks found, {len(self.expect)} expected once in order")
        elif any(t is None or not sg._bound(sg._glyphs(self.member, self.runs[N][1])[1], t) for N, t in got['marks']): why.append('run text not bound to source glyphs')
        if got['shown'] is not True: why.append("marks' common ancestor not shown")
        if got['url'] != self.parent_url: why.append('top URL changed')
        return why
    def count(self): return len(self.hrefs)
    def _locate(self, page, i, rec=None):  # source anchors: native source-order correspondence
        h = page.evaluate_handle(LOCATE, [self.hrefs, i]).as_element()
        return (h, None) if h is not None else (None, 'document anchors do not correspond to the source anchors')
    def act(self, browser, i, marked=True):
        from playwright.sync_api import Error as PlaywrightError  # the pinned library's public typed error (TimeoutError and TargetClosedError are subclasses)
        rec = {'log': [], 'errors': []}; ctx, page = self._page(browser, marked, rec); a = {'source_anchor': i, 'action': 'programmatic HTMLElement.click() (untrusted)', 'marked': marked}
        step, pre, mark = 'locate', None, None  # how far this observation got; the facts read just before the click
        try:
            if not rec['initial_settled']: a['state'] = 'refused: initial state not settled'; a['pre_action_facts'] = facts(rec); return a  # no action ran: an initial reading
            h, why_loc = self._locate(page, i, rec)
            if h is None: a['state'] = 'refused: ' + why_loc; a['pre_action_facts'] = facts(rec); return a  # no action ran: an initial reading
            step = 'pre-action reading'; a['control_shown'] = h.evaluate('e => e.checkVisibility()'); m0 = page.evaluate('() => window.__m'); mark, e0 = len(rec['log']), len(rec['errors'])
            self.pre_refused = getattr(self, 'pre_refused', {}); pre = facts(rec); self.pre_refused[marked] = pre['refused_get']
            step = 'click'; h.evaluate('e => e.click()'); step = 'settle'; settled = self._settle(page); step = 'after-action reading'; after = rec['log'][mark:]; errs = rec['errors'][e0:]; why = []
            hit = rec['source'].records.get(self.target)
            if not any(r[1] == self.target and r[0] == 'GET' and not r[2] for r in after): why.append('target not requested by GET after the action')
            elif marked and (not hit or hit.get('status') != 200 or hit.get('measured_sha256') != sha(self.body)): why.append('target not served its verified measurement body')
            if any(r[1] == self.target for r in rec['log'][:mark]): why.append('target requested before the action')
            if any(r[2] for r in after): why.append('navigation attempted (refused)')
            if errs: why.append(f'{len(errs)} page error(s)')
            if not settled: why.append('not settled within budget')
            if len(rec['pages']) > 1: why.append(f"{len(rec['pages']) - 1} new window(s) opened (answered/refused by the context rule, recorded)")
            f = facts(rec); new_refused = [x for x in f['refused_get'] if x not in self.pre_refused.get(marked, [])] if hasattr(self, 'pre_refused') else []
            if new_refused: why.append(f'{len(new_refused)} refused GET dependency(ies) first requested by the action (unresolved)')
            if marked and not why: why = self._included(page.evaluate(READ, self.prefix))
            doc, m1 = page.evaluate(SER, self.prefix)
            try: native = sg.native_state(page, self.prefix, blobs=self.blobs)[0]
            except sg.CaptureError as e: native = None; why = ['native capture refused: %s' % e]; a['capture_failed'] = True
            a.update(state='qualified' if not why else 'refused: ' + '; '.join(why), requests=after, doc=doc, facts=f, pre_action_facts=pre, native=native, mutations_before_action=m0, mutations_after_action=m1 - m0,
                     blocked_non_get_after_action=[r[:2] for r in after if r[0] != 'GET'], refused_by_source=sorted(k for k, v in rec['source'].records.items() if v.get('status') == 'refused'), extra_pages=len(rec['pages']) - 1)
            return a
        except PlaywrightError as e:  # ONE typed boundary for the whole action observation (Root CONTEXT_ACTION_OBSERVATION_REPAIR_20261022T0535): recorded, never qualified/missing/no-op
            if page.is_closed() or not browser.is_connected(): raise  # page, context or browser loss stays fatal (native state, no class or message list)
            a.update(state='failed: browser observation during ' + step, error={'type': type(e).__module__ + '.' + type(e).__qualname__, 'name': e.name, 'message': e.message, 'stack': e.stack},
                     pre_action_facts=pre if pre is not None else facts(rec), requests=rec['log'], errors=rec['errors'], extra_pages=len(rec['pages']) - 1)  # only observed values
            if pre is not None: a.update(facts=facts(rec), requests_after_action=rec['log'][mark:])  # after-action facts kept apart from the pre-action reading
            return a
        finally: ctx.close()
    attempts_per_reading = 3  # Root CONTEXT_CANONICAL_STATE_DECISION: at most 3 observation attempts per logical reading
    blobs = None  # existing content-addressed store for native captures (archive.store_blob), set by the caller; None keeps digests only

    def _canonical(self, observe, marked_first=None):
        """Canonical-state rule: the first settled, error-free UNMARKED observation is the one fixed reference of this logical reading; up to
        attempts_per_reading MARKED observations are compared with that same state (whole native serialization + received inputs); the first equal one
        that also passes the reading's own checks is used. Every attempt is kept with its identity and outcome; unmatched attempts give no readings;
        exhaustion = incomplete; a fatal observation (corrupt/unverified response, browser failure) = failed, never retried. `marked_first`: an
        already-made first marked observation (counts as attempt 1)."""
        n, log, ref = self.attempts_per_reading, [], None
        def ident(o): return {'native': o.get('native'), 'settled': o.get('settled'), 'doc_sha256': sha(o['doc'].encode()) if o.get('doc') is not None else None, 'delivered': len((o.get('facts') or {}).get('delivered', [])), 'refused_get': (o.get('facts') or {}).get('refused_get'), 'outbound': (o.get('facts') or {}).get('outbound_attempts_refused'), 'why': o.get('why'),
                              **({'failed_attempt': o['failed_attempt']} if o.get('failed_attempt') else {}),  # a failed repeat's whole raw record stays in the reading's log
                              **{k: o[k] for k in ('facts', 'pre_action_facts') if o.get(k) is not None}}  # every reading's own received/refused facts, only when observed (Root 0558)
        for k in range(n):
            o = observe(False); e = dict(ident(o), attempt=k, marked=False)
            if o.get('fatal'): log.append(dict(e, outcome='fatal: ' + o['fatal'])); return {'state': 'failed: ' + o['fatal'], 'attempts': log}
            if o.get('settled') and not o.get('errors') and o.get('doc') is not None: ref = o; log.append(dict(e, outcome='reference')); break
            log.append(dict(e, outcome='not a reference'))
        if ref is None: return {'state': 'incomplete: no settled unmarked reference within %d attempts' % n, 'attempts': log}
        for k in range(n):
            o = marked_first if (k == 0 and marked_first is not None) else observe(True); e = dict(ident(o), attempt=k, marked=True)
            if o.get('fatal'): log.append(dict(e, outcome='fatal: ' + o['fatal'])); return {'state': 'failed: ' + o['fatal'], 'attempts': log}
            same = bool(o.get('settled')) and o.get('doc') == ref['doc'] and o.get('native') == ref.get('native') and _same_inputs(o.get('facts'), ref.get('facts'))
            if same and not o.get('why'): log.append(dict(e, matches_reference=True, outcome='used')); return {'state': 'qualified', 'used': o, 'reference': ref, 'attempts': log}
            log.append(dict(e, matches_reference=same, outcome='not used'))
            if same: return {'state': 'refused: ' + '; '.join(o['why']), 'attempts': log}  # the reference state itself fails the reading's checks: deterministic, not retried
        return {'state': 'incomplete: no marked attempt matched the reference within %d attempts' % n, 'attempts': log}

    def _observe_view(self, browser, marked, action=None, checks=False):
        """One native observation of the initial (action None) or an activated view; `checks`: the initial-state reading checks on a marked view."""
        rec = {'log': [], 'errors': []}; ctx, page = self._page(browser, marked, rec); o = {}
        try:
            o['settled'] = self._settle(page)
            if action is not None:
                h, why = self._locate(page, action, rec)
                if h is None: return {'settled': False, 'doc': None, 'why': [why], 'errors': rec['errors']}
                h.evaluate('e => e.click()'); o['settled'] = self._settle(page)
            o['doc'], o['mutations'] = page.evaluate(SER, self.prefix); f = facts(rec); hit = rec['source'].records.get(self.target) or {}
            try: o['native'] = sg.native_state(page, self.prefix, blobs=self.blobs)[0]
            except sg.CaptureError as e: o['native'] = None; o['fatal'] = 'native capture refused: %s' % e
            o.update(facts=f, errors=rec['errors'], requests=rec['log'], blocked_non_get=[r[:2] for r in rec['log'] if r[0] != 'GET'], why=[])
            if marked and hit.get('status') == 'refused': o['fatal'] = 'target response not verified (%s)' % hit.get('why')
            elif marked and hit and hit.get('measured_sha256') != sha(self.body): o['fatal'] = 'target not served the reading body'
            if marked and checks:
                if not hit: o['why'].append('target not requested')
                else: o['why'] += self._included(page.evaluate(READ, self.prefix))
                if f['refused_get']: o['why'].append(f"{len(f['refused_get'])} refused GET dependency(ies) in the state (unresolved)")
                o['dom_anchors'] = page.evaluate("() => Array.from(document.getElementsByTagName('a')).filter(a => a.hasAttribute('href')).length")
            if rec['errors']: o['why'].append(f"{len(rec['errors'])} page error(s)")
            if not o['settled']: o['why'].append('not settled within the bound')
            return o
        finally: ctx.close()

    def initial(self, browser):
        """Initial-state qualification under the canonical-state rule: verified target body, inclusion/shown, no refused GET dependency, and equality
        with the one fixed unmarked reference state."""
        c = self._canonical(lambda m: self._observe_view(browser, m, None, checks=True)); u, r = c.get('used') or {}, c.get('reference') or {}
        self.initial_result = {'state': c['state'], 'neutral': c['state'] == 'qualified', 'attempts': c['attempts'], 'facts': {True: u.get('facts'), False: r.get('facts')},
                               'blocked_non_get': u.get('blocked_non_get'), 'mutations': u.get('mutations'), 'dom_anchors': u.get('dom_anchors'), 'source_anchors': len(self.hrefs), 'requests': len(u.get('requests') or [])}
        return self.initial_result
    def run(self, browser):
        rec = {'log': [], 'errors': []}; ctx, page = self._page(browser, True, rec); time.sleep(self.settle_s); self._settle(page); post = page.evaluate(READ, self.prefix); ctx.close()
        baseline = {'target_requested': any(r[1] == self.target for r in rec['log']), 'marks': len(post['marks']), 'errors': rec['errors'], 'blocked_non_get': [r[:2] for r in rec['log'] if r[0] != 'GET'], 'extra_pages': len(rec['pages']) - 1, 'facts': facts(rec)}  # the marked load before any action
        if baseline['target_requested'] and not baseline['errors']:  # the target is the parent's own initial selection: qualify that state, no action
            return {'source_anchors': len(self.hrefs), 'baseline': baseline, 'initial': self.initial(browser), 'attempts': [], 'actions': 'not attempted: the target is the initial selection',
                    'verdict': None} | (lambda i: {'verdict': 'initial' if i['state'] == 'qualified' else ('incomplete: initial reading ' + i['state']) if i['state'].startswith(('failed', 'incomplete')) else 'missing'})(self.initial_result)
        attempts = []
        for i in range(self.count()):
            a = self.act(browser, i, True)
            if a['state'] == 'qualified':  # canonical rule for the used reading of this action (the first marked act counts as attempt 1)
                def obs(m, i=i):
                    x = self.act(browser, i, m); return {'settled': None if 'error' in x else 'not settled' not in x['state'], 'doc': x.get('doc'), 'facts': x.get('facts'), 'pre_action_facts': x.get('pre_action_facts'), 'errors': x.get('errors'), 'native': x.get('native'),
                                                       'why': [] if x['state'] == 'qualified' or not m else [x['state']], **({'fatal': x['state']} if x.get('capture_failed') else {}),
                                                       **({'fatal': x['state'].removeprefix('failed: '), 'failed_attempt': x} if 'error' in x else {})}  # a failed repeat stops this reading: never a reference, never retried
                first = {'settled': True, 'doc': a.get('doc'), 'facts': a.get('facts'), 'pre_action_facts': a.get('pre_action_facts'), 'errors': a.get('errors'), 'native': a.get('native'), 'why': []}
                c = self._canonical(obs, marked_first=first); a['canonical'] = {'state': c['state'], 'attempts': c['attempts']}; a['neutral'] = c['state'] == 'qualified'
                if not a['neutral']: a['state'] = c['state'] if c['state'].startswith(('incomplete', 'failed')) else 'refused: ' + c['state']
            attempts.append(a)
        for a in attempts: a.pop('doc', None)
        ok = [a for a in attempts if a['state'] == 'qualified']; clean = not baseline['target_requested'] and not baseline['marks'] and not baseline['errors']
        open_ = [a for a in attempts if a['state'].startswith(('failed', 'incomplete'))]  # undecided attempts: never 'missing' (one known qualified action still selects; two stay ambiguous)
        return {'source_anchors': len(self.hrefs), 'baseline': baseline, 'attempts': attempts,
                'verdict': ('selected' if len(ok) == 1 else 'ambiguous' if ok else 'incomplete: %d action observation(s) not decided' % len(open_) if open_ else 'missing') if clean else 'baseline_not_clean'}


NODES = """() => { const path = el => { const p = []; for (let n = el; n && n !== document.documentElement; n = n.parentElement) p.unshift(Array.prototype.indexOf.call(n.parentElement.children, n)); return p; };
  const tags = el => { const t = []; for (let n = el; n && n !== document.documentElement; n = n.parentElement) t.unshift(n.localName); return t.join('>'); };
  return Array.from(document.getElementsByTagName('a')).filter(a => a.hasAttribute('href')).map(a => [path(a), tags(a), a.outerHTML]); }"""
RESOLVE = "(path) => { let n = document.documentElement; for (const i of path) { n = n ? n.children[i] : null; } return n || null; }"

class NativeSelection(Selection):
    """Controls of the recorded authoritative native parent state (scripts ran; menus may be script-built): each identified by that state's whole native
    serialization sha256 (our prefix comments removed) and the node's tree path and outerHTML sha256. Correspondence is proved afresh at every replay:
    the replayed state must serialize identically before the action and the node at the path must have the recorded outerHTML; otherwise refused.
    Not a raw-source anchor claim. Call prepare(browser) once (an unmarked load), then run(browser) as Selection."""
    def prepare(self, browser):
        rec = {'log': [], 'errors': []}; ctx, page = self._page(browser, False, rec)
        try:
            self._settle(page); doc, _ = page.evaluate(SER, self.prefix); self.state_sha = sha(doc.encode())
            self.nodes = [(p, t, sha(h.encode())) for p, t, h in page.evaluate(NODES)]; self.state_facts = facts(rec)
            self.state_record = {'state_sha256': self.state_sha, 'native_anchors': len(self.nodes), 'requests': rec['log'], 'errors': rec['errors'], 'facts': self.state_facts}
        finally: ctx.close()
        return self.state_record
    def count(self): return len(self.nodes)
    def _locate(self, page, i, rec=None):
        if rec is not None and not _same_inputs(facts(rec), self.state_facts): return None, 'replayed state received different inputs than the recorded state'
        p, t, want = self.nodes[i]; now = [(q, u, sha(h.encode())) for q, u, h in page.evaluate(NODES)]
        hits = [q for q, u, w in now if (u, w) == (t, want)]
        if len(hits) != 1: return None, ('recorded native node key matches %d nodes in the replayed state' % len(hits)) + (' (ambiguous)' if len(hits) > 1 else '')
        if hits[0] != p: return None, 'recorded native node found at another path'
        return page.evaluate_handle(RESOLVE, p).as_element(), None
