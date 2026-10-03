"""Reproducible Step 2 acquisition comparison; no conversion, AI or database writes."""
import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import unquote, urljoin, urlsplit

from driver.prepare.get.acquire import acquire, read_package, check_space, StorageError, _identity, _url
from driver.prepare.get.campaign import Campaign
from driver.prepare.get.inventory import parse_index, compare_inventory


class Links(HTMLParser):
    """Record explicit HTML references, never infer incorporation or crawl them."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.html = False

    def handle_starttag(self, tag, attrs):
        self.html |= tag == 'html'
        fields = {'a': 'href', 'link': 'href', 'img': 'src', 'script': 'src',
                  'iframe': 'src', 'object': 'data', 'source': 'src', 'video': 'poster'}
        value = dict(attrs).get(fields.get(tag))
        if value:
            self.links.append(dict(tag=tag, target=value, line_column=list(self.getpos())))


def references(files, manifest, base):
    observed = []
    for member in manifest['members']:
        if member['format_hint'] not in ('html', 'xml', 'unknown'):
            continue
        name = member['filename']
        try:
            text = files[name].decode('utf-8')
        except UnicodeDecodeError:
            observed.append(dict(source=name, status='encoding_unresolved'))
            continue
        parser = Links()
        parser.feed(text)
        if not parser.html:
            continue
        for link in parser.links:
            target = urljoin(base + name, link['target'])
            parsed = urlsplit(target)
            local = unquote(parsed.path[len(urlsplit(base).path):]) if target.startswith(base) else None
            status = ('inside_package' if local in files else
                      'missing_local_reference' if local is not None else
                      'external_reference' if parsed.scheme in ('http', 'https') else 'non_http_reference')
            observed.append(dict(link, source=name, source_sha256=member['sha256'],
                                 source_acceptance=manifest['acceptance'], target_url=target,
                                 target_file=local, target_time=manifest['acceptance'] if local in files else None,
                                 status=status))
    return observed


def run(inputs, package_root, output, live=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frozen = json.loads(Path(inputs).read_text())
    outcomes, refs = [], []
    started = time.monotonic()
    with Campaign(output / 'http', live=live) as campaign:
        for row in frozen['filings']:
            accession = row['acc']
            manifest = None
            outcome = dict(accession=accession, form=row['form'], package_sha256=row['sha256'],
                           package_retrieval_seconds=None, direct_files=[])
            try:
                check_space(output, campaign.minimum_free_bytes)
                source = Path(package_root) / (accession + '.txt')
                before = time.monotonic()
                expected = _identity(accession, row['cik'], row['form'])
                version = output / 'packages' / accession / row['sha256']
                if not version.exists():
                    version = acquire(accession, row['cik'], row['form'], output / 'packages',
                                      package=source, sha256=row['sha256'])
                stored, files = read_package(version)
                if (stored['package']['sha256'] != row['sha256']
                        or stored['identity']['accession'] != accession
                        or stored['identity']['form'] != row['form']
                        or expected['cik'] not in stored['identity']['ciks']):
                    raise ValueError('Selected package identity differs from frozen input')
                manifest = stored
                package_url = _url(dict(accession=accession, cik=row['cik']))
                base = package_url.rsplit('/', 1)[0] + '/'
                index_url = base + accession + '-index.html'
                outcome.update(package_bytes=manifest['package']['bytes'], member_count=len(manifest['members']),
                               member_types=dict(Counter(m['type'] for m in manifest['members'])),
                               member_formats=dict(Counter(m['format_hint'] for m in manifest['members'])),
                               package_archive_seconds=time.monotonic() - before)
                data, index_receipt = campaign.fetch(index_url)
                index = parse_index(data, index_url)
                outcome.update(index=index, index_receipt=index_receipt,
                               inventory=compare_inventory(manifest, index))
                for item in index:
                    data, receipt = campaign.fetch(item['url'])
                    name = item['filename']
                    outcome['direct_files'].append(dict(filename=name, receipt=receipt,
                        rendered_from=item.get('rendered_from'),
                        same_decoded_bytes=name in files and data == files[name],
                        package_member_bytes=len(files[name]) if name in files else None,
                        index_size=item['bytes']))
                outcome['status'] = 'inventory_gap' if any(outcome['inventory'][key] for key in
                    ('missing', 'metadata_mismatch')) else 'acquired'
            except (OSError, ValueError) as exc:
                outcome.update(status='failed', error=str(exc))
                if isinstance(exc, StorageError):
                    campaign.stopped = True
            if manifest is not None:
                refs.extend(dict(accession=accession, **ref) for ref in references(files, manifest, base))
            outcomes.append(outcome)
            print(accession, outcome['status'], len(outcome['direct_files']), flush=True)
            if campaign.stopped or (campaign.root / 'STOP.json').exists():
                break
        (output / 'outcomes.json').write_text(json.dumps(outcomes, indent=2) + '\n')
        (output / 'references.json').write_text(json.dumps(refs, indent=2) + '\n')
        records = list(campaign.records.values())
        sent_attempts = campaign.sent_attempts
    summary = dict(inputs_sha256=hashlib.sha256(Path(inputs).read_bytes()).hexdigest(),
                   requested=len(frozen['filings']), processed=len(outcomes),
                   unattempted=[r['acc'] for r in frozen['filings'][len(outcomes):]],
                   statuses=dict(Counter(r['status'] for r in outcomes)),
                   forms=dict(Counter(r['form'] for r in outcomes)),
                   reference_statuses=dict(Counter(r['status'] for r in refs)),
                   selected_http_responses=len(records),
                   sent_http_attempts=sent_attempts,
                   request_log=campaign.request_log,
                   recorded_http_attempts=sum(len(r['attempts']) for r in records),
                   recorded_http_bytes=sum(r.get('bytes', 0) for r in records),
                   elapsed_seconds=time.monotonic() - started,
                   notes=[f"{len(frozen['filings'])}-filing coverage sample, not a population estimate.",
                          'Package retrieval timings predate this run and are unknown.',
                          'HTTP versions preserve website transformations; byte differences do not prove missing content.',
                          'References are an HTML-link inventory, not semantic resolution; CSS/PDF/XML references need Convert.',
                          'External target times are unknown; do not use in historical prediction evidence.'])
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--package-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--live', action='store_true')
    print(json.dumps(run(**vars(parser.parse_args())), indent=2))
