# Why agreed-empty matches are not proved omissions

Read-only replay, 2026-09-15 UTC. No new match is awarded.

All115 `agreed_no_candidate` findings from Core2164 were joined to the exact
native score's emitted records. Existing scorer eligibility and the existing
exact matcher were used; no semantic matching heuristic was added.

| Leg | Findings | Source has excluded records | Exact emitted match outside offered pool | Exact match inside pool |
|---|---:|---:|---:|---:|
| P1 | 39 | 35 | 5 | 0 |
| P2 | 42 | 40 | 7 | 0 |
| UNION | 34 | 1 | 0 | 0 |

The12 exact outside-pool matches prove those model answers were emitted, not
lost. They do not authorize admitting a record excluded by the existing
conflicting-name rule. The remaining103 have no exact match in this diagnostic;
that does not prove absence of a semantically matching differently expressed
record. Saved G1 selections remain the actual qualified evidence; these
categories qualify attribution, not credit or source truth.

Native report656c18bd363ac3941a737d4d3ae55b101f303c209727ed261325a42e9664f08a
is unchanged. RECALL_ELIGIBILITY_2169.json is
151145922e4d6963e1ab10932498871c674cf17444e046590fcd498cd23a09bd;
caller trace_recall_eligibility_2169.py is
4c1a453781e0750fd6b14c4414d80d5d90ac1ed13ab9c925b84bb7a91f23bc52.
The run completed with exit0. All fact positions refer to the pinned native
report, so the diagnostic does not duplicate thousands of full records.

The original Core2164 JSON was reconstructed after Core's live copy gained
an extra field/reason without a new filename. Removing those additions and
serializing with its original one-space format regenerates original SHA
2e238ae6a9f25f2634595a7a0dbb7e4ab70712a1e5a26004155472510365d975.
Our durable CORE_RECALL_TRACE_2168.json holds that data plus one final newline,
SHA40f5ac16bdeb270e244eff1160c443f0b5bcdcf8001a6bdb4e9a3c4be96b58f0.
No raw model result or Core file was changed. The added newline is disclosed,
not falsely labelled byte-identical to the original artifact.
