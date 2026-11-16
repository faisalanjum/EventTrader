Okay this is the final Claude sub-agents' review. Store it first and then one by one analyze it only when the time comes. Make sure you analyze every one of them deeply without rubber-stamping them. I want you to think independently and rigorously and then tell me or include whether you are confident before accepting or rejecting it. The biggest takeaway: the rulebook makes each record's quote prove every detail, so build the quote first and ask everything else on the quote alone. Codex's own tests today point the same way. Below is the list to paste; it adds only what he isn't already doing.

▎ Independent review results (5 designers, 3 skeptics, 2 attackers; all 54 records, the rulebook and your latest tests considered):
▎ 1. Make the quote the centre of the design. The rules make the quote prove every field (1.17, 1.24, 3.29, 3.33).
▎    - Use the whole call only to find forecasts and pick their evidence sentences.
▎    - Ask every field question on the selected evidence plus the header (company, call date, fiscal calendar).
▎    - Your unit test shows it works: 12/12 in 33 s on evidence, vs 11/12 in 196 s on the whole call.
▎    - Move period, movement, shape, scale and scope there too. The whole-call field step (477 questions, 23 min) then disappears.
▎ 2. Quote building is now the bottleneck. Your 3/4 result came from context borrowed from another forecast. Keep going with "selected evidence only" for the model, and store the continuous quote separately.
▎    - Evidence = the forecast's sentence + its lead-in sentence + its attached assumption sentences.
▎ 3. Classify each relevant sentence once, then route it. One choice per sentence: numeric forecast / worded forecast / assumption or exclusion / movement or lead-in / comparison with earlier guidance / cause or explanation / actual result / other.
▎    - Only assumption sentences become conditions. Lead-ins go into the quote, and comparisons go to the comparison fields.
▎    - This fixes a likely failure: "we are raising guidance" stored as a condition.
▎    - It also limits your support-pair questions (already 86/88 correct) to assumption sentences.
▎ 4. Take metric naming out of the Decider. Rules 1.14 and 2.40–2.43 put naming and matching after extraction, working from the evidence. The owner's split is that the reader names Drivers.
▎    - The Decider then needs one check per record: "Does this evidence say what [V] measures?" No → extend the evidence or hold.
▎    - This drops the unsolved metric-span step (pointers 11/15; the short search returned confident wrong spans).
▎    - Tag and qualifier wording come from the same quote at naming time.
▎ 5. Keep qualifier meaning in the shape choice. Options: point / approximately / at least / more than / up to / less than / range / position in range (high or low end) / centre ± tolerance.
▎    - Without this, "approximately $101 million" is stored as an exact point.
▎    - The exact words stay in the quote and become tags later (3.25–3.26).
▎ 6. Comparisons: for each number group whose role is "earlier", ask one choice: which current forecast does it compare with (or none)? Store it as a comparison against previous guidance, never as a new record.
▎ 7. Worded forecasts: the anchor is the sentence from step 3, and value_text is that sentence if the owner accepts it under 4.7 (200 characters or fewer). Hold and count sentences with several worded forecasts: there's only one in the six calls.
▎ 8. No silent drops: main_path_fields.py lines 12, 14 and 67 drop unclear, below-cutoff and "several" items. Every item needs a recorded outcome (8.14).
▎ 9. Process: before more single-example probes, build the six-call development key (two blind passes plus owner cards) and score each stage's silent misses. Before demoting any class, run a census on a random one-call-per-company sample, since Micron and Ollie's show classes cluster by company.

Rejected as over-engineering: my own phrase menus and dependency-parser idea, value-by-metric pairing, clause-splitting chains, and counting or ordinal layers.
