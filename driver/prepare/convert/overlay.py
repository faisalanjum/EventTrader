"""Copied verbatim (below this line) from OCR's reviewed handoff /home/faisal/prepare_work/extraction_closeout_20261010/manual_review_20261021/context_candidate/ocr_handoff/measure.py (sha256 e750502b457dd7194842f1c26e81d21c7e00e70b31d77b28ecb715bd27f075f0): the response overlay with exact inverses."""
"""Source identity for a selected response (prototype; replaces response_identity_v1/overlay.py's own run/link marking and scanner check, which are cut).
measurement_body: ANY render's marked body from the caller (all kinds: s/a/g/j/p...: every comment the step writes begins with marker_prefix(raw), which
  the source never contains) set onto the verified published response. New logic = the position map only; proof = acquire._prove/_one_run; insertion =
  screen_grid.tag_cells used as the pure inserter. Inverse checks: drop our comments -> the response exactly; drop envelope + run -> the caller's body exactly.
NODE_JS: native node-level check of the inserted run (inert DOMParser + Node.normalize + isEqualNode; v1 without normalize is retained as
  measure_v1_retained.py: it false-failed a real clean insertion that left two adjacent text nodes), bytes decoded strictly (TextDecoder fatal) in the observation's
  declared charset (utf-8 when none): no replacement-decoded equality.
MeasuredSource: screen_grid.Source + one optional field: for a declared target URL, serve its measurement body only when the observation is a verified
  200 and dropping our comments gives exactly its recorded body; a declared target without one is refused (never served unmarked)."""
import hashlib, re
from driver.prepare.get.acquire import _one_run
from driver.prepare.convert import screen_grid as sg
sha = lambda b: hashlib.sha256(b).hexdigest()

def own_marks(plain, marked, prefix):  # [(byte in plain, comment)] of our comments, or None unless dropping them gives `plain` exactly
    out, rest, pos, cut = [], [], 0, 0
    for m in re.finditer(b'<!--' + re.escape(prefix.encode()) + b'.*?-->', marked, re.S):
        rest.append(marked[pos:m.start()]); out.append((m.start() - cut, m.group())); cut += len(m.group()); pos = m.end()
    rest.append(marked[pos:])
    return out if b''.join(rest) == plain else None

def measurement_body(copy, member, marked, prefix, proof, before=b'', after=b''):
    rec = {'form': proof['form'], 'inserted': proof['inserted'], 'prefix': prefix}
    if prefix.encode() in copy: return None, dict(rec, refused='the step prefix occurs in the response')
    marks = own_marks(member, marked, prefix)
    if marks is None: return None, dict(rec, refused="the caller's body is not the member plus our comments")
    head, tail = (before, after) if proof['form'] == 'block' else (b'', b'')
    if len(copy) < len(head) + len(tail) or not (copy.startswith(head) and copy.endswith(tail)): return None, dict(rec, refused='envelope differs from the proof')
    inner = copy[len(head):len(copy) - len(tail)]; run = _one_run(member, inner)
    if run is None or [len(head) + a for a in run] != proof['inserted']: return None, dict(rec, refused='proof does not map onto these member bytes')
    extra = hi = 0
    if run:
        extra, hi = run[1] - run[0], run[0]; lo = len(member) - _one_run(member[::-1], inner[::-1])[0]; rec['window'] = [lo, hi]
        if any(lo <= x <= hi for x, _ in marks): return None, dict(rec, unresolved="a mark at the inserted run's non-unique position")
    mapped = [(len(head) + x + (extra if run and x > hi else 0), m) for x, m in marks]
    body = sg.tag_cells(copy, False, (), mapped, prefix, cells=False)[0]  # ponytail: tag_cells as the pure inserter (cells=False, no gaps: vis unread)
    core = body[len(head):len(body) - len(tail)]
    if run: at = run[0] + sum(len(m) for x, m in marks if x < lo); core = core[:at] + core[at + extra:]; rec['run_at_in_body'] = len(head) + at
    rec.update(marks=len(mapped), kinds=sorted({re.match(rb'<!--' + re.escape(prefix.encode()) + rb'([a-z]*)', m).group(1).decode() for _, m in marks}),
               inverse_response=own_marks(copy, body, prefix) is not None, inverse_caller_body=core == marked)
    if not (rec['inverse_response'] and rec['inverse_caller_body']): return None, dict(rec, refused='inverse check failed')
    return body, rec

NODE_JS = """([a64, b64, charset, p]) => { const dec = s => new TextDecoder(charset, {fatal: true}).decode(Uint8Array.from(atob(s), c => c.charCodeAt(0)));
  let a, b; try { a = dec(a64); b = dec(b64); } catch (e) { return {node_level: false, why: 'bytes do not decode strictly as ' + charset}; }
  const P = new DOMParser(), A = P.parseFromString(a, 'text/html'), B = P.parseFromString(b, 'text/html');
  const w = A.createTreeWalker(A, NodeFilter.SHOW_COMMENT); let n, r0 = null, r1 = null;
  while ((n = w.nextNode())) { if (n.nodeValue === p + 'r:0') r0 = n; else if (n.nodeValue === p + 'r:1') r1 = n; }
  if (!r0 || !r1 || r0.parentNode !== r1.parentNode) return {node_level: false, why: 'run boundaries not sibling comments'};
  let x = r0; const gone = []; while (x) { gone.push(x); if (x === r1) break; x = x.nextSibling; }
  if (x !== r1) return {node_level: false, why: 'r:1 does not follow r:0'};
  gone.forEach(g => g.remove()); A.normalize(); B.normalize();  // native: adjacent text nodes left by the removal merge as the parser would have made them
  const eq = A.documentElement.isEqualNode(B.documentElement);
  return {node_level: eq, why: eq ? null : 'documents differ once the run is removed'}; }"""

def node_level(page, body, rec, charset):  # every equivalent placement of the run inside the window; accepted iff one is node-level
    import base64
    if 'window' not in rec: return {'node_level': True, 'placements': []}
    lo, hi = rec['window']; extra = rec['inserted'][1] - rec['inserted'][0]; p = rec['prefix'].encode(); base = rec['run_at_in_body'] - hi; out = []
    for q in range(lo, hi + 1):
        at = base + q; chk = body[:at] + b'<!--' + p + b'r:0-->' + body[at:at + extra] + b'<!--' + p + b'r:1-->' + body[at + extra:]
        r = page.evaluate(NODE_JS, [base64.b64encode(chk).decode(), base64.b64encode(body[:at] + body[at + extra:]).decode(), charset, rec['prefix']])
        out.append(dict(q=q, **r))
    return {'node_level': any(x['node_level'] for x in out), 'placements': out}

class MeasuredSource(sg.Source):
    def __init__(self, path, members, base=None, observed=None, bundle=None, measured=None, prefix=None):
        super().__init__(path, members, base, observed, bundle); self.measured, self.prefix = dict(measured or {}), prefix
    def answer(self, url, kind, navigation=False):
        if url not in self.measured or navigation: return super().answer(url, kind, navigation)
        got, body = self.observation(url, kind), self.measured[url]  # the recorded response by the Source's own rule (identity checked, recorded once), or refused there
        if got is None: return None
        if got[0] != 200 or body is None or own_marks(got[2], body, self.prefix) is None: return self._refuse(url, url, None, kind, 'declared target without a verified measurement body')
        self.records[url]['measured_sha256'] = sha(body)  # this page's measured body, beside the original identity
        return 200, got[1], body
