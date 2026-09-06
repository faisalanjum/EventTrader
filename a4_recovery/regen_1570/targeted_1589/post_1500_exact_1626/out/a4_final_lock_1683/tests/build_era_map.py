# -*- coding: utf-8 -*-
"""Derive an ERA bind map: the base projection plus one scoped read-only
override per era owner file (Codex SEQ 1696 epoch rule).

A historical run is re-proved with ITS OWN era owner closure, not the final
one. Each era file overrides the bench copy AT THE PLACE THAT COPY ALREADY
OCCUPIES, found by its own relative path - so nothing here decides where a
module lives, the constructed bench does. Two placements for one relative path
is refused: that is genuinely ambiguous.

An era file the bench has never carried cannot be bound as a file: the bench is
itself a read-only bind, so a mountpoint that is not already there cannot be
made. When the era's whole directory is a byte-identical SUPERSET of the bench one -
every bench file present in it at the same bytes - the era DIRECTORY is bound
over that directory instead: one row, nothing of the bench hidden or altered,
and not one byte copied into the projection. An empty bench directory is just
the trivial case of that. Anything else is REPORTED,
not placed at a guessed location: with no bench copy there is no final byte for
it to shadow, so if the reconstruction ever reaches it the read raises instead
of silently running the wrong era.

Usage: build_era_map.py <era_owners_dir> <out_map_basename>
"""
import io
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
UNIT = (R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
            "/out/a4_final_lock_1683")
L = UNIT + "/launcher"
sys.path.insert(0, L)
import boundary                                          # noqa: E402

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
BENCH = UNIT + "/bench/bench_1306"
# The roots a bench file can legitimately occupy, as the owners' own imports
# reach them: the harness directory on sys.path, and the repository root the
# owners compute five levels above it.
ROOTS = [("/.claude/plans/Drivers/experiments/harness_g1v3", ), ("", )]

era_dir, out_name = os.path.realpath(sys.argv[1]), sys.argv[2]

rows = list(io.open(L + "/recon_map.tsv", encoding="utf-8").read().splitlines())
extra, absent, ambiguous = [], [], []

def superset(era_path, bench_path):
    """Every file the bench directory holds is in the era directory at the SAME
    bytes, so binding the era directory over it hides and changes nothing."""
    for f in sorted(os.listdir(bench_path)):
        bp = os.path.join(bench_path, f)
        ep = os.path.join(era_path, f)
        if not os.path.isfile(bp):
            return False
        if not os.path.isfile(ep) or boundary.file_sha(ep) != boundary.file_sha(bp):
            return False
    return True


dir_candidates, by_dir = {}, {}
for dp, _dn, fn in os.walk(era_dir):
    for f in sorted(fn):
        src = os.path.join(dp, f)
        rel = os.path.relpath(src, era_dir)
        # the root where this exact relative path already sits
        found = [r[0] for r in ROOTS if os.path.isfile(BENCH + r[0] + "/" + rel)]
        if len(found) > 1:
            ambiguous.append("%s: %d bench placements %s" % (rel, len(found), found))
        elif found:
            by_dir.setdefault(os.path.dirname(rel), []).append(
                "%s\t%s\t%s\t%s"
                % (S + "/bench_1306" + found[0] + "/" + rel, src,
                   boundary.source_sha(src), "ro"))
        else:
            # no bench copy: the whole directory may be bindable instead
            dir_candidates.setdefault(os.path.dirname(rel), []).append(rel)

for reldir, files in sorted(dir_candidates.items()):
    src = os.path.join(era_dir, reldir)
    # an EMPTY bench directory is a mountpoint and hides nothing
    roots = [r[0] for r in ROOTS
             if os.path.isdir(BENCH + r[0] + "/" + reldir)
             and superset(src, BENCH + r[0] + "/" + reldir)]
    if len(roots) == 1 and reldir:
        # one directory row REPLACES the per-file rows under it: binding both
        # would stack a second mount on every file for no added guarantee
        by_dir.pop(reldir, None)
        extra.append("%s\t%s\t%s\t%s"
                     % (S + "/bench_1306" + roots[0] + "/" + reldir, src,
                        boundary.source_sha(src), "ro"))
    else:
        absent.extend(files)

for rows_ in by_dir.values():
    extra.extend(rows_)

if ambiguous:
    for p in ambiguous:
        print("REFUSE " + p)
    sys.exit(1)

with io.open(L + "/" + out_name, "w", encoding="utf-8") as fh:
    fh.write("\n".join(rows + sorted(extra)) + "\n")
print("%s: %d base rows + %d era overrides" % (out_name, len(rows), len(extra)))
for rel in sorted(absent):
    print("   no bench counterpart, NOT bound (raises if reached): %s" % rel)
