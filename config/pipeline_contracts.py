"""Pipeline contracts — canonical set of thinking_type names + experiment_name validator.

Single source of truth for the 3 real pipeline components and the
validator rule that keeps experiment_name traceable to a parent component.

No envelope schema — sdk_session_id is added as a flat top-level field
directly on each result.json (per .claude/plans/obsidian_thinking.md
locked decision: "No unified result envelope").
"""
from __future__ import annotations


KNOWN_TYPES: frozenset[str] = frozenset({"guidance", "prediction", "learning"})


def validate_experiment_name(thinking_type: str, experiment_name: str) -> None:
    """Raise ValueError unless experiment_name starts with f'{thinking_type}_' and has a non-empty tag.

    Rules:
      1. ``thinking_type`` must be in KNOWN_TYPES.
      2. ``experiment_name`` must start with ``f"{thinking_type}_"`` — this
         keeps every experiment traceable to exactly one parent component.
      3. The tag portion after the prefix must be non-empty — no bare
         ``"prediction_"``.

    Examples::

        validate_experiment_name("prediction", "prediction_no_lessons")  # OK
        validate_experiment_name("prediction", "learning_variant")       # raises
        validate_experiment_name("unknown",   "unknown_tag")             # raises
        validate_experiment_name("prediction", "prediction_")            # raises
    """
    if thinking_type not in KNOWN_TYPES:
        raise ValueError(
            f"unknown thinking_type {thinking_type!r}; "
            f"must be one of {sorted(KNOWN_TYPES)}"
        )
    prefix = f"{thinking_type}_"
    if not experiment_name.startswith(prefix):
        raise ValueError(
            f"experiment_name {experiment_name!r} must start with {prefix!r} "
            f"to be traceable to parent component {thinking_type!r}"
        )
    tag = experiment_name[len(prefix):]
    if not tag:
        raise ValueError(
            f"experiment_name {experiment_name!r} has empty tag after the "
            f"{prefix!r} prefix"
        )
