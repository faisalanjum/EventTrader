# Cause disposition for all 100 consumed key_miss judgments

Core, 2026-09-15. Read-only: no model call, no scoring rerun, no boundary job,
nothing written outside this unit.

## Three corrections I owe first — Codex is right on all three

1. **Class 1 is NOT a rule ambiguity. I withdraw that verdict.** FINAL_DESIGN.md
   4.3 (Metric) says verbatim: "A prior value stated IN THE SOURCE alongside the
   value routes to `increased`/`decreased` instead of `reported`." The rule is
   explicit in controlling law. I searched only the SERVED prompt, found the
   vocabulary not enumerated there, and called it under-specified - without
   checking FinalDesign, which my own LAW gate requires. The state-contract
   check is Codex's; I do not amend it.
2. **M4e236380221db347 does not belong in that population.** Its card is "the
   Term Secured Overnight Financing Rate plus a margin of 1.5% to 2.0%", values
   ['1.5','2.0'] - the two ends of one interest-rate range, not a temporal prior.
   My recognition signal was "card carries >1 value", which DECIDED rather than
   recognised. That is the no-hardcoding rule, broken by me.
3. **Mfdc3b99ab640f039 was in my report table but not in my own evidence file.**
   Its driver_state is `increased`, so it was never in the reported-state
   population. The table contradicted the JSON; the JSON was right.

I also accept the fourth point: equal quotes prove a shared source span, not
presence or absence of a fact. My own qualification said so and my headline did
not. This report replaces "90 grader errors" with a per-row disposition.

## Population and binding — proved, not assumed

The consumed extras are keyed [source_id, produced_idx] per leg. Counts:
P1 4, P2 12, UNION 84 = **100 key_miss**, exactly the expected split.

Question identity is X + sha256("G3|leg|source_id|produced_idx")[:16]. I
recomputed it with plain hashlib (no harness import) and it regenerates **all
116** frozen question ids exactly, so the leg/source/index -> question binding
is proved. The 100 consumed key_miss are the SAME SET as the 100 agreed
key_miss from my 116-question table: identical, nothing only-in-either.

Two mechanical facts about the run, both re-measured:
- **0 of the 100** extras have a produced index inside their event's matched
  set - the extras population is correctly unmatched. (My first check said
  otherwise; I had compared against element 0. The pair is [gold, produced] -
  `produced = row[1]` in eligible_comparators. Corrected.)
- **100 of 100** sit in an event with at least one UNMATCHED GOLD row.

## The 100 rows

| disposition | count | P1 | P2 | UNION |
|---|---|---|---|---|
| (a) really absent from the key | **0** | 0 | 0 | 0 |
| (b) present in the key, not credited by this run's matching | **86** | 2 | 9 | 75 |
| (c) record itself source-unsupported or misstated | **12** | 2 | 3 | 7 |
| (d) genuinely unresolved | **2** | 0 | 0 | 2 |

**No key_miss label in the consumed 100 is supported by this review.** No row
establishes a fact the key lacks, so the key-versioning/retest trigger is not
met by these 100. I make no claim about how that ranks against other outcomes.

### (b) 86 rows — the key carries it, the run did not credit it
- 75: a reference card on the record's own sentence carries ALL the record's
  asserted numbers (Decimal set comparison, no tolerance). The card is a gold
  row read by exact row identity with a hash-bound quote, so the key has the fact.
- 4: card present, record numberless on both sides (share-repurchase programme
  x3, total unit revenue x1).
- 4: the extra field the record adds is inside the card's own span or name -
  e.g. the FTE card is literally named "Regional (4) 32,500 30,700 5.9 %" and
  the record's change 5.9 is that span; adjusted net debt -760 x2; impairment
  171 with a 0 prior.
- 3: same sentence, other rendering - AZO "increased $329.5 million, or 6.7%"
  (the 6.7 rendering, x2) and DAL "by $1.2 billion, or 9.4%" (the 9.4 rendering).
  Both renderings are stated in the one sentence and the event's gold row for
  it went unmatched. For AZO P1 the matched pairs are [[0,0],[1,1],[2,2],[4,5]]:
  produced 3 and 4 are both asked and neither matched, and gold 3 is unmatched.
  This is the already-known non-bijective group gate, not a key omission.

### (c) 12 rows — the record misstates the source, so key_miss fails its own test
key_miss requires "a real claim of this source". These records do not state what
the source states, so the precondition fails before the key is even consulted.
- **2 magnitude errors.** Xa9539f6f9f30a4c6 stores -300000000 where the card and
  source say $300 million (-300). Xc60ccdea49a8ca1a stores change 4000 where the
  source says "a greater than $4 billion increase" and the card carries 4. Same
  unit and same scale evidence on both sides, so these are real quantity
  differences, not scale-encoding equivalences.
- **10 rows with no card on that sentence at all** - MCD $80m x4, YUM 377m/40m
  x4, DAL 85% travel survey x2 (3 distinct claims). I re-read the MCD source
  myself rather than adopt the existing exclusion: it says "pre-tax charges of
  $80 million PRIMARILY RELATED TO restructuring charges associated with
  Accelerating the Organization", while the record names the restructuring as
  the driver and assigns the whole $80m to it. That exact attribution is not
  what the source states, and the event's only two cards are unrelated claims
  (US +6.8%, 95% franchised). This agrees with the saved source-only exclusions
  033/184; I did not re-open those completed reviews for the YUM and DAL rows
  and I rely on them there, which I state as a limit rather than a fresh finding.

### (d) 2 rows — genuinely unresolved
Both Starlink rows (Xf6cbcbd375607d09, Xb100f34c67a98cff). The source does state
the quantity: "at least 300 aircraft planned by year-end 2026", and the record
stores level_low 300 count, which is the right slot for a floor. The event's
card for that sentence exists but carries NO values. Whether the key's gold row
for that announcement carries the 300 as a fact cannot be settled from the card
values alone; it needs the gold row's own fields, which are key-side evidence I
was not given. I leave these unresolved rather than guess either way.

## Confirmed grading-task defect: none. One named limit.

For the 86, the deciding evidence was IN the served prompt: a card on the same
sentence carrying the same numbers, plus rule 3 ("reference_cards identify
reviewed claims") and rule 1 ("Answer null if the evidence does not settle it;
null is a lawful answer and you must never guess"). The task was sufficient and
the lawful answer was null. That is a model violating a sufficient task, not a
task defect.

The limit, stated as a limit and not proposed as a change: the extras vocabulary
has no bucket meaning "the key carries this claim but this run's matching did
not credit it". With duplicate restricted to the matched pool, a record in that
situation can only lawfully be null, so an 86-row matching outcome is invisible
in the extras counts. I am not proposing a new bucket, relabelling anything, or
turning any key_miss into duplicate.

## Evidence in this unit

- `consumed_key_miss_100.json` - the 100 rows as consumed, leg/source/index/qid
- `key_miss_evidence_100.json` - each bound to served record, cards, match state
- `key_miss_dispositions_100.json` - the per-row disposition above
- `REVIEW_2167.md` - this report

Every count is recomputable from these files. Original outcomes are preserved:
no raw answer, Boolean, bucket, key row or score was altered.
