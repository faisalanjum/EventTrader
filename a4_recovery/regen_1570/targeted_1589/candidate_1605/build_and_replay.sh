#!/bin/bash
# Two more clean worlds from the candidate tree ALONE (Codex SEQ 1603 item 5 / 1605 item 4): the committed
# regen_1570 tree at HEAD plus the unit's candidate inputs, exported fresh; the unit's wrapper (worlds A and B)
# and, as the affected regression, the phase-1 wrapper (its own worlds A and B) run from the export with the
# in-place untracked siblings masked. Nothing here writes into the in-place tree.
set -u
CK="$(cd "$(dirname "$0")" && pwd)"; T1="$(cd "$CK/.." && pwd)"; REPO="$(cd "$T1/../../.." && pwd)"; E="$CK/export${EXPORT_TAG:-}"; L="$CK/replay_logs${EXPORT_TAG:-}"
[ -e "$E" ] && { echo "export already present"; exit 2; }
mkdir -p "$E" "$L"
git -C "$REPO" archive HEAD a4_recovery/regen_1570 | tar -x -C "$E" || exit 3
/home/faisal/EventMarketDB/venv/bin/python3 -B "$CK/list_candidate.py" > "$CK/CANDIDATE_INPUTS${EXPORT_TAG:-}.tsv" || exit 3
nv=0
while IFS=$'\t' read -r p h n c; do
  mkdir -p "$E/$(dirname "$p")" && cp -p "$REPO/$p" "$E/$p" || exit 3
  for f in "$REPO/$p" "$E/$p"; do [ "$(sha256sum "$f" | cut -c1-64)" = "$h" ] && [ "$(stat -c %s "$f")" = "$n" ] || { echo "copy of $p is not the manifest row"; exit 3; }; done
  nv=$((nv+1))
done < "$CK/CANDIDATE_INPUTS${EXPORT_TAG:-}.tsv"
echo "copied and verified $nv manifest rows (source and copy equal each row's sha256 and size)"
echo "export: $(find "$E" -type f | wc -l) files, candidate inputs $(wc -l < "$CK/CANDIDATE_INPUTS${EXPORT_TAG:-}.tsv")"
export MASK_EXTRA="$T1/targeted_run_1491 $T1/checkpoint_1600"
EU="$E/a4_recovery/regen_1570/targeted_1589/targeted_run_1491"; EP="$E/a4_recovery/regen_1570/targeted_1589/phase1_targeted_1488"
echo "== UNIT REPLAY $(date +%T)"; (cd "$EU" && bash run_1491.sh > "$L/run_1491.log" 2>&1); r1=$?; grep "RESULT\|GATE\|passed\|failed\|diff rc\|== DONE" "$L/run_1491.log" | tail -8
echo "== PHASE1 REGRESSION $(date +%T)"; (cd "$EP" && bash run_phase1_1488.sh > "$L/phase1.log" 2>&1); r2=$?; grep "RESULT\|GATE\|passed\|failed\|diff rc\|== DONE" "$L/phase1.log" | tail -8
echo "== COMPARE $(date +%T)"
diff -rq "$T1/targeted_run_1491/out/attempt6/A" "$EU/out/attempt6/A" > "$L/COMPARE_unit_A.txt" 2>&1; c1=$?; echo "unit A in-place vs export: diff rc=$c1 ($(wc -l < "$L/COMPARE_unit_A.txt") lines)"
diff -rq "$T1/targeted_run_1491/out/attempt6/B" "$EU/out/attempt6/B" > "$L/COMPARE_unit_B.txt" 2>&1; c2=$?; echo "unit B in-place vs export: diff rc=$c2"
: > "$L/PHASE1_VS_HEAD.tsv"; nd=0
while read -r f; do rel="${f#$E/}"; hs=$(git -C "$REPO" show "HEAD:$rel" 2>/dev/null | sha256sum | cut -c1-64); ws=$(sha256sum "$f" | cut -c1-64); st=same; [ "$hs" = "$ws" ] || { st=DIFF; nd=$((nd+1)); }; printf '%s\t%s\t%s\t%s\n' "$rel" "$hs" "$ws" "$st" >> "$L/PHASE1_VS_HEAD.tsv"; done < <(find "$EP/out/attempt5" -type f | sort)
echo "phase1 regenerated vs HEAD: $(wc -l < "$L/PHASE1_VS_HEAD.tsv") files, $nd differ: $(awk -F'\t' '$4=="DIFF"{print $1}' "$L/PHASE1_VS_HEAD.tsv" | xargs -n1 basename 2>/dev/null | tr '\n' ' ')"
names=$(awk -F'\t' '$4=="DIFF"{print $1}' "$L/PHASE1_VS_HEAD.tsv" | sort | tr '\n' ' ')
want="a4_recovery/regen_1570/targeted_1589/phase1_targeted_1488/out/attempt5/A_tests.txt a4_recovery/regen_1570/targeted_1589/phase1_targeted_1488/out/attempt5/reaudit.strace "
echo "== REPLAY DONE $(date +%T) unit=$r1 phase1=$r2 cmpA=$c1 cmpB=$c2 phase1_diff=$nd"
[ $r1 -eq 0 ] && [ $r2 -eq 0 ] && [ $c1 -eq 0 ] && [ $c2 -eq 0 ] && [ "$names" = "$want" ] || { echo "REPLAY FAIL-CLOSED"; exit 9; }
echo "REPLAY PASS"; exit 0
