# The bytes each picture occurrence is read from (Codex/Root, Oct 9). readers._image hands every reader convert('RGB'), which drops a picture's
# transparency: of the 80 non-opaque pictures in the 3,353 exposed documents, 17 came out one flat colour (prepare_work/alpha_backdrop_20261009).
# A picture is read as the page shows it, nothing chosen by us:
#   opaque member  - its own bytes (Pillow's has_transparency_data false, or alpha 255 everywhere): same bytes, same readings as before;
#   otherwise      - the page's own pixels round the picture's box: Chrome's capture (CDP Page.captureScreenshot; clip = the whole CSS pixels round
#                    the box, the picture first scrolled into view) at a scale that reaches the picture's natural resolution, the page loaded as the
#                    screen step loads one (JavaScript off; the original bytes in the charset the browser gives them) with the document's own package
#                    members served by exact name - its background, any background of its own and its display size as the page draws them. A page
#                    that names anything else (a sheet, a background, a picture) cannot be drawn as it is: its captures are unproved, never made.
# Each occurrence is its own source tag: its unit's anchor must be a shown picture tag of the source with the unit's src (anchor.Visible), and the
# step's comment marks (marker_prefix, tag_cells) bind it in the page - never its file name. A picture that cannot be read so has an error and no
# input, never its bytes with the transparency dropped. Readers, worker and cache are unchanged: the caller hands worker.run the bytes returned
# here, by the input SHA-256 written on each unit.
import base64, hashlib, io, math, mimetypes, urllib.parse
from PIL import Image
from ..convert import anchor, screen_grid
from ..get.acquire import StorageError

FIND_JS = """p => { const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT), out = {};
  while (w.nextNode()) { const c = w.currentNode, e = c.nextSibling;
    if (!c.data.startsWith(p)) continue;
    if (!e || e.nodeType !== 1 || e.tagName !== 'IMG') { out[c.data.slice(p.length)] = null; continue; }
    out[c.data.slice(p.length)] = {src: e.getAttribute('src'), loaded: e.complete && e.naturalWidth > 0, natural: [e.naturalWidth, e.naturalHeight]}; }
  return out; }"""
VIEW_JS = """k => { const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);
  while (w.nextNode()) if (w.currentNode.data === k) { const e = w.currentNode.nextSibling; e.scrollIntoView({block: 'nearest', inline: 'nearest'});
    const r = e.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; }
  return null; }"""


def opaque(data):  # the member's own bytes are its input: Pillow says it has no transparency (or none in any pixel); a picture Pillow cannot read
    try:            # stays as it is, and the readers report it as they do now
        im = Image.open(io.BytesIO(data)); im.load()
        return not im.has_transparency_data or im.convert('RGBA').getchannel('A').getextrema() == (255, 255)
    except (ImportError, MemoryError): raise   # a missing dependency or no memory is not the picture's own
    except Exception: return True


def prepare(raw, route, members, browser):
    """{input SHA-256: bytes} for one HTML document's pictures: its bytes, its route (html_route.prepare's), its package's verified members
    {name: bytes} and a browser the caller owns. Every picture unit (kind 'image': linked, or added from its source tag) gets u['input'], once its
    anchor is checked to be exactly a shown picture tag of the source with the unit's src (anchor.Visible, read as the route was made):
    {'member_sha256', 'input_sha256', 'how': 'member'} - an opaque member's own bytes; {..., 'how': 'page', 'box', 'clip', 'scale', 'size', 'browser'} -
    the page's pixels round its box (box: the picture's own, CSS pixels; clip: the whole CSS pixels captured; size: the capture's pixels = clip x scale,
    page pixels, not the member's); or {'error'} (and 'member_sha256' where there is one) with no input. Bytes that are not the route's source raise ValueError;
    a disconnected browser's error and storage, dependency and resource errors propagate."""
    anchor.check_source(raw, route.get('sha256')); out, todo = {}, []
    vis = anchor.Visible(raw, page=route.get('page_visibility')); tags = dict(vis.pictures)  # the source's own shown picture tags, read as the route was made
    for u in route['units']:
        if u.get('kind') != 'image': continue
        if not isinstance(u.get('anchor'), dict): u['input'] = {'error': 'the route places this picture at no source tag'}; continue
        a = u['anchor'].get('byte_start')
        if tags.get(a) != u['anchor'].get('byte_end_exclusive') or vis.picture_sources.get(a) != u.get('src'): u['input'] = {'error': 'not a shown picture tag of the source with its src'}; continue
        data = members.get(u.get('src'))
        if data is None: u['input'] = {'error': 'not a member of the package'}; continue
        m = hashlib.sha256(data).hexdigest()
        if opaque(data): out[m] = data; u['input'] = {'member_sha256': m, 'input_sha256': m, 'how': 'member'}
        else: todo.append((u, m))
    if todo:
        try: shots, error = _page(raw, vis, [u for u, _ in todo], members, browser), None
        except (OSError, StorageError, ImportError, MemoryError): raise
        except Exception as e:
            if not browser.is_connected(): raise
            shots, error = {}, 'page: ' + repr(e)[:200]
        for k, (u, m) in enumerate(todo):
            got = shots.get(k) or {'error': error or 'no capture'}
            if 'png' not in got: u['input'] = {'member_sha256': m, 'error': got['error']}; continue
            s = hashlib.sha256(got['png']).hexdigest(); out[s] = got['png']
            u['input'] = {'member_sha256': m, 'input_sha256': s, 'how': 'page', 'box': got['box'], 'clip': got['clip'], 'scale': got['scale'], 'size': got['size'], 'browser': browser.version}
    return out


def _page(raw, vis, units, members, browser):  # {k: {'png', 'box', 'clip', 'scale', 'size'} or {'error'}} for the k-th unit: the page's pixels round its picture
    prefix = screen_grid.marker_prefix(raw); address = 'http://%s.invalid/' % prefix; key = prefix + 'p:'
    page = screen_grid._offline_page(browser, None, (address, raw))  # first the original bytes: the charset the browser itself gives them
    try: page.goto(address, wait_until='load'); charset = page.evaluate('document.characterSet')
    finally: page.close()
    marked, _ = screen_grid.tag_cells(raw, vis, (), [(u['anchor']['byte_start'], b'<!--%s%d-->' % (key.encode(), k)) for k, u in enumerate(units)], prefix, cells=False)
    refused = []; page = screen_grid._offline_page(browser, None, (address, marked, charset))
    def serve(route, *_):  # registered after the page's own refusal, so tried first: a member by its exact name; anything else falls back to it, and is
        r = route.request; name = urllib.parse.unquote(urllib.parse.urlsplit(r.url).path[1:]) if r.url.startswith(address) else None  # noted unless it is the page itself
        if name in members and not r.is_navigation_request(): return route.fulfill(status=200, body=members[name], content_type=mimetypes.guess_type(name)[0] or 'application/octet-stream')
        if not (r.url == address and r.is_navigation_request()): refused.append(r.url)
        return route.fallback()
    try:
        page.route('**/*', serve); page.goto(address, wait_until='load')
        if refused: raise RuntimeError('what the page names cannot be read offline, so how it draws is unproved: ' + ', '.join(refused)[:150])  # a missing sheet, background or picture
        found, cdp, out = page.evaluate(FIND_JS, key), page.context.new_cdp_session(page), {}
        for k, u in enumerate(units):
            f = found.get(str(k))
            if not f or f['src'] != u['src']: out[k] = {'error': 'unbound: its mark is not right before its picture tag'}; continue
            if not f['loaded']: out[k] = {'error': 'the picture did not load in the page'}; continue
            (w, h), (x, y, bw, bh) = f['natural'], page.evaluate(VIEW_JS, key + str(k))  # in view: Chrome left a far-off picture unpainted (hal-20260331 g1-g3)
            if bw <= 0 or bh <= 0: out[k] = {'error': 'the picture has no box in the page'}; continue
            scale = max(1, w / bw, h / bh)  # at least one device pixel per CSS pixel, and the picture's own pixels in both directions
            clip = [math.floor(x), math.floor(y)]; clip += [math.ceil(x + bw) - clip[0], math.ceil(y + bh) - clip[1]]  # whole CSS pixels round the box: Chrome snaps a fractional clip
            shot = cdp.send('Page.captureScreenshot', {'format': 'png', 'fromSurface': True, 'captureBeyondViewport': True, 'clip': dict(zip(('x', 'y', 'width', 'height'), clip), scale=scale)})
            png = base64.b64decode(shot['data']); size = Image.open(io.BytesIO(png)).size
            if any(abs(a - b * scale) > 1 for a, b in zip(size, clip[2:])): out[k] = {'error': f'the capture is {size[0]}x{size[1]}, not its clip at scale {scale:.3f}'}; continue  # cut by a browser limit: never kept
            if not opaque(png): out[k] = {'error': 'the capture is not opaque'}; continue  # an input is never a picture with transparency
            out[k] = {'png': png, 'box': [x, y, bw, bh], 'clip': clip, 'scale': scale, 'size': list(size)}
        return out
    finally: page.close()
