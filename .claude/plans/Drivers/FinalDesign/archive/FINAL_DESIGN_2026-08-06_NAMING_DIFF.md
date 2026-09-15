# August 6 design snapshot — five-line naming change

Historical evidence only. [FINAL_DESIGN.md](../FINAL_DESIGN.md) remains the
live authority; none of the older wording below reinstates a rule.

five changed lines, all concerning one naming decision:

The following diff preserves all five old lines (`-`) and their replacements
(`+`) verbatim. The other 311 lines are identical. The August 11 ruling replaces
the stored `eps` exception with certain, written-out per-X names and removes
the pending-decision note; original source quotes remain unchanged.

```diff
--- FINAL_DESIGN_Aug_6th.md (historical)
+++ FINAL_DESIGN.md (August 11 owner ruling)
@@ -88 +88 @@
-8. **NAME-08** — keep standard financial phrases whole. Loss/deficit/negative-margin are negative regions of signed `net_income`, `operating_margin`, `eps`, etc.; never create duplicate loss Drivers.
+8. **NAME-08** — keep standard financial phrases whole. Loss/deficit/negative-margin are negative regions of signed `net_income`, `operating_margin`, `earnings_per_share`, etc.; never create duplicate loss Drivers.
@@ -94 +94 @@
-14. **NAME-13** — a stated business/physical per-X denominator stays in the name (`oil_price_per_barrel`); never invent one; different denominators are different Drivers and never `SAME_AS`; store the base unit; `eps` is the familiar exception. **[⏸ OWNER DECISION PENDING (deferred 2026-07-25): eps-as-sole-exception vs uniform spell-out (`earnings_per_share`) — the rule STANDS UNCHANGED until the owner rules. Any bot reading this: do not resolve, extend, or delete the exception — remind the owner a ruling is pending; evidence pack = experiments/WORKORDER_STATUS.md 2026-07-25 entries. See §10 OPEN.]**
+14. **NAME-13** — a stated business/physical per-X denominator stays in the name (`oil_price_per_barrel`); never invent one; different denominators are different Drivers and never `SAME_AS`; store the base unit. A per-X acronym or spelled phrase resolves to its written-out canonical form when the expansion is certain (`EPS`/'earnings per share' → `earnings_per_share`; `DPS` → `dividend_per_share` — worked examples of the general rule, not a list); an uncertain expansion abstains (reader skips; a name↔per_x conflict parks at admission), never guesses, never extends by analogy. Source quotes keep the acronym verbatim. Per-X only: NAME-07/NAME-08 names are untouched.
@@ -282 +282 @@
-- **XC-07 (deterministic veto — can only ABSTAIN, never create/change a link):** A = point-in-time share count must be `instant`, not duration weighted-average · B = bare eps/share_count must not map to the *Basic variant (convention = diluted) · C = a per-share metric must not map to a total-$ Cash concept · D = the exact 4-entry component-for-aggregate DENY set: sg_a→G&A · sg_a→S&M · operating_expenses→SG&A · total_debt→NotesPayable. Measured (274 companies): A–C 42→18 wrong; +D → 1 wrong, no recall cost.
+- **XC-07 (deterministic veto — can only ABSTAIN, never create/change a link):** A = point-in-time share count must be `instant`, not duration weighted-average · B = bare earnings_per_share/share_count must not map to the *Basic variant (convention = diluted) · C = a per-share metric must not map to a total-$ Cash concept · D = the exact 4-entry component-for-aggregate DENY set: sg_a→G&A · sg_a→S&M · operating_expenses→SG&A · total_debt→NotesPayable. Measured (274 companies): A–C 42→18 wrong; +D → 1 wrong, no recall cost.
@@ -288 +288 @@
-- **XC-17 (monitoring, non-LLM):** sample emitted links; check the concept's balance/period_type against the metric's expected signature (revenue = credit+duration; shares_outstanding = instant; eps = per-share) — a contradiction = a wrong link; track abstention by fact_type (conceptless classes ~100%). LIMIT: catches STRUCTURAL slips only, not new same-balance/same-period SCOPE mismatches — those need XC-16 or the periodic audit. Optional stability gate: run 2-3×, abstain on disagreement (~2% flips, all borderline, never creates a wrong link).
+- **XC-17 (monitoring, non-LLM):** sample emitted links; check the concept's balance/period_type against the metric's expected signature (revenue = credit+duration; shares_outstanding = instant; earnings_per_share = per-share) — a contradiction = a wrong link; track abstention by fact_type (conceptless classes ~100%). LIMIT: catches STRUCTURAL slips only, not new same-balance/same-period SCOPE mismatches — those need XC-16 or the periodic audit. Optional stability gate: run 2-3×, abstain on disagreement (~2% flips, all borderline, never creates a wrong link).
@@ -313 +313 @@
-- **OPEN (owner):** naming-form deferral 2026-07-25 — (1) `eps` sole-exception vs uniform spell-out; (2) the "familiar acronyms" open-class sentence still live in exp5_item_contract.md:127 + workflows/gate.js/reconcile.js/menu_build.js — both rules stand unchanged until ruled (evidence: experiments/WORKORDER_STATUS.md 2026-07-25) · catalog target 796-vs-786 + lifecycle/IPO absorption · full model/cost policy beyond signed EXP-2 · FS-23 cross-company slice comparison · 8-K item/content taxonomy only (earnings 8-K pairing is CLOSED by PER-21) · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis channel-charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement (part-2/news-channel) · Driver financial classification (owner 2026-07-19): NO field approved — for now derive exact facts (company-specific XBRL linkage, monetary units); revisit before production Driver creation ONLY if a named consumer and a testable definition exist; otherwise the field stays absent.
+- **OPEN (owner):** catalog target 796-vs-786 + lifecycle/IPO absorption · full model/cost policy beyond signed EXP-2 · FS-23 cross-company slice comparison · 8-K item/content taxonomy only (earnings 8-K pairing is CLOSED by PER-21) · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis channel-charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement (part-2/news-channel) · Driver financial classification (owner 2026-07-19): NO field approved — for now derive exact facts (company-specific XBRL linkage, monetary units); revisit before production Driver creation ONLY if a named consumer and a testable definition exist; otherwise the field stays absent.
```

## Complete source copies in Git

The removed August copy was untracked in main and already absent from recovery.
Its complete bytes match the first snapshot below; no unique content was lost.
Read either with `git show <commit>:<path>` using
`.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md` as the path.

| Snapshot | Commit | SHA-256 of the complete file |
|---|---|---|
| August 6 copy | `377d5f4a78e369d3ab5284c539f6ce6e12cf0ff4` | `34b87e93c2d5dbf8743fc82f3a4f167ecbea115e89b3890d1f78e5e7ab45f426` |
| August 11 approved naming rule | `2a4c06f8bdbe1618516b4ab7596b51f77ca46ea0` | `4218d73abe6b98ef2ecd325aef8b5e49985101b122e457b39784dee677f32a0b` |

Existing references in dated work orders and frozen inventories remain history;
they do not require restoring or serving the removed duplicate.
