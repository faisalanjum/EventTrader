"""THE one outcome-code vocabulary + ordering owner (T1, #827 F-VALID).

Owner ruling (answer sheet 412792b7 row T1, verbatim): "NEW TINY MODULE
(e.g. driver/core/outcome_codes.py) owns the ~21 codes + ordering; every
emitter imports it." Authority: BUILD:838-843 (explicit codes only; free
text never parsed) + ChannelContract:52-54 (outcome meanings).

Consumers land serially: driver_validators HERE (T1); xbrl_attach via F4;
the resolver's period codes via P-O2. The attach tokens are listed now so
the vocabulary is complete on day one — F4 wires their runtime consumption.
"""

#: The 30 validator tokens, MEASURED from the emitter's own source (the 29
#: `add()` codes — including the OD-21 surprise-trap codes F1..F9, which a
#: first letters-only scan missed — plus SHAPE, minted directly at the
#: shape-hint sites). The card's "~21" was an estimate; the vocabulary is
#: derived, never assumed. Order = the publication order groups appear in
#: validate_fact; ordering is part of the contract and owned HERE only.
VALIDATOR_CODES = (
    "DRIVER", "STATE", "QUOTE", "SHAPE", "SIGN", "BASELINE", "UNIT",
    "MOVEMENT", "VALUE_TEXT", "CONDITIONS", "DERIVABLE", "MALFORMED",
    "UNKNOWN_FIELD", "ID", "LANE", "PERIOD_LANE", "PERIOD_SYM", "SCOPE_PAIR",
    "ISO", "INSTANT", "FISCAL",
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9",
)

#: The 6 attach-door tokens (xbrl_attach's published outcome codes).
ATTACH_CODES = (
    "XBRL_CONTRACT_INVALID", "XBRL_BINDING_UNAVAILABLE", "NOT_STORABLE",
    "SOURCE_UNAVAILABLE", "SOURCE_COMPANY_AMBIGUOUS", "MEMBER_LINK_INVALID",
)

#: The 2 Core V2 event-route tokens, OWNER-FROZEN 2026-08-12.
#: `READER_ABSTAINED` — the reader looked at a SUBMITTED raw item and declined
#: it. That is an outcome, not an error, and it is why a lawful public `skipped`
#: was unconstructible until now.
#: `CHANNEL_CONTRACT_INVALID` — the GENERIC public channel boundary only: a
#: malformed Stage-A item from the channel. It never replaces, aliases or
#: duplicates `XBRL_CONTRACT_INVALID`, which stays the XBRL door's own code for
#: door-specific failures.
#: Each spelled ONCE here and imported by name, so no consumer restates a token.
READER_ABSTAINED = "READER_ABSTAINED"
CHANNEL_CONTRACT_INVALID = "CHANNEL_CONTRACT_INVALID"
ROUTE_CODES = (READER_ABSTAINED, CHANNEL_CONTRACT_INVALID)

#: The complete deduplicated vocabulary, validator order first then attach.
OUTCOME_CODES = VALIDATOR_CODES + tuple(
    c for c in ATTACH_CODES + ROUTE_CODES if c not in VALIDATOR_CODES)

#: THE compact-date ordering law (the F-PERIOD compact-20251231 conflict lands
#: HERE, at the one owner): a compact date carried INSIDE a period id is judged
#: by the ID GRAMMAR first — it publishes PERIOD_SYM, never ISO. ISO is the
#: date-field grammar for dates supplied AS dates. Behavior twin (evidence,
#: not law): test_827B2_compact_gp_end_names_PERIOD_SYM_never_F7. P-O2's one
#: period invariant consumes this ordering; no emitter re-decides it.
COMPACT_DATE_IN_ID_ORDER = ("PERIOD_SYM", "ISO")


def require_known(code):
    """Fail LOUD on a token outside the vocabulary — a rogue code is a
    programming error, never a park. Emitters call this at mint time."""
    if code not in OUTCOME_CODES:
        raise ValueError(f"outcome code {code!r} is not in the one vocabulary")
    return code
