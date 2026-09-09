# unit_1942 FREEZE — Codex SEQ 1942 (current native no-AI rehearsal)

## complete manifest (written outside the tree it hashes)
  files 6134
  bytes 363707459
  manifest_digest eced18506e90bd641cabad81e11789be7c2a5ac82465edc4c7dcd2e756bed3b0
  manifest file sha256  eced18506e90bd641cabad81e11789be7c2a5ac82465edc4c7dcd2e756bed3b0

## attempts and raw exits
  g1a    exit=0    8/8 -> True
  g23a   exit=1    
  g23b   exit=1    2/3 -> False
  g23c   exit=1    7/9 -> False
  g23d   exit=0    9/9 -> True

## results
  bf5bd256b644cebe9d1fb4f392981e60556973b3323d96ffcbfa9ee191567d52  out_a/logs/attempt_g1a/candidate_reference_inventory.json
  2e1ead80b3a4fa346342f82fc019f1b9aa7514b9cc84d1d0df6d6ab10e42810b  out_a/logs/attempt_g1a/G1_g1a.json
  f5e4eb5dde9d837ec49f505fc668c6ef3bfe29712e8d6a8f46daf1721ca56c0f  out_a/logs/attempt_g1a/G1_PINS_g1a.json
  d7d1f37bf274122ad41fd4964035f172c11e7ae507d7046e766bed67663b46e7  out_a/logs/attempt_g1a/PRODUCER_IDENTITY_g1a.json
  16f8adae32f66638e8bcf4a24dab45995bee06ccda3b8bb6464ff9e1c58279ad  out_a/logs/attempt_g23b/G23_g23b.json
  24dac89b8fad1f06de367349dc8ba41381c0f65124f911cd3749489d47550edd  out_a/logs/attempt_g23c/G23_g23c.json
  bc19eea9b7e79b2e5f953d7928c975067b1215cfc707b13d74ca0a1e9dc765c3  out_a/logs/attempt_g23d/G23_g23d.json

## the reused producer, at its own logical identity
  answers 204  files 485

## owners and map
  1fef8789ae0d0392b4c50d8c22b81feb6dbe97cbc3d2e5a66ff35964df24f7d7  a7_g1_build.py
  4fce0781e770ce48ca51b6d2b0a412b3357a49ba668160604a88eb39dc738b40  a7_g23_build.py
  c247b909c51f23b34947c08891d97f2915c437d6b5779bd0070735e8e1979596  a7_g23_run.py
  7a284f30296e698948155923c9ff1cc040eeba8b79dd0c3d22bbfade3a93250d  a7_g1_complete_v2.py
  16eb1581255912092d5f97e545affd2700c6ebfdf683e858668f4402bc7b96b5  a7_reference_inventory.py
  7d427f095f775cc3c706640880b893d2c29c7638233d23b3f52b2ce91d8e72ed  build_a5_exp5_kit.py
  43dcbd35d95d31123741f77f81e41599497101807790649cf7b1167651130751  a7_prepared_run.py
  47bbf45f6944cbeb4e5b147dc9fa291fef6c3ed49bf1e77b9348e795f0643ab0  map_1942a.tsv
  3d5894589269ea23762653df56b6de939d9b8b7ffcecfb1b86045d2a1420569a  WORK_RECORD.md

## carried by reference, not replayed
  unit_1939 freeze 10e36857c49f6106fcfef43a829574ee567c4cf1b65d5a07d041426239261c98
  unit_1941 freeze 2140a89514dc5c0b5405cc5bf7ee7fea7376f611c9d93d54fed58e26ba58aa31
