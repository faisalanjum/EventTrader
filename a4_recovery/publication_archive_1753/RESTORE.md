# Exact original history of this branch

Publishing this branch required compressing two log files; nothing else changed.
Eight commit IDs changed as a result. `COMMIT_MAP.tsv` maps all fifteen.
Every test record in this repository names the ORIGINAL commit IDs. Those tests
were never re-run against the published IDs.

## What is in this directory

    a4_exact_history.bundle.part0   the original-history Git bundle, first half
    a4_exact_history.bundle.part1   the same bundle, second half
    COMMIT_MAP.tsv                  original commit id -> published commit id

## Identities, for checking against; not steps to run

    part0                     76298537 bytes  3ee57251e15b51d9527b8aaa46cde670fa543598e25ae4bde8f24b0178a4054d
    part1                     76298536 bytes  4cc3b0e96eb9e6203bd963ff9383105301e3801c27c4f332e8f2bbbddb81473d
    a4_exact_history.bundle  152597073 bytes  dd5ea9d6754d2059c264d615b2af748d281bad3830da472365f0a212400929d9
    original tip              329b65cdbe9320af15057c0ef4545e2bb354381b
    original tip tree         ac493488a588406a0819c3e90fa64c3ea017f8d8
    required base             cd961e51d55bf13aa9311b79c5d7eca20e9b11cc   already published

## A. Rebuild the bundle, and check it before importing anything

Run A then B from the root of this published working copy in one Bash shell.
DEST must not already exist; any command failure stops the procedure.

    set -euC -o pipefail
    SRC=$(pwd)
    DEST=/home/faisal/EventMarketDB-driver-restored-history-1753
    mkdir "$DEST"
    cat "$SRC/a4_recovery/publication_archive_1753/a4_exact_history.bundle.part0" \
        "$SRC/a4_recovery/publication_archive_1753/a4_exact_history.bundle.part1" \
        > "$DEST/a4_exact_history.bundle"
    ( cd "$DEST" && echo "dd5ea9d6754d2059c264d615b2af748d281bad3830da472365f0a212400929d9  a4_exact_history.bundle" | sha256sum -c - )

The last line must print OK. If it does not, stop here and import nothing.
A truncated bundle still passes `git bundle verify`, and only the real import in
part B detects the damage, so this checksum is the gate.

## B. Import the original commits

This is the sequence that was tested and accepted. The base is transferred out of
this repository by an ordinary local Git fetch; no object store is shared.

    git init -q "$DEST/orig"
    git -C "$DEST/orig" fetch --depth=1 \
        --upload-pack='git -c uploadpack.allowReachableSHA1InWant=true upload-pack' \
        "file://$SRC" cd961e51d55bf13aa9311b79c5d7eca20e9b11cc
    git -C "$DEST/orig" update-ref refs/heads/base FETCH_HEAD
    git -C "$DEST/orig" fetch "$DEST/a4_exact_history.bundle" \
        refs/heads/recovery/a3-a7-verified:refs/heads/recovery/a3-a7-verified
    git -C "$DEST/orig" fsck --full --strict

In "$DEST/orig", refs/heads/base is then the published base and
refs/heads/recovery/a3-a7-verified is the original tip listed above.

## C. Recover either original log file

Run from the root of an isolated checkout of this published branch in Bash.
OUTDIR must be fresh; command failures and existing output files stop the procedure.

    set -euC -o pipefail
    OUTDIR=/home/faisal/EventMarketDB-driver-restored-traces-1753
    mkdir "$OUTDIR"
    mkdir -p "$OUTDIR/a4_recovery/regen_1570/foundation/out/11" \
             "$OUTDIR/a4_recovery/regen_1570/foundation/out/12"
    gzip -dc a4_recovery/regen_1570/foundation/out/11/closure.strace.gz \
        > "$OUTDIR/a4_recovery/regen_1570/foundation/out/11/closure.strace"
    gzip -dc a4_recovery/regen_1570/foundation/out/12/closure.strace.gz \
        > "$OUTDIR/a4_recovery/regen_1570/foundation/out/12/closure.strace"

Each file lands under OUTDIR at its own original path. Expected results:

    out/11/closure.strace  157809451 bytes  a07bf8f76b5553bcc2c2ec3d2db7e493af66b1622834c2d5bb39ec7afc88ba0d
    out/12/closure.strace  157809449 bytes  16eea8589c79a0c90cb8e8360581893920eecf5ec7c9fda118df2e8c13f236d2
