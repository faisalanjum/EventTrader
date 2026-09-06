# A4 recovery - exact restart

Every stage runs inside the existing private boundary through the one runner. The stage
names are the pipeline's own; `A4_STEPS` runs exactly those, in the order named.

    U=/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683
    cd $U

Round 2 (already complete; ledger 5217):

    A4_ROUND=2 A4_STEPS=review_receipt_1505,build_package,prepare_1506 bash tests/run_a4.sh
    python3 -B tests/seed_runs_rw.py a4_final_targeted_corr2_run_1506
    A4_ROUND=2 A4_STEPS=record_round1_states,finalize_round1 bash tests/run_a4.sh
    A4_ROUND=2 A4_STEPS=bind_1506 bash tests/run_a4.sh
    A4_ROUND=2 A4_STEPS=ledger_check A4_LEDGER=5217 \
      A4_A6=f323b7bcf7aabbb13b2a2d7e0ab495a7c3b8b36128db9d6059575633aecc15a0 bash tests/run_a4.sh

Round 3 (already complete; ledger 5219). The era owner is placed first:

    python3 -B tests/place_era_owner.py build_kfields_final_targeted.py <960ebdeb...>   # 1507 receipt
    A4_ROUND=3 A4_STEPS=review_receipt_1507 bash tests/run_a4.sh
    python3 -B tests/place_era_owner.py build_kfields_final_targeted.py <cdd008c1...>   # 1508 onward
    A4_ROUND=3 A4_STEPS=review_receipt_1508,budget_receipt_1508,build_package,prepare_1509 bash tests/run_a4.sh
    python3 -B tests/seed_runs_rw.py a4_final_targeted_corr3_run_1509
    A4_ROUND=3 A4_STEPS=record_round1_states,finalize_round1,evidence_1509 bash tests/run_a4.sh
    A4_ROUND=3 A4_STEPS=bind_1509,ledger_check A4_LEDGER=5219 \
      A4_A6=f0d7b8281ae13bc8184be34253bf0236132c1900f60db574d005ae018880d4de bash tests/run_a4.sh

Closure (already complete; lock written once):

    python3 -B tests/place_era_owner.py build_kfields_final_targeted.py <fb7c820d...>
    A4_ROUND=3 A4_A6=f0d7b8281ae13bc8184be34253bf0236132c1900f60db574d005ae018880d4de \
      A4_STEPS=build_final_candidate,harvest_final_sign_run,check_final_key_candidate,build_final_key_lock_run \
      bash tests/run_a4.sh

The lock stage refuses if the lock already exists: it is written once.

Recovery-side tests (no boundary needed):

    python3 -B tests/test_build_wrapper_refusal.py
    python3 -B tests/test_stage_propagation.py
    python3 -B tests/test_recovery_wrappers_1741.py
    python3 -B tests/test_placement_rules.py
