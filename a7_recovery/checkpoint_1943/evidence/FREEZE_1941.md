# unit_1941 FREEZE — Codex SEQ 1941 (the full affected regression)

## complete file manifest (written outside the tree it hashes)
  files 7867
  bytes 534261750
  manifest_digest 3744f3da62ef248d73cc21ca2462c2663cab7ce1759c38c8c3e1e04bda65b14b
  manifest file sha256  3744f3da62ef248d73cc21ca2462c2663cab7ce1759c38c8c3e1e04bda65b14b

## the six-file delta under test
  build_a5_exp5_kit.py         base 89853599d61b2c80e4c1bcbf009695d3d586fe869fbfbf3c7fb4308fc58d9101
                               cand 7d427f095f775cc3c706640880b893d2c29c7638233d23b3f52b2ce91d8e72ed
  a7_g1_build.py               base 524be73b325a8c2c929d08f07e1a8668d031306bc4cfa0b7b8e049fcfa20001e
                               cand 1fef8789ae0d0392b4c50d8c22b81feb6dbe97cbc3d2e5a66ff35964df24f7d7
  a7_key_correction.py         base 76cccc9afe9fbb099d9adf23d3af8d0e432c4e26de10d9299e30bbd98d3ea245
                               cand 6ba1218c397191360ee4ea5705c26ce6d0ac6e3b7763baa716105f4d6c022235
  a7_reference_inventory.py    base 65f8e34128041d82e28ae92992e542675f2d2acfd9e2b67dc73b8c3b54cf5a63
                               cand 16eb1581255912092d5f97e545affd2700c6ebfdf683e858668f4402bc7b96b5
  test_a5_route_1406.py        base ee0742df5b81525ecaa9176aa186ceff726ef7346b6fb0136f35e43cfb855d5e
                               cand 0125323ccb1b9601fa6ca2af9d7ed334080f36fcfc807371b7760cb7f2cb9a52
  test_harness_guards.py       base e87c0b7fba137074663381304e4f41bc9dfe4e1341406ecaf5e5e2b4c5c169ea
                               cand 292cda334e14449fd2d678650318219d2de5886e112dd555822e14d9965eb66c
  files differing in total: 6 (must be 6)

## attempts and raw exits
  base   exit=0      child exit 1  unique ids 207  collection errors 14  stable True
  cand   exit=0      child exit 1  unique ids 207  collection errors 14  stable True

## raw results, both sides
  0684fa693d2a0b20aab740599878c409be22d363dc62fe8b3f02e603ab8001f2  out_base/logs/attempt_base/ALIGNED_base.json
  8724327aa3f123b98d8e325791526e25947305ca91a8c3598794e9363b5403c7  out_base/logs/attempt_base/IDS_base.txt
  af890ffc61c57c1e033d141f66bda099b651fc1deb18af2cacf015779ffc54f2  out_base/logs/attempt_base/REGRESSION_base.txt
  a06abc431ff72c773639a5731b506fc84ac3af2896f5bf42bbdf8decd4f1e777  logs/attempt_base/stdout.txt
  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  logs/attempt_base/stderr.txt
  0767485c81987531b0ea18a8059684f0572302898f62f8994d99a452d4c9611c  out_cand/logs/attempt_cand/ALIGNED_cand.json
  8724327aa3f123b98d8e325791526e25947305ca91a8c3598794e9363b5403c7  out_cand/logs/attempt_cand/IDS_cand.txt
  52718b145beca618ddeb8623e16d3492a5a0bd2c26bab50d5f7b8f16ef4c4395  out_cand/logs/attempt_cand/REGRESSION_cand.txt
  15eb13d7bb70708a2aea5a4865671e0e838ef0858bab17977df6315cdb35950a  logs/attempt_cand/stdout.txt
  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  logs/attempt_cand/stderr.txt

## maps, identities, comparison, record
  69a1f520c14f3f899f8842cc3119ad92ff52ed584f5ad5fbf86f22dab3a618cd  map_1941_base.tsv
  af25da40bbc43529454c661602a03b0df78f8e0edf5337d225122468eeb5533d  map_1941_cand.tsv
  82b9d66eb848536d603693c305593070a7e02d9119968bf7ddd766a41a34e4e6  IDENTITIES_1941.md
  c0fc4922ac24f2340a14288bbeafc69f5962e1d68f5a1b1f6eb556acefdaf67b  COMPARISON_1941.json
  08a7d332257d3e566252750b221598ace8006f250f9fbbefa112e09094a5d3c2  WORK_RECORD.md
  9ca5b0bc68e92676afd04f9c7040f3102fbb9e5b176f8d5bd3e6121df7942fb6  ledger/a1_aligned_1941.py

## carried by reference, NOT rerun (accepted at their tested scope)
  unit_1939 freeze 10e36857c49f6106fcfef43a829574ee567c4cf1b65d5a07d041426239261c98
  iso_red/iso_g2, reload2, inv1 - see unit_1939_freeze/FREEZE_1939.md
