# A4 recovery - the signed checkpoint and how to hand it on

## What this snapshot is

A4 is recovered, signed and LOCKED. Every build, harvest and lock operation is
write-once and REFUSES a second run on this snapshot.

    lock               63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0
    lock receipt       7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3
    key identity       df5f8bbca0c052242a174f0805d6129d8dfd869f7db1af1d3d33a545fab094ca
    sidecar            e07ab7d05ce7a53f82bc0dd9eaad5615231c6f6cd743ebf6f7c402c0f11f7a84
    provenance         c17a37a4076cfba2b59881b87fee04021eaafcac59c58b52efd7f21ab94d453a
    validator receipt  a0e7c9d795fb52e0c5a9c9d59abfdb45d0203d999c27f652bc2a1e45932424dd
    signer prompt      04154f1b1bc282e58512d7bf75e1185e9c9644b1f3ee2515476703b3cc68688f
    signer launcher    7b190f48b8d7d6bfbe97d4b20f953926c682d6caf33a319a692137bb67579969
    signer manifest    45875261763f310ce43e68729b22e63fe764e9acfe34c6f731fff5058ef5e87d
    signer raw         fd57049fdc9df15247094ec869feba546c2410bd1eea57a7a740543738c86aeb
    signer evidence    0f87db538214dcd9106b4918c448129353e686527cb7408de388cc18230173a0
    signer reply       342afdcf00ae76ae3798b45c73283612910412a6bfb4e6a7ccbeb81edc1802a7
    round 1 binding    b1f516f6217ca05fae8bcb6af3b2f5ac3b259ab3ed571f09f79ef2a516ec48fd
    round 2 binding    fe3e6e03f9444aa238f1d110415e832b209546c1457e5dadb86d086b7c93e499
    round 3 binding    5f2b167deb5a5159a058a2027564f70d69dcdada1b9be11388fb8853c9754257

    call accounting    5219 -> 5220 (1 signer call, 0 retries), ceiling 6000
    manifest and seal: see FREEZE_1743/SEAL.json

## Check the checkpoint (builds nothing, changes no frozen byte)

    cd /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683
    A4_ROUND=3 A4_STEPS=verify_checkpoint \
      A4_A6=f0d7b8281ae13bc8184be34253bf0236132c1900f60db574d005ae018880d4de \
      bash tests/run_a4.sh

It re-hashes the ten bound inputs, the lock and its receipt, runs the lock
owner's own verify() on the live bytes and prints the call accounting.

WHAT THAT COMMAND WRITES, exactly - it is read-only about the ANSWER, not about
the run's own bookkeeping:

    logs/a4_<timestamp>.log        a NEW file each time
    launcher/a4_final_map.tsv      rebuilt from the same sources (re-measured)
    out/ARTIFACTS.tsv              rewritten by the preservation step

Nothing else changes: the candidate, the signer packet, the lock, the receipt,
the bindings, the run directories and every earlier log stay byte-identical, so
the manifest rows for those three bookkeeping files are the only ones expected
to move. To check without writing anything at all, verify the manifest instead:

    /home/faisal/EventMarketDB/venv/bin/python3 -B - <<'EOF'
    import hashlib, io
    R = '/home/faisal/EventMarketDB-driver-recovery'
    man = 'a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/FREEZE_1743/MANIFEST.sha256'
    bad = 0
    for line in io.open(R + '/' + man, encoding='utf-8').read().splitlines()[1:]:
        path, want, _n = line.split('\t')
        got = hashlib.sha256(io.open(R + '/' + path, 'rb').read()).hexdigest()
        bad += (got != want)
    print('manifest rows checked, mismatched', bad)
    raise SystemExit(1 if bad else 0)
    EOF

## If the original transcript is ever missing

The package carries a lossless gzip; the original is never touched by this. It
verifies an existing original, REFUSES a differing one, and publishes a restored
one only after the decompressed bytes hash to the expected value:

    T=/home/faisal/EventMarketDB-driver-recovery/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl
    GZ=/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/evidence/transcript/accepted_prefix.jsonl.gz
    WANT=d191941462674e63f16370104478a1e0774b88cbb953b8133a6face8353c1d93
    if [ -e "$T" ]; then
      if [ "$(sha256sum "$T" | cut -d' ' -f1)" = "$WANT" ]; then
        echo "present and correct - left unchanged"
      else
        echo "REFUSED: $T exists and differs - left unchanged" >&2; exit 1
      fi
    else
      mkdir -p "$(dirname "$T")" || exit 1
      TMP="$(mktemp "$(dirname "$T")/.accepted_prefix.XXXXXXXX")" || exit 1
      if gunzip -c "$GZ" > "$TMP" &&
         [ "$(sha256sum "$TMP" | cut -d' ' -f1)" = "$WANT" ]; then
        mv -n "$TMP" "$T"
        if [ -e "$TMP" ]; then
          rm -f "$TMP"
          echo "REFUSED: $T appeared while restoring - left unchanged" >&2; exit 1
        fi
        if [ "$(sha256sum "$T" | cut -d' ' -f1)" = "$WANT" ]; then
          echo "restored $T"
        else
          echo "REFUSED: the published bytes are not $WANT" >&2; exit 1
        fi
      else
        rm -f "$TMP"
        echo "REFUSED: the compressed copy does not give $WANT" >&2; exit 1
      fi
    fi

## The recovery-side tests (absolute paths; no boundary needed)

    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_build_wrapper_refusal.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_stage_propagation.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_recovery_wrappers_1741.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_placement_rules.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_freeze_gates_1742.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_boundary_checks_1743.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_handoff_command_1744.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/test_final_safety_1745.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/a4_owner_1726/tests/test_extraction_1726.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/a4_owner_1726/tests/test_missed_writes_1727.py
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/a4_owner_1726/tests/test_mixed_command_1728.py

## The next lawful gate

1. Codex verifies this complete snapshot.
2. Then staging only, of exactly the roots in FREEZE_1743/WHITELIST.tsv, for his
   staged-identity review; then the scoped commit and the normal push.
3. Then A5, in order. Nothing is staged now.

## History - how it was reconstructed. DO NOT RE-RUN on this snapshot.

The completed operations refuse a second run; these lines record what happened.

    2026-09-05T23:27:01	build_kfields_final_targeted.py	8f1cba41a27727a211d088a499c9f4c3394dd67e551208d4cb9c670ef90316d9	960ebdeb250845058d052680b216524cd3d50c5c83a68bb1e62c0f322717a7dc	a4_owner_1726/proved/build_kfields_final_targeted.960ebdeb.py
    2026-09-05T23:30:19	build_kfields_final_targeted.py	960ebdeb250845058d052680b216524cd3d50c5c83a68bb1e62c0f322717a7dc	cdd008c128f875c5e5154fbf4d350a91e1b9102f6b1032ce0bc6e4e3312f0015	a4_owner_1726/proved/build_kfields_final_targeted.cdd008c1.py
    2026-09-06T00:31:47	build_kfields_final_targeted.py	cdd008c128f875c5e5154fbf4d350a91e1b9102f6b1032ce0bc6e4e3312f0015	fb7c820d765565cc19722938caeb8f8f5e4bdefa9c19a0443c48398fda20113d	a4_owner_1726/proved/build_kfields_final_targeted.fb7c820d.py

    round 2  review_receipt_1505 build_package prepare_1506 record_round1_states finalize_round1 bind_1506 ledger_check(5217)
    round 3  review_receipt_1507 review_receipt_1508 budget_receipt_1508 build_package prepare_1509
             record_round1_states finalize_round1 evidence_1509 bind_1509 ledger_check(5219)
    closure  build_final_candidate harvest_final_sign_run check_final_key_candidate build_final_key_lock_run

    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/seed_runs_rw.py a4_final_targeted_corr2_run_1506
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/seed_runs_rw.py a4_final_targeted_corr3_run_1509
    /home/faisal/EventMarketDB/venv/bin/python3 -B /home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/tests/seed_runs_rw.py a4_final_targeted_corr_run_1504

