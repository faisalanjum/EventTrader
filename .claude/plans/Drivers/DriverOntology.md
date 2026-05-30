# Driver Naming Ontology

## §1. Purpose

This file defines what a valid driver name is — the meaning of the naming contract, not its execution. Any LLM that follows this file produces, given the same evidence + the same registry catalog + the same runtime vocab/thresholds, one of: the same reuse of an existing driver name, the same new driver proposal, or the same deterministic rejection. Determinism scope (LEXICAL, not semantic): this reproducibility covers spelling/order variants + the known synonym/plural/acronym maps; it does NOT by itself converge different WORD-CHOICES for the same concept (e.g. iphone_china_sales vs iphone_china_demand) -- that semantic convergence is the learned synonym map (Pass-2) + the isolated judge = EVENTUAL consistency, not a first-emission guarantee. Producers whose source labels do not follow this ontology (e.g., fiscal.ai KPI ingest) are exempt from the naming contract for raw ingest; their entries may be carried alongside but are not subject to this ontology until canonicalized through a conforming proposal.

This file defines meaning, not execution. At runtime the LLM also receives: the live registry catalog (existing names, aliases, segments, allowed_states, definitions), the current vocab (token categories and entries), and the current numerical thresholds. Their contents are not in this file. This file alone is not a runnable spec.

## §2. Glossary

- **driver**: a reusable causal variable that moves a stock price.
- **driver_name**: the lowercase identifier of one driver. Contains only ASCII letters, digits, and underscores; starts with a letter; does not end with an underscore; contains no consecutive underscores; has at least two characters.
- **alias**: an exact spelling or order variant of one driver's name; never a different concept.
- **registry**: the live set of drivers visible at the run's PIT cutoff.
- **driver_state**: a verb describing what happened to the variable in this evidence.
- **direction**: the stock impact for the affected company; `long` or `short`.
- **evidence**: source-grounded references (quotes, IDs, dates, magnitudes, provider names) supporting an emission.
- **segment**: the dimension this driver represents; `"Total"` unless the name itself encodes a sub-dimension.
- **base_label**: an optional canonical financial-metric label.
- **allowed_states**: the closed list of verbs valid for this driver, drawn from a single state class.
- **definition**: one sentence describing the variable named by `driver_name`.
- **canonical form**: the unique form of a name where tokens are in the fixed slot order; no stopwords remain; each token is the canonical token per the runtime synonym/plural/acronym maps; and compound metrics appear as a single metric slot.

## §3. Field Placement

| Field | Content |
|---|---|
| `driver_name` | The reusable causal noun variable only. |
| `driver_state` | A single verb from the runtime state vocab, drawn from this driver's `allowed_states`. |
| `direction` | `long` or `short`. |
| `evidence` | Source-grounded refs: quotes, IDs, dates, magnitudes, provider names, raw wording. |
| `aliases` | Exact spelling/order variants of the same driver. |
| `label` | Display text whose concept tokens equal the `driver_name` tokens as a set. |
| `segment` | `"Total"` if `driver_name` has no sub-dimension; otherwise the sub-dimension the name encodes. |
| `base_label` | Null or a canonical financial-metric label from runtime banks. |
| `definition` | One sentence describing the variable; not a tautology of name tokens. |
| `allowed_states` | A subset of one state class; size bounded per runtime threshold. |

## §4. Naming Rules

**R1. Reuse first.** Before proposing a new driver, verify the candidate does not already exist in the registry — neither as an exact `driver_name` nor as an alias, including under canonical form. If a registry driver matches under canonical form, reuse that driver's exact name.

**R2. Name only the causal variable.** `driver_name` carries only the reusable causal noun the evidence is about. What happened to it is `driver_state`. The stock impact is `direction`. Identity, period, magnitude, source, provider, and quote wording belong in `evidence`. If the evidence contains two or more independent causal variables, emit a separate driver tag per variable; never bundle them into one name.

**R3. Slot order is fixed.** When a name has multiple tokens, they appear in this order: theme, object, customer, geography, institution, metric. Each token belongs to exactly one slot per runtime vocab. Unused slots are absent. The same set of tokens in any other order is not a different name; it is the same name (the canonical form). If the runtime vocab ever classifies a token to more than one slot, the earlier slot in this order wins. A single-token name is valid only when the token is itself a standalone shortcut (R5); otherwise the name requires at least one discriminator slot. At most one token per slot. A name with two tokens that classify to the same slot is rejected.

**R4. Closed vocabulary.** Every token in a `driver_name` is either in the runtime vocab or in an existing registry name/alias. A previously unseen token may appear only inside a new driver proposal that satisfies R11.

**R5. Standalone shortcut.** Some standard names appear as full canonical entries in the runtime shortcuts vocab. When your assembled name exactly equals such an entry, that entry is the canonical form and slot order does not further apply. R5 covers macro, regulatory, corporate-action, and event shortcuts (e.g., `yield_curve`, `fda_approval`, `share_buyback`, `opec_supply`, `chip_shortage`) — renamed from the prior "Macro shortcut" wording per E23 / OQ3 because R5 is multi-domain, not macro-only. **Note on examples:** the names listed here are illustrative; not all are necessarily seeded in the §F.1 `SHORTCUTS_VOCAB` bootstrap list. Pattern B (E27) allows new shortcut Drivers to be added at runtime via `propose_new_drivers[]` with `is_shortcut=true` (subject to the v7-2 ≥2-token gate + R11 evidence gate + banned-content gate). Per E27 Pattern B (DriverImprovements v10 fold), shortcut Drivers are registered directly as `:Driver{name, is_shortcut:true}` rows with the `is_shortcut: bool DEFAULT false` schema property (per v8-1) — no parallel store. The runtime shortcuts vocab is populated from the SHORTCUTS_VOCAB markdown seed (mechanism file §F.1) PLUS the live Driver registry filtered by `is_shortcut=true` at writer bootstrap.

**R6. Compound metrics count as one slot.** Specific multi-token financial concepts (listed in the runtime compound-metrics bank) occupy a single metric slot even though they contain underscores.

**R7. Banned content categories.** None of the following appears inside `driver_name`. The specific tokens in each category are in the runtime vocab.
- State verbs and verb-derived word forms (progressive `-ing` or past-tense `-ed` endings) — belong in `driver_state`. Exception: a small allowlist of legitimate accounting/financial qualifiers (e.g., `consolidated`, `diluted`, `weighted`) is defined in the runtime vocab.
- Direction or polarity words — belong in `direction`.
- Motion or change nouns describing what happened to the variable — belong in `driver_state`, not in name.
- Tickers, legal entity names, person names.
- Period tokens (quarters, years, fiscal markers).
- Numeric or qualitative thresholds, magnitudes, or size descriptors.
- Source-type labels (filing forms, document kinds).
- Provider or vendor labels.
- Accounting-tag prefixes (XBRL namespaces).
- Metaphors, sentiment adjectives, effect-on-stock words.
- Bare category labels standalone.
- Vague descriptors too broad to name a causal variable.
- Stopwords.

**R8. Length is bounded.** Effective slot count is bounded by the runtime threshold; exceeding it is a deterministic rejection. Compound metrics count as one slot toward the bound.

**R9. Granularity.** Include in the name only the slots that the evidence directly attributes as part of the cause. Removing any included slot must change the causal variable named. Add a sub-dimension slot (geography, customer, object, theme) only when the evidence directly attributes the cause to that sub-dimension. Do not add sub-dimensions the evidence does not name.

**R10. Companion field rules.**
- `aliases` never bridge two different drivers; each alias is an exact variant of the same concept.
- `label` tokens equal `driver_name` tokens as a set.
- `segment` is `"Total"` unless `driver_name` encodes a sub-dimension; if it does, `segment` is that sub-dimension's canonical label.
- `allowed_states` is drawn from one state class.
- `definition` is exactly one sentence describing the variable; not a token-by-token restatement of the name.
- `base_label` is null or a canonical financial-metric label from the runtime banks.

**R11. New driver gate.** A new driver may be proposed only when ALL hold:
- No registry name or alias matches the candidate under canonical form.
- The candidate satisfies every rule above.
- Every token in the name is either in runtime vocab/registry/aliases, or it is a new token whose slot is unambiguously determined by its position among known tokens; the new token is not in any banned category, does not equal any existing name/alias/vocab entry, and appears (or its synonym/plural/acronym pre-image appears) in the supporting evidence.
- The same emission attaches this driver to at least one causal claim with non-empty evidence.
- The driver must not be tied to a single specific event, date, filing, company-quarter, headline, or source row; one-off concepts are rejected.
- If applying R1–R10 produces more than one unresolved candidate name, do not propose a new driver; reject as ambiguous.
- All companion fields satisfy R10.

## §5. Examples (illustrative only)

**State and magnitude do not enter the name.**
Evidence: "OPEC announced a 1-million-barrel-per-day supply cut."
Outcome: `driver_name = opec_supply` (standalone shortcut from runtime vocab — R5 covers macro/regulatory/corporate-action/event shortcuts); `driver_state = cut`; the magnitude stays in evidence; `direction` is company-specific and is not illustrated here. Demonstrates R2, R5, R7.

**Word-order variant reuses the registry name.**
Evidence: "Apple's iPhone sales in mainland China decelerated."
Registry contains `iphone_china_sales`. The candidate `china_iphone_sales` is in the same canonical form as the registry name and reuses it. "Apple" does not enter the name. "Decelerated" is the state. Demonstrates R1, R3, R7.
