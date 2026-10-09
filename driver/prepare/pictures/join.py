# One document's pictures from its route to their readings and packets (Root, ROOT_CONNECTION_ORDER / ROOT_CONNECTION_REVIEW_V3, Oct 9): the existing
# steps, unchanged, joined - inputs.prepare -> worker.run (one call per reader) -> readers.free_record -> read_picture. Nothing before joined them: the
# worker's records hold no occurrence and packet() measures a file. Here every picture unit is an occurrence ('<route file_id>#<unit id>', its index
# kept) of the route, which is returned whole; every input it names is archived (get/archive) before any reader starts and read back from there; each
# of the three records must be of that input's bytes; one packet per input, named by it ('sha256:<input>': a bound reference, not a link), measured from
# a temporary file of the archived bytes; the raw records stay with every occurrence (the packet is a projection of them). A unit's input error, a
# reader's failure, a cut-off reading and bytes the readers cannot decode stay explicit, each with its occurrence. Any broken binding stops the job;
# storage, dependency and resource errors propagate.
import hashlib, os, tempfile
from PIL import Image
from ..get import archive
from . import inputs, worker, readers, read_picture

READERS = ('chandra', 'pp', 'ox')
sha = lambda b: hashlib.sha256(b).hexdigest()


def read_pictures(raw, route, members, browser, folder, make_readers, enable_sonnet=False, second=None):
    """join() of a route's pictures as inputs.prepare marks them now. The caller owns the reviewed route (html_route.prepare's) with its source bytes,
    the package's verified members, the browser, the folder (the worker's records and, under inputs/, the archive; one job at a time) and its
    integrity, and the readers it builds; a second reader's results are not kept between calls."""
    return join(route, inputs.prepare(raw, route, members, browser), folder, make_readers, enable_sonnet, second)


def join(route, got, folder, make_readers, enable_sonnet=False, second=None):
    """(route, one entry per picture unit in route order) from a route inputs.prepare has marked and {input SHA-256: bytes} holding at least the inputs
    its units name. make_readers: {'chandra', 'pp', 'ox'}, each a worker make_reader. An entry: occurrence, unit (index), id, input (the unit's own);
    with an input also records {chandra, pp, ox} (the worker's, as saved) and archive {root, sha256}, then packet, packet_record, flags, sonnet_asked -
    or picture_error, where the readers cannot decode the input. Occurrences of one input share its records and its packet."""
    occ = [(k, u, f"{route['file_id']}#{u['id']}") for k, u in enumerate(route['units']) if u.get('kind') == 'image']
    if len({o for _, _, o in occ}) != len(occ): raise ValueError('an occurrence id is given twice in this route')
    for s, data in got.items():
        if sha(data) != s: raise ValueError(f'prepared bytes under {s[:12]} are not those bytes')
    root, data, pairs = os.path.abspath(os.path.join(folder, 'inputs')), {}, []   # absolute: the recorded root still names it after the caller changes directory
    for _, u, o in occ:
        i = u.get('input')
        if not isinstance(i, dict) or ('input_sha256' in i) == ('error' in i): raise ValueError(f'{o}: neither an input nor an input error')
        if 'error' in i: continue
        s = i['input_sha256']
        if s not in got: raise ValueError(f'{o}: its input {s[:12]} is not among the prepared bytes')
        if s not in data: archive.store_blob(root, got[s]); data[s] = archive.load_blob(root, s)   # durable before any reader starts
        pairs.append((o, data[s]))
    recs = {r: worker.run(folder, pairs, make_readers[r]) for r in READERS} if pairs else {}
    made, out = {}, []
    for k, u, o in occ:
        e = dict(occurrence=o, unit=k, id=u['id'], input=u['input']); out.append(e)
        if 'error' in u['input']: continue
        s = u['input']['input_sha256']; c, pp, ox = (recs[r][o] for r in READERS)
        if any(x['image_sha256'] != s for x in (c, pp, ox)): raise ValueError(f'{o}: a reader record is of other bytes than its input')
        if s not in made: made[s] = _packet(s, data[s], c, pp, ox, enable_sonnet, second)
        fields, size = made[s]
        if u['input'].get('how') == 'page' and fields.get('packet') and list(size) != list(u['input']['size']): raise ValueError(f'{o}: the capture is not the size its input records')
        e.update(records=dict(chandra=c, pp=pp, ox=ox), archive=dict(root=root, sha256=s), **fields)
    return route, out


def _packet(s, data, c, pp, ox, enable_sonnet, second):  # ({packet fields} or {picture_error}, the picture's size) for one input
    try: readers._image(data)                                             # the readers' own decoder: what they cannot read has no packet
    except readers.PictureError as e: return dict(picture_error=str(e)), None
    limit, free = c['settings'].get('max_tokens'), readers.free_record(pp, ox)   # Chandra's own limit, never the caller's
    if type(limit) is not int: raise ValueError("Chandra's reader settings name no max_tokens")
    html, tokens = (None, None) if c['status'] == 'error' else (c['result'][0], c['result'][1].get('generation_tokens'))
    if c['status'] != 'error' and (c['status'] == 'cut off') != ((tokens or 0) >= limit): raise ValueError("Chandra's status and its own limit disagree")
    with tempfile.NamedTemporaryFile(suffix='.input') as f:                # packet() measures a file; the second reader reads it
        f.write(data); f.flush()
        with Image.open(f.name) as im: size = im.size
        if free and (free['w'], free['h']) != size: raise ValueError('the free OCR frame is not the picture read')
        asked, flags, text, rec = read_picture(f'sha256:{s}', f.name, html, tokens, free, limit, enable_sonnet, second, picture_ref=f'sha256:{s}')
    return dict(packet=text, packet_record=rec, flags=flags, sonnet_asked=asked), size
