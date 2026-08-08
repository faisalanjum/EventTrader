"""#827 round 9 — what shape a GRAPH-stored qname may lawfully take.

`graph_qname_parts` is the one owner of that grammar, and both the dimension
decoder and the concept target consume it. These pin it permanently, through
those two narrow boundaries as well as directly, because the rule was
previously demonstrated only by a terminal probe — and a probe scrolls away.

THE CORPUS-SHAPED MISTAKE THIS EXISTS TO PREVENT: I required every stored qname
to carry a prefix, because every row in today's graph does. That prices the
shape; it does not make it law. The writer stores `str(qname)`, and Arelle's
`QName.__str__` emits the LOCAL NAME ALONE when there is no prefix:

    str(QName(None, 'urn:example', 'Revenue'))  ->  'Revenue'
    str(QName('ex',  'urn:example', 'Revenue'))  ->  'ex:Revenue'

so an unprefixed stored qname IS the frozen writer contract
(`XBRL/xbrl_dimensions.py:95,269` — read-only, unmodified). It loses nothing:
the namespace lives independently inside the composite id.
"""
import pytest

from driver.core.driver_neo4j_adapter import _namespace_from_uid
from driver.relocation.inline_html import graph_concept_target
from driver.xml_names import graph_qname_parts

NS = "urn:example"


# ---------------------------------------------------------------------------
# THE GRAMMAR — lawful shapes and their malformed twins
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qname,parts,why", [
    ("Revenue", ("", "Revenue"), "unprefixed — the writer's own shape"),
    ("ex:Revenue", ("ex", "Revenue"), "prefixed"),
    ("_x", ("", "_x"), "an underscore starts a lawful XML name"),
    ("Ünïcode", ("", "Ünïcode"), "XML names permit Unicode"),
])
def test_a_LAWFUL_graph_qname_splits(qname, parts, why):
    assert graph_qname_parts(qname) == parts, why


@pytest.mark.parametrize("qname,why", [
    ("a:b:c", "an NCName may not contain a colon, so two is not a QName"),
    ("a: b", "a space is not part of a name"),
    (" a:b", "nor is leading padding"),
    ("a:", "an empty local part names nothing"),
    (":x", "an empty prefix is not a Prefix"),
    ("", "the empty string is not a name"),
    ("1abc", "an XML name may not start with a digit"),
    (None, "a non-string is not a qname"),
])
def test_a_MALFORMED_graph_qname_is_refused(qname, why):
    assert graph_qname_parts(qname) is None, why


# ---------------------------------------------------------------------------
# THE TWO CONSUMERS must accept the same shapes — one grammar, not three
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qname,why", [
    ("Revenue", "unprefixed, exactly as the writer would store it"),
    ("ex:Revenue", "prefixed"),
])
def test_the_DIMENSION_DECODER_accepts_the_writer_shape(qname, why):
    """`company_id + ':' + namespaceURI + ':' + qname`, decoded back."""
    assert _namespace_from_uid(f"1:{NS}:{qname}", qname) == NS, why


@pytest.mark.parametrize("qname,why", [
    ("a:b:c", "two colons"),
    ("a: b", "inner space"),
    ("", "empty"),
])
def test_the_DIMENSION_DECODER_refuses_a_malformed_qname(qname, why):
    """MUST-REFUSE twin: the decoder does not have its own looser grammar."""
    assert _namespace_from_uid(f"1:{NS}:{qname}", qname) is None, why


def test_the_CONCEPT_TARGET_accepts_an_unprefixed_qname():
    """The same shape through the other consumer, so the two cannot drift."""
    assert graph_concept_target("Revenue", NS, "Revenue") == (NS, "Revenue")


def test_the_CONCEPT_TARGET_accepts_a_prefixed_qname():
    assert graph_concept_target("ex:Revenue", NS, "ex:Revenue") == (NS, "Revenue")


@pytest.mark.parametrize("qname,why", [
    ("a:b:c", "two colons"),
    ("a:", "empty local"),
    ("", "empty"),
])
def test_the_CONCEPT_TARGET_refuses_a_malformed_qname(qname, why):
    assert graph_concept_target(qname, NS, qname) is None, why


def test_the_writer_really_does_emit_a_bare_local_name():
    """THE PREMISE, checked against the INSTALLED library rather than assumed.

    If a future Arelle changed `QName.__str__` this test fails and the rule
    above is revisited — instead of the rule quietly resting on a claim nobody
    re-checks.

    IMPORTED NORMALLY, never `importorskip`. Arelle is a REQUIRED writer
    dependency, so its absence must break collection loudly; skipping would turn
    the storage-contract premise into a silent pass and hand a zero-skip gate a
    green it did not earn. (Pinning the exact distribution/version is a separate
    decision and is not made here.)
    """
    from arelle.ModelValue import QName
    assert str(QName(None, NS, "Revenue")) == "Revenue"
    assert str(QName("ex", NS, "Revenue")) == "ex:Revenue"
