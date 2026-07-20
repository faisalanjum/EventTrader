"""Neutral locator entrypoint (Universal Locator v5.5 §2-§3; WP2 plan v4 step 1).

PRODUCTION anchor rebuild — pure, no I/O, ZERO fiscal.ai/channel imports, ZERO Core imports
(ids are DECODED here independently; only Core composes them). Anchors are rebuilt on demand;
nothing is stored; no registry.

Anchor identity = the 7 fields: company (via the fact's OWN parsed source id looked up in a
TRUSTED edge map — the exactly-one graph-edge query's output) · driver · fact_type=metric ·
slice · measurement · series_unit · time_type.
Search clues (NON-authoritative, retrieval only, never proof): wording = the Driver's immutable
definitional_evidence.birth_quotes PRIMARY, the stored fact quote as fallback (LWW, hence
fallback only) · one ACTIVE ConceptResolution qname when EXACTLY one exists.
NO prior (axis, member) pairs — old XBRL dimensions are never reused; each target source proves
its own complete address.

Prove-or-stop: any unreconstructable identity field raises ValueError naming the SMALLEST
missing piece — never patched with a registry, never guessed.
"""

_ALLOWED_SLOTS = ("period", "slice", "measurement", "quote_hash")   # metric-only: surprise= forbidden
_TIME_TYPES = ("duration", "instant")


def rebuild_anchor(fact_id, props, driver_node, edge_map, fact_quote=None,
                   concept_resolutions=(), numeric_value_present=None):
    """(anchor, stripped_slots) rebuilt from ONE stored fact — or ValueError (fail closed).

    props            : stored fact node fields {fact_scope, series_unit, time_type}
    driver_node      : {name, fact_type, definitional_evidence: {birth_quotes: [...]}}
    edge_map         : {source_id: company_key} — the ONLY way a company enters
    fact_quote       : stored fact quote (LWW) — wording FALLBACK only
    concept_resolutions: ACTIVE ConceptResolution qnames for this Driver; >1 = ambiguous = fail
    numeric_value_present: True if the fact carries a numeric value (then series_unit=None is
                       illegal); None/False = numberless or unknown, no extra check
    """
    seg = fact_id.split(":", 3)
    if len(seg) != 4 or seg[0] != "du":
        raise ValueError(f"bad id shape: {fact_id!r}")
    _, source_id, driver, scope = seg
    for key in ("fact_scope", "series_unit", "time_type"):
        if key not in props:
            raise ValueError(f"missing identity field: props[{key!r}]")
    if props["fact_scope"] != scope:
        raise ValueError(f"stored fact_scope != id suffix: {props['fact_scope']!r} vs {scope!r}")
    parsed = {}
    for slot in scope.split("|"):
        k, _, v = slot.partition("=")
        if k not in _ALLOWED_SLOTS:
            raise ValueError(f"metric-only decoder: forbidden/unknown slot {k!r}")
        if k in parsed:
            raise ValueError(f"duplicate slot {k!r}")
        parsed[k] = v
    if "period" not in parsed:
        raise ValueError("missing identity field: period slot")
    if driver_node.get("name") != driver:
        raise ValueError(f"Driver node name {driver_node.get('name')!r} != id driver {driver!r}")
    if driver_node.get("fact_type") != "metric":
        raise ValueError(f"not a metric Driver: {driver_node.get('fact_type')!r}")
    if props["time_type"] not in _TIME_TYPES:
        raise ValueError(f"missing identity field: time_type {props['time_type']!r} "
                         f"is not one of {_TIME_TYPES}")
    if numeric_value_present and props["series_unit"] is None:
        raise ValueError("numeric fact lacking series_unit (series_unit=None is legal ONLY "
                         "for numberless metrics)")
    company = edge_map.get(source_id)
    if company is None:
        raise ValueError(f"no company edge for THIS fact's source id {source_id!r} "
                         f"(cross-wired or missing edge)")
    birth = tuple(q for q in driver_node.get("definitional_evidence", {}).get("birth_quotes", ())
                  if isinstance(q, str) and q.strip())
    if birth:
        wording = birth
    elif isinstance(fact_quote, str) and fact_quote.strip():
        wording = (fact_quote,)                      # LWW fallback — only when birth is blank
    else:
        raise ValueError("blank wording clues: no nonblank birth_quotes and no fact quote")
    actives = tuple(concept_resolutions)
    if len(actives) > 1:
        raise ValueError(f"{len(actives)} ACTIVE ConceptResolutions — ambiguous, fail closed")
    anchor = {
        "source_id": source_id,
        "company": company,
        "driver": driver,
        "slice": parsed.get("slice", ""),
        "measurement": parsed.get("measurement", ""),
        "series_unit": props["series_unit"],
        "time_type": props["time_type"],
        "fact_type": driver_node["fact_type"],
        "wording": wording,
        "concept_clue": actives[0] if actives else None,   # RETRIEVAL only — never proof
    }
    return anchor, sorted(k for k in ("period", "quote_hash") if k in parsed)
