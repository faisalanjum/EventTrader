"""The selected HTML route for one document (DESIGN §67): EdgarTools reads it (`edgartools_html.convert`), the source's own strike-through is written on
(`source_formatting.step`), the page's geometry is measured in the caller's browser (`screen_grid.step`); where the scanner cannot certify which text
the page hides, the browser first says it (`visibility`), and the conversion and the screen step read by that. A thin composition of those calls: no
browser launcher, scheduler, cache or parser of its own."""
from driver.prepare.convert import anchor, edgartools_html, screen_grid, source_formatting
from driver.prepare.get.acquire import StorageError


def visibility(raw, vis, browser):
    """(reading, error) for one document before the tool reads it (`vis`: the scanner's reading of the bytes): that reading where it is certain;
    else the reading with the browser's verdict on its text (`screen_grid.page_visibility`, one render in the caller's browser: Visible's `page`), or -
    a page that cannot be read - the scanner's reading and the error. A disconnected browser's error, and storage, dependency and resource errors, propagate."""
    if vis.certain: return vis, None
    try: return anchor.Visible(raw, page=screen_grid.page_visibility(raw, vis, browser)), None
    except (OSError, StorageError, ImportError, MemoryError): raise
    except Exception as e:
        if not browser.is_connected(): raise
        return vis, repr(e)[:200]


def unresolved(vis):
    """The reason a page is partial whose browser verdict reached some of its text runs not at all (`page_visibility['unresolved']`: kept as source,
    never shown or hidden; the encoding's own byte order mark, which no page shows, aside): its reading is not certified whole."""
    n = sum(1 for r in vis.page.get('unresolved') or [] if r['why'] != 'byte order mark') if vis.paged else 0
    return ['page visibility: %d text run%s without a browser verdict' % (n, '' if n == 1 else 's')] if n else []


def prepare(raw, file_id, sha256, browser):
    """(route, facts) for one HTML document: the caller's bytes, their SHA-256 and a browser the caller owns and may reuse. `facts` holds each step's own
    result - `formatting` its count (None where nothing can be certified), `screen` its facts, `visibility` (a file the scanner cannot certify) the
    browser's counts or why it could not read them. A failed conversion stops there (no step runs, `facts` empty). A page that cannot be measured keeps
    the units it has and marks the route PARTIAL with the step's error, as a partial conversion is marked (DESIGN §36); so does a page whose visibility
    cannot be read, which keeps the scanner's reading. A disconnected browser's error propagates so the caller can stop and restart it. Source-identity,
    storage, dependency and resource errors propagate. The bytes are read once as written and, where the scanner cannot certify them, once as the
    browser shows them: formatting reads the first, the conversion and the screen step the reading the route is made with (each step called alone
    reads its own)."""
    anchor.check_source(raw, sha256); original = anchor.Visible(raw); vis, failed = visibility(raw, original, browser)
    route = edgartools_html.convert(raw, file_id, sha256, vis=vis)  # one scan: a certain file is not read twice
    if route['status'] != 'OK': return route, {}
    anchor.check_source(raw, route.get('sha256'))  # the route names these bytes before the steps change it with this call's own readings
    facts = {'formatting': source_formatting._step(original, route)}; del original  # the source as written is for formatting only: not kept through the screen work
    facts['screen'] = screen_grid._step(raw, route, browser, vis)
    if failed or vis.paged: facts['visibility'] = {'error': failed} if failed else {k: len(v) if isinstance(v, list) else v for k, v in vis.page.items()}
    errors = (['page visibility: ' + failed] if failed else []) + unresolved(vis) + (['screen step: ' + facts['screen']['error']] if 'error' in facts['screen'] else [])
    if errors: route['status'], route['error'] = 'PARTIAL', '; '.join(errors)
    return route, facts
