"""Exact locations for manually read test references; never used by the extractor."""
import hashlib
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path('/tmp/decider_claude_review_20261115')

class Reference:
    def __init__(self, source_id):
        self.source = next(s for s in json.loads((ROOT/'sources.json').read_text()) if s['id'] == source_id)
        self.parts = {p['id']: p['text'] for p in self.source['passages']}
        self.starts, offset = {}, 0
        for p in self.source['passages']:
            self.starts[p['id']] = offset
            offset += len(p['text']) + 2
        assert '\n\n'.join(self.parts.values()) == self.source['text']
        self.claims = []

    def span(self, part, text, role):
        assert self.parts[part].count(text) == 1, (part, text, self.parts[part].count(text))
        a = self.parts[part].index(text)
        g = self.starts[part] + a
        assert self.source['text'][g:g+len(text)] == text
        return dict(passage=part, start=a, end=a+len(text), global_start=g,
                    global_end=g+len(text), text=text, role=role)

    def between(self, part, first, last, role):
        t = self.parts[part]
        assert t.count(first) == t.count(last) == 1, (part, first, last)
        a, b = t.index(first), t.index(last) + len(last)
        assert a < b
        return self.span(part, t[a:b], role)

    def add(self, claim_id, meaning, evidence, expected, unresolved=(), status='confirmed_claim'):
        self.claims.append(dict(id=claim_id, meaning=meaning, status=status, evidence=evidence,
            expected_source_fields=expected, unresolved_fields_or_policy=list(unresolved),
            complete_record_gold=False,
            continuous_quote_interval=dict(start=min(e['global_start'] for e in evidence),
                                           end=max(e['global_end'] for e in evidence))))

    def save(self, coverage):
        assert set(coverage) == set(self.parts), (set(self.parts)-set(coverage), set(coverage)-set(self.parts))
        assert len({c['id'] for c in self.claims}) == len(self.claims)
        data = dict(source_id=self.source['id'],
            source_text_sha256=hashlib.sha256(self.source['text'].encode()).hexdigest(),
            snapshot_sha256=self.source['snapshot_sha256'],
            rulebook_sha256=hashlib.sha256(Path('/home/faisal/EventMarketDB/.claude/plans/Drivers/DriversFinal/DRIVER_RULES_Categorized.md').read_bytes()).hexdigest(),
            annotated_at=datetime.now(ZoneInfo('America/Toronto')).isoformat(),
            method='Root agent read every source passage before consulting draft labels or legacy rows for this pass. Prior conversation exposure exists; NOT blinded or double-reviewed. Annotations never enter extraction prompts.',
            status='Source claim inventory with exact evidence; not an adjudicated complete-record key.',
            record_policy='../record_policy.md', claims=self.claims,
            passage_coverage=[dict(passage=k, reason=v, text_sha256=hashlib.sha256(self.parts[k].encode()).hexdigest()) for k,v in coverage.items()])
        (ROOT/'reference_key'/f"{self.source['id']}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
        with (ROOT/'progress.md').open('a') as f:
            f.write(f"\nTest: Source-first reference reading of every passage in {self.source['id']}, under the current Driver rulebook.\nResult: {len(self.parts)} passages accounted for; {len(self.claims)} claim/interpretation entries with exact source locations; no complete-gold or independent-blind claim.\nNext: Compare legacy/draft inventories only after this source pass, adjudicate differences and finish the remaining calls before further narrow model tuning.\n")
        print(json.dumps(dict(source=self.source['id'], passages=len(self.parts), entries=len(self.claims))))
