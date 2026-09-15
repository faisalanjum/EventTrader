# Remaining source and recall causes — independent review addendum

Codex 01a05829-3086-73e0-89c9-e5773b322d80, 2026-09-15 UTC.
This adds review evidence to FINAL_SCORE_CAUSES_2168.md, SHA-256
de85c8f6d23c6fea703e3160b6d5b23399aa83b0dc826c4802ba6eab82311ff3.
It changes no source, key, raw answer, qualified verdict, scoring rule or score.
Core's only active task remains Codex2173's frozen 24-call collection.

## Three remaining source questions outside the new 38-question collection

All three identities were regenerated from the full candidate's exact
leg/source/gold-index/produced-index tuple with the existing opaque-id formula.
The native score/key remains 656c18bd363ac3941a737d4d3ae55b101f303c209727ed261325a42e9664f08a.
The complete served prompt, its actual question record and its complete source
part were independently rehashed, not just a quoted sentence or reference card.

### M8624b63494238990 — a grading false-positive lead, not a reader error

UNION / 0000764478-25-000057 / gold3 / produced8. The complete produced fact
equals the approved gold fact in EVERY produced field: fact_type, the entire
item, part_ref, occurrence_in_part and per_x. This was checked recursively,
not with numeric-set or quote equality. Full source context independently
supports it: the Domestic segment table's first two columns are the current
and prior-year three-month periods; 31.8% and 31.4% are its online revenue
shares. Surrounding prose identifies the current period as Q3 FY2026.
The generic revenue_mix name and domestic/online population preserve the
stated meaning, and the increase follows the signed values.

The served judgment's sole negative aspect, record_matches_source, has no
source-supported defect established by this review. It cannot be presented as
a confirmed reader mistake merely because two graders returned false. This
is NOT authority to overwrite those replies or turn this review into a third
scorer. Preserve the measured flag and identify the grading-model limitation.

Prompt SHA-256: 4973db60f080e5f344e1828a8faafa3f6ad34e51aa957cf3b731b84288a1e199.
Full mdna part: dbac58d3ebb2e5f2ab648317e173721569b489eac512d6cf377980e5615280ce.

### Ma31af1665347b9ec — an actual name/population error, not a forced number

UNION / 0001041061-26-000003 / gold3 / produced3. The source's own definition
identifies digital as the way consumers order at system restaurants. Its
fourth-quarter bullet gives digital system sales and their mix. Under
FINAL_DESIGN NAME-10/11 and section5.2, this is the company's measured sales
channel, which belongs in the population, not the driver name. The record
instead says digital_mix with an EMPTY population; it also drops the
system-sales qualification. That is a concrete naming/scope cause for the
whole-record negative result. A lawful name synonym is not the issue.

Do NOT call the null numeric slots or null level_unit an error merely because
the source says nearly60%. A cautious numberless representation does not
assert an exact60, and section6.1 explicitly says no number means no unit
resolution. The reviewed cause is separate from that lawful caution. The
approved key's system_sales_mix/channel:digital is a consistent comparison;
source context and the role rule, not the key label alone, establish the cause.

Prompt SHA-256: 4973db60f080e5f344e1828a8faafa3f6ad34e51aa957cf3b731b84288a1e199.
Full exhibit_99_1: c5c1dcec3446db26b749483224ad41c563564c5f426d1384c4cd95f381f5800c.

### Md2061d63bedc8f75 — remaining representation ambiguity

P1 / AAL_2026-04-23T08.30 / gold7 / produced7. The full source gives Q2
40–50%, Q3 75–85%, then conditional Q4 recapture in the90s. The produced
record stores only a90 floor. The independently signed key deliberately uses
qualitative guidance instead, with an explicit ambiguity note. Neither the
key's caution nor mathematical entailment of a weaker lower bound, alone,
settles whether this is a wrong assertion or lost precision under the test's
source-faithfulness rule. The graders recorded only false for the whole
record, not a reason; do not invent their reasoning.

Keep this limitation explicit; do not manufacture an upper bound, invent
numeric-word rules, overwrite the negative label or reroll a valid answer.
Plan section2 rule7 exhibit / proposed clarification for FINAL_DESIGN7.1:
"Specify whether an entailed but incomplete open bound is an acceptable
encoding of a vague source band, or whether that band must stay qualitative."
This is a proposal, NOT adopted law or a new prerequisite to partial scoring.

Prompt SHA-256: ab75b6d8b06c5346c04fafad480921f6f713f9913cd27fd3e4a867e45ba175a6.
Full qa part: 1b1b4097f88630f98fbd0d9549167ab147e9e43a2b8e30e5adb3c26fa253d740.

Evidence owners reused: G2_CARRIED_FALSE_SOURCE_EVIDENCE_2165.json
82d727fdb7dc6ee8eaef8e0db6326e1663de5a310aed6d098aedc1527fa74281;
G2_CORRECTIVE_BATCH345_SOURCE_EVIDENCE_2165.json
055a479c8ba9e7b92cc7aaf2de3d5e7e5b4475dfebe7f9c7989188841a0e4913.

## The one supposedly post-selection recall miss is also a matching conflict

UNION / ULTA_2026-03-12T16.30 / gold5 / Qa46ca6933d9623c2. Both G1 replies
select produced4 for gold5, but laneA ALSO selects produced4 for gold4; laneB
selects nothing for gold4. Under event_credit's explicit UNION-of-edges law,
produced4 has degree2, so even the agreed gold5 edge receives no credit.
This is before the grading consumer, not an unexplained route rejection.

Actual raw replies were rehashed and parsed without modifying their bytes:
unit_2088_real_grading/g1/raw/00186.attempt1.raw.json
7d9d11bff4942c71c2b68f0da5169accd2b1b76e839b1f4d68cfa471030ca149;
00187.attempt1.raw.json
087e82357649b3336669c9a3898cb475394e9d885e82e1ce4a740e09cd86cb6b.
The live owner unit_2006/harness_g1v3/a7_g1_build.py event_credit was invoked
on those exact relations: only gold0/1/2 receive credit. Positive control:
removing ONLY laneA's competing gold4 edge makes gold5->produced4 receive
credit. Both assertions passed, raw exit0; no model call or file mutation.

The immediate-cause inventory therefore reads:115 agreed no-safe-match,
63 withheld by multi-row/contended matching,5 exhausted-invalid and2 paired
disagreements =185 misses. This refines Core's62+1 split without changing
which facts missed or any score. Do NOT call all115 proven producer omissions:
the earlier audit located12 exact emitted records outside the lawful offered
pool because their names carry conflicting fact types. That exclusion is the
explicit experiment rule, not permission to remove it for more recall.

## Metric-state instruction lead — no further correction round justified

FINAL_DESIGN4.3 is clear: a current and prior value stated in the source do
not take the bare reported state. The served task already requires graders
to distinguish a source-stated prior comparison from a bare reported level;
the current correction also states signed numerical direction. The observed
true/false spread is not, by itself, a contradiction in those instructions.
The earlier ORLY source checks establish wrong positive state judgments, but
not that the task supplied wrong evidence or permitted that interpretation.

Decision for this bounded run: preserve and report those grading-model errors;
do not add another prompt version or reroll completed judgments merely to
seek better labels. A more explicit sentence might improve a future grader,
but that possibility alone does not establish a required test-code fix. This
does not endorse the wrong judgments or make their precision counts
source-verified. A new concrete counterexample to the task can reopen this
decision; the mere existence of a disagreement cannot.

## Checklist after this pass

| Requirement | Status / verification |
|---|---|
| Generality | No new rules or executable semantic choices. Names above are evidence identities only; live generic role/representation rules were applied. |
| Complete workflow and real causes | Three source questions separately disposed as above; the remaining post-selection cause reproduced through its actual owner and positive control. Three other earlier open source questions await the38-question correction. The metric-state lead is ruled on above: no further prompt/call round justified by the observed spread alone. |
| Duplication / organization | Existing source records, immutable score, key, prompts and matching owner reused. This addendum is review evidence, not another scorer or altered grade. |
| Simplicity | No prompt/code change, extra AI call, new framework, broad audit or production work. No source fact is accepted on shared text alone. |
| Tests / limitations | Full-field equality, actual question/source hashes and the live matching scenario/control verified with exit0. Published290 tests +29subtests are unchanged. The38-question run and final consumer remain open; semantic-model and representation limits remain explicit. |
