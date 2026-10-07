"""The OCR saved data for the picture tests, read only through support.FixtureStore and the pinned 506-record index (fixtures/manifest.json).

Every input occurrence is an explicit index record: a missing Chandra output, an unrecorded token count or an absent saved reading is a
stated state, never a missing file. Pictures are materialized under the caller's temporary folder. The only path difference allowed
against a saved expectation is the named picture relocation: the materialized path stands where the saved packet has the literal path
of the frozen baseline record (whose normal form must equal the manifest's original_path), in the first line's src attribute and in
record['picture']; nothing else is rewritten or left out."""
import io
import json
import os
from pathlib import Path

from tests.driver.prepare.support import FixtureStore

INDEX = 'real575_20261005/fixture_manifest_20261007/v2/OCR_INPUTS_506.json'
SETS = {'validation120': 120, 'development336': 336, 'hard50': 50}
RUNTIME_KEYS = ('sonnet', 'flags', 'extraction_status', 'format')   # the runtime's own record keys (the status line is the one addition)


class Saved:
    def __init__(self, tmp, store=None):
        self.store = store or FixtureStore()
        self.tmp, self._lines = Path(tmp), {}
        index = json.loads(self.store.read(INDEX))
        self.limit, self.records = index['chandra_max_tokens'], index['records']
        self.by_name = {r['name']: r for r in self.records}
        if len(self.records) != sum(SETS.values()) or len(self.by_name) != len(self.records):
            raise AssertionError('the pinned index must hold 506 distinct input occurrences')

    def text(self, asset_id):
        return self.store.read(asset_id).decode('utf-8')

    def json(self, asset_id):
        return json.loads(self.store.read(asset_id))

    def line(self, asset_id, number):  # one JSON line, split exactly as the saved files were read (universal newlines)
        if asset_id not in self._lines:
            self._lines[asset_id] = list(io.TextIOWrapper(io.BytesIO(self.store.read(asset_id)), encoding='utf-8'))
        return json.loads(self._lines[asset_id][number])

    def picture(self, r):
        path = self.tmp / 'pictures' / r['set'] / r['name']
        if not path.exists():
            self.store.materialize(r['picture'], path)
        return str(path)

    def original(self, r):  # the literal path the saved packets carry, from the frozen baseline record; its normal form is the manifest's
        literal = self.line(r['expected']['off']['asset'], r['expected']['off']['line'])['record']['picture']
        if os.path.normpath(literal) != self.store.assets[r['picture']]['provenance']['original_path']:
            raise AssertionError(f"{r['id']}: the baseline's picture path is not the manifest's original_path")
        return literal

    def inputs(self, r):  # (name, picture path, Chandra HTML or None, generated tokens, free-OCR row or None, (saved reading, its pointer))
        ch = r['chandra']
        html = self.text(ch['asset']) if ch['asset'] else None
        if (ch['state'] == 'present') != (html is not None):
            raise AssertionError(f"{r['id']}: Chandra state and asset disagree")
        if isinstance(ch['tokens_source'], dict) and self.line(ch['tokens_source']['asset'], ch['tokens_source']['line']).get('generation_tokens') != ch['generated_tokens']:
            raise AssertionError(f"{r['id']}: token count differs from its run log")
        free = self.line(r['free']['asset'], r['free']['lines'][-1]) if r['free']['lines'] else None   # the last row wins, as saved
        sr = r['second_reading']
        if sr['asset']:
            row = self.line(sr['asset'], sr['line'])
            if row.get('ok') is not True:
                raise AssertionError(f"{r['id']}: the indexed saved reading is not a successful one")
            second = (row['text'], pointer(sr['asset'], row))
        else:
            second = (None, None)
        return r['name'], self.picture(r), html, ch['generated_tokens'], free, second

    def relocated(self, r, text, rec):  # the named picture relocation, and nothing else
        path, orig = self.picture(r), self.original(r)
        first, sep, rest = text.partition('\n')
        if f'src="{path}"' not in first or path in rest:
            raise AssertionError(f"{r['id']}: the picture path is not where the packet format puts it")
        text = first.replace(f'src="{path}"', f'src="{orig}"', 1) + sep + rest
        if rec is not None:
            if rec.get('picture') != path:
                raise AssertionError(f"{r['id']}: record['picture'] is not the materialized picture")
            rec = dict(rec, picture=orig)
        return text, rec


def pointer(asset_id, row):  # the saved reading's source pointer, in the format the packets record
    if asset_id.endswith('/validation_20261006/sonnet.jsonl'):
        return 'sonnet.jsonl#' + row['image']
    return asset_id.removeprefix('real575_20261005/') + '#' + row['image']


def body(text, rec):  # the packet text without the one status line; the record without the runtime's own keys
    lines = text.split('\n')
    if len(lines) < 2 or lines[1] != rec['extraction_status'] or not lines[1].startswith('[EXTRACTION STATUS: '):
        raise AssertionError('the status line is not the second line')
    return '\n'.join(lines[:1] + lines[2:]), {k: v for k, v in json.loads(json.dumps(rec)).items() if k not in RUNTIME_KEYS}


def status_follows_flags(line, flags):
    return (('MISSING' in line) == ('no reading' in flags) and ('INCOMPLETE' in line) == ('cut off' in flags)
            and ('possible skipped' in line) == ('missed' in flags) and ('unconfirmed' in line) == ('no support' in flags))
