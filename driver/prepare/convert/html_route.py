"""The selected HTML route for one document (DESIGN §67): EdgarTools reads it (`edgartools_html.convert`), the source's own strike-through is written on
(`source_formatting.step`), the page's geometry is measured in the caller's browser (`screen_grid.step`); where the scanner cannot certify which text
the page hides, the browser first says it (`visibility`), and the conversion and the screen step read by that. A thin composition of those calls: no
browser launcher, scheduler, cache or parser of its own."""
from driver.prepare.convert import anchor, edgartools_html, screen_grid, source_formatting
from driver.prepare.get.acquire import StorageError


def visibility(raw, vis, browser, source=None):
    """(reading, error) for one document before the tool reads it (`vis`: the scanner's reading of the bytes): that reading where it is certain;
    else the reading with the browser's verdict on its text (`screen_grid.page_visibility`, one render in the caller's browser: Visible's `page`), or -
    a page that cannot be read - the scanner's reading and the error. A disconnected browser's error, and storage, dependency and resource errors, propagate."""
    if vis.certain and getattr(source, 'context', None) is None: return vis, None  # a contextual state is always read by the browser: the parent's styles and the action can change it
    try: return anchor.Visible(raw, page=screen_grid.page_visibility(raw, vis, browser, source)), None
    except (OSError, StorageError, ImportError, MemoryError): raise
    except Exception as e:
        if not browser.is_connected(): raise
        return vis, repr(e)[:200]


def unresolved(vis, skip=()):  # `skip`: source spans a contextual state reports apart (a control whose own label its action replaced)
    """The reason a page is partial whose browser verdict reached some of its text runs not at all (`page_visibility['unresolved']`: kept as source,
    never shown or hidden; the encoding's own byte order mark, which no page shows, aside): its reading is not certified whole."""
    n = sum(1 for r in vis.page.get('unresolved') or [] if r['why'] != 'byte order mark' and not any(a <= r['at']['byte_start'] and r['at']['byte_end_exclusive'] <= b for a, b in skip)) if vis.paged else 0
    p = len(vis.page.get('unresolved_pictures') or []) if vis.paged else 0  # a picture tag no verdict reached: the scanner's reading stays for it, said apart from text
    return (['page visibility: %d text run%s without a browser verdict' % (n, '' if n == 1 else 's')] if n else []) + (['page visibility: %d picture tag%s without a browser verdict' % (p, '' if p == 1 else 's')] if p else [])


NATIVE_DECLARATIONS = """([hrefs, byTag]) => { const a = document.createElement('a');
  const protocols = hrefs.map(h => { a.setAttribute('href', h); return a.protocol; });  // the browser's own URL result for each exact decoded href (nothing runs)
  const events = Object.fromEntries(Object.entries(byTag).map(([t, ns]) => { const e = document.createElement(t); return [t, ns.filter(n => n in e)]; }));  // its own event-handler properties per element type
  return [protocols, events]; }"""


def declarations(vis, browser):
    """The one declaration decision (Root CONTEXT_AUTOMATIC_ENTRY_IMPLEMENT, CONTEXT_DECLARED_ACTION_BOUNDARY and CONTEXT_NATIVE_DECLARATION_URL_REVIEW,
    20261022), shared by the route status and the caller's automatic entry; the pinned browser owns both URL semantics and event recognition, in one call
    on a blank page: ({link start: script_action} for source links whose decoded href has the javascript: protocol or whose on* attributes are event-handler
    properties of an anchor, [{tag, start, tag_end, hidden, event_attributes}] for elements outside the supported link path whose on* attributes are
    event-handler properties of their own element type). No list and no URL parsing of ours; raw evidence (href, attributes, source location) kept."""
    by_tag = {}
    for l in vis.links: by_tag.setdefault('a', set()).update(l.get('on_attributes') or ())
    for d in vis.declared: by_tag.setdefault(d['tag'], set()).update(d['on_attributes'])
    by_tag = {t: sorted(n) for t, n in by_tag.items() if n}
    if not vis.links and not by_tag: return {}, []
    ctx = browser.new_context()
    try: protocols, native = ctx.new_page().evaluate(NATIVE_DECLARATIONS, [[l['href'] for l in vis.links], by_tag])
    finally: ctx.close()
    native = {t: set(n) for t, n in native.items()}; links = {}
    for l, protocol in zip(vis.links, protocols):
        js, ev = protocol == 'javascript:', sorted(set(l.get('on_attributes') or ()) & native.get('a', set()))
        if js or ev: links[l['start']] = {'javascript_href': js, 'event_attributes': ev}
    outside = [dict(tag=d['tag'], start=d['start'], tag_end=d['tag_end'], hidden=d['hidden'], event_attributes=[n for n in d['on_attributes'] if n in native.get(d['tag'], ())]) for d in vis.declared]
    return links, [d for d in outside if d['event_attributes']]


def prepare(raw, file_id, sha256, browser, source=None, parse=None):
    """(route, facts) for one HTML document: the caller's bytes, their SHA-256 and a browser the caller owns and may reuse. `facts` holds each step's own
    result - `formatting` its count (None where nothing can be certified), `screen` its facts, `visibility` (a file the scanner cannot certify) the
    browser's counts or why it could not read them. A failed conversion stops there (no step runs, `facts` empty). A page that cannot be measured keeps
    the units it has and marks the route PARTIAL with the step's error, as a partial conversion is marked (DESIGN §36); so does a page whose visibility
    cannot be read, which keeps the scanner's reading. A disconnected browser's error propagates so the caller can stop and restart it. Source-identity,
    storage, dependency and resource errors propagate. The bytes are read once as written and, where the scanner cannot certify them, once as the
    browser shows them: formatting reads the first, the conversion and the screen step the reading the route is made with (each step called alone
    reads its own). `parse`: the tool call `convert` makes (`edgartools_html.parse` when None), so a caller can keep the tool's own reading - the plain
    dump with its version - before the route is made of it; nothing here stores it."""
    anchor.check_source(raw, sha256)
    given = source; source = source or screen_grid.Source('', {})  # one document's evidence for every render (none given: nothing answers), its charset read once
    source.bind(raw)  # the evidence is this document's, before any render
    original = anchor.Visible(raw); vis, failed = visibility(raw, original, browser, source)
    route = edgartools_html.convert(raw, file_id, sha256, vis=vis, **({} if parse is None else {'parse': parse}))  # one scan: a certain file is not read twice
    if route['status'] != 'OK':
        if given is not None: route['resources'] = source.identity()  # what the renders before the failed conversion used
        return route, {}
    anchor.check_source(raw, route.get('sha256'))  # the route names these bytes before the steps change it with this call's own readings
    facts = {'formatting': source_formatting._step(original, route)}; del original  # the source as written is for formatting only: not kept through the screen work
    facts['screen'] = screen_grid._step(raw, route, browser, vis, source=source)
    if failed or vis.paged: facts['visibility'] = {'error': failed} if failed else {k: len(v) if isinstance(v, list) else v for k, v in vis.page.items()}
    errors = (['page visibility: ' + failed] if failed else []) + unresolved(vis, source.context.label_spans(raw) if getattr(source, 'context', None) is not None else ()) + (['screen step: ' + facts['screen']['error']] if 'error' in facts['screen'] else [])
    if getattr(source, 'context', None) is not None: errors += ['context: ' + w for w in source.context.gate()]  # every render reached the state and agrees
    declared, outside = declarations(vis, browser)  # the one shared decision, carried on each source link record (route.source_links follows vis.links)
    for rec in route.get('source_links') or []:
        if rec['tag']['byte_start'] in declared: rec['script_action'] = declared[rec['tag']['byte_start']]
    scripted = len(declared) if getattr(source, 'context', None) is None else 0  # a context route's actions are qualified by its activations
    if scripted: errors.append(f'context: {scripted} declared script action(s) not qualified (no context entered)')  # unknown, never standalone success
    document = getattr(source, 'context', None) is None or source.context.control is None  # the document-level route: the default one, or a context's initial view
    if outside and document:  # declared outside the supported link path: never activated here, so the document stays explicitly incomplete, context or not
        facts['declared_outside_link_path'] = outside; errors.append(f'context: {len(outside)} declared event handler(s) outside the supported link path (not activated)')
    if errors: route['status'], route['error'] = 'PARTIAL', '; '.join(errors)
    if given is not None: route['resources'] = source.identity()  # the document, its bundle and every dependency the renders asked for, once
    return route, facts
