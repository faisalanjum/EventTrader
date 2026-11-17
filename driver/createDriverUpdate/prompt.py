from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from neo4j.graph import Node

from .asset import Asset


_PROMPTS = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "Prompts"),
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)


def render_find_facts(source_type: str | Node | Asset | None = None) -> str:
    """Pass a source node, prepared asset or type. Use "" for plain text. Omit for all rules."""
    if isinstance(source_type, Node):
        kinds = (source_type.get("formType"),) if "Report" in source_type.labels else source_type.labels
    elif isinstance(source_type, Asset):
        kinds = (source_type.source_type,)
    else:
        kinds = (source_type,)
    selected = {kind.strip().casefold() for kind in kinds if kind}
    return _PROMPTS.get_template("find_facts.txt").render(
        applies_to=lambda *types: source_type is None or any(kind.casefold() in selected for kind in types)
    )
