"""Generic context acquisition (OCR handoff v2, after Root's CONTEXT_ACQUISITION_ROOT_REVIEW; v1 retained as context_acquire_v1_retained.py).
Inputs: a Campaign (proposed `declared_by`; existing cache, receipts, pacing, failures, 403 STOP), a browser, the VERIFIED package version directory
(acquire.read_package: manifest + members with their recorded proofs - no reparse), the member filename, the caller's own marked render body + prefix.
Addresses exactly as existing code derives them (index: full_run line 67; member: acquire line 242); the envelope by the one shared framing helper
(acquire.document_parts, proposed: the existing <DOCUMENT> rule hoisted, persisted manifest unchanged); overlay from the runtime owner
(driver.prepare.convert.overlay). No issuer/filename/label/position branch.
Error policy (typed, Root CONTEXT_ACQUISITION_FAILURE_CLASS): one request = `_get`. Only an ordinary DownloadError while the Campaign is not stopped
(no stop flag, no persisted STOP.json) and the typed campaign.OfflineCacheMiss (an offline campaign's uncached URL; nothing requested) are recorded
unavailable. Every other error propagates and stops: any other AcquisitionError (wrong cached identity or size, changed blob, stopped campaign,
unsupported URL), StorageError, OSError, MemoryError, a DownloadError after a stop (e.g. HTTP 403), a closed browser. No message parsing.
Waits use the shared quiet-window rule; nothing is swallowed.
Responses (Root CONTEXT_RESPONSE_BOUNDARY_INVENTORY): the render map holds ONLY this acquisition's own Campaign.fetch results (that owner's receipt URL,
size and blob checks; a failed attempt's status from the error's receipt), never the whole campaign; the parent is served by Source.observation.
Dependencies: the parent's own unanswered official non-navigation GETs at startup AND those introduced by its observed selection actions, each fetched
once declared_by that parent, the request budget checked before EVERY request; exhaustion = incomplete with the unfinished inventory.
Scope (Root CONTEXT_MINIMAL_COMPLETENESS_DECISION, option A): 'associated' = exactly ONE known qualified official context (its own source proof,
dependency closure and selection all passed); evidence parent_url/evidence_identity name the context represented. It is NOT a claim that this is the
only presentation: other indexed candidates keep their raw verdicts, and unknown ones stay in undecided_parents (never called missing). Two or more
qualified -> 'ambiguous'; none -> 'incomplete'.
Returns {'outcome', 'evidence' (Context's contract: parent_url, target_url, observed restricted to the used state's delivered inputs + parent + target,
selection, proof, before, after) or None, 'record' (raw acquisition/selection evidence)}."""
import gzip, json
from pathlib import Path
from urllib.parse import quote, urlsplit
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from driver.prepare.get.acquire import _identity, _url, read_package, document_parts, _readings, _prove, AcquisitionError, StorageError
from driver.prepare.get.campaign import OfflineCacheMiss
from driver.prepare.get.transport import DownloadError, closes as _closes
from driver.prepare.convert import screen_grid as sg, overlay
import hashlib
sha = lambda b: hashlib.sha256(b).hexdigest()

def _get(campaign, url, declared_by, log, observed=None):
    """One request through the Campaign: bytes, or None recorded unavailable (typed offline miss; ordinary DownloadError of a running campaign);
    every other error propagates. `observed`: this acquisition's response map, filled ONLY from what Campaign.fetch returned after its own checks
    (a 200: its receipt and bytes; a failed attempt: the error's receipt status, no body)."""
    try:
        data, rec = campaign.fetch(url, declared_by) if declared_by else campaign.fetch(url)
    except OfflineCacheMiss as e:
        log.append({'url': url, 'outcome': 'unavailable offline: ' + str(e), 'declared_by': declared_by}); _failed(observed, url, e.receipt); return None
    except DownloadError as e:
        if campaign.stopped or (campaign.root / 'STOP.json').exists(): raise  # the existing stop fields: a 403 or stop is never a missing page
        log.append({'url': url, 'outcome': 'unavailable: ' + str(e), 'declared_by': declared_by}); _failed(observed, url, e.receipt); return None
    log.append({'url': url, 'outcome': 200, 'cache_hit': rec.get('cache_hit'), 'sha256': rec.get('sha256'), 'declared_by': declared_by})
    if observed is not None:
        last = rec['attempts'][-1]; observed[url] = {'status': last['status'], 'content_type': (last.get('headers') or {}).get('content-type'), 'observed_at': rec['retrieved_at'], 'sha256': rec['sha256'], 'body': data}
    return data

def _failed(observed, url, receipt):  # a failed attempt's own last status, kept raw with no body (404 = original absence); no status = no observation
    last = ((receipt or {}).get('attempts') or [{}])[-1]; status = last.get('status')
    if observed is not None and status is not None:
        observed[url] = {'status': last['status'], 'content_type': (last.get('headers') or {}).get('content-type'), 'observed_at': last['started_at'], 'sha256': None, 'body': None}

class _Fetcher:
    def __init__(self, campaign, budget): self.campaign, self.budget, self.log, self.observed = campaign, budget, [], {}  # observed: only this acquisition's own responses
    def get(self, url, declared_by=None):  # the request budget is checked before EVERY request
        if self.campaign.sent_attempts >= self.budget: self.log.append({'url': url, 'outcome': 'not requested: request budget reached', 'declared_by': declared_by}); return None
        return _get(self.campaign, url, declared_by, self.log, self.observed)

def _official_get(url): s = urlsplit(url); return s.scheme == 'https' and s.netloc == 'www.sec.gov'

def _startup_dependencies(fetch, browser, parent, settle_s=3.0):
    """Fixed point of the parent's own startup requests (offline render from this acquisition's own validated responses)."""
    from driver.prepare.get.acquisition import quiet_settle, count_requests, INIT
    rounds = []
    for _ in range(8):
        obs = dict(fetch.observed); src = sg.Source('context', {}, observed=obs); asked, first, roles = [], [True], []
        ctx = browser.new_context(service_workers='block', offline=True); ctx.add_init_script(INIT)
        def answer(route):
            q = route.request
            if first[0] and q.url == parent and q.is_navigation_request():  # the parent by the Source's own observation rule (recorded identity, verified bytes)
                first[0] = False; got = src.observation(parent, 'document')
                if not got: raise AcquisitionError('candidate parent response refused by the source rule: %s' % (src.records.get(parent) or {}).get('why'))
                return route.fulfill(status=got[0], content_type=got[1], body=got[2])
            got = src.answer(q.url, q.resource_type, q.is_navigation_request()) if q.method == 'GET' else None
            if not got: asked.append((q.method, q.url, q.resource_type, q.is_navigation_request()))
            if not got and q.is_navigation_request(): roles.append({'url': q.url, 'top_level': q.frame == page.main_frame, 'frame_name': q.frame.name})  # native frame role (request.frame)
            return route.fulfill(status=got[0], content_type=got[1], body=got[2]) if got else route.abort('aborted')
        ctx.route('**/*', answer); page = ctx.new_page(); box = count_requests(page)
        try:
            try: page.goto(parent, wait_until='load', timeout=30000); settled = quiet_settle(page, box, settle_s)
            except PlaywrightTimeout: settled = False  # only a load timeout is an observation outcome; any other browser error propagates
        finally: ctx.close()
        # an attempt is not a response; a served 3xx/retry-exhausted response is known but open: only _closes() completes a dependency
        unknown = sorted({u for m, u, k, nav in asked if m == 'GET' and not nav and not _closes(fetch.observed.get(u))}
                         | {r['url'] for r in src.records.values() if r.get('url') and r.get('status') != 'refused' and not _closes(fetch.observed.get(r['url']))})
        navigations = sorted({u for m, u, k, nav in asked if nav})  # the parent's own load is answered first; any further navigation is pending: unknown, never absence
        need = [u for u in unknown if _official_get(u) and not any(x['url'] == u for x in fetch.log)]
        rounds.append({'settled': settled, 'unanswered': sorted({(m, u, k, nav) for m, u, k, nav in asked}), 'fetching': need, 'unobserved': unknown, 'navigations': navigations, 'navigation_frames': roles})
        if not need:
            if unknown or navigations or not settled:
                return {'fixed_point': False, 'incomplete': 'pending navigation' if navigations else 'unobserved dependency' if unknown else 'not settled', 'unobserved': unknown, 'navigations': navigations, 'rounds': rounds}
            return {'fixed_point': True, 'rounds': rounds}
        for u in need:
            if fetch.get(u, {'kind': 'native_request', 'declarer': parent, 'declarer_sha256': obs[parent]['sha256'], 'phase': 'startup'}) is None and fetch.log[-1]['outcome'].startswith('not requested'):
                return {'fixed_point': False, 'incomplete': 'request budget reached', 'unfinished': [x for x in need if not any(y['url'] == x and y['outcome'] == 200 for y in fetch.log)], 'rounds': rounds}
    return {'fixed_point': False, 'incomplete': 'round bound reached', 'rounds': rounds}

def _strip(r):  # selection result without native serializations
    r = json.loads(json.dumps(r, default=str))
    for a in r.get('attempts', []): a.pop('doc', None)
    return r

def _reading_facts(r):  # (facts, initial?) of every reading a selection result carries; an action that never ran (pre_action_facts) is an initial reading
    acts = [x for a in r.get('attempts', []) for x in [a] + list((a.get('canonical') or {}).get('attempts', []))]  # each action record and EVERY canonical reading of it, whatever its outcome (Root 0558)
    initial = [(r.get('baseline') or {}).get('facts')] + list(((r.get('initial') or {}).get('facts') or {}).values()) + [e.get('facts') for e in (r.get('initial') or {}).get('attempts', [])] + [a.get('pre_action_facts') for a in acts]  # every initial canonical reading is initial
    return [(f, True) for f in initial if f] + [(a['facts'], False) for a in acts if a.get('facts')]

def _select(fetch, browser, parent, target, member, body, prefix, max_actions, title=None):
    """acquisition.select_parent (the one native selector: first fully qualified context, at most max_actions controls tried) with dependency closure
    of action-introduced requests (bounded)."""
    from driver.prepare.get.acquisition import select_parent
    closure, history = [], []  # history: every reading of every round; a later result never erases an earlier required observation
    for _ in range(3):
        obs = dict(fetch.observed); r, s = select_parent(browser, parent, obs, target, member, body, prefix, max_actions, offline=True, title=title); kind = 'native_node'; first = None
        history.append((r['prepared_state'].get('facts'), True)); history += _reading_facts(r)  # the native preparation is an unmarked initial load of the parent
        # open = refused and not closed by a recorded response, or delivered with an open status unless a later recorded response closes it
        unknown = sorted({u for f, _ in history if f for u, k in f.get('refused_get') or [] if k != 'navigation' and not _closes(fetch.observed.get(u))}
                         | {d[0] for f, _ in history if f for d in f.get('delivered') or [] if isinstance(d[1], int) and not _closes(fetch.observed.get(d[0]) or {'status': d[1]})})
        navigations = sorted({u for f, initial in history if f and initial for u in f.get('refused_navigation') or []})  # initial readings only; an action's navigation stays its refusal
        refused = [u for u in unknown if _official_get(u) and not any(x['url'] == u for x in fetch.log)]
        closure.append({'selection_kind': kind, 'verdict': r['verdict'], 'search': r.get('search'), 'action_refused_gets': refused, 'unobserved': unknown, 'navigations': navigations, **({'source_anchor_result': first} if first is not None else {})})
        if not refused:  # a selected target never erases an unobserved dependency or a pending initial navigation of any reading
            return dict(_strip(r), kind=kind, closure=closure, **({'verdict': 'incomplete: pending navigation' if navigations else 'incomplete: unobserved dependency', 'selection_verdict': r['verdict'],
                                                                    'unobserved': unknown, 'navigations': navigations} if unknown or navigations else {})), s
        for u in refused:
            if fetch.get(u, {'kind': 'native_request', 'declarer': parent, 'phase': 'selection action'}) is None and fetch.log[-1]['outcome'].startswith('not requested'):
                return dict(_strip(r), kind=kind, closure=closure, verdict='incomplete: request budget reached', selection_verdict=r['verdict'], unfinished=refused), s
    return dict(_strip(r), kind=kind, closure=closure, verdict='incomplete: closure round bound reached', selection_verdict=r['verdict']), s

def _report_title(files, filename):
    """The member's declared report title (ShortName) from the verified package's own FilingSummary.xml, read by the installed native API
    (edgar.sgml.filing_summary): (title, None) or (None, why). Used only to ORDER the native search. A storage, memory or import failure is no
    metadata verdict and propagates; an absent member, unreadable XML or no report for the member gives no title (the recorded order)."""
    from edgar.sgml.filing_summary import FilingSummary
    raw = files.get('FilingSummary.xml')
    if raw is None: return None, 'no FilingSummary.xml member'
    try: report = FilingSummary.parse(raw.decode('utf-8')).reports.get_by_filename(filename)
    except (OSError, MemoryError, ImportError, StorageError): raise
    except Exception as e: return None, 'FilingSummary not read: ' + repr(e)[:200]
    title = getattr(report, 'short_name', None) if report is not None else None
    return (title, None) if isinstance(title, str) and title.strip() else (None, 'no report title for the member')


def acquire_context(campaign, browser, version_dir, filename, marked, prefix, requested_cik=None, budget=80, max_actions=200):
    from driver.prepare.get.acquisition import index_parent_candidates
    manifest, files = read_package(version_dir); ident = manifest['identity']; fetch = _Fetcher(campaign, budget)
    rec = {'identity': {'accession': ident['accession'], 'ciks': ident['ciks'], 'form': ident['form'], 'filename': filename, 'package_sha256': manifest['package']['sha256']}, 'requests': fetch.log}
    cik = requested_cik if requested_cik is not None else ident['ciks'][0] if len(ident['ciks']) == 1 else None
    if cik is None or cik not in ident['ciks']: return {'outcome': 'refused: no single requested CIK of the package', 'evidence': None, 'record': rec}
    member = files.get(filename); rows = [m for m in manifest['members'] if m['filename'] == filename]
    title, why = _report_title(files, filename); rec['report_title'] = {'short_name': title, **({'unavailable': why} if why else {})}  # search order only (acquisition.NativeSelection._order)
    if member is None or not rows: return {'outcome': 'refused: member not in the verified package custody', 'evidence': None, 'record': rec}
    data = gzip.decompress((Path(version_dir) / 'submission.txt.gz').read_bytes())
    if sha(data) != manifest['package']['sha256']: raise AcquisitionError('package bytes differ from the verified manifest')
    before, after = document_parts(data, rows[0]['package_range'][0]); rec['envelope'] = {'before_sha256': sha(before), 'after_sha256': sha(after), 'rows': len(rows)}
    directory = _url(_identity(ident['accession'], cik, ident['form'])).rsplit('/', 1)[0] + '/'
    index_url = directory + ident['accession'] + '-index.html'; index = fetch.get(index_url)
    if index is None: return {'outcome': 'incomplete: index unavailable', 'evidence': None, 'record': rec}
    cands, counts = index_parent_candidates(index, index_url, ident['accession']); rec.update(index={'url': index_url, 'sha256': sha(index)}, candidates=cands, candidate_counts=counts)
    target = directory + quote(filename); copy = fetch.get(target)
    if copy is None: return {'outcome': 'incomplete: member observation unavailable', 'evidence': None, 'record': rec}
    fit = _prove(copy, _readings(member, filename)[0], before, after); rec['target'] = {'url': target, 'observation_sha256': sha(copy), 'proof': None if fit is None else fit[1]}
    if fit is None: return {'outcome': 'refused: published copy not proved to be the member', 'evidence': None, 'record': rec}
    body, mrec = overlay.measurement_body(copy, fit[0], marked, prefix, fit[1], before, after); rec['target']['measure'] = {k: v for k, v in mrec.items() if k != 'prefix'}
    if body is None: return {'outcome': 'refused: measurement body', 'evidence': None, 'record': rec}
    if 'window' in mrec:
        pg = browser.new_page(java_script_enabled=False)
        try: nl = overlay.node_level(pg, body, mrec, 'utf-8')
        finally: pg.close()
        rec['target']['node_level'] = nl
        if not nl['node_level']: return {'outcome': 'refused: inserted run not node-level', 'evidence': None, 'record': rec}
    rec['parents'], chosen = {}, []
    for parent in cands:
        if fetch.get(parent, {'kind': 'index_link', 'declarer': index_url, 'declarer_sha256': sha(index)}) is None: rec['parents'][parent] = {'verdict': 'parent unavailable', 'request': fetch.log[-1]['outcome']}; continue
        dep = _startup_dependencies(fetch, browser, parent)
        if not dep['fixed_point']: rec['parents'][parent] = {'dependencies': dep, 'verdict': 'incomplete: ' + dep.get('incomplete', '')}; continue
        r, s = _select(fetch, browser, parent, target, member, body, prefix, max_actions, title); rec['parents'][parent] = {'dependencies': dep, 'selection': r, 'verdict': r['verdict']}
        if r['verdict'] in ('initial', 'selected'): chosen.append((parent, r, s))
    rec['undecided_parents'] = sorted(p for p, v in rec['parents'].items() if v['verdict'] not in ('initial', 'selected', 'missing'))  # unavailable, unbudgeted, incomplete, unclean, ambiguous
    if len(chosen) > 1: return {'outcome': 'ambiguous', 'evidence': None, 'record': rec}
    if not chosen:  # undecided alternates stay recorded verbatim (record['parents'], undecided_parents); they never block nor become 'missing'
        return {'outcome': 'incomplete: ' + ('candidate parent not decided' if rec['undecided_parents'] else 'no candidate parent qualifies the member'), 'evidence': None, 'record': rec}
    parent, r, s = chosen[0]
    if r['verdict'] == 'initial':
        selection, facts = {'initial': True}, (r.get('initial') or {}).get('facts') or {}
        delivered = {d[0] for k in ('true', 'false', 'True', 'False', True, False) for d in (facts.get(k) or {}).get('delivered', [])}
    else:
        a = next(x for x in r['attempts'] if x['state'] == 'qualified'); delivered = {d[0] for d in (a.get('facts') or {}).get('delivered', [])}
        from driver.prepare.get.acquisition import selection_record
        selection = selection_record(r, s)
    obs = fetch.observed; keep = (delivered | {parent, target}) & set(obs)
    evidence = {'parent_url': parent, 'target_url': target, 'observed': {u: obs[u] for u in sorted(keep)}, 'selection': selection, 'proof': fit[1], 'before': before, 'after': after}
    rec['evidence_identity'] = {'parent_url': parent, 'target_url': target, 'selection': selection, 'observed': {u: obs[u]['sha256'] for u in sorted(keep)}, 'proof': fit[1]}
    return {'outcome': 'associated', 'evidence': evidence, 'record': rec}
