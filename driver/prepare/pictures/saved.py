"""OCR supplements of saved extraction; the source attempts remain immutable."""
import hashlib
import copy
import json
import os
import sys
from pathlib import Path

from ..get import archive
from ..get.acquire import AcquisitionError, StorageError, read_package, _sync_dir
from ..job import clean_row
from ..reconstruct import _custody
from . import join, pdf, readers, worker

sha = lambda b: hashlib.sha256(b).hexdigest()
encode = lambda value: (json.dumps(value, sort_keys=True, ensure_ascii=False) + '\n').encode()


def read_attempt(attempt, folder, make_readers):
    """Read the exact prepared images already bound by an extraction completion."""
    attempt = Path(attempt).absolute()
    route, prepared, custody = _custody(attempt)
    pins = {u['input']['input_sha256'] for u in route.get('units') or []
            if isinstance(u.get('input'), dict) and 'input_sha256' in u['input']}
    images = {pin: archive.load_blob(prepared, pin) for pin in pins}
    _, pictures = join.join(route, images, folder, make_readers)
    return dict(source=dict(attempt=str(attempt), file_id=route['file_id'], sha256=route['sha256'],
                            route_sha256=custody['route_sha256'], complete_sha256=custody['complete_sha256']),
                pictures=pictures)


def read_pdf(raw, file_id, source_sha256, folder, make_readers):
    route, images = pdf.pages(raw, file_id, source_sha256)
    _, pictures = join.join(route, images, folder, make_readers)
    return dict(source=dict(file_id=file_id, sha256=source_sha256), route=route, pictures=pictures)


def issues(document):
    """Existing native/input/reader uncertainty, separate from transcription accuracy."""
    reasons = []
    route = document.get('route') or {}
    if route and route.get('status') != 'OK': reasons.append(f"native PDF {route.get('status')}: {route.get('error') or route.get('unprocessed') or 'unread content'}")
    for picture in document['pictures']:
        name = picture['occurrence']
        if 'error' in picture['input']: reasons.append(f"{name}: {picture['input']['error']}")
        if picture.get('picture_error'): reasons.append(f"{name}: {picture['picture_error']}")
        for role, record in (picture.get('records') or {}).items():
            if record['status'] != 'complete': reasons.append(f"{name}: {role} {record['status']}")
        for flag in picture.get('flags') or []:
            if flag != 'table': reasons.append(f'{name}: {flag}')  # table alone is a risk, not demonstrated missing content
        if any((block.get('free_ocr') or {}).get('conflicts') for block in (picture.get('packet_record') or {}).get('blocks') or []):
            reasons.append(f'{name}: retained free-OCR disagreement')
    return reasons


def _pinned(reference):
    body = Path(reference['path']).read_bytes()
    if sha(body) != reference['sha256']: raise ValueError('saved source file differs from its pin')
    return json.loads(body)


def _source(receipt):
    plan, result, original = (_pinned(receipt[k]) for k in ('plan', 'result', 'manifest'))
    manifest, members = read_package(receipt['version'])
    if manifest != original or manifest['package']['sha256'] != receipt['package_sha256']: raise ValueError('OCR source package differs')
    if result.get('plan_sha256') != receipt['plan']['sha256']: raise ValueError('OCR source result names another plan')
    commands = {r['file_id']: r for r in plan['source_commands']}
    rows = result['rows']
    if len(commands) != len(plan['source_commands']) or sorted(r['file_id'] for r in rows) != sorted(commands):
        raise ValueError('OCR source rows do not match the selected source commands')
    for command in commands.values():
        if sha(members[command['filename']]) != command['source_sha256']: raise ValueError('OCR command source bytes differ')
    return commands, rows, manifest, members


def _inventory(commands, rows, manifest):
    """One source-owned inventory for execution and saved-result verification."""
    wanted, reasons = [], []
    def attempt(path, label, command):
        path = Path(path).absolute()
        route, _, custody = _custody(path)
        if (route['file_id'], route['sha256']) != (command['file_id'], command['source_sha256']):
            raise ValueError('OCR attempt does not belong to the selected source command')
        source = dict(attempt=str(path), file_id=route['file_id'], sha256=route['sha256'],
                      route_sha256=custody['route_sha256'], complete_sha256=custody['complete_sha256'], view=label)
        wanted.append((source, route))
        child = path / 'source_reading'
        if (child / 'COMPLETE.json').exists(): attempt(child, label + '/source_reading', command)
    for row in rows:
        if row.get('outcome') != 'verified_saved_output' or not clean_row(row):
            reasons.append(f"{row['file_id']}: extraction not verified; OCR not attempted"); continue
        command = commands[row['file_id']]
        if command['dispatch'] != 'html': continue
        attempt(row['attempt'], 'initial', command)
        for state in row.get('states') or {}: attempt(Path(row['attempt']) / 'states' / state, state, command)
    for member in manifest['members']:
        if member.get('format_hint') == 'pdf': wanted.append((dict(file_id=member['filename'], sha256=member['sha256']), None))
    return wanted, reasons


def _factories(config):
    """Existing reader interface, constructed only when there are prepared images."""
    made = {}
    def make(role):
        if role not in made:
            if role == 'chandra': made[role] = readers.chandra_vllm(config['endpoint'], config['identity'], config.get('timeout', 660))
            else:
                pp, ox = readers.free_readers(); made.update(pp=pp, ox=ox)
        return made[role]
    return {role: (lambda role=role: make(role)) for role in join.READERS}


def _snapshot(document, folder):
    """Immutable raw snapshots: later worker error retries must not change old supplements."""
    for picture in document['pictures']:
        for role, record in (picture.get('records') or {}).items():
            pin = archive.store_blob(folder / 'readings', encode(record))
            picture['records'][role] = dict(root=str(folder / 'readings'), sha256=pin)


def _restore(reference):
    try: return json.loads(archive.load_blob(reference['root'], reference['sha256']))
    except StorageError: raise
    except (AcquisitionError, ValueError, OSError, EOFError) as error: raise ValueError('OCR record does not restore') from error


def verify(reference, receipt=None):
    """Restore the bound source, every input and raw reader record; no OCR call or rerender."""
    report = _restore(reference)
    if report.get('schema') != 'prepare-ocr-supplement/1' or report.get('fidelity') != 'unverified': raise ValueError('unknown OCR supplement contract')
    if receipt is not None and report['source'] != receipt: raise ValueError('OCR supplement belongs to another source receipt')
    commands, rows, manifest, members = _source(report['source'])
    inventory, reasons = _inventory(commands, rows, manifest)
    if encode([d['source'] for d in report['documents']]) != encode([s for s, _ in inventory]):
        raise ValueError('OCR document/state inventory differs from source')
    restored = []
    for document, (expected, route) in zip(report['documents'], inventory):
        document = copy.deepcopy(document)
        source = document['source']
        if route is None:
            route = document['route']
            if (route['file_id'], route['sha256']) != (source['file_id'], source['sha256']): raise ValueError('OCR PDF source changed')
            import pypdfium2 as pdfium
            try: original = pdfium.PdfDocument(members[source['file_id']])
            except pdfium.PdfiumError:
                if route.get('status') != 'FAILED' or route['units']: raise ValueError('unreadable PDF presented as read')
            else:
                try:
                    if len(route['units']) != len(original) or [u['page'] for u in route['units']] != list(range(1, len(original) + 1)):
                        raise ValueError('OCR PDF page inventory differs from original')
                    if len(route.get('attachments') or []) != original.count_attachments(): raise ValueError('OCR PDF attachment inventory differs')
                    if original.count_attachments() and route.get('status') == 'OK': raise ValueError('unread PDF attachments presented as handled')
                finally: original.close()
        expected_pictures = [dict(unit=k, id=u['id'], occurrence=f"{route['file_id']}#{u['id']}", input=u.get('input'))
                             for k, u in enumerate(route['units']) if u.get('kind') == 'image']
        if encode([{k: p.get(k) for k in ('unit', 'id', 'occurrence', 'input')} for p in document['pictures']]) != encode(expected_pictures):
            raise ValueError('OCR image occurrence inventory differs from source')
        for picture in document['pictures']:
            if 'input_sha256' not in picture['input']: continue
            pin = picture['input']['input_sha256']
            data = archive.load_blob(picture['archive']['root'], pin)
            if picture['archive']['sha256'] != pin or set(picture.get('records') or {}) != set(join.READERS):
                raise ValueError('OCR picture input/reader account differs')
            for role, saved in picture['records'].items():
                record = _restore(saved)
                check = type('Status', (), {'status': staticmethod(readers._chandra_status if role == 'chandra' else readers._free_status)})
                worker._check(record, check)
                if record['image_sha256'] != pin or record['settings'] != report['reader_settings'][role]:
                    raise ValueError('OCR reader identity differs from its input/settings')
                picture['records'][role] = record
            fields, _ = join._packet(pin, data, *(picture['records'][r] for r in join.READERS), False, None)
            if encode(fields) != encode({k: picture.get(k) for k in fields}): raise ValueError('OCR packet differs from raw readings')
        restored.append(document)
        if (document.get('status'), document.get('reasons')) != _status([document], []):
            raise ValueError('OCR document outcome differs from its retained evidence')
    status, reasons = _status(restored, reasons)
    if reference.get('status') != report['status'] or (report['status'], report['reasons']) != (status, reasons):
        raise ValueError('OCR outcome differs from its retained evidence')
    return report


def _status(documents, reasons):
    reasons = list(reasons)
    failed = any(record['status'] == 'error' for doc in documents for p in doc['pictures'] for record in (p.get('records') or {}).values())
    for doc in documents:
        reasons += [f"{doc['source']['file_id']} {doc['source'].get('view', 'PDF')}: {r}" for r in issues(doc)]
    return ('failed' if failed else 'incomplete' if reasons else 'complete'), reasons


def run(receipt, config, folder, make_readers=None):
    """One filing's OCR supplement, using the existing reader cache; originals are never modified."""
    folder = Path(folder).absolute()
    commands, rows, manifest, members = _source(receipt)
    factories, initialized = make_readers or _factories(config), {}
    def make(role):
        if role not in initialized: initialized[role] = factories[role]()
        return initialized[role]
    makers = {role: (lambda role=role: make(role)) for role in join.READERS}
    inventory, reasons = _inventory(commands, rows, manifest)
    documents = []
    for source, route in inventory:
        document = (read_attempt(source['attempt'], folder / 'cache', makers) if route is not None else
                    read_pdf(members[source['file_id']], source['file_id'], source['sha256'], folder / 'cache', makers))
        document['source'] = source
        documents.append(document)
    status, reasons = _status(documents, reasons)
    for doc in documents:
        doc['status'], doc['reasons'] = _status([doc], [])
        doc['fidelity'] = 'unverified'
        _snapshot(doc, folder)
    code = sha(b''.join(p.name.encode() + p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py'))))
    report = dict(schema='prepare-ocr-supplement/1', source=receipt, code_sha256=code,
                  reader_settings={role: reader.settings for role, reader in initialized.items()},
                  status=status, fidelity='unverified', reasons=reasons, documents=documents)
    pin = archive.store_blob(folder / 'manifests', encode(report))
    reference = dict(root=str(folder / 'manifests'), sha256=pin, status=status, fidelity='unverified', reasons=reasons)
    verify(reference, receipt)
    folder.mkdir(parents=True, exist_ok=True)
    pending = folder / 'RESULT.pending'
    with pending.open('wb') as f: f.write(encode(reference)); f.flush(); os.fsync(f.fileno())
    os.replace(pending, folder / 'RESULT.json'); _sync_dir(folder)
    return reference


def main(argv=None):
    """RECEIPT.json OCR_CONFIG.json OUT_DIR; one existing caller, no additional queue."""
    receipt, config, folder = (sys.argv[1:] if argv is None else argv)
    os.umask(0o077)
    source = json.loads(sys.stdin.read()) if receipt == '-' else json.loads(Path(receipt).read_bytes())
    result = run(source, json.loads(Path(config).read_bytes()), folder)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
