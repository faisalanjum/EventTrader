"""An INVENTED filing for the native single-version qualification path (root-native-automatic-trigger-closeout-20261028t211651877057z).
Only the public SEC website renderer assets are real (fixtures/invented_version_qualification: jQuery, Show.js, accordionMenu.js, CSS, images and the
viewer page, whose filer header, menu, data slots and trailing tag are replaced here). The filer, accession, package, R page text, index page and the
'bot' script are invented. The served copy of R1.htm is the package's own <DOCUMENT> block plus ONE inserted <script src> (SEC's block form). The
campaign is recorded through the native Campaign with a stub sender (no network): every address the native acquisition asks for is served from this
map, any other one is a final 404; the job then replays it offline."""
import gzip, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]; A = HERE / 'fixtures' / 'invented_version_qualification'
EXE = os.environ.get('BROWSER_EXECUTABLE', '/home/faisal/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell')
CIK, ACC, FORM = '1234567', '0001234567-26-000001', '10-K'
FOLDER = '/Archives/edgar/data/%s/%s/' % (CIK, ACC.replace('-', '')); SEC = 'https://www.sec.gov'
VIEWER = SEC + '/cgi-bin/viewer?action=view&cik=%s&accession_number=%s&xbrl_type=v' % (CIK, ACC)
BOT_PATH = '/Bot9q/inv/x7'
sha = lambda b: hashlib.sha256(b).hexdigest()

BOT = (b"(function () { var u = '" + BOT_PATH.encode() + b"';\n"
       b"  window.addEventListener('click', function () { var x = new XMLHttpRequest(); x.open('POST', u); x.onerror = function () {}; try { x.send('s'); } catch (e) {}\n"
       b"    var f = document.createElement('iframe'); f.style.display = 'none'; document.body.appendChild(f); f.remove(); }, true);\n})();\n")
EVIL = BOT.replace(b"f.remove(); }, true);", b"f.remove(); var c = document.querySelector('#reportDiv td.text'); if (c) c.textContent = c.textContent + ' (changed)'; }, true);")


def member():  # the renderer's exact head (its reviewed toggleNextSibling helper included) and an invented one-concept report
    head = (HERE / 'convert/context/fixtures/public_ccl_r2_optional_controls/R2.htm').read_bytes().split(b'<body>')[0]
    body = (b'<body>\n<span style="display: none;">v3.22.4</span><table class="report" border="0" cellspacing="2" id="idm1">\n'
            b'<tr>\n<th class="tl" colspan="1" rowspan="2"><div style="width: 200px;"><strong>Invented Information<br></strong></div></th>\n<th class="th" colspan="1">12 Months Ended</th>\n</tr>\n'
            b'<tr><th class="th"><div>Jan. 01, 2026</div></th></tr>\n<tr class="re">\n'
            b'<td class="pl" style="border-bottom: 0px;" valign="top"><a class="a" href="javascript:void(0);" onclick="Show.showAR( this, \'defref_inv_Widgets\', window );">Widget Count</a></td>\n'
            b'<td class="text">42<span></span>\n</td>\n</tr>\n</table>\n<div style="display: none;">\n'
            b'<table border="0" cellpadding="0" cellspacing="0" class="authRefData" style="display: none;" id="defref_inv_Widgets">\n'
            b'<tr><td class="hide"><a style="color: white;" href="javascript:void(0);" onclick="Show.hideAR();">X</a></td></tr>\n'
            b'<tr><td><div class="body" style="padding: 2px;">\n'
            b'<a href="javascript:void(0);" onclick="Show.toggleNext( this );">- Definition</a><div><p>The number of invented widgets.</p></div>\n'
            b'<a href="javascript:void(0);" onclick="Show.toggleNext( this );">+ References</a><div style="display: none;"><p>No definition available.</p></div>\n'
            b'</div></td></tr>\n</table>\n</div>\n</body>\n</html>\n')
    return head + body


def package(doc):  # the native package framing (as tests/driver/prepare/get/test_acquire.package writes it)
    nl = b'\n'
    out = nl.join([b'<SEC-DOCUMENT>' + ACC.encode() + b'.txt : 20260101', b'<SEC-HEADER>' + ACC.encode() + b'.hdr.sgml : 20260101', b'<ACCEPTANCE-DATETIME>20260101071224',
                   b'ACCESSION NUMBER: ' + ACC.encode(), b'CONFORMED SUBMISSION TYPE: ' + FORM.encode(), b'PUBLIC DOCUMENT COUNT: 1', b'FILER:', b'\tCENTRAL INDEX KEY: ' + CIK.encode(), b'</SEC-HEADER>', b''])
    out += nl.join([b'<DOCUMENT>', b'<TYPE>XML', b'<SEQUENCE>1', b'<FILENAME>R1.htm', b'<DESCRIPTION>IDEA: XBRL DOCUMENT', b'<TEXT>', b'']) + doc + nl.join([b'</TEXT>', b'</DOCUMENT>', b''])
    return out + b'</SEC-DOCUMENT>' + nl


def viewer():  # the public viewer page with the invented filer and accession in its header, menu and data slots, and the invented bot tag
    v = (A / 'viewer_template_source.html').read_bytes()
    for old, new in ((b'AFFILIATED MANAGERS GROUP, INC.', b'INVENTED FILER, INC.'), (b'0001004434-23-000015', ACC.encode()), (b'000100443423000015', ACC.replace('-', '').encode()),
                     (b'0001004434', b'000' + CIK.encode()), (b'1004434', CIK.encode()), (b'amg-20230501.htm', b'inv-20260101.htm'), (b'001-13459', b'001-00000'), (b'SIC=6282', b'SIC=0000'),
                     (b'/MysEuRLP/LP1/Elt/jlLflGgMiF/bab9VzmQ6DfhG2SYJ1/UR4dAQ/MB/xhfghUEns', BOT_PATH.encode()),
                     (b'043218510', b'000000000'), (b'777 SOUTH FLAGLER DRIVE', b'1 INVENTED WAY'), (b'SUITE 1401 EAST TOWER', b'SUITE 0'), (b'WEST PALM BEACH FL 33401', b'NOWHERE ZZ 00000'),
                     (b'(800) 345-1100', b'(000) 000-0000'), (b'23869976', b'00000000'), (b'Investment Advice', b'Invented Industry'), (b'6282', b'0000')):
        v = v.replace(old, new)
    menu = (b'    <li class="accordion">\n      <a id="menu_cat2" href="#">Cover</a>\n      <ul>\n'
            b'            <li class="accordion" id="r1" ><a class="xbrlviewer" onClick="javascript:highlight(this);" href="javascript:loadReport(1);">Cover page</a></li>\n      </ul>\n    </li>\n')
    assert v.count(menu) == 1  # flattened: no hidden submenu, so the viewer chrome has no ready-time open/closed race in this invented page
    return v.replace(menu, b'    <li class="accordion" id="r1" ><a class="xbrlviewer" onClick="javascript:highlight(this);" href="javascript:loadReport(1);">Cover page</a></li>\n')


def build(t, bot=BOT, filings=1):
    """t: an empty folder. -> (plan_path, plan_sha256, out_dir_factory, facts). Publishes the package natively, records the campaign, writes the plan."""
    sys.path.insert(0, str(ROOT))
    from driver.prepare.get import acquire as acq, campaign as cmp, context_acquire, transport
    from driver.prepare.convert import screen_grid
    doc = member(); data = package(doc); src = t / 'submission.txt'; src.write_bytes(data)
    version = acq.acquire(ACC, CIK, FORM, t / 'packages', package=src, sha256=sha(data))
    manifest, files = acq.read_package(version); row0 = next(m for m in manifest['members'] if m['filename'] == 'R1.htm')
    before, after = acq.document_parts(data, row0['package_range'][0]); tag = b'<script type="text/javascript"  src="' + BOT_PATH.encode() + b'"></script>'
    served = before + files['R1.htm'].replace(b'</body>', tag + b'</body>') + after
    index = (b'<html><body><table><tr><td><a href="' + FOLDER.encode() + b'R1.htm">R1.htm</a></td></tr></table>'
             b'<p><a href="/cgi-bin/viewer?action=view&amp;cik=' + CIK.encode() + b'&amp;accession_number=' + ACC.encode() + b'&amp;xbrl_type=v">Interactive Data</a></p></body></html>')
    ctype = lambda n: 'text/css' if n.endswith('.css') else 'image/png' if n.endswith('.png') else 'image/gif' if n.endswith('.gif') else 'application/javascript' if n.endswith('.js') else 'text/html'
    site = {SEC + FOLDER + ACC + '-index.html': index, VIEWER: viewer(), SEC + FOLDER + 'R1.htm': served, SEC + BOT_PATH: bot,
            SEC + '/js/third-party/jquery-latest.min.js': (A / 'jquery-latest.min.js').read_bytes(), SEC + '/include/accordionMenu.js': (A / 'accordionMenu.js').read_bytes(),
            SEC + '/include/Show.js': (A / 'Show.js').read_bytes(), SEC + '/include/interactive2.css': (A / 'interactive2.css').read_bytes(),
            SEC + '/edgar/search/global/css/bootstrap/bootstrap.min.css': (A / 'bootstrap.min.css').read_bytes(), SEC + '/include/report.css': (A / 'report.css').read_bytes(),
            SEC + '/include/xbrlViewerStyle.css': (A / 'xbrlViewerStyle.css').read_bytes(), SEC + '/include/print.css': (A / 'print.css').read_bytes(),
            SEC + '/edgar/search/images/edgar-logo-2x.png': (A / 'edgar-logo-2x.png').read_bytes(), SEC + '/images/reports.gif': (A / 'reports.gif').read_bytes(),
            SEC + '/edgar/search/images/bigeagle.png': (A / 'bigeagle.png').read_bytes()}
    asked = []
    def sender(url, *a, **k):  # the stub web: the map above, every other address a final 404 (recorded as such)
        asked.append(url); b = site.get(url)
        return (200, {'content-type': ctype(url.split('?')[0])}, b) if b is not None else (404, {'content-type': 'text/plain'}, b'invented fixture: absent')
    camp_dir = t / 'campaign'
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=EXE); version_str = b.version
        with cmp.Campaign(camp_dir, live=True, sender=sender, minimum_free_bytes=0, sleep=lambda _: None) as camp:  # the recording pass: the native acquisition itself asks
            p = screen_grid.marker_prefix(files['R1.htm']); from driver.prepare import document
            got = context_acquire.acquire_context(camp, b, version, 'R1.htm', document.run_marked(files['R1.htm'], screen_grid, p), p)
        b.close()
    meta = t / 'ORIGINAL_MANIFEST.json'; shutil.copyfile(version / 'manifest.json', meta)
    rows = [{'file_id': f'invented/{ACC}/R1.htm#{i}', 'dispatch': 'html', 'immutable_package_directory': str(version), 'package_metadata_path': str(meta), 'package_metadata_sha256': sha(meta.read_bytes()),
             'package_sha256': manifest['package']['sha256'], 'filename': 'R1.htm', 'source_sha256': sha(files['R1.htm'])} for i in range(filings)]
    tree = {str(q.relative_to(ROOT)): sha(q.read_bytes()) for q in sorted((ROOT / 'driver').rglob('*')) if q.is_file() and '__pycache__' not in q.parts}
    man = t / 'RUNTIME_MANIFEST.json'; man.write_text(json.dumps({'files': tree}))
    store = t / 'store'; store.mkdir()
    plan = {'runtime_root': str(ROOT), 'runtime_manifest': {'path': str(man), 'sha256': sha(man.read_bytes())}, 'browser_executable': EXE, 'browser_executable_sha256': sha(Path(EXE).read_bytes()),
            'browser_version': version_str, 'source_commands': rows, 'context_campaign': {'campaign': str(camp_dir), 'live': False}, 'context_explore': False, 'script_qualifications': str(store)}
    body = json.dumps(plan).encode(); pp = t / 'PLAN.json'; pp.write_bytes(body)
    return pp, sha(body), {'acquisition': got['outcome'], 'asked': asked, 'served_sha256': sha(served), 'bot_sha256': sha(bot), 'store': store, 'record': got['record']}


def run_job(t, pp, pin, name='out', seconds=600):
    out = t / name
    p = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'driver/prepare/job.py'), str(pp), pin, str(out), str(ROOT / 'driver/prepare/document.py'), str(seconds)],
                       env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', str(t))}, stdin=subprocess.DEVNULL, capture_output=True)
    (t / (name + '.stderr')).write_bytes(p.stderr); return p.returncode, out
