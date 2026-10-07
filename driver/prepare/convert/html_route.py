"""The selected HTML route for one document (DESIGN §67): EdgarTools reads it (`edgartools_html.convert`), the source's own strike-through is written on
(`source_formatting.step`), the page's geometry is measured in the caller's browser (`screen_grid.step`). A thin composition of those calls: no browser
launcher, scheduler, cache or parser of its own."""
from driver.prepare.convert import edgartools_html, screen_grid, source_formatting


def prepare(raw, file_id, sha256, browser):
    """(route, facts) for one HTML document: the caller's bytes, their SHA-256 and a browser the caller owns and may reuse. `facts` holds each step's own
    result - `formatting` its count (None where nothing can be certified), `screen` its facts. A failed conversion stops there (no step runs, `facts`
    empty). A page that cannot be measured keeps the units it has and marks the route PARTIAL with the step's error, as a partial conversion is marked
    (DESIGN §36). A disconnected browser's error propagates so the caller can stop and restart it. Source-identity, storage, dependency
    and resource errors propagate."""
    route = edgartools_html.convert(raw, file_id, sha256)
    if route['status'] != 'OK': return route, {}
    facts = {'formatting': source_formatting.step(raw, route), 'screen': screen_grid.step(raw, route, browser)}
    if 'error' in facts['screen']: route['status'], route['error'] = 'PARTIAL', 'screen step: ' + facts['screen']['error']
    return route, facts
