# Active Codex checkpoint — source-only key packaging

Core's separate, unchanged task remains Codex2005: collect the66 primary blind
reviews under unit2004. Do not send another task while it runs, do not interrupt
valid calls for this work, and never repeat a successful model call.

This is the owner's requested pre-grading dependency check, done with existing
TEST data while the real reviews run. No real key, signature or A7 grade exists.
No tracked file, old owner, running review, main file or database was changed.

## Reproduced failure and bounded fix

`unit2004/ledger/probe_final_consumer_2005.py` proved the existing source-only
TEST key still passes its actual signing gate and detailed lock, but the
later canonical artifact builder raises FileNotFoundError for the explicit
no-phase-one sentinel's finalization file. This is not an AI answer defect.
Probe stdout SHA `e3e3769ff5aa798e88da7af919c25f3efc3476a66cb6392c671358153b53b90a`.

Only two new owner files:

- `owner/build_final_key_candidate.py`: exact unit1955 owner with its ordinary
  stage-binding block extracted unchanged into `ordinary_bindings(bound)`.
  No parser, materializer, signer, artifact serializer, lock or grading rule
  changes. SHA `64932cd2b71b9e89a1c06c3c8ebc4ef3f97ab386df4c9325f954c703f1810bd4`.
- `owner/a4_source_candidate.py`: one serial context supplies that binding
  list from the real initial-source, hard-review and final-key stages while
  using unchanged CL.final_scope. Every actual primary/child receipt and
  finalization is bound, the offered key identity must match exactly, and the
  original function is restored in finally. No fake historical file and no
  semantic ruling. SHA `b35ca5c8e82058236f0418468cf1409207524b06183560b5aec79817fe8a06e3`.

## Verification — code handoff, not real key approval

`check_candidate_2005.py`, attempt `codex_candidate2005_b`:32/32 pass, stderr
empty. Stdout SHA `6f6132026bbcef6bcf7e9f5c4618b7946e94e7dc08b21f596be906cb55528a4e`.
Primary and real invalid-only-child TEST keys both build/re-derive the existing
candidate and signer packet; bind all actual stages; count calls once; preserve
191 rows and exact Decimal materialization through the grader. Wrong offered
key and missing review refuse; context restores on success/failure. Historical
binding order/hash stays unchanged, with/without review; missing historical
phase-one still refuses. No approved-key identity was tested by the diagnostic
grader call: it deliberately supplied a TEST bound to isolate the materializer.

First regression attempt `codex_candidate2005_a` reached the last historical
fixture then failed because the TEST omitted Bound's required `fix=None`.
Corrected the fixture (and used namedtuple `_replace`); no owner change.

`check_signed_candidate_2005.py`, attempt `codex_signed2005_a`:16/16 pass,
stderr empty. The exact generated signer prompt/launcher passes the unchanged
unit1955 native proof, raw harvest, canonical compact lock and receipt. The
harvest resumes with identical bytes and the saved-call selector returns reuse.
Four native identity/status/tool-use mutations refuse with restored positives;
all33 existing compact-lock mutations refuse. No real model call or signature.
Stdout SHA `f1d8954006cb71c8eb9171067ff7b77e8b3051a9669be9aff1dfceaa5bbd31a5`.

`check_approved_consumer_2005.py`, attempt `codex_approved2005_b`:11/11 pass,
stderr empty. A fresh boundary pins the TEST lock/receipt/ordinary binding;
the actual A5 hash-chain and G1/current-key readers consume it without a fake
approval or serialized-key adapter. Exact Decimal values survive. The original
scheduled denominator is36 events/191 items/382 answers despite33 item-bearing
key shards; a different supported plan derives its own counts. A coherently
altered lock AND receipt still refuse against the unchanged approval pins.
Stdout SHA `d7292bb6b8bb908a271c85af3ec0747f7fb1c51640c3c27b99387876bd3023ad`.
The first attempt stopped on a TEST reference to a nonexistent constant; the
test now compares with the independently frozen source-plan inventory hash.
No owner change was needed.

`check_scope_failures_2005.py`, attempt `codex_scope2005_a`:36/36 pass plus
the unchanged12/12 final-scope and17/17 package regressions. All five ordinary
identity fields and every required file derived from the live binding list
are tested; absent binding, caller failure and restoration are covered.
Stdout SHA `c5a2783e60f5c66d37d19d2abd7e56d469735a4db670194b0e9dbcd42cb8dc02`.

## Short review checklist

| Pass | Status, change and verification |
| --- | --- |
| Generality / hardcoding | Verified locally: actual stage paths, optional invalid-only children and counts derive from existing owners. No source-id, example, semantic-word or new configuration rule. Both primary/child and historical bindings tested. |
| Workflow / correctness | Verified locally for the key handoff: candidate -> exact TEST native signature -> harvest/resume -> compact lock/receipt -> externally pinned A5/G1 key reader. Real source truth and the separate saved-answer evaluation packet remain open. |
| Duplication / organization | Verified locally: one extracted ordinary-binding callback, one source-only supplier; all parser, materializer, signer, retry and lock owners unchanged. Historical frozen owners remain required evidence, not duplicate active rules. |
| Simplicity | Verified locally: no new proof engine, schema, backend, grading rule or production adopter. Only the reproduced nonexistent-phase dependency is replaced by actual stage evidence. |
| Tests / evidence |32+16+11+36 focused checks, unchanged12+17 affected scope/package regressions,33 compact-lock mutations; all exit0. Prior1639 dependency pins must recheck during snapshot freeze. Core independent review still pending. |

## Remaining gates — do not enlarge this code task

Freeze this exact code/test/dependency snapshot, then have Core independently
review at its next lawful mailbox checkpoint. No real signature or publication
is authorized by these TEST results. The real66 reviews,33 final adjudications,
signature, A5/A6 saved-answer evaluation binding and A7 grading remain separate
ordered work. A5's old NEW-producer plan is not the saved-answer reuse route;
do not regenerate382 evaluated answers or repair their response bodies.

All outputs are clearly TEST-labelled and durable. The only new native records
are in the explicit unit2002 TEST store, after a samefile guard proves the real
store is shadowed. Existing qualified TEST and real source evidence is unchanged.
Production adoption debt (materializer/lock interface) remains a later Step3/5
gate, not a new A7 task. Core's current real collection remains separate.

Active sessions: Codex01a05829-3086-73e0-89c9-e5773b322d80,
Core5ae9b86b-f0f6-4449-beee-9cac7cfa7200. Reuse watcher/listener85562 and active
goal. Last outgoing2005 SHA97199d746160fdf480e70357a97de490638c06ffbd0e8f182dfe0d78c2215807,
last incoming1989 SHA9ec27c96527a51abeed39fa4012b57b432348e76eb21518cdc0ef801b9e13451.
No pending test commands at this checkpoint. Core is active, not blocked.
