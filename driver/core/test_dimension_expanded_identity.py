"""#827 round 9 — a dimension is a QName, not a spelling.

A filing writes `srt:StatementGeographicalAxis`; the graph stores
`srt:StatementGeographicalAxis`. Comparing those two strings looks like
identity and is not: `srt` is a prefix each document chooses for itself, so two
filings may write the SAME axis under different prefixes, and two DIFFERENT
axes under the same one.

The graph does not carry a namespace on Dimension or Member — it is composed
into the stored `u_id` (`XBRL/xbrl_dimensions.py:107`, read-only). The adapter
decodes it at its own boundary and publishes `axis_namespace` /
`member_namespace`; `u_id` itself never travels further.

EVERY CASE HERE GOES THROUGH THE PUBLIC ADAPTER DOOR —
`Neo4jStore.get_xbrl_fact_dimensions`, the one production calls — never the
private decoder, so these keep binding on any rewrite of the internals. Every
refusal has a lawful twin.
"""
import pytest

from driver.core.driver_neo4j_adapter import Neo4jStore

GAAP24 = "http://fasb.org/us-gaap/2024"
GAAP22 = "http://fasb.org/us-gaap/2022"
SRT = "http://fasb.org/srt/2024"


def _store(defs):
    """A Neo4jStore whose reads are the given definition records."""
    store = Neo4jStore.__new__(Neo4jStore)

    def read(q, **p):
        if "HAS_XBRL" in q:
            return [{"fid": "f1", "fact_id": "f-1", "context_id": "c-1",
                     "period_type": "duration", "start_date": "2026-01-01",
                     "end_date": "2026-04-01", "unit_ref": "usd",
                     "value": "390", "decimals": "0", "unit_name": "iso4217:USD",
                     "is_divide": "0", "concept_namespace": GAAP24,
                     "graph_concept_qname": "us-gaap:Revenues",
                     # CONTEXT SIDE = the ten-digit Company spelling; the node
                     # ids stay `1:…`, that same cik's archive spelling.
                     "company_cik": "0000000001",
                     "dus": ["0000000001:d"], "mus": ["0000000001:m"]}]
        return defs
    store._read = read
    return store


def _rows(defs):
    """THE public door — the one production calls, by its real name."""
    return _store(defs).get_xbrl_fact_dimensions("S1", "us-gaap:Revenues")


def _rec(kind, qname, namespace, uid_company="1", label=None):
    """One definition record in the graph's own stored shape."""
    return {"id": f"1:{'d' if kind == 'Dimension' else 'm'}", "kind": kind,
            "qname": qname, "label": label,
            "u_id": f"{uid_company}:{namespace}:{qname}"}


# ---------------------------------------------------------------------------
# 1. DIFFERENT PREFIXES, SAME NAME — the same dimension, and it must bind
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("axis_q,member_q,label", [
    ("srt:StatementGeographicalAxis", "us-gaap:ProductMember", "alias A"),
    ("s:StatementGeographicalAxis", "g:ProductMember", "alias B"),
    ("zzz:StatementGeographicalAxis", "qq:ProductMember", "alias C"),
])
def test_the_SAME_axis_and_member_bind_whatever_prefix_spells_them(
        axis_q, member_q, label):
    """MUST-ALLOW. Three spellings of one (namespace, local) pair.

    The prefixes differ in every case; the namespaces and local names do not.
    A reader comparing raw text calls these three different dimensions."""
    rows = _rows([_rec("Dimension", axis_q, SRT),
                  _rec("Member", member_q, GAAP24, label="North America")])
    assert len(rows.rows) == 1, f"{label}: the lawful pair must survive"
    d = dict(rows.rows[0]["dims"][0])
    assert d["axis_namespace"] == SRT, label
    assert d["member_namespace"] == GAAP24, label
    assert d["axis"] == axis_q and d["member"] == member_q, \
        "the RAW spelling is still carried for the product/display contract"


# ---------------------------------------------------------------------------
# 2. SAME LOCAL NAME, ANOTHER NAMESPACE — a different thing, and it must show
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("axis_ns,member_ns,what", [
    (GAAP24, GAAP24, "the axis namespace is wrong"),
    (SRT, GAAP22, "the member namespace is another taxonomy year"),
])
def test_the_SAME_local_names_under_ANOTHER_namespace_are_not_the_same(
        axis_ns, member_ns, what):
    """The spellings are IDENTICAL to the lawful case above — only the
    namespaces differ. So the published identity must differ too; anything that
    reported these as the same dimension would be comparing text."""
    rows = _rows([_rec("Dimension", "srt:StatementGeographicalAxis", axis_ns),
                  _rec("Member", "us-gaap:ProductMember", member_ns,
                       label="North America")])
    assert len(rows.rows) == 1, "the row itself is readable"
    d = dict(rows.rows[0]["dims"][0])
    assert (d["axis_namespace"], d["member_namespace"]) != (SRT, GAAP24), what
    assert d["axis"] == "srt:StatementGeographicalAxis", \
        "...while the raw spelling is byte-identical to the lawful case"


# ---------------------------------------------------------------------------
# 3. A MALFORMED COMPOSITE ID — the existing truthful unresolved reason
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("uid,why", [
    ("nocolonatall", "no company boundary"),
    (":" + GAAP24 + ":srt:StatementGeographicalAxis", "blank company"),
    ("1::srt:StatementGeographicalAxis", "blank namespace"),
    ("1:" + GAAP24 + ":a-different:qname", "the qname is not the suffix"),
])
def test_a_MALFORMED_composite_id_leaves_the_pair_unresolved(uid, why):
    """FAIL-CLOSED, under the reason that already exists. A namespace is never
    invented to make an undecodable record usable."""
    bad = _rec("Dimension", "srt:StatementGeographicalAxis", SRT)
    bad["u_id"] = uid
    rows = _rows([bad, _rec("Member", "us-gaap:ProductMember", GAAP24,
                            label="North America")])
    assert rows.rows == (), why
    assert any(e["event"] == "dimension_definition_unresolved"
               for e in rows.exclusions), why


def test_the_LAWFUL_stored_composite_still_resolves():
    """MUST-ALLOW twin of all four malformed shapes: the real storage shape,
    exactly as `XBRL/xbrl_dimensions.py` composes it, still works."""
    rows = _rows([_rec("Dimension", "srt:StatementGeographicalAxis", SRT),
                  _rec("Member", "us-gaap:ProductMember", GAAP24,
                       label="North America")])
    assert len(rows.rows) == 1
    d = dict(rows.rows[0]["dims"][0])
    assert d["axis_namespace"] == SRT and d["member_namespace"] == GAAP24
    assert d["label"] == "North America", "the label survives untouched"
