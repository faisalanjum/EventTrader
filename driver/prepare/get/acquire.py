"""Acquire one SEC submission package; readability is a later preparation step."""
import argparse
import binascii
from datetime import datetime
import errno
import hashlib
import gzip
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import quote
import zlib

from .transport import DownloadError, download


class AcquisitionError(ValueError):
    """Invalid input, package or immutable cache; no successful version published."""


class StorageError(AcquisitionError):
    """Stop the entire run; more filings cannot resolve a storage failure."""


def check_space(path, minimum_free_bytes=5 * 1024**3):
    path = Path(path).absolute()
    while not path.exists():
        path = path.parent
    free = shutil.disk_usage(path).free
    if free < minimum_free_bytes:
        raise StorageError(f'Low disk space: {free} bytes free; reserve is {minimum_free_bytes}')


def _identity(accession, cik, form):
    if (not all(isinstance(value, str) for value in (accession, cik, form))
            or not re.fullmatch(r'[0-9]{10}-[0-9]{2}-[0-9]{6}', accession)
            or not re.fullmatch(r'[0-9]{1,10}', cik) or not int(cik)
            or not form or form != form.strip() or not form.isascii()
            or any(ord(char) < 32 for char in form)):
        raise AcquisitionError('Invalid expected accession, CIK or form')
    return dict(accession=accession, cik=cik.zfill(10), form=form)


def _url(identity):
    accession = identity['accession']
    return (f"https://www.sec.gov/Archives/edgar/data/{int(identity['cik'])}/"
            f"{accession.replace('-', '')}/{accession}.txt")


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def _filename(value):
    if (not value or value.startswith('/') or '\\' in value or ':' in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise AcquisitionError('Unsafe member filename')
    return value


def _uu_invalid(line):
    count = (line[0] - 32) & 63
    return count > 45 or len(line) > ((count + 2) // 3) * 4 + 1 or any(not 32 <= byte <= 96 for byte in line)


def _decode(body, filename, dash=False):
    """Exact decoding of one TEXT (member wrapper, uudecode). dash: read the last uuencoded line as having lost a
    leading '- ' (only a final 13-byte line can start with it: every other line holds 45 bytes)."""
    wrapper = re.match(rb'<(XBRL|XML|PDF|JSON)>\r?\n', body)
    if wrapper:
        close = re.search(rb'</' + wrapper[1] + rb'>\r?\n?\Z', body)
        if not close:
            raise AcquisitionError('Unclosed SEC member wrapper')
        body = body[wrapper.end():close.start()]
    if not body.startswith(b'begin '):
        return body
    lines = body.split(b'\n')
    if lines[-1] == b'':
        lines.pop()
    lines = [line[:-1] if line.endswith(b'\r') else line for line in lines]
    header = re.fullmatch(rb'begin [0-7]{3} (.+)', lines[0])
    if not header or header[1].decode('utf-8') != filename or lines[-1] != b'end':
        raise AcquisitionError('Invalid uuencode filename or framing')
    data_lines = [i for i, line in enumerate(lines[1:-1], 1) if line not in (b'', b'`', b' ')]
    decoded = bytearray()
    for i, line in enumerate(lines[1:-1], 1):
        if not line:
            continue  # A zero-length UU line may be entirely trimmed by SEC.
        if dash and i == data_lines[-1]:
            line = b'- ' + line
        if _uu_invalid(line):
            raise AcquisitionError('Invalid uuencode line')
        count = (line[0] - 32) & 63
        # a2b_uu restores trimmed spaces. Exclude unused padding sextets, which
        # SEC can leave nonzero; the length prefix determines the original bytes.
        decoded.extend(binascii.a2b_uu(line[:1 + (count * 8 + 5) // 6]))
    return bytes(decoded)


def _readings(text, filename):
    """Every exact reading SEC's escaping allows, as [(text, bytes)], and whether proof is needed. Escaping undone: one
    dot removed from each line starting with '..' (older packages doubled leading dots), and a '- ' put back on a last
    uuencoded line that cannot be read without it (SEC dropped it once in 1,667 such lines; a line it can be read
    without is taken as published). Such a reading has text None: no package TEXT holds it, so only its bytes can
    prove it. Proof is needed whenever a reading undoes escaping."""
    texts = [text] + ([re.sub(rb'(?m)^\.\.', b'.', text)] if re.search(rb'(?m)^\.\.', text) else [])
    readings, guessed, failure = [], False, None
    for variant in texts:
        for dash in (False, True):
            try:
                readings.append((None if dash else variant, _decode(variant, filename, dash)))
                guessed |= dash
                break
            except AcquisitionError as exc:
                failure = exc
    if not readings:
        raise failure
    return readings, guessed or len(texts) > 1


def _one_run(expected, copy):
    """[start, end] of the one run `copy` inserts into `expected`, [] if they are equal, None otherwise."""
    extra = len(copy) - len(expected)
    if extra <= 0:
        return [] if copy == expected else None
    low, high = 0, len(expected)  # longest common prefix, by halving; each compare runs in C
    while low < high:
        middle = (low + high + 1) // 2
        if copy[:middle] == expected[:middle]:
            low = middle
        else:
            high = middle - 1
    return [low, low + extra] if copy[low + extra:] == expected[low:] else None


def _prove(copy, readings, before, after):
    """(bytes, how) of the one file SEC's own copy proves: the copy equals a reading's decoded bytes, or its <DOCUMENT>
    block from the package (before + TEXT + after, the envelope exact). It may also hold one run inserted inside those
    bytes or that TEXT, shorter than them (SEC's web server adds a script to some pages; most of the copy must still be
    the file). Runs count only when no reading fits exactly, since a run could hide a dot. All fitting readings must
    give the same bytes; otherwise None."""
    found = {False: {}, True: {}}  # exact fits, fits with one inserted run
    for form, head, tail in (('bytes', b'', b''), ('block', before, after)):
        if len(copy) < len(head) + len(tail) or not (copy.startswith(head) and copy.endswith(tail)):
            continue
        inner = copy[len(head):len(copy) - len(tail)]
        for text, data in readings:
            body = data if form == 'bytes' else text
            if body is None:
                continue  # a '- ' put back: a block holding the package's own damaged line proves nothing
            run = _one_run(body, inner)
            if run == [] or (run and run[1] - run[0] < len(body)):
                found[bool(run)][data] = dict(form=form, inserted=[len(head) + at for at in run])
    fits = found[False] or found[True]
    return fits.popitem() if len(fits) == 1 else None


def _format_hint(data):
    for prefix, hint in ((b'%PDF-', 'pdf'), (b'PK\x03\x04', 'zip'), (b'\xff\xd8\xff', 'jpeg'),
                         (b'\x89PNG\r\n\x1a\n', 'png'), (b'GIF87a', 'gif'), (b'GIF89a', 'gif')):
        if data.startswith(prefix):
            return hint
    prefix = data.lstrip()[:64].lower()
    if prefix.startswith(b'<?xml'):
        return 'xml'
    if re.match(rb'(?:<!doctype\s+html\b|<html(?:\s|>))', prefix):
        return 'html'
    return 'unknown'


def parse_package(data, accession, cik, form, proofs=None, fetch=None):
    """Return deterministic manifest and filename-to-bytes map; ranges are half-open. A file needing proof uses its
    recorded member entry in `proofs` (package offset -> entry; replay, no network), else SEC's copy from `fetch(url)`
    (bytes or None); without proof it is listed unresolved and left out of the files."""
    identity = _identity(accession, cik, form)
    header = re.match(rb'<SEC-DOCUMENT>([^\r\n]*)\r?\n(<SEC-HEADER>.*?</SEC-HEADER>)\r?\n', data, re.S)
    if not header:
        raise AcquisitionError('Malformed SEC package header')
    try:
        def field(pattern):
            values = re.findall(pattern, header[2], re.M)
            if len(values) != 1:
                raise AcquisitionError('Missing or ambiguous SEC header field')
            return values[0].decode('ascii').strip()

        ciks = sorted({_identity(accession, value.decode('ascii').strip(), form)['cik']
                       for value in re.findall(
                           rb'^[ \t]*CENTRAL INDEX KEY:[ \t]*([^\r\n]*)', header[2], re.M)})
        if (field(rb'^[ \t]*ACCESSION NUMBER:[ \t]*([^\r\n]*)') != accession
                or field(rb'^[ \t]*CONFORMED SUBMISSION TYPE:[ \t]*([^\r\n]*)') != form
                or identity['cik'] not in ciks
                or header[1].split(b' ', 1)[0] != accession.encode() + b'.txt'):
            raise AcquisitionError('Package identity differs from expected filing')
        accepted = field(rb'^<ACCEPTANCE-DATETIME>([^\r\n]*)')
        if not re.fullmatch(r'[0-9]{14}', accepted):
            raise AcquisitionError('Invalid acceptance timestamp')
        datetime.strptime(accepted, '%Y%m%d%H%M%S')
        count = field(rb'^[ \t]*PUBLIC DOCUMENT COUNT:[ \t]*([^\r\n]*)')
        if not re.fullmatch(r'[0-9]+', count):
            raise AcquisitionError('Invalid document count')
        members, files = [], {}
        # SEC can leave empty lines between framing tags (seen once: Landstar 0001193125-23-048874). Only empty
        # LF/CRLF lines outside every TEXT block are skipped; spaces or any other byte there still fail.
        blank_lines = re.compile(rb'(?:\r?\n)*')
        cursor = blank_lines.match(data, header.end()).end()
        document = re.compile(rb'<DOCUMENT>\r?\n(.*?)<TEXT>\r?\n(.*?)</TEXT>\r?\n</DOCUMENT>\r?\n', re.S)
        while data.startswith(b'<DOCUMENT>', cursor):
            match = document.match(data, cursor)
            if (not match
                    or not re.fullmatch(rb'(?:<(?:TYPE|SEQUENCE|FILENAME|DESCRIPTION)>[^\r\n]*\r?\n)+', match[1])
                    or re.search(rb'^</?(?:DOCUMENT|TEXT)>\r?$', match[2], re.M)):
                raise AcquisitionError('Malformed SEC document framing or metadata')
            fields = {}
            for key in ('TYPE', 'SEQUENCE', 'FILENAME', 'DESCRIPTION'):
                values = re.findall(b'^<' + key.encode() + rb'>([^\r\n]*)', match[1], re.M)
                if len(values) > 1 or (key != 'DESCRIPTION' and (not values or not values[0])):
                    raise AcquisitionError('Missing or ambiguous member metadata')
                fields[key.lower()] = values[0].decode('utf-8') if values else None
            if not re.fullmatch(r'[0-9]+', fields['sequence']):
                raise AcquisitionError('Invalid member sequence')
            name = _filename(fields['filename'])
            readings, needs_proof = _readings(match[2], name)
            body, proof = readings[0][1], None
            if needs_proof:
                body, recorded = None, (proofs or {}).get(match.start())
                if recorded:
                    proof = recorded['proof']
                    body = next((read for _, read in readings if _hash(read) == recorded['sha256']), None)
                    if body is None and 'unresolved' not in proof:
                        raise AcquisitionError('Recorded proof matches no reading: ' + name)
                elif fetch:
                    url = _url(identity).rsplit('/', 1)[0] + '/' + quote(name)
                    copy = fetch(url)
                    fit = copy is not None and _prove(copy, readings, data[match.start():match.start(2)],
                                                      data[match.end(2):match.end()])
                    body, how = fit or (None, dict(unresolved='SEC copy unavailable' if copy is None
                                                   else 'SEC copy fits no single reading'))
                    proof = dict(how, url=url, copy_sha256=None if copy is None else _hash(copy))
                else:
                    proof = dict(unresolved='not checked against SEC copy')
            if body is not None:
                if name in files and files[name] != body:
                    raise AcquisitionError('Duplicate member path conflict: ' + name)
                files[name] = body
            kept = body is not None
            members.append(dict(fields, bytes=len(body) if kept else None, sha256=_hash(body) if kept else None,
                                format_hint=_format_hint(body) if kept else None, package_range=list(match.span()),
                                **({} if proof is None else dict(proof=proof))))
            cursor = blank_lines.match(data, match.end()).end()
        if not re.fullmatch(rb'</SEC-DOCUMENT>\r?\n?', data[cursor:]) or not members:
            raise AcquisitionError('Incomplete or empty SEC package')
        for name in files:
            if any(str(parent) in files for parent in Path(name).parents if str(parent) != '.'):
                raise AcquisitionError('Member file/directory path conflict: ' + name)
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, AcquisitionError):
            raise
        raise AcquisitionError('Invalid SEC metadata encoding or date: ' + str(exc)) from exc
    proven = any('proof' in member for member in members)  # v1 = nothing needed proof: decoding unchanged
    manifest = dict(version=2, decoder='sec-framing-uu-v2' if proven else 'sec-framing-uu-v1',
                    identity=dict(accession=accession, ciks=ciks, form=form),
                    acceptance=dict(printed=accepted, timezone='America/New_York'),
                    package=dict(path='submission.txt.gz', bytes=len(data), sha256=_hash(data)),
                    document_count=dict(stated=int(count), actual=len(members)),
                    header_range=list(header.span(2)), members=members)
    return manifest, files


def _no_symlinks(path):
    try:
        linked = any(parent.is_symlink() for parent in (path, *path.parents))
    except OSError as exc:  # a path's metadata unreadable (a missing path is not an error here): the disk, not the filing
        raise StorageError(f'Path check failed: {path}: {exc}') from exc
    if linked:
        raise AcquisitionError('Symlink output/cache path is unsupported')


def _sync_dir(path):
    """Make new or renamed names in a directory survive power loss; a file's own fsync does not."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:  # the disk no longer promises what was written: stop the whole run
        raise StorageError(f'Directory flush failed: {path}: {exc}') from exc


def _make_dirs(path):
    """mkdir -p whose newly created directories are durable too."""
    path = Path(path)
    if not path.is_dir():
        _make_dirs(path.parent)
        path.mkdir(exist_ok=True)
        _sync_dir(path.parent)


def _compress(data):
    result = io.BytesIO()
    with gzip.GzipFile(fileobj=result, mode='wb', compresslevel=6, mtime=0) as handle:
        handle.write(data)
    return result.getvalue()


def _uncompress(data):
    try:
        return gzip.decompress(data)
    except (OSError, EOFError, zlib.error) as exc:
        raise AcquisitionError('Invalid compressed package: ' + str(exc)) from exc


def _read_cache(target):
    try:
        _no_symlinks(target)
        paths = list(target.iterdir())
        if ({path.name for path in paths} != {'submission.txt.gz', 'manifest.json', 'receipt.json'}
                or any(path.is_symlink() or not path.is_file() for path in paths)):
            raise AcquisitionError('Conflicting paths in immutable cache')
        data = _uncompress((target / 'submission.txt.gz').read_bytes())
        manifest = json.loads((target / 'manifest.json').read_bytes())
        if _hash(data) != manifest['package']['sha256'] or target.name != manifest['package']['sha256']:
            raise AcquisitionError('Immutable cache package hash differs')
        if not isinstance(json.loads((target / 'receipt.json').read_bytes()), dict):
            raise AcquisitionError('Invalid immutable cache receipt')
        return data, manifest
    except (OSError, ValueError, KeyError, TypeError) as exc:
        error = (StorageError if isinstance(exc, StorageError) or isinstance(exc, OSError) and exc.errno != errno.ENOENT
                 else AcquisitionError)
        raise error('Invalid cache: ' + str(exc)) from exc


def read_package(path):
    """Verify and unpack a saved version once; return manifest and filename-to-bytes map."""
    data, stored = _read_cache(Path(path).absolute())
    try:
        identity = stored['identity']
        manifest, files = parse_package(data, identity['accession'], identity['ciks'][0], identity['form'],
                                        proofs={m['package_range'][0]: m for m in stored['members'] if 'proof' in m})
        if manifest != stored:
            raise AcquisitionError('Immutable cache manifest differs')
        return manifest, files
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise AcquisitionError('Invalid cache: ' + str(exc)) from exc


def acquire(accession, cik, form, output, *, package=None, sha256=None, live=False,
            minimum_free_bytes=5 * 1024**3, fetch=None, repair=False):
    """Publish/verify one version; supplied gzip is immutable and hard-linked. `fetch(url)` gives SEC's own copy of a
    file needing proof — the caller's campaign, so cache, request limit and 403 stop are shared; without it such a file
    stays unresolved. A saved version of the same package whose manifest differs is
    moved to <output>_superseded/ (kept whole) when it has an unresolved file (never usable) or with `repair`;
    otherwise it fails."""
    identity = _identity(accession, cik, form)
    if (package is None) == (not live) or (package is not None and not sha256) or (live and sha256 is not None):
        raise AcquisitionError('Use --package with --sha256, or --live')
    if sha256 is not None and not re.fullmatch(r'[0-9a-fA-F]{64}', sha256):
        raise AcquisitionError('Invalid SHA-256')
    output = Path(output).absolute()
    _no_symlinks(output)
    receipt = None
    compressed_source = None
    try:
        if live:
            check_space(output, minimum_free_bytes)
            data, receipt = download(_url(identity))
        else:
            _no_symlinks(Path(package).absolute())
            data = Path(package).read_bytes()
            if data.startswith(b'\x1f\x8b'):
                compressed_source = Path(package)
                data = _uncompress(data)
            if _hash(data) != sha256.lower():
                raise AcquisitionError('Supplied package SHA-256 mismatch; cache is not repaired')
            receipt = dict(source='supplied-package', retrieved_at=None)
        manifest = parse_package(data, accession, identity['cik'], form, fetch=fetch)[0]
        parent = output / accession
        target = parent / manifest['package']['sha256']
        _no_symlinks(target)
        if target.exists():
            cached_data, cached_manifest = _read_cache(target)
            unusable = any('unresolved' in member.get('proof', {}) for member in cached_manifest['members'])
            if cached_data != data or (cached_manifest != manifest and not (repair or unusable)):
                raise AcquisitionError('Immutable cache differs')
            if cached_manifest == manifest:
                _sync_dir(parent)  # its name may come from a run that stopped before flushing it
                return target
            kept = output.with_name(output.name + '_superseded') / accession / (
                target.name + '.' + _hash(_json(cached_manifest))[:16])
            _make_dirs(kept.parent)
            os.rename(target, kept)  # the old version stays whole, only moved
            _sync_dir(kept.parent)
            _sync_dir(parent)
        check_space(output, minimum_free_bytes)
        _make_dirs(parent)
        staged = Path(tempfile.mkdtemp(prefix='.pending-', dir=parent))
        try:
            contents = {'manifest.json': _json(manifest), 'receipt.json': _json(receipt)}
            if compressed_source is not None:
                os.link(compressed_source, staged / 'submission.txt.gz', follow_symlinks=False)
            else:
                contents['submission.txt.gz'] = _compress(data)
            for name, body in contents.items():
                path = staged / name
                with path.open('xb') as handle:
                    handle.write(body)
                    handle.flush()
                    os.fsync(handle.fileno())
            _sync_dir(staged)  # the three names inside the version
            os.rename(staged, target)
            _sync_dir(parent)  # the version's own name, before any caller records success
        finally:
            if staged.exists():
                shutil.rmtree(staged)
        return target
    except (OSError, AcquisitionError) as exc:
        # any filesystem error but a missing file is the disk, not the filing; DownloadError is transport
        fatal = isinstance(exc, StorageError) or (isinstance(exc, OSError)
                 and not isinstance(exc, DownloadError) and exc.errno != errno.ENOENT)
        error = (StorageError if fatal else AcquisitionError)(str(exc))
        error.receipt = getattr(exc, 'receipt', receipt)
        raise error from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('accession', 'cik', 'form', 'output'):
        parser.add_argument('--' + name, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--package')
    source.add_argument('--live', action='store_true')
    parser.add_argument('--sha256')
    args = parser.parse_args(argv)
    try:
        print(acquire(**vars(args)))
    except AcquisitionError as exc:
        print(str(exc), file=sys.stderr)
        if getattr(exc, 'receipt', None):
            print(_json(exc.receipt).decode(), file=sys.stderr, end='')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
