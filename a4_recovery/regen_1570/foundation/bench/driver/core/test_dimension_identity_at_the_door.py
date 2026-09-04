"""#827 round 9 — an axis is a QName at the ATTACHMENT DOOR, not a spelling.

These are the semantic pairs. They go through `bind_graph_fact`, the door
production actually binds with, and they must ATTACH or REFUSE — not merely
report a different field. A test that observes a tuple and refuses nothing
proves nothing, which is what the first draft of this file did.

THE RULE: a dimension is `(namespace URI, local name)`. The prefix spelling is
the filing's own choice and the graph's own choice, and the two need not agree.

  * same URI + same local, different prefixes  -> ATTACH
  * same local, WRONG axis or member URI       -> REFUSE, by name

Every refusal below has a lawful twin differing in exactly one respect.
"""
import pytest

from driver.relocation.inline_html import bind_graph_fact

IX = "http://www.xbrl.org/2013/inlineXBRL"
XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
ISO = "http://www.xbrl.org/2003/iso4217"
GAAP = "http://fasb.org/us-gaap/2024"
SRT = "http://fasb.org/srt/2024"
OTHER = "http://fasb.org/us-gaap/2022"


def doc(axis_prefix="srt", member_prefix="mem", axis_ns=SRT, member_ns=GAAP):
    """A lawful one-fact report whose single dimension is spelled by the
    caller's prefixes and bound to the caller's namespaces."""
    # EACH PREFIX DECLARED EXACTLY ONCE. A repeated attribute is not well-formed
    # XML, so a template that emitted `xmlns:us-gaap` twice would test the
    # parser's error path instead of the rule this file is about.
    declared = {"ix": IX, "xbrli": XBRLI, "xbrldi": XBRLDI, "iso4217": ISO,
                "us-gaap": GAAP}
    declared[axis_prefix] = axis_ns
    declared[member_prefix] = member_ns
    xmlns = " ".join(f'xmlns:{p}="{u}"' for p, u in declared.items())
    return f'''<html xmlns="http://www.w3.org/1999/xhtml" {xmlns}>
<body>
<div style="display:none"><ix:header><ix:resources>
<xbrli:context id="c1"><xbrli:entity>
<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>
</xbrli:entity><xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>
<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>
<xbrli:scenario><xbrldi:explicitMember
 dimension="{axis_prefix}:StatementGeographicalAxis"
 >{member_prefix}:ProductMember</xbrldi:explicitMember></xbrli:scenario>
</xbrli:context>
<xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
</ix:resources></ix:header></div>
<table><tr><td>Revenue</td><td><ix:nonFraction name="us-gaap:Revenues"
 contextRef="c1" unitRef="u1" scale="6" decimals="0" id="f-1"
 >390</ix:nonFraction></td></tr></table>
</body></html>'''


def _bind(html, dims):
    return bind_graph_fact(
        html, inline_element_id="f-1", concept="us-gaap:Revenues",
        context_id="c1", unit_ref="u1", unit_name="iso4217:USD",
        is_divide="0", period_type="duration", start_date="2026-01-01",
        end_date="2026-04-01", dims=dims, entity_cik="0000320193",
        raw_value="390,000,000", concept_namespace=GAAP,
        graph_concept_qname="us-gaap:Revenues")


#: the expanded identity of the one dimension the documents above declare
LAWFUL = (((SRT, "StatementGeographicalAxis"), (GAAP, "ProductMember")),)


# ---------------------------------------------------------------------------
# ATTACH — the same dimension, however either side spells it
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("axis_prefix,member_prefix,label", [
    ("srt", "mem", "the conventional prefixes"),
    ("s", "g", "one-letter aliases"),
    ("zzz", "qq", "arbitrary aliases"),
])
def test_the_SAME_dimension_attaches_whatever_prefix_either_side_uses(
        axis_prefix, member_prefix, label):
    """MUST-ALLOW. The filing spells the axis and member differently in each
    case; the namespaces and local names never change. A binder comparing raw
    text calls these three different dimensions and refuses two of them."""
    bound, why = _bind(doc(axis_prefix, member_prefix), LAWFUL)
    assert why == "ok" and bound is not None, f"{label}: {why}"


# ---------------------------------------------------------------------------
# REFUSE — the same local names under another namespace are another dimension
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("axis_ns,member_ns,what", [
    (OTHER, GAAP, "the AXIS is from another taxonomy"),
    (SRT, OTHER, "the MEMBER is from another taxonomy"),
    (OTHER, OTHER, "both are"),
])
def test_the_SAME_local_names_under_a_WRONG_namespace_do_not_attach(
        axis_ns, member_ns, what):
    """MUST-REFUSE. The filing's spelling is byte-identical to the lawful case —
    `srt:StatementGeographicalAxis` / `mem:ProductMember` — and only the URIs
    those prefixes are bound to differ. Raw-text comparison cannot see this at
    all, and would attach a fact to a dimension it does not have.

    THE MEMBER PREFIX IS DELIBERATELY NOT `us-gaap`: that prefix also spells the
    CONCEPT here, so rebinding it would change two things at once and the fact
    would refuse for the concept, not the dimension — a test passing for the
    wrong reason."""
    bound, why = _bind(doc(axis_ns=axis_ns, member_ns=member_ns), LAWFUL)
    assert bound is None, f"{what}: a wrong-namespace dimension attached"
    assert why == "dimension_set_mismatch", f"{what}: refused as {why!r}"


def test_a_MISSING_graph_dimension_identity_fails_closed():
    """A claim whose axis or member carries no usable identity may never
    attach by falling back to the spelling."""
    bound, why = _bind(doc(), ((("", "StatementGeographicalAxis"),
                               (GAAP, "ProductMember")),))
    assert bound is None and why == "dimension_set_mismatch", why


def _two_member_doc(axis1_prefix, axis2_prefix, axis1_ns=SRT, axis2_ns=SRT):
    """One context carrying TWO explicit members, whose axes the caller spells
    and binds independently."""
    declared = {"ix": IX, "xbrli": XBRLI, "xbrldi": XBRLDI, "iso4217": ISO,
                "us-gaap": GAAP, "mem": GAAP}
    declared[axis1_prefix] = axis1_ns
    declared[axis2_prefix] = axis2_ns
    xmlns = " ".join(f'xmlns:{p}="{u}"' for p, u in declared.items())
    return f'''<html xmlns="http://www.w3.org/1999/xhtml" {xmlns}>
<body>
<div style="display:none"><ix:header><ix:resources>
<xbrli:context id="c1"><xbrli:entity>
<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>
</xbrli:entity><xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>
<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>
<xbrli:scenario>
<xbrldi:explicitMember dimension="{axis1_prefix}:StatementGeographicalAxis"
 >mem:ProductMember</xbrldi:explicitMember>
<xbrldi:explicitMember dimension="{axis2_prefix}:StatementGeographicalAxis"
 >mem:ServiceMember</xbrldi:explicitMember>
</xbrli:scenario>
</xbrli:context>
<xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
</ix:resources></ix:header></div>
<table><tr><td>Revenue</td><td><ix:nonFraction name="us-gaap:Revenues"
 contextRef="c1" unitRef="u1" scale="6" decimals="0" id="f-1"
 >390</ix:nonFraction></td></tr></table>
</body></html>'''


def test_ONE_axis_spelled_TWO_WAYS_in_one_context_is_a_repeated_dimension():
    """MUST-REFUSE. XBRL Dimensions 1.0 §3.1.4.2: a context MUST NOT contain
    more than one value for a dimension —`xbrldie:RepeatedDimensionInInstance`.

    `srt:` and `s2:` are bound to the SAME URI here, so these two members give
    the SAME axis two different values. A uniqueness check on the raw spelling
    sees two distinct axes and lets it through, which is the identity defect
    this whole round removes, wearing one more hat.

    https://www.xbrl.org/specification/dimensions/per-2011-11-20/dimensions-per-2011-11-20.html
    """
    html = _two_member_doc("srt", "s2")
    # THE CLAIM MATCHES WHAT THE DOCUMENT DECLARES, so a set-size difference
    # cannot do the refusing for us — the repeated axis is the only thing left
    # to object to. Without this the test refuses as `dimension_set_mismatch`
    # and proves nothing about §3.1.4.2.
    claim = tuple(sorted((
        ((SRT, "StatementGeographicalAxis"), (GAAP, "ProductMember")),
        ((SRT, "StatementGeographicalAxis"), (GAAP, "ServiceMember")))))
    bound, why = _bind(html, claim)
    assert bound is None, "a repeated axis attached"
    assert why == "exact_id_malformed_context_structure", why


def test_TWO_GENUINELY_DIFFERENT_axes_in_one_context_are_lawful():
    """MUST-ALLOW twin: two members, two DIFFERENT axis URIs — one value each,
    which is exactly what the rule permits. Otherwise the check above could be
    satisfied by refusing every multi-axis context."""
    html = _two_member_doc("srt", "other", axis2_ns=OTHER)
    both = ((((SRT, "StatementGeographicalAxis"), (GAAP, "ProductMember")),
             ((OTHER, "StatementGeographicalAxis"), (GAAP, "ServiceMember"))))
    bound, why = _bind(html, tuple(sorted(both)))
    assert why == "ok" and bound is not None, why


def test_the_LAWFUL_claim_still_attaches():
    """MUST-ALLOW twin for the whole group — otherwise every rule above could
    be satisfied by a door that refuses everything."""
    bound, why = _bind(doc(), LAWFUL)
    assert why == "ok" and bound is not None, why
