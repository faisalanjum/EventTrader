"""Immutable blobs and durable named records; serialization belongs to each caller."""
import errno
import os
from pathlib import Path
import re
import resource
import tempfile

from .acquire import AcquisitionError, _compress, _hash, _make_dirs, _no_symlinks, _sync_dir, _uncompress


def record_path(path):
    """Resolve a logical ROUTE/R name to exactly one final representation."""
    path = Path(path)
    if path.name in ('ROUTE.json.gz', 'R.json.gz'):
        raise ValueError('Use the logical record name without .gz')
    if path.name not in ('ROUTE.json', 'R.json'):
        return path
    compressed = path.with_name(path.name + '.gz')
    _no_symlinks(path); _no_symlinks(compressed)
    if path.exists() and compressed.exists():
        raise AcquisitionError(f'Ambiguous plain and compressed record: {path}')
    return compressed if compressed.exists() else path


def read_record(path):
    """Exact decoded bytes; a selected compressed record never falls back."""
    stored = record_path(path)
    data = stored.read_bytes()
    return _uncompress(data) if stored != Path(path) else data


def make_dir(path, *, parents=False, mode=0o700):
    """Create an exclusive owned directory and persist its name."""
    path = Path(path)
    if parents: _make_dirs(path.parent)
    path.mkdir(mode=mode)
    _sync_dir(path.parent)


def write_record(path, data, *, replace=False, mode=None):
    """Publish exact caller bytes, exclusively by default; only ROUTE/R use gzip6."""
    if not isinstance(data, bytes): raise TypeError('Named records require serialized bytes')
    path = Path(path); existing = record_path(path)
    compressed = path.name in ('ROUTE.json', 'R.json')
    if compressed and replace: raise ValueError('Compressed records are immutable')
    if not replace and existing.exists(): raise FileExistsError(errno.EEXIST, 'Record exists', str(existing))
    target = path.with_name(path.name + '.gz') if compressed else path
    _no_symlinks(target)
    if compressed:
        limit = resource.getrlimit(resource.RLIMIT_FSIZE)[0]
        if limit != resource.RLIM_INFINITY and len(data) > limit:
            raise OSError(errno.EFBIG, 'Decoded record exceeds inherited file limit', str(path))
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.pending-', delete=False) as handle:
        staged = Path(handle.name)
        try:
            handle.write(_compress(data) if compressed else data)
            if mode is not None: os.fchmod(handle.fileno(), mode)
            handle.flush(); os.fsync(handle.fileno())
            if replace: os.replace(staged, target)
            else: os.link(staged, target)
        finally:
            staged.unlink(missing_ok=True)
    _sync_dir(target.parent)


def _path(root, sha256):
    if not isinstance(sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', sha256):
        raise ValueError('Invalid blob SHA-256')
    path = Path(root).absolute() / (sha256 + '.gz')
    _no_symlinks(path)
    return path


def load_blob(root, sha256):
    """Read and verify exact bytes; missing or damaged blobs fail explicitly."""
    data = _uncompress(_path(root, sha256).read_bytes())
    if _hash(data) != sha256:
        raise AcquisitionError('Blob SHA-256 mismatch; cache is not repaired')
    return data


def store_blob(root, data: bytes):
    """Lossless deterministic gzip, verified reuse, atomic no-overwrite publication."""
    if not isinstance(data, bytes):
        raise TypeError('Archive requires bytes before parsing or cleanup')
    sha256 = _hash(data)
    target = _path(root, sha256)
    if target.exists():
        load_blob(root, sha256)
        _sync_dir(target.parent)  # its name may come from a run that stopped before flushing it
        return sha256
    _make_dirs(target.parent)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.pending-', delete=False) as handle:
        staged = Path(handle.name)
        try:
            handle.write(_compress(data))
            handle.flush()
            os.fsync(handle.fileno())
            try:
                os.link(staged, target)
            except FileExistsError:
                load_blob(root, sha256)
        finally:
            staged.unlink()
    _sync_dir(target.parent)  # the blob's name survives power loss before any receipt points at it
    return sha256
