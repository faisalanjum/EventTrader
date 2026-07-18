"""FS-18 kind-scoped member fold — the ONE lawful fold equality (FINAL_DESIGN
§5.2 FS-18; STATUS R9 2026-07-17). An incoming XBRL member CLIPS ONTO an
existing company slice value ONLY when its complete kind:norm(value) token
matches an existing token EXACTLY — set membership, never a fuzzy near-match
snap, never stemming/suffix-stripping (the shared format-only normalizer).
Equal value strings under DIFFERENT kinds never fold or share a member link —
unknown included: the unknown-axis sentinel (driver_ids.encode_unknown_axis)
IS its own complete token, so unknowns reuse only by exact sentinel match
(FINAL_DESIGN:174 "enter the company menu for later reuse"). The KIND comes
from the member's own axis through the frozen table and is never reconsidered
here. The semantic producer menu (S3 step-7 proper) builds ON this equality;
the five R9-pinned cases live in test_driver_member_fold.py."""
from driver.core.driver_ids import IdLawError, norm

__all__ = ["member_token", "fold_target"]


def member_token(kind, member_label):
    """The complete kind:norm(value) token for a KNOWN slice kind. Unknown axes
    never come through here — encode_unknown_axis builds their complete token."""
    value = norm(member_label)
    if not kind or not value:
        raise IdLawError(f"empty member token: {kind!r} / {member_label!r} — "
                         f"park, never guess")
    return f"{kind}:{value}"


def fold_target(existing_tokens, token):
    """FS-18 fold decision within ONE company's existing tokens: an exact
    complete-token match returns the existing token (the link clips on, no new
    value is coined); anything else returns None (coin new / keep separate)."""
    return token if token in existing_tokens else None
