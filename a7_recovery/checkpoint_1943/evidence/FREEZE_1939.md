# unit_1939 FREEZE — Codex SEQ 1939

## complete file manifest (written outside the tree it hashes)
  files 6336
  bytes 367048555
  manifest_digest c26c49b1325d5ae53e3bc76007e7b585a1db1f8ee8c33939cb34cdc460067ee9
  manifest file sha256   c26c49b1325d5ae53e3bc76007e7b585a1db1f8ee8c33939cb34cdc460067ee9

## attempts and raw exits
  base       exit=143  
  inv1       exit=0    7/7 -> True
  iso_g2     exit=0    3/3 -> True
  iso_green  exit=1    
  iso_red    exit=1    0/3 -> False
  reload1    exit=1    6/7 -> False
  reload2    exit=0    7/7 -> True

## every result file
  397273281699cb9a0f03b9b6f48dbff8860ba1b9bb9f7782dfc2b8d651e2e9c9  out_a/logs/attempt_inv1/FINALIZATION_inv1.json
  55b0605a3de6e2f9ad78ab39b6eced5381be410c7844325ae5ea0683905367a7  out_a/logs/attempt_inv1/INVALID_inv1.json
  be80730bd8b829cde23f8d4a2a39ed7bd15c7cacb267bd89c06b19fe2d64b2a4  out_a/logs/attempt_inv1/PROBLEMS_inv1.json
  68bea566bc4c2fa9542e8a0d14890c18e9948b358b5abb9b02a1485e38d507f4  out_a/logs/attempt_iso_g2/ISOLATION_iso_g2.json
  671449b5f68ebf921f476054695868e4289e4637b4213055f0290bc74b7f33ea  out_a/logs/attempt_iso_red/ISOLATION_iso_red.json
  ac9d9f6f1b7c6c538601882bccc94f957b255073ccb69cb83b2d56ccd2a81d8f  out_a/logs/attempt_reload1/A6_RENDER_reload1.txt
  bf5bd256b644cebe9d1fb4f392981e60556973b3323d96ffcbfa9ee191567d52  out_a/logs/attempt_reload1/a7_reference_inventory_reload1.json
  d7d1f37bf274122ad41fd4964035f172c11e7ae507d7046e766bed67663b46e7  out_a/logs/attempt_reload1/identity_reload1.json
  8babda02757369bed1b20f2684d12f844c403efa60ca30d52f05cc8b9728a5b5  out_a/logs/attempt_reload1/key_reload1.json
  fcac9373d20b24f62c858313e8b00252ac593c81f8c64dbb01d6c415036008cf  out_a/logs/attempt_reload1/meta_reload1.json
  136b50a3dbd74ad5a10eabda386b816aee1f88ff24cad20eeda54f52e226aa7a  out_a/logs/attempt_reload1/negative_problems_reload1.json
  0c7154fb6e0c0764daaf673f1d30e0f5ca242968571b29fd7c2bf233dc6c43c9  out_a/logs/attempt_reload1/reference_rows_reload1.json
  fba004221c7869aae2862b125744416c303be0701efb9a6a0fccd36a41468ff0  out_a/logs/attempt_reload1/RELOAD_reload1.json
  5ad634fe27001ef0dc8947521f26c562937b04945b2cbab1b8d5393d72c40c1f  out_a/logs/attempt_reload1/sidecar_reload1.json
  49173fd10457bad1b480035e643848db53b5f7b18e85b718b131f269961b2f41  out_a/logs/attempt_reload2/A6_ACCEPTED_reload2.json
  ac9d9f6f1b7c6c538601882bccc94f957b255073ccb69cb83b2d56ccd2a81d8f  out_a/logs/attempt_reload2/A6_LIVE_reload2.json
  bf5bd256b644cebe9d1fb4f392981e60556973b3323d96ffcbfa9ee191567d52  out_a/logs/attempt_reload2/a7_reference_inventory_reload2.json
  d7d1f37bf274122ad41fd4964035f172c11e7ae507d7046e766bed67663b46e7  out_a/logs/attempt_reload2/identity_reload2.json
  8babda02757369bed1b20f2684d12f844c403efa60ca30d52f05cc8b9728a5b5  out_a/logs/attempt_reload2/key_reload2.json
  fcac9373d20b24f62c858313e8b00252ac593c81f8c64dbb01d6c415036008cf  out_a/logs/attempt_reload2/meta_reload2.json
  136b50a3dbd74ad5a10eabda386b816aee1f88ff24cad20eeda54f52e226aa7a  out_a/logs/attempt_reload2/negative_problems_reload2.json
  0c7154fb6e0c0764daaf673f1d30e0f5ca242968571b29fd7c2bf233dc6c43c9  out_a/logs/attempt_reload2/reference_rows_reload2.json
  3667229322595d8f03f19111e5330c5e551706655924fd20906266778966090d  out_a/logs/attempt_reload2/RELOAD_reload2.json
  5ad634fe27001ef0dc8947521f26c562937b04945b2cbab1b8d5393d72c40c1f  out_a/logs/attempt_reload2/sidecar_reload2.json

## runtime owners now
  7d427f095f775cc3c706640880b893d2c29c7638233d23b3f52b2ce91d8e72ed  build_a5_exp5_kit.py
  1fef8789ae0d0392b4c50d8c22b81feb6dbe97cbc3d2e5a66ff35964df24f7d7  a7_g1_build.py
  6ba1218c397191360ee4ea5705c26ce6d0ac6e3b7763baa716105f4d6c022235  a7_key_correction.py
  16eb1581255912092d5f97e545affd2700c6ebfdf683e858668f4402bc7b96b5  a7_reference_inventory.py
  4fce0781e770ce48ca51b6d2b0a412b3357a49ba668160604a88eb39dc738b40  a7_g23_build.py
  5d83bf326f5d7d2dd6ddc143203c30f3a83f51a0c4c5f8bdf792c525521937e9  build_kfields_final.py
  df19a68b6ea661af5365c6ec95a62194e738658e2dcd743996b506e49d1553ed  build_kfields_key.py
  bbcba73d587a2bc2e8fc34ce27ba555065b52d89480783b2440568cede19c4b2  a6_launch_freeze.py
  43dcbd35d95d31123741f77f81e41599497101807790649cf7b1167651130751  a7_prepared_run.py

## test fixtures changed this round
  0125323ccb1b9601fa6ca2af9d7ed334080f36fcfc807371b7760cb7f2cb9a52  test_a5_route_1406.py (candidate)
  ee0742df5b81525ecaa9176aa186ceff726ef7346b6fb0136f35e43cfb855d5e  test_a5_route_1406.py (baseline)
  292cda334e14449fd2d678650318219d2de5886e112dd555822e14d9965eb66c  test_harness_guards.py (candidate)
  e87c0b7fba137074663381304e4f41bc9dfe4e1341406ecaf5e5e2b4c5c169ea  test_harness_guards.py (baseline)

## maps
  f8132abafcdf6c029b2512e49c5c8594360d09ba7b7cbc7390915a734dbfe693  map_1939a.tsv (107 rows)
  1b3912c814290f3a1164c88b32ce5e06438ee9e529fcd295efdf4f577a49e62f  map_1939_base.tsv (107 rows)

## approval pins
  df67408054ca7ecf20c8fcbb94ee0c26c73002ee129aca46b2b7fd3a292634dc  approved_key/a4_final_key_lock.json
  ab1620e1a5e9d170bca999a1113b3a830ead37943ccaf7f18199a0096ad8635f  approved_key/a4_final_key_lock_receipt.json
  4b45dd36e2a4c23603bc3e501c4bc3709a45b459e813cd638912dcb796befedc  approved_key/ordinary_bound.json

## reused surviving runs (not regenerated)
  mut5/positive  204 answers
  mut5/m3        203 answers

## comparison
  5fc1693aa8ac3e5c1e8c78df877e75da8ecd732bc771e23180ce3b9c8fc60ff4  WORK_RECORD.md
