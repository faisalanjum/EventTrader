"""Single-owner SEC acquisition campaign: explicit cache, shared pacing, 403 stop."""
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlsplit

from .acquire import AcquisitionError, StorageError, check_space, _json, _make_dirs, _no_symlinks, _sync_dir
from .archive import load_blob, store_blob
from .transport import download, DownloadError, http_request


class OfflineCacheMiss(AcquisitionError):
    """The exact URL has no selected response in this offline campaign (live=False): nothing was requested. The only acquisition error a
    caller may treat as an ordinary unavailable resource; every other AcquisitionError is custody, stop or input failure. `receipt`: the
    URL's latest recorded failed attempt (its HTTP status, as DownloadError.receipt), or None when it was never attempted."""
    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.receipt = receipt


class Campaign:
    """Transactional receipts select exact response versions; replay is offline.

    One process owns a campaign directory. New observations belong in a new
    campaign, not an implicit refresh of already-selected evidence. Failed
    attempts are kept in `failures` and never select a URL, so live mode retries it.
    """
    def __init__(self, directory, *, live=False, sender=http_request,
                 now=time.monotonic, sleep=time.sleep, requests_per_second=5,
                 minimum_free_bytes=5 * 1024**3):
        if not 0 < requests_per_second <= 10 or minimum_free_bytes < 0:
            raise ValueError('Expected 0 < requests/second <= 10 and a nonnegative disk reserve')
        self.root = Path(directory).absolute()
        _no_symlinks(self.root)
        _make_dirs(self.root)
        self.live, self.sender, self.now, self.sleep = live, sender, now, sleep
        self.interval, self.minimum_free_bytes = 1 / requests_per_second, minimum_free_bytes
        # Also separates consecutive processes reusing this campaign.
        self.next_request = now() + self.interval
        self.stopped = False
        self.sent_attempts, self.request_log = 0, []
        self.lock = None
        self.db = None

    def __enter__(self):
        _no_symlinks(self.root / '.lock')
        self.lock = (self.root / '.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            path = self.root / 'responses.sqlite3'
            for suffix in ('', '-journal', '-wal', '-shm'):
                _no_symlinks(Path(str(path) + suffix))
            self.db = sqlite3.connect(path)
            self.db.execute('PRAGMA synchronous=FULL')
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            if version == 0:
                # Import the previous receipt format once, without changing it.
                legacy = self.root / 'responses.json'
                _no_symlinks(legacy)
                records = json.loads(legacy.read_text()) if legacy.exists() else {}
                if not isinstance(records, dict):
                    raise AcquisitionError('Invalid response selection; expected a URL-to-record object')
                with self.db:
                    self.db.execute('BEGIN IMMEDIATE')
                    self.db.execute('CREATE TABLE responses (url TEXT PRIMARY KEY, receipt TEXT NOT NULL)')
                    self.db.executemany('INSERT INTO responses VALUES (?, ?)',
                                        ((url, json.dumps(record)) for url, record in records.items()))
                    self.db.execute('PRAGMA user_version=1')
            elif version != 1:
                raise AcquisitionError('Unsupported receipt database version')
            return self
        except Exception:
            if self.db is not None:
                self.db.close()
            self.lock.close()
            raise

    def __exit__(self, *args):
        try:
            self.db.close()
        finally:
            self.lock.close()

    def _record(self, url, record):
        with self.db:
            self.db.execute('INSERT INTO responses VALUES (?, ?)', (url, json.dumps(record)))

    @property
    def records(self):
        """Audit snapshot; normal fetching reads only the requested receipt."""
        return {url: json.loads(record) for url, record in
                self.db.execute('SELECT url, receipt FROM responses')}

    def _save(self, name, value):
        path = self.root / name
        temporary = self.root / (name + '.pending')
        _no_symlinks(path)
        _no_symlinks(temporary)
        with temporary.open('wb') as handle:
            handle.write(_json(value))
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        _sync_dir(self.root)

    def _pace(self):
        if self.stopped or (self.root / 'STOP.json').exists():
            raise AcquisitionError('Campaign stopped; see the initial failure or STOP.json')
        check_space(self.root, self.minimum_free_bytes)
        self.sleep(max(0, self.next_request - self.now()))
        self.next_request = self.now() + self.interval

    def _request(self, url, *args):
        started = self.now()
        self.sent_attempts += 1
        entry = dict(url=url, started_monotonic=started, status=None)
        self.request_log.append(entry)
        try:
            result = self.sender(url, *args)
            entry['status'] = result[0]
        finally:
            entry['elapsed_seconds'] = self.now() - started
        if result[0] == 403:
            self.stopped = True
            try:
                self._save('STOP.json', {'url': url, 'reason': 'HTTP 403; all live work stopped'})
            except OSError as exc:
                raise AcquisitionError('HTTP 403; stop marker could not be saved') from exc
        return result

    def fetch(self, url, declared_by=None):
        """Return exact bytes and receipt with cache_hit; never guess a version. `declared_by` (proposal): an official reference outside the package rule,
        with the evidence that declared it (the filing's index link, or a recorded official response's own native request); kept in its receipt."""
        try:
            return self._fetch(url, declared_by)
        except DownloadError:
            raise  # A recorded HTTP failure need not stop unrelated filings.
        except (StorageError, OSError, sqlite3.Error) as exc:
            self.stopped = True
            raise StorageError('Campaign storage failure: ' + str(exc)) from exc

    def _fetch(self, url, declared_by=None):
        parsed = urlsplit(url)
        if declared_by is None and (parsed.scheme != 'https' or parsed.netloc != 'www.sec.gov'
                or not parsed.path.startswith('/Archives/') or parsed.query or parsed.fragment):
            raise AcquisitionError('Expected an exact SEC Archives URL without query/fragment')
        if declared_by is not None and (not isinstance(declared_by, dict) or parsed.scheme != 'https' or parsed.netloc != 'www.sec.gov' or parsed.fragment):
            raise AcquisitionError('Expected a declared exact official https://www.sec.gov reference without fragment')
        declared = {} if declared_by is None else {'declared_by': declared_by}
        if self.stopped or (self.root / 'STOP.json').exists():
            raise AcquisitionError('Campaign stopped; see the initial failure or STOP.json')
        saved = self.db.execute('SELECT receipt FROM responses WHERE url=?', (url,)).fetchone()
        if saved:
            record = json.loads(saved[0])
            if not isinstance(record, dict) or record.get('url') != url:
                raise AcquisitionError('Invalid cached response identity; cache is not repaired')
            if record.get('error'):
                raise AcquisitionError('Recorded retrieval failure: ' + record['error'])
            data = load_blob(self.root / 'blobs', record.get('sha256'))
            if record.get('bytes') != len(data):
                raise AcquisitionError('Cached response size differs; cache is not repaired')
            return data, dict(record, cache_hit=True)
        if not self.live:
            failed = self.db.execute("SELECT name FROM sqlite_master WHERE name='failures'").fetchone() and self.db.execute(
                'SELECT receipt FROM failures WHERE url=? ORDER BY rowid DESC LIMIT 1', (url,)).fetchone()
            failure = json.loads(failed[0]) if failed else None
            if failure is not None and (not isinstance(failure, dict) or failure.get('url') != url):
                raise AcquisitionError('Invalid recorded failure identity; cache is not repaired')
            raise OfflineCacheMiss('Uncached URL; live acquisition was not enabled', failure)
        started = self.now()
        try:
            data, receipt = download(url, sender=self._request, now=self.now, sleep=self.sleep,
                                     before_send=self._pace)
        except DownloadError as exc:
            with self.db:  # created on first failure, so replays never alter older evidence
                self.db.execute('CREATE TABLE IF NOT EXISTS failures (url TEXT NOT NULL, receipt TEXT NOT NULL)')
                self.db.execute('INSERT INTO failures VALUES (?, ?)', (url, json.dumps(
                    dict(exc.receipt, error=str(exc), elapsed_seconds=self.now() - started, **declared))))
            raise
        # Cookies do not establish filing provenance and are not needed for replay.
        for attempt in receipt['attempts']:
            attempt.get('headers', {}).pop('set-cookie', None)
        record = dict(receipt, sha256=store_blob(self.root / 'blobs', data),
                      bytes=len(data), elapsed_seconds=self.now() - started, **declared)
        self._record(url, record)
        return data, dict(record, cache_hit=False)
