# Real final candidate — Codex2082 review

Scope: actual source-key package and immediate signer/lock connection only.
The source decisions are closed; no new source call or grading-code change.

## Findings and smallest fixes

1. Core's first attempt core_cand2081_a refused because R.candidate_scope was
   entered inside N.input_scope. The former revalidates the old reviews, so
   it must be entered before the newer worker profile. Core corrected only
   that caller ordering; core_cand2081_b then passed17 checks. No owner bug.
2. Independent read of that candidate showed ordinary.recovery absent while
   the frozen packet requires unit_2053_owner_retry/RECOVERY_BINDING.json.
   Its key identity had neither recovery_binding nor recovery_record and
   omitted the recovered run. A direct independent assertion failed exit1
   (actual undefined versus the exact saved path). A Bound round-trip cannot
   see this: recovery is deliberately a separate ordinary-binding field.
   The existing a4_source_candidate owner already pins all four recovery
   artifacts when this field is supplied. Codex added only the saved field.
3. The caller's origin test accepted merely33 entries through OR, rather
   than comparing exact per-source origins/raw hashes. Codex uses the
   already-read real gate's complete origin/raw map as the independent input.
   Its RESULT also looked for the signer manifest at a nonexistent path;
   corrected that single path, matching Core's correct manual mailbox hash.

Original reported driver preserved byte-exact as
build_real_candidate_2081.before_recovery.txt:
d3fffce007e72bfa2ca89c247a3c1f75fa497ff797308256bf2b1a5b1a1be112.
Current driver8799b52572df41c96250f1767583bb9a47295c8157cc8019ffb782c9e4dd67f1.
Old candidates/attempts remain intact, uncalled and unapproved for signing.
Runtime owners, old source evidence and667 completed calls are unchanged.

## Selected new candidate and completed build

unit_2081_final_key_candidate/codex_cand2082_a.
Actual payload exit0,18 checks, stderr empty; stdout
ce7c85b08dbdb5f09191a4e681bc209b479ee160ec443c50fb0aab2d91c52b38.
Existing C.build and C.verify accept the real key. All four recovery artifacts
and the recovered run are now explicitly carried; every33-source origin/raw
hash agrees.667 pre-signer calls; one planned signer would reach668.

| Artifact | SHA256 |
|---|---|
|RESULT.json|bf19032ebc2ce89431d2d784473630d2eb2b855f5f8175f898814f1de5bbe4c8|
|ordinary_bound.json|e7117620ca7a33ab4a68814d8107df4d47304e408f0c1296bbe5dcc14c9a01c7|
|candidate/key_identity.json|e77684b2472f583cce116a1cadc845bcadcfd5b84a808ddbaec8139adaf13635|
|candidate/provenance.json|a7804d6cdd67a95b22a1d9888f83b8dcb0cec44ca9343ebc4f0a45dfca938687|
|candidate/sidecar.json|7cc31690134040d453c3bb01dc36f810b62f18984e86b0f6cea59e5b12677b62|
|candidate/validator_receipt.json|ab24158521d822b685befeeedd8032d2d18dab0ff65868d4ca8f5b5667224923|
|candidate/signer/signer.manifest.json|414354a66a26238ea0edd3cf8434c20af3f1fbc5322396bac59163247432911e|
|candidate/signer/signer_prompt.txt|b7987ebd324ad66491d9990f3522a846e58a104903c36c203293447c353a267c|
|candidate/signer/final_sign.attempt1.js|87f896d24bb211524467239ed7482b40d88d439bd3aa0949102b5baefcace9fe|

Signer script385373bytes <524288 limit. UNRUN: no signature or lock yet.

## Completed independent cold proof

verify_real_candidate_2082.py
2f7c4efe48cecc1ebe4e1934de192c0a54985a3cadc118af92460e6585f8ffe7;
attempt codex_candcold2082_a consumes the saved REAL candidate from a fresh
process. The existing C.verify re-derives every byte, checks current source
input and full history/origins/counts, drops only recovery at the real reader
to require a changed candidate, then restores the actual reader as a positive
control. No native/source/candidate input bytes change. This is a focused
caller-binding test, not a repeated full grading-code audit.

Core's one current task is READ ONLY: trace the immediate existing real
signer-harvest/compact-lock call path and exact scope ordering. No Core launch
or file edit is authorized. Codex2082 mailbox hash
90ce74ee790d93c0f460bb7d41c80afd75f7dd90c994fc7cf2c924c68a659471;
Core2082 report1bd3a1f2cc026d8c490e4b80dffcc29d34b1c6bb340eb77fd2c9a8269e50653f.

Actual codex_candcold2082_a payload exit0,15 checks, stderr empty. Stdout
528aedd1d14b383d2e5268120aa74caf675a8605a22da1b5f8576921174d57d1.
Removing the recovery declaration at the existing metadata reader changed
exactly key_identity/provenance/prompt/both prepared scripts/signer manifest;
the saved complete candidate could not be reproduced. Restoring the reader
reproduced every byte, and all saved candidate input bytes remained unchanged.
Current signer input is exactly profile78b58fe7/attachmenta755758d.

Core2083's read-only trace1520d61082c78d3af998cc31f11045f8c463dc6bce5f441cc48f5f5c151c49e2
correctly identifies the lock's bare CAND import: preload the exact unit_2005
owner before loading the compact lock, not the obsolete adjacent copy.
Standalone harvest also MUST serve profile2068 explicitly; SP.prove checks
the manifest's declared input against the served input owner even though it
does not reconstruct the key. The key-reconstructing lock instead enters
historical review under the old profile before N supplies the new profile.
No owner change or new framework is required for either caller requirement.

The existing SP.select_saved_call independently returned launch/None/None for
this exact script in codex_signselect2083_a, payload exit0, no model call.
The current profile declaration and exact packet passed before that search.
Codex2083 now authorizes ONE real signature collection only, hash
7f380c75c4d19500a639daab2a1acf75a3cabcc5ed2b47adf420bbbadc3b85ea.
Core writes unit_2083_signer_collection, then reports once; no retry/harvest/
lock/publication authorization in that collection task.

Checklist: source closure VERIFIED; caller repair/build VERIFIED; independent
cold/mutation proof VERIFIED; one real signer collection AUTHORIZED, outcome
unknown; real lock/preparation publication/actual grading NOT STARTED.
No universal reliability claim.
