"""The selected HTML route for one document (DESIGN §67): EdgarTools reads it (`edgartools_html.convert`), the source's own strike-through is written on
(`source_formatting.step`), the page's geometry is measured in the caller's browser (`screen_grid.step`); where the scanner cannot certify which text
the page hides, the browser first says it (`visibility`), and the conversion and the screen step read by that. A thin composition of those calls: no
browser launcher, scheduler, cache or parser of its own."""
from bisect import bisect_left

from driver.prepare.convert import anchor, edgartools_html, screen_grid, source_formatting, xml_fields
from driver.prepare.get.acquire import StorageError

INLINE_XBRL_HEADER = '{http://www.xbrl.org/2013/inlineXBRL}header'  # the inline XBRL 1.1 header element, by expanded name (never a prefix)


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
    outside = [dict(tag=d['tag'], start=d['start'], tag_end=d['tag_end'], hidden=d['hidden'], event_attributes=[n for n in d['on_attributes'] if n in native.get(d['tag'], ())], declarations=d['declarations']) for d in vis.declared]
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
    seen = (['page visibility: ' + failed] if failed else []) + unresolved(vis, source.context.label_spans(raw) if getattr(source, 'context', None) is not None else ())  # the visibility list
    screen = ['screen step: ' + facts['screen']['error']] if 'error' in facts['screen'] else []
    rest = ['context: ' + w for w in source.context.gate()] if getattr(source, 'context', None) is not None else []  # every render reached the state and agrees
    declared, outside = declarations(vis, browser)  # the one shared decision, carried on each source link record (route.source_links follows vis.links)
    for rec in route.get('source_links') or []:
        if rec['tag']['byte_start'] in declared: rec['script_action'] = declared[rec['tag']['byte_start']]
    scripted = len(declared) if getattr(source, 'context', None) is None else 0  # a context route's actions are qualified by its activations
    if scripted: rest.append(f'context: {scripted} declared script action(s) not qualified (no context entered)')  # unknown, never standalone success
    document = getattr(source, 'context', None) is None or source.context.control is None  # the document-level route: the default one, or a context's initial view
    if outside and document:  # declared outside the supported link path: never activated here, so the document stays explicitly incomplete, context or not
        facts['declared_outside_link_path'] = outside; rest.append(f'context: {len(outside)} declared event handler(s) outside the supported link path (not activated)')
    errors = seen + screen + rest
    if errors: route['status'], route['error'] = 'PARTIAL', '; '.join(errors)
    route['text_proved'] = facts['screen'].get('text_proved') is True and not seen and not rest  # the route-text proof: the screen step's, and no visibility, context, script or handler failure (an unread picture alone may stand); absent (a failed conversion) is false
    if given is not None: route['resources'] = source.identity()  # the document, its bundle and every dependency the renders asked for, once
    return route, facts


def source_reading(raw, file_id, sha256, displayed, parse=None):
    """The typed whole-source reading of one HTML document beside its displayed route `displayed` (the same document's saved initial route):
    (route, None), or (None, why) when nothing in it is proved hidden. The SAME tool parse and linker (`edgartools_html.convert`) on
    `anchor.Visible(source=True)` rebuilt from the displayed route's OWN saved visibility evidence (`page_visibility`, the browser's verdict; the
    scanner where none was needed) - never another render - so the hidden authored text the displayed route leaves out is kept in its own place,
    order and table structure. It is NOT a display state and never stands for one: its route record names it (`+source-reading`,
    `settings.reading`). Proved hidden = what the displayed route's filter removed (`edgartools_html.named`: the scanner's spans where certain,
    else the browser-proved ones). Each such run is a `source_hidden` record placed by the one run-to-owner rule (`screen_grid._owners`: owners
    with code-point `text_at` in their saved text, as `source_inline`); a run it cannot place is listed `unresolved` with its reason, never guessed,
    and keeps the route PARTIAL. Runs the browser gave no verdict stay as the displayed route reads them and keep it PARTIAL (`unresolved`).
    Where the same bytes are a complete strict XML document with an inline-XBRL header (EdgarTools deletes that header before it parses, so no
    HTML reading can place it), the reading is instead the existing XML route of the whole document (`xml_fields.convert`, unchanged: every element,
    attribute and byte anchor), labelled the same way (`_xml_source`); a document that does not parse so keeps the HTML reading above."""
    anchor.check_source(raw, sha256)
    if displayed.get('sha256') != sha256: raise ValueError('the displayed route is not this document')
    page = displayed.get('page_visibility'); whole = anchor.Visible(raw, page=page, source=True)
    proved = sorted(whole.hidden if whole.certain else whole.browser_hidden)
    if not proved: return None, 'no proved-hidden span' + ('' if whole.certain or page is not None else ' (the scanner is not certain and the displayed route has no browser verdict: hidden content unproved)')
    basis = 'browser verdict of the displayed route' if page is not None else 'scanner (certain)'
    xml = xml_fields.convert(raw, file_id, sha256)
    if xml['status'] == 'OK' and any(e['name'] == INLINE_XBRL_HEADER for e in xml['xml_elements']): return _xml_source(xml, displayed, basis, whole), None
    route = edgartools_html.convert(raw, file_id, sha256, vis=whole, **({} if parse is None else {'parse': parse}))
    route['route'] = dict(route['route'], name=route['route']['name'] + '+source-reading', settings=dict(route['route'].get('settings') or {}, reading='source (not a display state)', hidden_basis=basis))
    if route['status'] != 'OK': return route, None
    owners, records, failed = screen_grid._owners(whole, route['units']), [], []
    for a, b in proved:
        lo, hi = bisect_left(whole.s, a), bisect_left(whole.s, b)
        if hi == lo: continue  # no character a reader could hold (collapsible white space only)
        own, why = owners(a, b)
        (records.append({'byte_start': a, 'byte_end_exclusive': b, 'owners': own}) if own else failed.append({'byte_start': a, 'byte_end_exclusive': b, 'why': why}))
    route['source_hidden'] = {'read': True, 'basis': basis, 'records': records, **({'unresolved': failed} if failed else {})}
    errors = (['source reading: %d proved-hidden run%s not placed' % (len(failed), '' if len(failed) == 1 else 's')] if failed else []) + unresolved(whole)
    pictures = sum(1 for u in route['units'] if u.get('kind') == 'image')
    if pictures: errors.append('source reading: %d picture%s not prepared (named, not reconstructed)' % (pictures, '' if pictures == 1 else 's'))
    if errors: route['status'], route['error'] = 'PARTIAL', '; '.join(errors)
    return route, None


def _xml_source(route, displayed, basis, whole):
    """The existing XML route as the typed source reading, labelled like the HTML one. Its pictures are read once, in the displayed route. Which source
    tags are pictures is the scanner's ONE inventory the displayed route is made from (`whole`, anchor.Visible: `picture_tags`, every img and svg
    opening tag, shown or hidden, whatever its namespace; `picture_names`, the src it decodes): each must be exactly ONE displayed picture unit's
    occurrence - the same opening-tag span and src - whose preparation the caller checks there. Spans are compared in that opening-tag convention: the
    XML element at the tag starts at the same byte, and its own anchor runs to its end tag where it has content (an svg), so it is never the measure.
    Any other (hidden-only, duplicated, not named, or with no XML element starting there) is listed by its span and keeps this reading PARTIAL."""
    route['route'] = dict(route['route'], name=route['route']['name'] + '+source-reading', settings=dict(route['route']['settings'], reading='source (not a display state)', hidden_basis=basis,
                          pictures="each source picture tag is the displayed route's picture unit at the same opening-tag span and src, read there"))
    shown = {}
    for u in displayed.get('units') or []:
        if u.get('kind') == 'image' and isinstance(u.get('anchor'), dict):
            k = (u['anchor'].get('byte_start'), u['anchor'].get('byte_end_exclusive'), u.get('src')); shown[k] = shown.get(k, 0) + 1
    starts = {e['anchor']['byte_start'] for e in route['xml_elements']}
    unread = ['%d-%d' % (a, b) for a, b in whole.picture_tags if a not in starts or shown.get((a, b, (whole.picture_names.get(a) or (None, None))[1])) != 1]
    if unread: route['status'], route['error'] = 'PARTIAL', 'source reading: %d source picture tag%s not one displayed picture occurrence (not read): %s' % (len(unread), '' if len(unread) == 1 else 's', ', '.join(unread))
    return route
