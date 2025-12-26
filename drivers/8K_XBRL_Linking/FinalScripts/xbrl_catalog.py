"""
XBRL Catalog - Neo4j Integration for Company XBRL Data
=======================================================

Fetches and structures XBRL data from Neo4j in an LLM-friendly format.
Provides normalized reference tables and comprehensive relationship data.

IMPORTANT: Only 10-K, 10-Q, 10-K/A, and 10-Q/A filings have XBRL data.
8-K and other form types do NOT contain structured XBRL financial data.

Usage:
    from xbrl_catalog import xbrl_catalog, search_xbrl_concepts, XBRL_FORM_TYPES

    # Get full catalog for a company (by CIK or ticker)
    # By default, fetches only 10-K and 10-Q filings (the only ones with XBRL)
    catalog = xbrl_catalog("ICE")  # or xbrl_catalog("1571949")

    # Get LLM-ready context
    print(catalog.to_llm_context())

    # Access normalized data
    print(catalog.concepts)      # All concepts with fact counts
    print(catalog.periods)       # All reporting periods
    print(catalog.members)       # Business segments

    # Query specific data
    revenue_series = catalog.get_time_series("us-gaap:Revenues")

    # Search for concepts
    results = search_xbrl_concepts("revenue", cik="1571949")

    # Only fetch 10-K filings
    catalog = xbrl_catalog("ICE", form_types=["10-K"])

Environment Variables Required:
    NEO4J_URI: Neo4j connection URI (default: bolt://localhost:30687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (required)
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# Load .env from project root (search upward from this file)
# Use override=True to ensure .env values take precedence over shell env vars
_project_root = Path(__file__).resolve().parents[3]  # Experiments -> 8K_XBRL_Linking -> drivers -> EventMarketDB
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)
else:
    load_dotenv(override=True)  # Fallback to default behavior

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class XBRLFact:
    """Individual XBRL fact with full context."""
    concept_label: str
    concept_qname: str
    value: str
    is_numeric: bool
    decimals: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    period_type: str  # instant or duration
    unit: Optional[str]
    balance: Optional[str]  # credit, debit, or null
    dimensional_context: List[Dict[str, str]] = field(default_factory=list)  # [{dimension: label, member: label}, ...]
    context_id: Optional[str] = None
    report_accession: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "concept": self.concept_label,
            "qname": self.concept_qname,
            "value": self.value,
            "numeric": self.is_numeric,
            "decimals": self.decimals,
            "period": {
                "start": self.period_start,
                "end": self.period_end,
                "type": self.period_type
            },
            "unit": self.unit,
            "balance": self.balance,
            "dimensional_context": self.dimensional_context
        }

    @property
    def period_display(self) -> str:
        """Human-readable period string."""
        if self.period_type == "instant":
            return f"As of {self.period_start}" if self.period_start else ""
        else:
            if self.period_start and self.period_end:
                return f"{self.period_start} to {self.period_end}"
            return ""

    @property
    def members(self) -> List[str]:
        """Get list of member labels for this fact."""
        return [dc.get("member") for dc in self.dimensional_context if dc.get("member")]

    @property
    def dimensions(self) -> List[str]:
        """Get list of dimension labels for this fact."""
        return [dc.get("dimension") for dc in self.dimensional_context if dc.get("dimension")]

    @property
    def member(self) -> Optional[str]:
        """Get first member label (for backward compatibility)."""
        return self.members[0] if self.members else None

    @property
    def dimension(self) -> Optional[str]:
        """Get first dimension label (for backward compatibility)."""
        return self.dimensions[0] if self.dimensions else None


@dataclass
class XBRLFiling:
    """XBRL data for a single SEC filing."""
    accession_no: str
    form_type: str
    period_of_report: str
    xbrl_id: Optional[str] = None
    facts: List[XBRLFact] = field(default_factory=list)
    key_metrics: Dict[str, Dict] = field(default_factory=dict)

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    def get_concepts(self) -> Dict[str, List[XBRLFact]]:
        """Group facts by concept label."""
        concepts = {}
        for fact in self.facts:
            if fact.concept_label not in concepts:
                concepts[fact.concept_label] = []
            concepts[fact.concept_label].append(fact)
        return concepts

    def get_dimensions(self) -> Dict[str, List[str]]:
        """Get unique dimensions and their members."""
        dims = {}
        for fact in self.facts:
            for dc in fact.dimensional_context:
                dim = dc.get("dimension")
                mem = dc.get("member")
                if dim:
                    if dim not in dims:
                        dims[dim] = set()
                    if mem:
                        dims[dim].add(mem)
        return {k: sorted(list(v)) for k, v in dims.items()}

    def get_facts_for_concept(self, concept_label: str) -> List[XBRLFact]:
        """Get all facts for a specific concept."""
        return [f for f in self.facts if f.concept_label == concept_label]

    def to_dict(self) -> dict:
        return {
            "accession_no": self.accession_no,
            "form_type": self.form_type,
            "period_of_report": self.period_of_report,
            "fact_count": self.fact_count,
            "key_metrics": self.key_metrics,
            "concepts": {
                label: [fact.to_dict() for fact in facts]
                for label, facts in self.get_concepts().items()
            },
            "dimensions": self.get_dimensions()
        }


@dataclass
class XBRLCatalog:
    """
    Complete XBRL catalog for a company - LLM-optimized structure.

    Provides:
    - Normalized reference tables (concepts, periods, units, members)
    - Denormalized facts for easy querying
    - Calculation relationships
    - Multiple output formats optimized for LLM consumption
    """
    cik: str
    company_name: str
    ticker: str
    industry: str = ""
    sector: str = ""

    # Filings with their facts
    filings: List[XBRLFiling] = field(default_factory=list)

    # Normalized reference tables (with fact counts)
    concepts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    periods: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    units: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dimensions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    members: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Relationship structures (compact, LLM-friendly)
    calculation_trees: List[Dict[str, Any]] = field(default_factory=list)  # Legacy format

    # New compact network representations
    # calculation_network: {parent_qname: [{child: qname, weight: +1/-1, label: str}, ...]}
    calculation_network: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    # presentation_sections: {section_label: [concept_qnames...]}
    presentation_sections: Dict[str, List[str]] = field(default_factory=dict)

    # ==========================================================================
    # CORE PROPERTIES
    # ==========================================================================

    @property
    def all_facts(self) -> List[XBRLFact]:
        """Get all facts across all filings."""
        facts = []
        for filing in self.filings:
            facts.extend(filing.facts)
        return facts

    @property
    def total_facts(self) -> int:
        """Total number of facts across all filings."""
        return sum(f.fact_count for f in self.filings)

    # ==========================================================================
    # QUERY METHODS
    # ==========================================================================

    def get_facts_for_concept(self, concept_qname: str) -> List[XBRLFact]:
        """Get all facts for a specific concept (by qname) across all filings."""
        return [f for f in self.all_facts if f.concept_qname == concept_qname]

    def get_facts_by_label(self, concept_label: str) -> List[XBRLFact]:
        """Get all facts for a specific concept (by label) across all filings."""
        return [f for f in self.all_facts if f.concept_label == concept_label]

    def get_time_series(self, concept_qname: str, member: str = None) -> List[Dict]:
        """
        Get time series data for a concept across all filings.

        Args:
            concept_qname: XBRL concept qname (e.g., "us-gaap:Revenues")
            member: Optional member filter (e.g., segment name)

        Returns:
            List of facts sorted by period, oldest to newest
        """
        facts = self.get_facts_for_concept(concept_qname)

        if member:
            facts = [f for f in facts if f.member and member.lower() in f.member.lower()]

        # Convert to dicts and sort by period
        results = []
        for fact in facts:
            results.append({
                "filing": fact.report_accession,
                "value": fact.value,
                "period_start": fact.period_start,
                "period_end": fact.period_end,
                "period_display": fact.period_display,
                "unit": fact.unit,
                "member": fact.member,
                "is_numeric": fact.is_numeric
            })

        # Sort by period end date (or start for instant)
        def sort_key(r):
            return r.get("period_end") or r.get("period_start") or ""

        return sorted(results, key=sort_key)

    def get_concept_timeseries(self, concept_label: str) -> List[Dict]:
        """
        Get all values for a concept (by label) across filings.
        Alias for compatibility with existing code.
        """
        facts = self.get_facts_by_label(concept_label)
        results = []
        for fact in facts:
            results.append({
                "filing": fact.report_accession,
                "form": next((f.form_type for f in self.filings
                             if f.accession_no == fact.report_accession), ""),
                "period_of_report": next((f.period_of_report for f in self.filings
                                         if f.accession_no == fact.report_accession), ""),
                "value": fact.value,
                "period_start": fact.period_start,
                "period_end": fact.period_end,
                "unit": fact.unit,
                "member": fact.member
            })
        return sorted(results, key=lambda x: x.get("period_of_report", ""))

    # ==========================================================================
    # INDEX PROPERTIES (Formatted views)
    # ==========================================================================

    @property
    def concept_index(self) -> str:
        """Formatted index of all concepts reported by this company."""
        if not self.concepts:
            return "No concepts found."

        # Group concepts by namespace
        by_namespace = {}
        for qname, info in self.concepts.items():
            ns = info.get("namespace", "").split("/")[-1] if info.get("namespace") else "custom"
            if ns not in by_namespace:
                by_namespace[ns] = []
            by_namespace[ns].append({
                "qname": qname,
                "label": info.get("label", qname),
                "balance": info.get("balance"),
                "period_type": info.get("period_type"),
                "fact_count": info.get("fact_count", 0)
            })

        lines = [f"CONCEPT INDEX FOR {self.company_name} (CIK: {self.cik})", "=" * 60]

        for ns, concepts in sorted(by_namespace.items()):
            lines.append(f"\n## {ns.upper()} ({len(concepts)} concepts)")
            for c in sorted(concepts, key=lambda x: -x.get("fact_count", 0))[:25]:
                balance_str = f" [{c['balance']}]" if c.get("balance") and c["balance"] != "null" else ""
                lines.append(f"  - {c['label']}{balance_str}: {c['fact_count']} facts")
            if len(concepts) > 25:
                lines.append(f"  ... and {len(concepts) - 25} more")

        return "\n".join(lines)

    @property
    def period_index(self) -> str:
        """Formatted list of all reporting periods."""
        if not self.periods:
            return "No periods found."

        lines = [f"REPORTING PERIODS FOR {self.company_name}", "=" * 50]

        instant = [(k, v) for k, v in self.periods.items() if v.get("type") == "instant"]
        duration = [(k, v) for k, v in self.periods.items() if v.get("type") == "duration"]

        if instant:
            lines.append("\n## Point-in-Time (Instant) Periods:")
            for pid, p in sorted(instant, key=lambda x: x[1].get("date", ""), reverse=True)[:15]:
                lines.append(f"  - {p.get('date', 'N/A')}: {p.get('fact_count', 0)} facts")

        if duration:
            lines.append("\n## Time Range (Duration) Periods:")
            for pid, p in sorted(duration, key=lambda x: x[1].get("end", ""), reverse=True)[:15]:
                lines.append(f"  - {p.get('start', '?')} to {p.get('end', '?')}: {p.get('fact_count', 0)} facts")

        return "\n".join(lines)

    @property
    def segment_breakdown(self) -> str:
        """Breakdown of dimensional data (business segments, geographies, etc.)."""
        if not self.members:
            return "No dimensional/segment data found."

        lines = [f"SEGMENT/DIMENSION BREAKDOWN FOR {self.company_name}", "=" * 55]

        # Group members by dimension
        by_dimension = {}
        for mem_qname, info in self.members.items():
            dim = info.get("dimension", "Unknown Dimension")
            if dim not in by_dimension:
                by_dimension[dim] = []
            by_dimension[dim].append({
                "qname": mem_qname,
                "label": info.get("label", mem_qname.split(":")[-1] if ":" in mem_qname else mem_qname),
                "fact_count": info.get("fact_count", 0)
            })

        for dim, mems in by_dimension.items():
            dim_label = dim.split(":")[-1] if dim and ":" in dim else (dim or "Unknown")
            lines.append(f"\n## {dim_label}")
            for m in sorted(mems, key=lambda x: -x.get("fact_count", 0))[:15]:
                lines.append(f"  - {m['label']}: {m['fact_count']} facts")
            if len(mems) > 15:
                lines.append(f"  ... and {len(mems) - 15} more")

        return "\n".join(lines)

    # ==========================================================================
    # SERIALIZATION
    # ==========================================================================

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "company": {
                "cik": self.cik,
                "name": self.company_name,
                "ticker": self.ticker,
                "industry": self.industry,
                "sector": self.sector
            },
            "summary": self._build_summary(),
            "catalog": {
                "concepts": self.concepts,
                "periods": self.periods,
                "units": self.units,
                "dimensions": self.dimensions,
                "members": self.members
            },
            "filings": [f.to_dict() for f in self.filings],
            "relationships": {
                "calculation_trees": self.calculation_trees
            }
        }

    def _build_summary(self) -> dict:
        """Build a summary of all data."""
        # Count report types
        report_types = {}
        for f in self.filings:
            report_types[f.form_type] = report_types.get(f.form_type, 0) + 1

        # Find date range
        periods = [f.period_of_report for f in self.filings if f.period_of_report]

        return {
            "total_filings": len(self.filings),
            "total_facts": self.total_facts,
            "unique_concepts": len(self.concepts),
            "unique_periods": len(self.periods),
            "unique_units": len(self.units),
            "unique_segments": len(self.members),
            "report_types": report_types,
            "date_range": {
                "earliest": min(periods) if periods else None,
                "latest": max(periods) if periods else None
            },
            "has_calculation_relationships": len(self.calculation_trees) > 0
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    # ==========================================================================
    # LLM OUTPUT FORMATS
    # ==========================================================================

    def to_markdown(self, max_facts_per_concept: int = 5) -> str:
        """
        Generate LLM-friendly markdown representation.

        This format is optimized for LLM consumption with:
        - Clear hierarchical structure
        - Human-readable labels
        - Compact but complete information
        """
        lines = []

        # Header
        lines.append(f"# XBRL Catalog: {self.company_name} ({self.ticker})")
        lines.append(f"**CIK:** {self.cik}")
        if self.industry:
            lines.append(f"**Industry:** {self.industry}")
        if self.sector:
            lines.append(f"**Sector:** {self.sector}")
        lines.append("")

        # Summary
        summary = self._build_summary()
        lines.append("## Summary")
        lines.append(f"- **Total Filings:** {summary['total_filings']}")
        lines.append(f"- **Total Facts:** {summary['total_facts']:,}")
        lines.append(f"- **Unique Concepts:** {summary['unique_concepts']}")
        if summary['date_range']['earliest']:
            lines.append(f"- **Date Range:** {summary['date_range']['earliest']} to {summary['date_range']['latest']}")
        lines.append("")

        # Filing Inventory
        lines.append("## Available Filings")
        lines.append("| Accession No | Form | Period | Facts |")
        lines.append("|--------------|------|--------|-------|")
        for f in sorted(self.filings, key=lambda x: x.period_of_report or "", reverse=True):
            lines.append(f"| {f.accession_no} | {f.form_type} | {f.period_of_report} | {f.fact_count:,} |")
        lines.append("")

        # Concept Index grouped by period type
        lines.append("## Concept Index")
        lines.append("")

        instant_concepts = []
        duration_concepts = []

        for qname, info in self.concepts.items():
            label = info.get("label", qname)
            balance = info.get("balance") or "N/A"
            ns = qname.split(":")[0] if ":" in qname else "custom"
            entry = f"- **{label}** [{ns}] ({balance}) - {info.get('fact_count', 0)} facts"

            if info.get("period_type") == "instant":
                instant_concepts.append((info.get("fact_count", 0), entry))
            else:
                duration_concepts.append((info.get("fact_count", 0), entry))

        lines.append("### Balance Sheet Items (point-in-time)")
        for _, entry in sorted(instant_concepts, reverse=True)[:30]:
            lines.append(entry)
        if len(instant_concepts) > 30:
            lines.append(f"- ... and {len(instant_concepts) - 30} more")
        lines.append("")

        lines.append("### Income Statement / Flow Items (period-based)")
        for _, entry in sorted(duration_concepts, reverse=True)[:30]:
            lines.append(entry)
        if len(duration_concepts) > 30:
            lines.append(f"- ... and {len(duration_concepts) - 30} more")
        lines.append("")

        # Segments/Dimensions
        if self.members:
            lines.append("## Available Dimensions (Segment Breakdowns)")
            # Group by dimension
            by_dim = {}
            for mem_qname, info in self.members.items():
                dim = info.get("dimension") or "Unknown"
                if dim not in by_dim:
                    by_dim[dim] = []
                by_dim[dim].append(info.get("label", mem_qname))

            for dim, members in by_dim.items():
                dim_label = dim.split(":")[-1] if dim and ":" in dim else dim
                lines.append(f"### {dim_label}")
                for m in members[:10]:
                    lines.append(f"- {m}")
                if len(members) > 10:
                    lines.append(f"- ... and {len(members) - 10} more")
                lines.append("")

        # Calculation & Presentation Networks (Compact format)
        networks = self.render_networks_compact()
        if networks:
            lines.append(networks)
            lines.append("")

        # Sample Facts from most recent filing
        if self.filings:
            recent = sorted(self.filings, key=lambda x: x.period_of_report or "", reverse=True)[0]
            lines.append(f"## Sample Facts (from {recent.form_type} {recent.period_of_report})")
            lines.append("")
            lines.append("| Concept | Value | Period | Unit | Segment |")
            lines.append("|---------|-------|--------|------|---------|")

            shown = 0
            for label, facts in sorted(recent.get_concepts().items()):
                for fact in facts[:max_facts_per_concept]:
                    period = fact.period_end or fact.period_start or "N/A"
                    segment = fact.member or "-"
                    concept_short = label[:40] + ('...' if len(label) > 40 else '')
                    lines.append(f"| {concept_short} | {fact.value} | {period} | {fact.unit or '-'} | {segment} |")
                    shown += 1
                    if shown >= 50:
                        break
                if shown >= 50:
                    break

            if shown >= 50:
                lines.append(f"\n*... showing 50 of {recent.fact_count:,} facts*")

        return "\n".join(lines)

    def to_llm_context(self,
                       include_facts: bool = True,
                       max_facts: int = 50,
                       max_concepts: int = 100,
                       include_relationships: bool = True) -> str:
        """
        Generate LLM-optimized text representation with qnames for Neo4j linking.

        Designed for LLMs that need to:
        - Match extracted data to XBRL concepts
        - Output exact qnames for Neo4j queries
        - Validate extracted values against known data

        Args:
            include_facts: Whether to include sample fact values
            max_facts: Maximum sample facts (default 50)
            max_concepts: Maximum concepts to show (default 100 for matching coverage)
            include_relationships: Whether to include calc/presentation networks
        """
        L = []  # lines
        SEP = "─" * 72

        # ══════════════════════════════════════════════════════════════════════
        # HEADER
        # ══════════════════════════════════════════════════════════════════════
        L.append("<<<BEGIN_XBRL_REFERENCE_DATA>>>")
        L.append(f"COMPANY: {self.company_name} ({self.ticker})")
        L.append(f"CIK: {self.cik}" + (f" | Industry: {self.industry} | Sector: {self.sector}" if self.industry else ""))

        # ══════════════════════════════════════════════════════════════════════
        # LEGEND - Reference data explanation (instructions belong in prompt)
        # ══════════════════════════════════════════════════════════════════════
        L.append("")
        L.append("LEGEND:")
        L.append("• qname = unique concept identifier (e.g., us-gaap:Revenues)")
        L.append("• label = human-readable name")
        L.append("• balance: credit = ↑equity/liability | debit = ↑assets/expenses")

        # ══════════════════════════════════════════════════════════════════════
        # FILINGS
        # ══════════════════════════════════════════════════════════════════════
        L.append("")
        L.append(SEP)
        L.append(f"FILINGS ({len(self.filings)} reports, {self.total_facts:,} total facts)")
        L.append(SEP)

        for f in sorted(self.filings, key=lambda x: x.period_of_report or "", reverse=True):
            metrics_str = ""
            if f.key_metrics:
                metrics = [f"{k}={v.get('value','?')}" for k, v in list(f.key_metrics.items())[:3]]
                metrics_str = " | " + ", ".join(metrics)
            L.append(f"{f.form_type} {f.period_of_report} [{f.fact_count:,} facts]{metrics_str}")

        # ══════════════════════════════════════════════════════════════════════
        # CONCEPTS - With qnames and history for matching & validation
        # ══════════════════════════════════════════════════════════════════════
        L.append("")
        L.append(SEP)
        L.append(f"CONCEPTS ({len(self.concepts)} total, top {min(max_concepts, len(self.concepts))} shown)")
        L.append("History shows recent values for magnitude validation (10-K=annual, 10-Q=quarterly)")
        L.append(SEP)

        # Build concept history from all filings (for magnitude validation)
        concept_history = {}
        for filing in sorted(self.filings, key=lambda x: x.period_of_report or "", reverse=True):
            for fact in filing.facts:
                if fact.concept_qname and fact.is_numeric and not fact.member:
                    if fact.concept_qname not in concept_history:
                        concept_history[fact.concept_qname] = []
                    # Only keep up to 4 periods per concept
                    if len(concept_history[fact.concept_qname]) < 4:
                        # Handle 'null' string from database as None
                        pe = fact.period_end if fact.period_end and fact.period_end != 'null' else None
                        ps = fact.period_start if fact.period_start and fact.period_start != 'null' else None
                        concept_history[fact.concept_qname].append({
                            "value": fact.value,
                            "period_start": ps,
                            "period_end": pe or ps or filing.period_of_report,
                            "period_type": fact.period_type,
                            "form_type": filing.form_type,
                            "unit": fact.unit
                        })

        top_concepts = sorted(self.concepts.items(), key=lambda x: -x[1].get("fact_count", 0))[:max_concepts]

        # Show history for top 30 concepts (key financials), just qname for rest
        history_limit = 30

        # ── TOP CONCEPTS (with history for magnitude validation) ──
        L.append("── TOP CONCEPTS (with history for magnitude validation) ──")
        for idx, (qname, info) in enumerate(top_concepts[:history_limit]):
            label = info.get("label", qname.split(":")[-1])
            label_short = label[:30] + "..." if len(label) > 30 else label
            balance = info.get("balance", "")
            bal_str = balance if balance and balance != "null" else "-"

            L.append(f"{qname} | {label_short} | {bal_str}")

            # Add history line for magnitude validation
            history = concept_history.get(qname, [])
            if history:
                hist_parts = []
                for h in history[:4]:
                    val = _format_value(h["value"], h.get("unit"))
                    form = h["form_type"][:4] if h.get("form_type") else "?"
                    # Format period to match matched_period output contract
                    ptype = h.get("period_type", "")
                    ps = h.get("period_start", "")
                    pe = h.get("period_end", "")
                    if ptype == "duration" and ps and pe:
                        # Normalize: XBRL often uses exclusive end date, subtract 1 day
                        from datetime import datetime, timedelta
                        try:
                            end_dt = datetime.strptime(pe[:10], "%Y-%m-%d")
                            end_normalized = (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                            period = f"{ps[:10]}→{end_normalized}"
                        except:
                            period = f"{ps[:10]}→{pe[:10]}"
                    elif pe:
                        period = pe[:10]
                    else:
                        period = "?"
                    hist_parts.append(f"{val} ({form}, {period})")
                L.append(f"  History: {', '.join(hist_parts)}")

        # ── ADDITIONAL CONCEPTS (qname + label only) ──
        if len(top_concepts) > history_limit:
            L.append("")
            L.append(f"── ADDITIONAL CONCEPTS ({len(top_concepts) - history_limit} more) ──")
            for qname, info in top_concepts[history_limit:]:
                label = info.get("label", qname.split(":")[-1])
                label_short = label[:35] + "..." if len(label) > 35 else label
                balance = info.get("balance", "")
                bal_str = balance if balance and balance != "null" else "-"
                L.append(f"{qname} | {label_short} | {bal_str}")

        if len(self.concepts) > max_concepts:
            L.append(f"...+{len(self.concepts) - max_concepts} more concepts (less common)")

        # Note: UNMATCHED fallback belongs in prompt, not reference data

        # ══════════════════════════════════════════════════════════════════════
        # PERIODS - Exact format for output
        # ══════════════════════════════════════════════════════════════════════
        L.append("")
        L.append(SEP)
        L.append(f"PERIODS ({len(self.periods)} unique)")
        L.append(SEP)

        # Collect unique periods (normalize duration end dates - XBRL uses exclusive end)
        from datetime import datetime, timedelta
        instants, durations = set(), set()
        for pid, p in self.periods.items():
            ptype = p.get("type", "")
            end = p.get("end") or p.get("date") or ""
            start = p.get("start", "")
            if ptype == "instant" and end:
                instants.add(end[:10])  # Just date part
            elif ptype == "duration" and start and end:
                # Normalize: subtract 1 day from XBRL exclusive end date
                try:
                    end_dt = datetime.strptime(end[:10], "%Y-%m-%d")
                    end_normalized = (end_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                    # Zero-length durations (start == normalized end) → treat as instant
                    if start[:10] == end_normalized:
                        instants.add(end_normalized)
                    else:
                        durations.add(f"{start[:10]}→{end_normalized}")
                except:
                    durations.add(f"{start[:10]}→{end[:10]}")

        if instants:
            sorted_instants = sorted(instants, reverse=True)[:12]
            L.append(f"Instant: {', '.join(sorted_instants)}" + (f" +{len(instants)-12}more" if len(instants) > 12 else ""))
        if durations:
            sorted_durations = sorted(durations, reverse=True)[:8]
            L.append(f"Duration: {', '.join(sorted_durations)}" + (f" +{len(durations)-8}more" if len(durations) > 8 else ""))

        # ══════════════════════════════════════════════════════════════════════
        # UNITS - Dynamically extract canonical names from XBRL unit metadata
        # ══════════════════════════════════════════════════════════════════════
        # Filter to numeric units and convert to canonical format
        canonical_units = []
        seen = set()
        for uname, info in sorted(self.units.items(), key=lambda x: -x[1].get("fact_count", 0)):
            utype = info.get("type", "")
            canonical = None

            if utype == "monetaryItemType" and uname.startswith("iso4217:"):
                # iso4217:USD → USD, iso4217:EUR → EUR
                canonical = uname.split(":")[1]
            elif utype == "perShareItemType" and uname.startswith("iso4217:") and uname.endswith("shares"):
                # iso4217:USDshares → USD/share
                currency = uname.split(":")[1].replace("shares", "")
                canonical = f"{currency}/share"
            elif utype == "sharesItemType" or uname == "shares":
                canonical = "shares"
            elif uname == "pure":
                canonical = "pure"

            if canonical and canonical not in seen:
                canonical_units.append(canonical)
                seen.add(canonical)

        L.append("")
        L.append(SEP)
        L.append("UNITS")
        L.append(SEP)
        L.append(" | ".join(canonical_units) if canonical_units else "USD | shares | pure")

        # ══════════════════════════════════════════════════════════════════════
        # DIMENSIONS → MEMBERS - Full qnames for segmented data
        # ══════════════════════════════════════════════════════════════════════
        # Build set of active member labels from loaded filings
        active_member_labels = set()
        for fact in self.all_facts:
            for dc in fact.dimensional_context:
                if dc.get("member"):
                    active_member_labels.add(dc.get("member"))

        # Filter members to only those with facts in loaded filings
        active_members = {
            qname: info for qname, info in self.members.items()
            if info.get("label") in active_member_labels
        }

        if self.dimensions or active_members:
            L.append("")
            L.append(SEP)
            L.append(f"DIMENSIONS → MEMBERS ({len(active_members)} active in these filings)")
            L.append(SEP)

            # Group members by dimension with full qnames
            dim_members = {}
            for mem_qname, info in active_members.items():
                dim = info.get("dimension", "Unknown")
                if dim not in dim_members:
                    dim_members[dim] = []
                dim_members[dim].append((mem_qname, info.get("fact_count", 0)))

            # Sort dimensions by total facts
            for dim_qname in sorted(dim_members.keys(), key=lambda d: sum(m[1] for m in dim_members[d]), reverse=True)[:12]:
                members = sorted(dim_members[dim_qname], key=lambda x: -x[1])[:8]
                L.append(f"{dim_qname}:")
                for mem_qname, fc in members:
                    L.append(f"  → {mem_qname}")
                if len(dim_members[dim_qname]) > 8:
                    L.append(f"  → +{len(dim_members[dim_qname])-8} more members")

        # ══════════════════════════════════════════════════════════════════════
        # CALCULATION NETWORK - How values compute (grouped by statement)
        # ══════════════════════════════════════════════════════════════════════
        if include_relationships and self.calculation_network:
            L.append("")
            L.append(SEP)
            L.append(f"CALCULATIONS ({len(self.calculation_network)} formulas) - how values sum")
            L.append(SEP)
            L.append("Format: [Statement] Result = +adds −subtracts")

            # Group calculations by statement
            by_statement = {}
            for parent_qname, data in self.calculation_network.items():
                # Handle both old format (list) and new format (dict with children/network)
                if isinstance(data, dict):
                    children = data.get("children", [])
                    network = data.get("network", "Other")
                else:
                    children = data
                    network = "Other"

                if network not in by_statement:
                    by_statement[network] = []
                by_statement[network].append((parent_qname, children))

            # Statement display order
            stmt_order = ["IncomeStatement", "BalanceSheet", "CashFlows", "Equity", "ComprehensiveIncome", "Other"]
            shown = 0
            max_formulas = 15

            for stmt in stmt_order:
                if stmt not in by_statement or shown >= max_formulas:
                    continue

                formulas = sorted(by_statement[stmt], key=lambda x: len(x[1]), reverse=True)
                for parent_qname, children in formulas[:4]:  # Max 4 per statement
                    if shown >= max_formulas:
                        break
                    parent_short = parent_qname.split(":")[-1]
                    parts = []
                    for child in children[:5]:
                        w = child.get("weight", 1)
                        sign = "+" if float(w) >= 0 else "−"
                        child_short = child.get("child", "").split(":")[-1]
                        parts.append(f"{sign}{child_short}")
                    if len(children) > 5:
                        parts.append(f"+{len(children)-5}more")
                    L.append(f"[{stmt}] {parent_short} = {' '.join(parts)}")
                    shown += 1

        # ══════════════════════════════════════════════════════════════════════
        # PRESENTATION STRUCTURE - How values are displayed (grouped by statement)
        # ══════════════════════════════════════════════════════════════════════
        if include_relationships and self.presentation_sections:
            L.append("")
            L.append(SEP)
            L.append(f"PRESENTATION ({len(self.presentation_sections)} sections) - display groupings")
            L.append(SEP)

            # Group presentations by statement
            by_statement = {}
            for section, data in self.presentation_sections.items():
                # Handle both old format (list) and new format (dict with concepts/network)
                if isinstance(data, dict):
                    concepts = data.get("concepts", [])
                    network = data.get("network", "Other")
                else:
                    concepts = data
                    network = "Other"

                if network not in by_statement:
                    by_statement[network] = []
                by_statement[network].append((section, concepts))

            # Statement display order
            stmt_order = ["IncomeStatement", "BalanceSheet", "CashFlows", "Equity", "Cover", "Notes", "Other"]
            shown = 0
            max_sections = 15

            for stmt in stmt_order:
                if stmt not in by_statement or shown >= max_sections:
                    continue

                L.append(f"[{stmt}]")
                sections = sorted(by_statement[stmt], key=lambda x: len(x[1]), reverse=True)
                for section, concepts in sections[:3]:  # Max 3 per statement
                    if shown >= max_sections:
                        break
                    section_clean = section.replace(" [Abstract]", "").replace(" [Line Items]", "").replace(" [Roll Forward]", "")
                    section_clean = section_clean[:30] + "..." if len(section_clean) > 30 else section_clean
                    concept_shorts = [c.split(":")[-1][:18] for c in concepts[:4]]
                    concept_str = ", ".join(concept_shorts)
                    if len(concepts) > 4:
                        concept_str += f" +{len(concepts)-4}more"
                    L.append(f"  {section_clean} ({len(concepts)}): {concept_str}")
                    shown += 1

        # ══════════════════════════════════════════════════════════════════════
        # SAMPLE FACTS - With qnames for validation
        # ══════════════════════════════════════════════════════════════════════
        if include_facts and self.all_facts:
            L.append("")
            L.append(SEP)
            L.append(f"SAMPLE FACTS ({min(max_facts, len(self.all_facts))} of {self.total_facts:,}) - numeric values for magnitude validation")
            L.append(SEP)
            L.append("qname | value | unit | period | segment")

            shown = 0
            seen = set()
            # Prioritize: numeric first, then consolidated (no segment), then by qname
            sorted_facts = sorted(
                self.all_facts,
                key=lambda f: (not f.is_numeric, f.member is not None, f.concept_qname)
            )

            for fact in sorted_facts:
                if shown >= max_facts:
                    break
                if fact.concept_qname in seen:
                    continue
                seen.add(fact.concept_qname)

                qname = fact.concept_qname
                # Format value for readability if numeric
                if fact.is_numeric:
                    val = _format_value(fact.value, fact.unit)
                else:
                    # Truncate text values
                    val = fact.value[:50] + "..." if len(str(fact.value)) > 50 else fact.value
                unit = _canonical_unit(fact.unit)  # Use canonical unit format
                period = fact.period_display or "?"
                segment = fact.member if fact.member else "-"

                L.append(f"{qname} | {val} | {unit} | {period} | {segment}")
                shown += 1

        # ══════════════════════════════════════════════════════════════════════
        # FOOTER
        # ══════════════════════════════════════════════════════════════════════
        L.append("")
        L.append(f"TOTALS: {self.total_facts:,} facts | {len(self.concepts)} concepts | {len(self.periods)} periods")
        L.append("<<<END_XBRL_REFERENCE_DATA>>>")

        return "\n".join(L)

    # ==========================================================================
    # COMPACT NETWORK RENDERING (LLM-OPTIMIZED)
    # ==========================================================================

    def render_calculation_network(self, max_formulas: int = 15, max_children: int = 6) -> str:
        """
        Render calculation network in ultra-compact LLM-friendly format.

        Format:
            ## CALCULATION NETWORK (46 formulas)
            OperatingExpenses = +DepreciationAndAmortization +SG&A +Tech ...
            AssetsCurrent = +Cash +RestrictedCash +AR +Inventory ...

        Args:
            max_formulas: Maximum number of formulas to show
            max_children: Maximum children per formula
        """
        if not self.calculation_network:
            return ""

        lines = [f"## CALCULATION NETWORK ({len(self.calculation_network)} formulas)"]

        # Sort by number of children (most complex first)
        sorted_formulas = sorted(
            self.calculation_network.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:max_formulas]

        for parent_qname, children in sorted_formulas:
            # Get short name (strip namespace)
            parent_short = parent_qname.split(":")[-1] if ":" in parent_qname else parent_qname

            # Build compact formula
            parts = []
            for i, child in enumerate(children[:max_children]):
                weight = child.get("weight", 1)
                sign = "+" if float(weight) >= 0 else "−"
                child_qname = child.get("child", "")
                child_short = child_qname.split(":")[-1] if ":" in child_qname else child_qname
                parts.append(f"{sign}{child_short}")

            if len(children) > max_children:
                parts.append(f"...+{len(children) - max_children} more")

            lines.append(f"{parent_short} = {' '.join(parts)}")

        return "\n".join(lines)

    def render_presentation_sections(self, max_sections: int = 15, max_concepts: int = 8) -> str:
        """
        Render presentation structure in ultra-compact LLM-friendly format.

        Format:
            ## PRESENTATION STRUCTURE (45 sections)
            Segment Reporting (183 facts): Revenue, OpExp, OpIncome, Assets...
            Equity (130 facts): StockholdersEquity, CommonStock, RetainedEarnings...

        Args:
            max_sections: Maximum sections to show
            max_concepts: Maximum concepts per section
        """
        if not self.presentation_sections:
            return ""

        lines = [f"## PRESENTATION STRUCTURE ({len(self.presentation_sections)} sections)"]

        # Sort by concept count (most important first)
        sorted_sections = sorted(
            self.presentation_sections.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:max_sections]

        for section_label, concept_qnames in sorted_sections:
            # Clean up section label
            section_clean = section_label.replace(" [Abstract]", "").replace(" [Line Items]", "")
            section_clean = section_clean.replace(" [Roll Forward]", "")

            # Get short concept names
            short_concepts = []
            for qname in concept_qnames[:max_concepts]:
                short = qname.split(":")[-1] if ":" in qname else qname
                # Abbreviate common long names
                short = short.replace("AndCashEquivalents", "").replace("IncludingPortion", "")
                short = short.replace("AttributableTo", "").replace("Noncurrent", "NC")
                short_concepts.append(short[:25])  # Truncate very long names

            concepts_str = ", ".join(short_concepts)
            if len(concept_qnames) > max_concepts:
                concepts_str += f", +{len(concept_qnames) - max_concepts} more"

            lines.append(f"{section_clean} ({len(concept_qnames)}): {concepts_str}")

        return "\n".join(lines)

    def render_networks_compact(self) -> str:
        """
        Render both networks in a single compact block for LLM context.
        Returns empty string if no networks available.
        """
        parts = []

        calc = self.render_calculation_network()
        if calc:
            parts.append(calc)

        pres = self.render_presentation_sections()
        if pres:
            parts.append(pres)

        return "\n\n".join(parts)

    def __repr__(self):
        return f"XBRLCatalog(cik={self.cik}, company={self.company_name}, filings={len(self.filings)}, facts={self.total_facts}, concepts={len(self.concepts)})"


# =============================================================================
# NEO4J CONNECTION
# =============================================================================

def get_neo4j_driver():
    """Get Neo4j driver from environment variables."""
    from neo4j import GraphDatabase

    uri = os.getenv("NEO4J_URI", "bolt://localhost:30687")
    # Support both NEO4J_USER and NEO4J_USERNAME for compatibility
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")

    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable not set")

    return GraphDatabase.driver(uri, auth=(user, password))


def _normalize_cik(cik: str) -> tuple:
    """Normalize CIK to standard format and return both versions."""
    cik_clean = str(cik).lstrip("0")
    cik_padded = cik_clean.zfill(10)
    return cik_padded, cik_clean


def _format_value(value: str, unit: str = None) -> str:
    """
    Format large numbers for readability.

    Examples:
        24374000000 → $24.4B
        1500000 → $1.5M
        4.80 → $4.80
    """
    try:
        # Handle string values
        if isinstance(value, str):
            # Remove commas and try to parse
            num = float(value.replace(",", ""))
        else:
            num = float(value)

        # Format based on magnitude
        if abs(num) >= 1e9:
            formatted = f"{num/1e9:.1f}B"
        elif abs(num) >= 1e6:
            formatted = f"{num/1e6:.1f}M"
        elif abs(num) >= 1e3:
            formatted = f"{num/1e3:.1f}K"
        elif abs(num) < 100:
            formatted = f"{num:.2f}"
        else:
            formatted = f"{num:.0f}"

        # Add currency symbol if USD
        if unit and ("USD" in str(unit) or "usd" in str(unit).lower()):
            return f"${formatted}"
        return formatted
    except (ValueError, TypeError):
        # Return truncated original if parsing fails
        return str(value)[:12]


def _canonical_unit(unit: str) -> str:
    """
    Convert XBRL unit qname to canonical LLM-friendly format.

    Examples:
        iso4217:USD → USD
        iso4217:USDshares → USD/share
        shares → shares
        pure → pure
    """
    if not unit:
        return "-"

    # Currency units: iso4217:XXX → XXX
    if unit.startswith("iso4217:"):
        code = unit.split(":")[1]
        # Per-share units: iso4217:USDshares → USD/share
        if code.endswith("shares"):
            return f"{code[:-6]}/share"
        return code

    # Already canonical
    if unit in ("shares", "pure"):
        return unit

    # Unknown - return as-is but stripped of prefix
    if ":" in unit:
        return unit.split(":")[1]
    return unit


def _normalize_statement_name(network_name: str) -> str:
    """
    Normalize network/statement names to standard short forms.

    Maps various naming conventions to consistent short names:
    - "Consolidated Statements of Cash Flows" → "CashFlows"
    - "CONSOLIDATED BALANCE SHEETS" → "BalanceSheet"
    - etc.
    """
    if not network_name:
        return "Other"

    name = network_name.lower()

    # Balance Sheet variants
    if "balance sheet" in name or "financial position" in name:
        return "BalanceSheet"

    # Income Statement variants
    if "operations" in name or "income" in name or "earnings" in name:
        if "comprehensive" in name:
            return "ComprehensiveIncome"
        return "IncomeStatement"

    # Cash Flow variants
    if "cash flow" in name:
        return "CashFlows"

    # Equity variants
    if "equity" in name or "stockholder" in name or "shareholder" in name:
        return "Equity"

    # Cover/Document info
    if "cover" in name or "document" in name or "entity" in name:
        return "Cover"

    # Notes/Disclosures
    if "note" in name or "disclosure" in name or "schedule" in name:
        return "Notes"

    # Parenthetical
    if "parenthetical" in name:
        return "Parenthetical"

    return "Other"


# =============================================================================
# MAIN FETCH FUNCTIONS
# =============================================================================

# Form types that have XBRL data (10-K, 10-Q and their amendments)
# 8-K and other forms do NOT have XBRL data
XBRL_FORM_TYPES = ["10-K", "10-Q", "10-K/A", "10-Q/A"]


def get_xbrl_catalog(
    cik: str,
    form_types: Optional[List[str]] = None,
    limit_filings: Optional[int] = None,
    include_relationships: bool = True,
    driver=None
) -> XBRLCatalog:
    """
    Fetch complete XBRL catalog for a company from Neo4j.

    This is the main function for fetching XBRL data. It retrieves:
    - Company information (name, ticker, industry, sector)
    - All filings with XBRL data (10-K, 10-Q and amendments only)
    - Normalized reference tables (concepts, periods, units, members)
    - Calculation relationships
    - Key metrics from latest 10-K

    NOTE: Only 10-K, 10-Q, 10-K/A, and 10-Q/A have XBRL data.
    8-K and other forms do NOT contain structured XBRL financial data.

    Args:
        cik: Company CIK (with or without leading zeros)
        form_types: Filter by form types. Defaults to ["10-K", "10-Q", "10-K/A", "10-Q/A"].
                   Only these form types have XBRL data.
        limit_filings: Maximum number of filings to fetch. None for all.
        include_relationships: Whether to fetch calculation edges.
        driver: Optional Neo4j driver. If None, creates one from env vars.

    Returns:
        XBRLCatalog object with all XBRL data for the company.

    Example:
        catalog = get_xbrl_catalog("1571949")  # ICE - fetches 10-K/10-Q only
        catalog = get_xbrl_catalog("1571949", form_types=["10-K"])  # Only 10-K
        print(catalog.to_llm_context())  # LLM-friendly format
    """
    # Default to XBRL-capable form types
    if form_types is None:
        form_types = XBRL_FORM_TYPES

    cik_padded, cik_clean = _normalize_cik(cik)

    close_driver = False
    if driver is None:
        driver = get_neo4j_driver()
        close_driver = True

    try:
        with driver.session() as session:
            # 1. Get company info
            company_result = session.run("""
                MATCH (c:Company)
                WHERE c.cik = $cik_padded OR c.cik = $cik_clean
                RETURN c.cik as cik, c.name as name, c.ticker as ticker,
                       c.industry as industry, c.sector as sector
                LIMIT 1
            """, cik_padded=cik_padded, cik_clean=cik_clean)

            company = company_result.single()
            if not company:
                raise ValueError(f"Company with CIK {cik} not found")

            catalog = XBRLCatalog(
                cik=company["cik"],
                company_name=company["name"] or "",
                ticker=company["ticker"] or "",
                industry=company["industry"] or "",
                sector=company["sector"] or ""
            )

            actual_cik = company["cik"]

            # 2. Build filing query - only fetch reports that have XBRL data
            limit_clause = ""
            if limit_filings:
                limit_clause = f"LIMIT {limit_filings}"

            # 3. Get filings with XBRL - require HAS_XBRL relationship
            # This ensures we only get reports that actually have XBRL data
            filings_query = f"""
                MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {{cik: $cik}})
                MATCH (r)-[:HAS_XBRL]->(x:XBRLNode)
                WHERE r.xbrl_status = 'COMPLETED'
                  AND r.formType IN $form_types
                RETURN DISTINCT r.accessionNo as accession_no,
                       r.formType as form_type,
                       r.periodOfReport as period_of_report,
                       x.id as xbrl_id,
                       x.cik as xbrl_cik
                ORDER BY r.periodOfReport DESC
                {limit_clause}
            """

            filings_result = session.run(
                filings_query,
                cik=actual_cik,
                form_types=form_types
            )

            filings_data = list(filings_result)

            # 4. Fetch facts for each filing
            for filing_record in filings_data:
                accession_no = filing_record["accession_no"]
                xbrl_cik = filing_record["xbrl_cik"]

                # Fixed query: collect dimension-member pairs to avoid row multiplication
                facts_result = session.run("""
                    MATCH (f:Fact)-[:REPORTS]->(x:XBRLNode)
                    WHERE x.accessionNo = $accession_no AND x.cik = $xbrl_cik
                    OPTIONAL MATCH (f)-[:HAS_CONCEPT]->(concept:Concept)
                    OPTIONAL MATCH (f)-[:HAS_PERIOD]->(period:Period)
                    OPTIONAL MATCH (f)-[:HAS_UNIT]->(unit:Unit)
                    OPTIONAL MATCH (f)-[:FACT_MEMBER]->(mem:Member)
                    OPTIONAL MATCH (dim:Dimension)-[:HAS_DOMAIN]->(dom:Domain)-[:HAS_MEMBER|PARENT_OF*]->(mem)
                    WITH f, concept, period, unit,
                         collect(DISTINCT {dimension: dim.label, member: mem.label}) as dimensional_context
                    RETURN f.qname as qname,
                           f.value as value,
                           f.is_numeric as is_numeric,
                           f.decimals as decimals,
                           f.context_id as context_id,
                           concept.label as concept_label,
                           concept.qname as concept_qname,
                           concept.balance as balance,
                           concept.period_type as concept_period_type,
                           period.start_date as period_start,
                           period.end_date as period_end,
                           period.period_type as period_type,
                           unit.name as unit_name,
                           dimensional_context
                """, accession_no=accession_no, xbrl_cik=xbrl_cik)

                facts = []
                for fact_record in facts_result:
                    # Filter out empty dimension-member pairs
                    dim_ctx = [dc for dc in fact_record["dimensional_context"]
                               if dc.get("dimension") or dc.get("member")]
                    facts.append(XBRLFact(
                        concept_label=fact_record["concept_label"] or fact_record["qname"] or "Unknown",
                        concept_qname=fact_record["concept_qname"] or fact_record["qname"] or "",
                        value=fact_record["value"] or "",
                        is_numeric=fact_record["is_numeric"] == "1",
                        decimals=fact_record["decimals"],
                        period_start=fact_record["period_start"],
                        period_end=fact_record["period_end"],
                        period_type=fact_record["period_type"] or fact_record["concept_period_type"] or "unknown",
                        unit=fact_record["unit_name"],
                        balance=fact_record["balance"],
                        dimensional_context=dim_ctx,
                        context_id=fact_record["context_id"],
                        report_accession=accession_no
                    ))

                filing = XBRLFiling(
                    accession_no=accession_no,
                    form_type=filing_record["form_type"],
                    period_of_report=filing_record["period_of_report"] or "",
                    xbrl_id=filing_record["xbrl_id"],
                    facts=facts
                )
                catalog.filings.append(filing)

            # 5. Fetch normalized concept catalog with fact counts
            concepts_data = session.run("""
                MATCH (x:XBRLNode {cik: $cik})
                MATCH (f:Fact)-[:REPORTS]->(x)
                MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
                RETURN c.qname AS qname, c.label AS label, c.balance AS balance,
                       c.period_type AS period_type, c.concept_type AS data_type,
                       c.namespace AS namespace, c.category AS category,
                       count(f) AS fact_count
                ORDER BY fact_count DESC
            """, cik=actual_cik).data()

            for c in concepts_data:
                catalog.concepts[c["qname"]] = {
                    "label": c["label"],
                    "balance": c["balance"],
                    "period_type": c["period_type"],
                    "data_type": c["data_type"],
                    "namespace": c["namespace"],
                    "category": c["category"],
                    "fact_count": c["fact_count"]
                }

            # 6. Fetch normalized periods with fact counts
            periods_data = session.run("""
                MATCH (x:XBRLNode {cik: $cik})
                MATCH (f:Fact)-[:REPORTS]->(x)
                MATCH (f)-[:HAS_PERIOD]->(p:Period)
                RETURN p.u_id AS period_id, p.period_type AS type,
                       p.start_date AS start_date, p.end_date AS end_date,
                       count(f) AS fact_count
                ORDER BY COALESCE(p.end_date, p.start_date) DESC
            """, cik=actual_cik).data()

            for p in periods_data:
                period_id = p["period_id"]
                if p["type"] == "instant":
                    catalog.periods[period_id] = {
                        "type": "instant",
                        "date": p["start_date"],
                        "fact_count": p["fact_count"]
                    }
                else:
                    catalog.periods[period_id] = {
                        "type": "duration",
                        "start": p["start_date"],
                        "end": p["end_date"],
                        "fact_count": p["fact_count"]
                    }

            # 7. Fetch normalized units with fact counts
            units_data = session.run("""
                MATCH (x:XBRLNode {cik: $cik})
                MATCH (f:Fact)-[:REPORTS]->(x)
                MATCH (f)-[:HAS_UNIT]->(u:Unit)
                RETURN u.name AS name, u.item_type AS type,
                       u.is_simple_unit AS is_simple, count(f) AS fact_count
                ORDER BY fact_count DESC
            """, cik=actual_cik).data()

            for u in units_data:
                catalog.units[u["name"]] = {
                    "type": u["type"],
                    "is_simple": u["is_simple"] == "1",
                    "fact_count": u["fact_count"]
                }

            # 8. Fetch dimensions and members with fact counts
            members_data = session.run("""
                MATCH (x:XBRLNode {cik: $cik})
                MATCH (f:Fact)-[:REPORTS]->(x)
                MATCH (f)-[:FACT_MEMBER]->(m:Member)
                OPTIONAL MATCH (f)-[:FACT_DIMENSION]->(d:Dimension)
                RETURN m.qname AS member_qname, m.label AS member_label,
                       d.qname AS dimension_qname, d.label AS dimension_label,
                       count(f) AS fact_count
                ORDER BY fact_count DESC
            """, cik=actual_cik).data()

            for m in members_data:
                catalog.members[m["member_qname"]] = {
                    "label": m["member_label"],
                    "dimension": m["dimension_qname"],
                    "dimension_label": m["dimension_label"],
                    "fact_count": m["fact_count"]
                }
                if m["dimension_qname"] and m["dimension_qname"] not in catalog.dimensions:
                    catalog.dimensions[m["dimension_qname"]] = {
                        "label": m["dimension_label"],
                        "member_count": 0
                    }

            # Count members per dimension
            for mem_info in catalog.members.values():
                dim = mem_info.get("dimension")
                if dim and dim in catalog.dimensions:
                    catalog.dimensions[dim]["member_count"] += 1

            # 9. Fetch calculation relationships with statement grouping
            if include_relationships:
                calc_data = session.run("""
                    MATCH (x:XBRLNode {cik: $cik})
                    MATCH (pf:Fact)-[:REPORTS]->(x)
                    MATCH (pf)-[calc:CALCULATION_EDGE]->(cf:Fact)
                    MATCH (pf)-[:HAS_CONCEPT]->(pc:Concept)
                    MATCH (cf)-[:HAS_CONCEPT]->(cc:Concept)
                    WITH calc.network_name AS network,
                         pc.qname AS parent_concept, pc.label AS parent_label,
                         collect(DISTINCT {
                             child: cc.qname,
                             label: cc.label,
                             weight: calc.weight
                         }) AS children
                    RETURN network, parent_concept, parent_label, children
                    ORDER BY size(children) DESC
                """, cik=actual_cik).data()

                for tree in calc_data:
                    # Legacy format
                    catalog.calculation_trees.append({
                        "parent_concept": tree["parent_concept"],
                        "children": tree["children"]
                    })
                    # New compact format with network info
                    catalog.calculation_network[tree["parent_concept"]] = {
                        "children": tree["children"],
                        "network": _normalize_statement_name(tree.get("network", ""))
                    }

            # 10. Fetch presentation structure with statement grouping
            if include_relationships:
                pres_data = session.run("""
                    MATCH (a:Abstract)-[pres:PRESENTATION_EDGE]->(f:Fact)-[:REPORTS]->(x:XBRLNode)
                    WHERE x.cik = $cik
                    MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
                    WITH pres.network_name AS network, a.label as section,
                         collect(DISTINCT c.qname) as concepts
                    RETURN network, section, concepts
                    ORDER BY size(concepts) DESC
                """, cik=actual_cik).data()

                for row in pres_data:
                    catalog.presentation_sections[row["section"]] = {
                        "concepts": row["concepts"],
                        "network": _normalize_statement_name(row.get("network", ""))
                    }

            # 11. Extract key metrics from latest 10-K
            latest_10k = next((f for f in catalog.filings if f.form_type == "10-K"), None)
            if latest_10k:
                key_concepts = [
                    "us-gaap:Revenues",
                    "us-gaap:NetIncomeLoss",
                    "us-gaap:Assets",
                    "us-gaap:StockholdersEquity",
                    "us-gaap:EarningsPerShareBasic"
                ]
                key_metrics = {}
                for fact in latest_10k.facts:
                    if fact.concept_qname in key_concepts and not fact.member:
                        label = catalog.concepts.get(fact.concept_qname, {}).get("label", fact.concept_label)
                        if label not in key_metrics:
                            key_metrics[label] = {
                                "value": fact.value,
                                "unit": fact.unit,
                                "period": fact.period_display
                            }
                latest_10k.key_metrics = key_metrics

            return catalog

    finally:
        if close_driver:
            driver.close()


def get_xbrl_for_filing(
    accession_no: str,
    cik: Optional[str] = None,
    driver=None
) -> XBRLFiling:
    """
    Fetch XBRL data for a specific filing.

    Args:
        accession_no: SEC accession number
        cik: Optional CIK to narrow search
        driver: Optional Neo4j driver

    Returns:
        XBRLFiling object with all facts
    """
    close_driver = False
    if driver is None:
        driver = get_neo4j_driver()
        close_driver = True

    try:
        with driver.session() as session:
            # Get filing info
            cik_filter = ""
            if cik:
                cik_padded, cik_clean = _normalize_cik(cik)
                cik_filter = f"AND (x.cik = '{cik_padded}' OR x.cik = '{cik_clean}')"

            filing_result = session.run(f"""
                MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)
                WHERE x.accessionNo = $accession_no {cik_filter}
                RETURN r.formType as form_type,
                       r.periodOfReport as period_of_report,
                       x.cik as xbrl_cik,
                       x.id as xbrl_id
                LIMIT 1
            """, accession_no=accession_no)

            filing = filing_result.single()
            if not filing:
                raise ValueError(f"Filing {accession_no} not found")

            # Get all facts - fixed query to collect dimension-member pairs
            facts_result = session.run("""
                MATCH (f:Fact)-[:REPORTS]->(x:XBRLNode)
                WHERE x.accessionNo = $accession_no AND x.cik = $xbrl_cik
                OPTIONAL MATCH (f)-[:HAS_CONCEPT]->(concept:Concept)
                OPTIONAL MATCH (f)-[:HAS_PERIOD]->(period:Period)
                OPTIONAL MATCH (f)-[:HAS_UNIT]->(unit:Unit)
                OPTIONAL MATCH (f)-[:FACT_MEMBER]->(mem:Member)
                OPTIONAL MATCH (dim:Dimension)-[:HAS_DOMAIN]->(dom:Domain)-[:HAS_MEMBER|PARENT_OF*]->(mem)
                WITH f, concept, period, unit,
                     collect(DISTINCT {dimension: dim.label, member: mem.label}) as dimensional_context
                RETURN f.qname as qname,
                       f.value as value,
                       f.is_numeric as is_numeric,
                       f.decimals as decimals,
                       f.context_id as context_id,
                       concept.label as concept_label,
                       concept.qname as concept_qname,
                       concept.balance as balance,
                       concept.period_type as concept_period_type,
                       period.start_date as period_start,
                       period.end_date as period_end,
                       period.period_type as period_type,
                       unit.name as unit_name,
                       dimensional_context
            """, accession_no=accession_no, xbrl_cik=filing["xbrl_cik"])

            facts = []
            for fact_record in facts_result:
                # Filter out empty dimension-member pairs
                dim_ctx = [dc for dc in fact_record["dimensional_context"]
                           if dc.get("dimension") or dc.get("member")]
                facts.append(XBRLFact(
                    concept_label=fact_record["concept_label"] or fact_record["qname"] or "Unknown",
                    concept_qname=fact_record["concept_qname"] or fact_record["qname"] or "",
                    value=fact_record["value"] or "",
                    is_numeric=fact_record["is_numeric"] == "1",
                    decimals=fact_record["decimals"],
                    period_start=fact_record["period_start"],
                    period_end=fact_record["period_end"],
                    period_type=fact_record["period_type"] or fact_record["concept_period_type"] or "unknown",
                    unit=fact_record["unit_name"],
                    balance=fact_record["balance"],
                    dimensional_context=dim_ctx,
                    context_id=fact_record["context_id"],
                    report_accession=accession_no
                ))

            return XBRLFiling(
                accession_no=accession_no,
                form_type=filing["form_type"],
                period_of_report=filing["period_of_report"] or "",
                xbrl_id=filing["xbrl_id"],
                facts=facts
            )

    finally:
        if close_driver:
            driver.close()


# =============================================================================
# SEARCH AND DISCOVERY FUNCTIONS
# =============================================================================

def search_xbrl_concepts(
    search_term: str,
    cik: Optional[str] = None,
    limit: int = 50,
    driver=None
) -> List[Dict[str, Any]]:
    """
    Search for XBRL concepts matching a term.

    Args:
        search_term: Text to search for in concept labels
        cik: Optional CIK to filter by company
        limit: Maximum results to return
        driver: Optional Neo4j driver

    Returns:
        List of matching concepts with sample values
    """
    close_driver = False
    if driver is None:
        driver = get_neo4j_driver()
        close_driver = True

    try:
        with driver.session() as session:
            cik_filter = ""
            params = {"search_term": search_term, "limit": limit}

            if cik:
                cik_padded, cik_clean = _normalize_cik(cik)
                cik_filter = "AND (x.cik = $cik_padded OR x.cik = $cik_clean)"
                params["cik_padded"] = cik_padded
                params["cik_clean"] = cik_clean

            result = session.run(f"""
                MATCH (f:Fact)-[:REPORTS]->(x:XBRLNode)
                MATCH (f)-[:HAS_CONCEPT]->(c:Concept)
                WHERE toLower(c.label) CONTAINS toLower($search_term)
                {cik_filter}
                WITH c, f, x
                OPTIONAL MATCH (f)-[:HAS_PERIOD]->(p:Period)
                OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit)
                RETURN DISTINCT c.label as concept,
                       c.qname as qname,
                       c.balance as balance,
                       c.period_type as period_type,
                       collect(DISTINCT f.value)[0..3] as sample_values,
                       collect(DISTINCT u.name)[0] as unit,
                       count(DISTINCT f) as fact_count
                ORDER BY fact_count DESC
                LIMIT $limit
            """, **params)

            return [dict(r) for r in result]

    finally:
        if close_driver:
            driver.close()


def list_companies_with_xbrl(
    limit: int = 100,
    form_types: Optional[List[str]] = None,
    driver=None
) -> List[Dict[str, Any]]:
    """
    List companies that have XBRL data available.

    Args:
        limit: Maximum number of companies to return
        form_types: Filter by form types. Defaults to ["10-K", "10-Q", "10-K/A", "10-Q/A"].
        driver: Optional Neo4j driver

    Returns:
        List of companies with their XBRL filing counts
    """
    if form_types is None:
        form_types = XBRL_FORM_TYPES

    close_driver = False
    if driver is None:
        driver = get_neo4j_driver()
        close_driver = True

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Company)<-[:PRIMARY_FILER]-(r:Report)-[:HAS_XBRL]->(x:XBRLNode)
                WHERE r.formType IN $form_types
                  AND r.xbrl_status = 'COMPLETED'
                WITH c, count(DISTINCT x) as xbrl_count
                WHERE xbrl_count > 0
                RETURN c.cik as cik, c.name as name, c.ticker as ticker,
                       c.industry as industry, c.sector as sector, xbrl_count
                ORDER BY xbrl_count DESC
                LIMIT $limit
            """, limit=limit, form_types=form_types)

            return [dict(r) for r in result]

    finally:
        if close_driver:
            driver.close()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def xbrl_catalog(identifier: str, **kwargs) -> XBRLCatalog:
    """
    Smart XBRL catalog fetcher - accepts either CIK or ticker.

    This is the recommended entry point for fetching XBRL data.

    Args:
        identifier: Either a CIK (e.g., "0001571949") or ticker (e.g., "ICE")
        **kwargs: Additional arguments passed to get_xbrl_catalog

    Returns:
        XBRLCatalog object with all XBRL data

    Example:
        catalog = xbrl_catalog("ICE")
        catalog = xbrl_catalog("0001571949")

        # Get LLM-ready context
        context = catalog.to_llm_context()

        # Get specific views
        print(catalog.concept_index)
        print(catalog.segment_breakdown)

        # Query facts
        revenue_facts = catalog.get_time_series("us-gaap:Revenues")
    """
    # Heuristic: if it looks like a CIK (all digits or starts with 0), use directly
    if identifier.replace("-", "").isdigit() or identifier.startswith("0"):
        return get_xbrl_catalog(identifier, **kwargs)

    # Otherwise, look up by ticker first
    driver = None
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Company)
                WHERE toUpper(c.ticker) = toUpper($ticker)
                RETURN c.cik AS cik
            """, ticker=identifier).single()

            if not result:
                raise ValueError(f"Company with ticker {identifier} not found")

            cik = result["cik"]
            return get_xbrl_catalog(cik, driver=driver, **kwargs)
    finally:
        if driver:
            driver.close()


def quick_catalog(cik: str, form_types: Optional[List[str]] = None) -> str:
    """
    Quick one-liner to get LLM-ready catalog.

    Args:
        cik: Company CIK or ticker
        form_types: Optional filter for form types

    Returns:
        Markdown string ready for LLM consumption
    """
    catalog = xbrl_catalog(cik, form_types=form_types)
    return catalog.to_llm_context()


def get_company_facts(cik: str, concept: str) -> List[Dict]:
    """
    Get all facts for a specific concept across all filings.

    Args:
        cik: Company CIK or ticker
        concept: Concept qname or label to search for

    Returns:
        List of fact dictionaries with time series data
    """
    catalog = xbrl_catalog(cik)

    # Try by qname first, then by label
    results = catalog.get_time_series(concept)
    if not results:
        results = catalog.get_concept_timeseries(concept)

    return results


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def print_catalog_summary(catalog: XBRLCatalog):
    """Print a quick summary of the catalog to console."""
    print(f"\n{'='*60}")
    print(f"XBRL Catalog: {catalog.company_name} ({catalog.ticker})")
    print(f"CIK: {catalog.cik}")
    if catalog.industry:
        print(f"Industry: {catalog.industry}")
    if catalog.sector:
        print(f"Sector: {catalog.sector}")
    print(f"{'='*60}")

    summary = catalog._build_summary()
    print(f"\nTotal Filings: {summary['total_filings']}")
    print(f"Total Facts: {summary['total_facts']:,}")
    print(f"Unique Concepts: {summary['unique_concepts']}")

    print(f"\nFilings:")
    for f in sorted(catalog.filings, key=lambda x: x.period_of_report or "", reverse=True):
        print(f"  - {f.form_type} ({f.period_of_report}): {f.fact_count:,} facts")

    if catalog.members:
        print(f"\nTop Segments:")
        top_members = sorted(catalog.members.items(), key=lambda x: -x[1].get("fact_count", 0))[:5]
        for mem_qname, info in top_members:
            print(f"  - {info.get('label', mem_qname)}: {info.get('fact_count', 0)} facts")

    print(f"\n{'='*60}\n")


def display_catalog(catalog: XBRLCatalog, format: str = "summary"):
    """
    Display catalog in various formats.

    Args:
        catalog: XBRLCatalog to display
        format: "markdown", "json", "llm", or "summary"
    """
    if format == "markdown":
        print(catalog.to_markdown())
    elif format == "json":
        print(catalog.to_json())
    elif format == "llm":
        print(catalog.to_llm_context())
    else:
        print_catalog_summary(catalog)


# =============================================================================
# EXAMPLE USAGE (when run directly)
# =============================================================================

if __name__ == "__main__":
    print("Fetching XBRL catalog for ICE (CIK: 1571949)...")

    try:
        catalog = xbrl_catalog("ICE", limit_filings=3)
        print_catalog_summary(catalog)

        print("\n--- LLM-Ready Context Format ---\n")
        print(catalog.to_llm_context(max_facts=20))

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure NEO4J_PASSWORD is set in your environment.")
