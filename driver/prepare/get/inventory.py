"""Compare a preserved SEC filing index with the submission's actual members."""
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from .acquire import AcquisitionError, _filename

BINARY = ('pdf', 'zip', 'jpeg', 'png', 'gif')  # format hints of members stored uuencoded


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None
        self.file_table = self.in_title = self.in_identity = False
        self.title, self.identity = '', ''
        self.document_table_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self.in_title = True
        if tag == 'div' and attrs.get('id') == 'secNum':
            self.in_identity = True
        if tag == 'table':
            self.file_table = attrs.get('summary') in ('Document Format Files', 'Data Files')
            self.document_table_count += attrs.get('summary') == 'Document Format Files'
        if tag == 'tr' and self.file_table:
            self.handle_endtag('tr')
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = {'text': '', 'links': [], 'header': tag == 'th'}
            self.row.append(self.cell)
        elif tag == 'a' and self.cell is not None:
            href = attrs.get('href')
            if href:
                self.cell['links'].append(href)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'div':
            self.in_identity = False
        if tag in ('td', 'th'):
            self.cell = None
        elif tag in ('tr', 'table'):
            if self.row is not None:
                self.rows.append(self.row)
            self.row = self.cell = None
            if tag == 'table':
                self.file_table = False

    def handle_data(self, text):
        if self.in_title:
            self.title += text
        if self.in_identity:
            self.identity += text
        if self.cell is not None:
            self.cell['text'] += text


def parse_index(data, url):
    """Read SEC's five-column file tables, including HTML's optional end tags.

    Keep duplicate exhibit labels; only the full-submission row is excluded.
    Size is SEC's published size, not a substitute for byte equality.
    """
    accession = url.rsplit('/', 1)[-1].removesuffix('-index.html')
    text = data.decode('utf-8')
    parser = _Tables()
    parser.feed(text)
    if parser.file_table:  # the page ended inside a file table: its list may be partial, so never close it here
        raise AcquisitionError('Incomplete SEC filing index')
    if parser.document_table_count != 1:
        raise AcquisitionError('Missing or duplicate SEC document table')
    for declared in (parser.title, parser.identity):
        if re.findall(r'\b[0-9]{10}-[0-9]{2}-[0-9]{6}\b', declared) != [accession]:
            raise AcquisitionError('Wrong or missing filing index identity')
    result = []
    for row in parser.rows:
        if [c['text'].strip() for c in row] == ['Seq', 'Description', 'Document', 'Type', 'Size']:
            continue
        if len(row) != 5 or len(row[2]['links']) != 1:
            raise AcquisitionError('Incomplete filing-index file row')
        seq, description, _, kind, size = [c['text'].strip() for c in row]
        href = row[2]['links'][0]
        parsed = urlsplit(href)
        href = parse_qs(parsed.query).get('doc', [href])[0]
        target = urljoin(url, href)
        parsed = urlsplit(target)
        member = re.fullmatch(r'/Archives/edgar/data/[0-9]+/' + accession.replace('-', '') + r'/(.+)', parsed.path)
        if (parsed.scheme != 'https' or parsed.netloc != 'www.sec.gov'
                or not member or parsed.query or parsed.fragment):
            raise AcquisitionError('Index file is outside the expected filing')
        name = _filename(unquote(member[1]))
        if name == accession + '.txt' and not seq and not kind:
            continue
        if not seq.isdigit() or not kind or (size and not size.isdigit()):
            raise AcquisitionError('Unrecognized filing-index file row')
        result.append(dict(filename=name, sequence=seq, type=kind, description=description,
                           bytes=int(size) if size else None, url=target))
    if not result or len({r['filename'] for r in result}) != len(result):
        raise AcquisitionError('Empty or duplicate index inventory')
    for row in result:
        if row['bytes'] is None:
            matches = [raw for raw in result if raw['bytes'] is not None
                       and row['filename'] != raw['filename']
                       and raw['filename'] == row['filename'].rsplit('/', 1)[-1]
                       and all(raw[k] == row[k] for k in ('sequence', 'type'))]
            if len(matches) != 1:
                raise AcquisitionError('Unresolved or ambiguous index rendering')
            # An index presentation relationship, not content equivalence.
            row['rendered_from'] = matches[0]['filename']
    return result


def compare_inventory(manifest, index):
    """No extension/type exemptions: every SEC-listed member must be present.

    Binary members are uuencoded in the package and SEC lists their exact decoded size,
    so a size difference exposes a decoding error. Text sizes differ by SEC's web wrappers.
    """
    members = {m['filename']: m for m in manifest['members']}
    expected = {r['filename']: r for r in index if 'rendered_from' not in r}
    shared = members.keys() & expected.keys()
    def mismatch(name):
        member, row = members[name], expected[name]
        return (any(member[key] != row[key] for key in ('type', 'sequence'))
                or member.get('format_hint') in BINARY and row['bytes'] not in (None, member.get('bytes')))
    return dict(missing=sorted(expected.keys() - members.keys()),
                package_only=sorted(members.keys() - expected.keys()),
                metadata_mismatch=sorted(filter(mismatch, shared)))
