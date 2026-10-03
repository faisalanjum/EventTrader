"""Immutable raw-byte blobs. Source/version/timing receipts belong to the caller."""
import os
from pathlib import Path
import re
import tempfile

from .acquire import AcquisitionError, _compress, _hash, _make_dirs, _no_symlinks, _sync_dir, _uncompress


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
