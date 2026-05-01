"""Sections 2 & 9 — Results & Expectations + Reference.

Both renderers extracted from earnings_orchestrator.py (commit 13/20):
  _render_results_and_expectations (line 881 of pre-extraction baseline)
  _render_reference                (line 932)

Combined here because both deal with the 8-K packet (EX-99.1 vs other
exhibits). Imports `_fmt_money` from `_formatters`.
"""
from __future__ import annotations

from ._formatters import _fmt_money, _fmt_pct, _fmt_eps


def _render_results_and_expectations(bundle: dict) -> str:
    """Section 2: Consensus bar (estimates only) + EX-99.1 reported results."""
    parts = ["## 2. Results & Expectations"]
    errors = bundle.get("builder_errors") or {}

    # ── Subsection A: Consensus Bar (estimates only — standardized for live + historical) ──
    consensus = bundle.get("consensus")

    if "consensus" in errors:
        parts.append(f"\n### Consensus Bar\n[BUILDER ERROR: {errors['consensus']}]")
    elif not consensus:
        parts.append("\n### Consensus Bar\n[NO DATA]")
    else:
        # `or []` defensively handles both missing key AND explicit None.
        rows = consensus.get("quarterly_rows") or []
        current = next((r for r in rows if r.get("is_current_quarter")), None)

        if current:
            parts.append("\n### Consensus Bar")
            parts.append("")
            est_eps  = current.get("estimatedEPS")
            act_eps  = current.get("reportedEPS")
            surp_eps = current.get("epsSurprisePct")
            est_rev  = current.get("revenueEstimate")
            act_rev  = current.get("revenueActual")
            surp_rev = current.get("revenueSurprisePct")
            has_actuals = (act_eps is not None) or (act_rev is not None)
            if has_actuals:
                parts.append("| Metric  | Estimate | Actual | Surprise |")
                parts.append("|---------|----------|--------|----------|")
                parts.append(f"| EPS     | {_fmt_eps(est_eps)} | {_fmt_eps(act_eps)} | {_fmt_pct(surp_eps)} |")
                parts.append(f"| Revenue | {_fmt_money(est_rev)} | {_fmt_money(act_rev)} | {_fmt_pct(surp_rev)} |")
            else:
                parts.append("| Metric  | Estimate |")
                parts.append("|---------|----------|")
                parts.append(f"| EPS     | {_fmt_eps(est_eps)} |")
                parts.append(f"| Revenue | {_fmt_money(est_rev)} |")
        else:
            # U3: branch the empty-Consensus-Bar message by underlying cause.
            # Distinguishes AV upstream failure (rate-limit / endpoint error)
            # from genuinely-empty data, from the row-present-but-no-match
            # (ACI-class) fiscal-fallback case U1 introduced.
            gaps = consensus.get("gaps") or []
            upstream_errs = [g for g in gaps
                             if isinstance(g, dict) and g.get("type") == "upstream_error"]
            if upstream_errs and not rows:
                reasons = "; ".join(
                    (g.get("reason") or "AV upstream error") for g in upstream_errs
                )
                parts.append(f"\n### Consensus Bar\n[Consensus unavailable — AV upstream failed: {reasons}]")
            elif not rows:
                parts.append("\n### Consensus Bar\n[No quarterly data]")
            else:
                # U2 deferred: do NOT fall through to consensus.forward_estimates[0]
                # here. After U1's cutoff fix, the just-reported provider FDE is
                # excluded from forward_estimates, so fwd[0] is the *next-next*
                # quarter — labeling it as the current event would mislead the
                # predictor. Forward consensus stays visible in §1.3. Revisit if/when
                # at-release prediction (~1 min after 8-K, AV-lag transient) becomes
                # a primary workflow that justifies target-quarter verification.
                parts.append("\n### Consensus Bar\n[No current-quarter row found]")

    # ── U6: Other items in this 8-K (non-routine items inside the target filing) ──
    # Surfaces items beyond the routine earnings pair {2.02, 9.01} so the
    # predictor sees bundled disclosures (restructuring, dividends, etc.)
    # without parsing the EX-99.1 prose. Distinct from U7, which lists OTHER
    # 8-Ks filed in the inter-quarter window — U6 is about the target 8-K's
    # OWN items list.
    packet = bundle.get("8k_packet")
    if packet:
        items = packet.get("items") or []
        routine = {"Item 2.02", "Item 9.01"}
        labels: list[str] = []
        for item in items:
            head = item.split(":", 1)[0].strip()
            if head in routine:
                continue
            if ":" in item:
                num, desc = item.split(":", 1)
                labels.append(f"{num.strip()} ({desc.strip()})")
            else:
                labels.append(item.strip())
        if labels:
            parts.append(f"\nOther items in this 8-K: {', '.join(labels)}")

    # ── Subsection B: Reported Results (EX-99.1 only — other exhibits go to Reference) ──

    if "8k_packet" in errors:
        parts.append(f"\n### Reported Results\n[BUILDER ERROR: {errors['8k_packet']}]")
    elif not packet:
        parts.append("\n### Reported Results\n[NO DATA]")
    else:
        exhibits = packet.get("exhibits_99", [])
        ex991 = next((e for e in exhibits if e.get("exhibit_number") == "EX-99.1"), None)

        if ex991:
            parts.append("\n### Reported Results (EX-99.1)")
            parts.append("")
            parts.append(ex991.get("content", "[NO CONTENT]").strip())
        else:
            parts.append("\n### Reported Results\n[No EX-99.1 found]")

    return "\n".join(parts)


def _render_reference(bundle: dict) -> str:
    """Section 9: Reference — filing metadata, other exhibits, 8-K section text."""
    parts = ["## 9. Reference"]
    packet = bundle.get("8k_packet")
    if not packet or not isinstance(packet, dict):
        parts.append("\n[NO 8-K DATA]")
        return "\n".join(parts)

    # Filing metadata
    items = packet.get("items", [])
    items_short = ", ".join(
        i.split(":")[0].replace("Item ", "") if ":" in i else i
        for i in items
    ) if items else "—"
    accession = packet.get("accession_8k", "—")
    form = packet.get("form_type", "—")
    inv = packet.get("content_inventory", {})
    # U36: surface CIK + matched periodic filing + amendment flag.
    # Source fields: 8k_packet.cik, 8k_packet.is_amendment,
    # quarter_info.accession_periodic, quarter_info.form_type_periodic.
    cik = packet.get("cik") or "—"
    qi = bundle.get("quarter_info") or {}
    acc_periodic = qi.get("accession_periodic")
    form_periodic = qi.get("form_type_periodic")
    if acc_periodic and form_periodic:
        periodic_str = f"{acc_periodic} ({form_periodic})"
    elif acc_periodic:
        periodic_str = acc_periodic
    elif form_periodic:
        periodic_str = f"— ({form_periodic} expected)"
    else:
        periodic_str = "—"
    is_amendment = packet.get("is_amendment")
    amendment_str = "yes" if is_amendment else "no"
    parts.append(f"\n### Filing Metadata")
    parts.append(f"Accession: {accession} | Form: {form} | Items: {items_short}")
    parts.append(f"CIK: {cik} | Periodic: {periodic_str} | Amendment: {amendment_str}")
    parts.append(f"Sections: {len(inv.get('section_names', []))} | Exhibits: {', '.join(inv.get('exhibit_numbers', [])) or '—'}")

    # Other EX-99.x exhibits (not EX-99.1)
    exhibits = packet.get("exhibits_99", [])
    other_ex99 = [e for e in exhibits if e.get("exhibit_number") != "EX-99.1"]
    for ex in other_ex99:
        parts.append(f"\n### {ex.get('exhibit_number', 'Exhibit')}")
        parts.append(ex.get("content", "[NO CONTENT]").strip())

    # Non-99 exhibits (previews)
    for ex in packet.get("exhibits_other", []):
        num = ex.get("exhibit_number", "Exhibit")
        preview = ex.get("content_preview", "").strip()
        full_size = ex.get("full_size", 0)
        if preview:
            parts.append(f"\n### {num} (preview, {full_size} chars full)")
            parts.append(preview)

    # 8-K section text
    sections = packet.get("sections", [])
    if sections:
        parts.append("\n### 8-K Section Text")
        for sec in sections:
            name = sec.get("section_name", "")
            content = sec.get("content", "").strip()
            if content:
                parts.append(f"\n**{name}**\n{content}")

    # Filing text fallback
    ft = packet.get("filing_text")
    if ft:
        parts.append("\n### Filing Text (fallback)")
        parts.append(ft.strip())

    return "\n".join(parts)
