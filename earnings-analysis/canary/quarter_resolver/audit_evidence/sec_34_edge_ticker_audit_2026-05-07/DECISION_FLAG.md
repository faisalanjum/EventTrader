DECISION_FLAG_RULE_G2 = promising_but_not_shippable

## Inputs
- AB coverage: 400/408 = 98.0%
- G2-calendar-only: D fail-closes → correct AUTO_OK: 221, D fail-closes → wrong AUTO_OK: 37, new wrong AUTO_OK on AB: 37
- G2-all-fy-disagreement: D fail-closes → correct AUTO_OK: 239, D fail-closes → wrong AUTO_OK: 39, new wrong AUTO_OK on AB: 39

## Rule
yes iff: AB coverage ≥ 90% AND zero new wrong AUTO_OK on Tier A+B AND every G2-changed AUTO_OK matches truth AND meaningful reduction of D fail-closes AND PHR/PINC/PRU not worsened.
promising_but_not_shippable iff: G2 improves fail-closed coverage but has ≥1 wrong changed-to-AUTO_OK row, insufficient AB coverage, or unresolved unclear blockers.
no iff: G2 does not materially improve D, or evidence insufficient.

