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
import zlib

from .transport import download


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


def _decode_member(body, filename):
    # SEC doubles leading dots inside TEXT. Preserve all other file whitespace.
    body = re.sub(rb'^\.\.', b'.', body, flags=re.M)
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
    decoded = bytearray()
    for line in lines[1:-1]:
        if not line:
            continue  # A zero-length UU line may be entirely trimmed by SEC.
        count = (line[0] - 32) & 63
        width = ((count + 2) // 3) * 4
        if count > 45 or len(line) > width + 1 or any(not 32 <= byte <= 96 for byte in line):
            raise AcquisitionError('Invalid uuencode line')
        # a2b_uu restores trimmed spaces. Exclude unused padding sextets, which
        # SEC can leave nonzero; the length prefix determines the original bytes.
        decoded.extend(binascii.a2b_uu(line[:1 + (count * 8 + 5) // 6]))
    return bytes(decoded)


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


def parse_package(data, accession, cik, form):
    """Return deterministic manifest and filename-to-bytes map; ranges are half-open."""
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
        cursor = header.end()
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
            body = _decode_member(match[2], name)
            if name in files and files[name] != body:
                raise AcquisitionError('Duplicate member path conflict: ' + name)
            files[name] = body
            members.append(dict(fields, bytes=len(body), sha256=_hash(body),
                                format_hint=_format_hint(body), package_range=list(match.span())))
            cursor = match.end()
        if not re.fullmatch(rb'</SEC-DOCUMENT>\r?\n?', data[cursor:]) or not members:
            raise AcquisitionError('Incomplete or empty SEC package')
        for name in files:
            if any(str(parent) in files for parent in Path(name).parents if str(parent) != '.'):
                raise AcquisitionError('Member file/directory path conflict: ' + name)
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, AcquisitionError):
            raise
        raise AcquisitionError('Invalid SEC metadata encoding or date: ' + str(exc)) from exc
    manifest = dict(version=2, decoder='sec-framing-uu-v1',
                    identity=dict(accession=accession, ciks=ciks, form=form),
                    acceptance=dict(printed=accepted, timezone='America/New_York'),
                    package=dict(path='submission.txt.gz', bytes=len(data), sha256=_hash(data)),
                    document_count=dict(stated=int(count), actual=len(members)),
                    header_range=list(header.span(2)), members=members)
    return manifest, files


def _no_symlinks(path):
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise AcquisitionError('Symlink output/cache path is unsupported')


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
        raise AcquisitionError('Invalid cache: ' + str(exc)) from exc


def read_package(path):
    """Verify and unpack a saved version once; return manifest and filename-to-bytes map."""
    data, stored = _read_cache(Path(path).absolute())
    try:
        identity = stored['identity']
        manifest, files = parse_package(data, identity['accession'], identity['ciks'][0], identity['form'])
        if manifest != stored:
            raise AcquisitionError('Immutable cache manifest differs')
        return manifest, files
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise AcquisitionError('Invalid cache: ' + str(exc)) from exc


def acquire(accession, cik, form, output, *, package=None, sha256=None, live=False,
            minimum_free_bytes=5 * 1024**3):
    """Publish/verify one version; supplied gzip is immutable and hard-linked."""
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
        manifest = parse_package(data, accession, identity['cik'], form)[0]
        parent = output / accession
        target = parent / manifest['package']['sha256']
        _no_symlinks(target)
        if target.exists():
            cached_data, cached_manifest = _read_cache(target)
            if cached_data != data or cached_manifest != manifest:
                raise AcquisitionError('Immutable cache differs')
            return target
        check_space(output, minimum_free_bytes)
        parent.mkdir(parents=True, exist_ok=True)
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
            os.rename(staged, target)
        finally:
            if staged.exists():
                shutil.rmtree(staged)
        return target
    except (OSError, AcquisitionError) as exc:
        fatal = isinstance(exc, StorageError) or getattr(exc, 'errno', None) in (errno.ENOSPC, errno.EDQUOT, errno.EXDEV)
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
