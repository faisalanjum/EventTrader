# One reader job (Codex r15 worker plan, r16 corrections): each picture's bytes are read once per reader settings and kept as ONE result
# file - the reading with its settings and status - published whole; one job per output folder. The saved reading holds no file or
# document name: occurrences and their context are attached when the packet is made. Statuses: 'complete'; 'cut off' (a successful reading
# that stopped at its output limit: kept, never read again with the same settings); 'error' (the reader failed: no reading, read again on
# the next run - never twice in one run). One rule checks a record when it is saved and when it is loaded. Storage and memory failures, invalid
# saved results and malformed reader returns stop the job; only the reader's own failures are recorded as a picture's error.
import contextlib, fcntl, hashlib, json, os
from ..get.acquire import StorageError, _make_dirs, _sync_dir             # the downloader's own durability rules

sha = lambda b: hashlib.sha256(b).hexdigest()
FIELDS = {'status', 'result', 'error', 'image_sha256', 'settings'}


@contextlib.contextmanager
def only_job(folder):  # one job per output folder; the system releases the lock when the job ends or dies (the lock file stays)
    _make_dirs(folder); fd = os.open(os.path.join(folder, '.lock'), os.O_CREAT | os.O_RDWR)
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError(f'another job is using {folder}') from None
        yield
    finally: os.close(fd)


def run(folder, pictures, make_reader):
    """Read (occurrence id, bytes) pairs into `folder` with the reader make_reader() builds (read(bytes), settings, status; see readers.py),
    the lock taken first. Returns {occurrence id: result record}; occurrences with the same bytes share one record and one read; a repeated
    occurrence id stops the job (it would replace another picture). ponytail: holds one batch's records; call per batch."""
    with only_job(folder):
        reader = make_reader(); settings = json.loads(json.dumps(reader.settings))
        sid = sha(json.dumps(settings, sort_keys=True).encode()); out, seen = {}, {}
        for name, data in pictures:
            if name in out: raise ValueError(f'occurrence id given twice: {name}')
            image = sha(data)
            if image not in seen: seen[image] = _one(os.path.join(folder, f'{image}-{sid}.json'), image, data, reader, settings)
            out[name] = seen[image]
        return out


def _one(path, image, data, reader, settings):
    rec = _load(path, image, settings, reader)
    if rec and rec['status'] != 'error': return rec
    try: result = reader.read(data)
    except (OSError, StorageError, MemoryError): raise                     # the disk, the store or the machine's memory, not the picture: stop
    except Exception as e: rec = dict(status='error', result=None, error=f'{type(e).__name__}: {str(e)[:300]}')
    else: rec = dict(status=reader.status(result), result=result, error=None)   # a malformed return stops here: it is not a reading error
    rec.update(image_sha256=image, settings=settings); _check(rec, reader)
    temporary = path + '.pending'                                            # a pending file is never a result
    with open(temporary, 'w') as f: json.dump(rec, f); f.flush(); os.fsync(f.fileno())
    os.replace(temporary, path); _sync_dir(os.path.dirname(path))
    return rec


def _check(rec, reader):  # the one rule for a record, saved or loaded: its fields, its status, and its reader's own status of the reading
    if not isinstance(rec, dict) or set(rec) != FIELDS: raise ValueError('not a result record')
    if rec['status'] == 'error':
        if rec['result'] is not None or not isinstance(rec['error'], str) or not rec['error']: raise ValueError('an error record holds its error and no reading')
        return
    if rec['status'] not in ('complete', 'cut off') or rec['result'] is None or rec['error'] is not None: raise ValueError('a reading record holds a reading and no error')
    try: status = reader.status(rec['result'])
    except Exception as e: raise ValueError(f'its reader does not recognise the reading: {type(e).__name__}: {e}') from e
    if status != rec['status']: raise ValueError(f"status {rec['status']!r} where its reader says {status!r}")


def _load(path, image, settings, reader):  # the saved result, None when there is none; anything unreadable or inconsistent stops
    try: f = open(path)
    except FileNotFoundError: return None                                  # only a missing file is a cache miss; any other disk error stops
    with f:
        try: rec = json.load(f)
        except ValueError as e: raise StorageError(f'invalid saved result: {path}: {e}') from e
    try: _check(rec, reader)
    except ValueError as e: raise StorageError(f'invalid saved result: {path}: {e}') from e
    if rec['image_sha256'] != image or rec['settings'] != settings: raise StorageError(f'saved result does not match its key: {path}')
    return rec
