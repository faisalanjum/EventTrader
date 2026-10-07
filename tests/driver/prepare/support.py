"""Read-only, hash-pinned test fixtures; no downloads or baseline generation."""
import json
import os
from pathlib import Path
import re

from driver.prepare.get.archive import load_blob


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate manifest key: {key}')
        result[key] = value
    return result


class FixtureStore:
    def __init__(self, manifest_path=None, root=None):
        manifest_path = Path(manifest_path) if manifest_path is not None else Path(__file__).with_name('fixtures') / 'manifest.json'
        root = root if root is not None else os.environ.get('PREPARE_TEST_DATA')
        if not root:
            raise AssertionError('Set PREPARE_TEST_DATA to the provisioned immutable fixture store')
        self.root = Path(root).absolute()
        try:
            manifest = json.loads(manifest_path.read_bytes(), object_pairs_hook=_unique)
            if not isinstance(manifest, dict) or manifest.get('schema') != 'prepare-test-fixtures/1':
                raise ValueError('unsupported schema')
            self.assets, self.groups = manifest['assets'], manifest['groups']
            if not isinstance(self.assets, dict) or not isinstance(self.groups, dict):
                raise ValueError('assets and groups must be mappings')
            for name, entry in self.assets.items():
                if (not name or not isinstance(entry, dict)
                        or not isinstance(entry.get('sha256'), str)
                        or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])
                        or type(entry.get('bytes')) is not int or entry['bytes'] < 0
                        or entry.get('role') not in ('input', 'expected')
                        or not isinstance(entry.get('provenance'), dict) or not entry['provenance']):
                    raise ValueError(f'invalid asset: {name}')
            for name, ids in self.groups.items():
                if (not name or not isinstance(ids, list)
                        or any(not isinstance(key, str) or key not in self.assets for key in ids)
                        or len(ids) != len(set(ids))):
                    raise ValueError(f'invalid group: {name}')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise AssertionError(f'Invalid fixture manifest {manifest_path}: {exc}') from exc

    def members(self, group_name):
        if group_name not in self.groups:
            raise AssertionError(f'Unknown fixture group: {group_name}')
        return list(self.groups[group_name])

    def read(self, asset_id):
        if asset_id not in self.assets:
            raise AssertionError(f'Unknown fixture asset: {asset_id}')
        entry = self.assets[asset_id]
        try:
            data = load_blob(self.root / 'blobs', entry['sha256'])
            if len(data) != entry['bytes']:
                raise ValueError('byte length differs from manifest')
            return data
        except (OSError, ValueError) as exc:
            raise AssertionError(f'Fixture {asset_id} ({entry["sha256"]}) unavailable or damaged: {exc}') from exc

    def materialize(self, asset_id, exact_destination_path):
        target = Path(exact_destination_path)
        if target.resolve().is_relative_to(self.root.resolve()):
            raise AssertionError('Fixture store is read-only; use a separate temporary directory')
        data = self.read(asset_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle:
            handle.write(data)
        return target
