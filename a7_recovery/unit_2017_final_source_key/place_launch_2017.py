# -*- coding: utf-8 -*-
"""Codex SEQ 2017: make the 33 prepared requests CALLABLE, still uncalled.

The same fix that served the four reviews: each durable script is copied, byte
for byte, to the launch path the runtime can open, and one extra read-only row
pins that path to the durable directory so the boundary proves the two are the
same bytes. NOTHING IS LAUNCHED HERE.

Usage: place_launch_2017.py <record.json> <scripts_dir> <launch_dir>
                           <map_in.tsv> <map_out.tsv>
"""
import hashlib
import io
import json
import os
import shutil
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570"
                   "/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
import boundary                                                    # noqa: E402

RECORD, SCRIPTS, LAUNCH, MAP_IN, MAP_OUT = sys.argv[1:6]


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


record = json.loads(io.open(RECORD, encoding="utf-8").read())
pinned = {os.path.basename(i["scriptPath"]): i for i in record["invocations"]}
assert sorted(pinned) == sorted(os.listdir(SCRIPTS)), (sorted(pinned),
                                                       sorted(os.listdir(SCRIPTS)))
os.path.isdir(LAUNCH) or os.makedirs(LAUNCH)
assert not os.listdir(LAUNCH), "the launch directory is not fresh: " + LAUNCH
placed = []
for name, inv in sorted(pinned.items()):
    durable = os.path.join(SCRIPTS, name)
    assert fsha(durable) == inv["script_sha256"], durable
    target = os.path.join(LAUNCH, name)
    shutil.copyfile(durable, target)
    assert io.open(target, "rb").read() == io.open(durable, "rb").read(), target
    assert fsha(target) == inv["script_sha256"], target
    placed.append({"label": inv["label"], "launch_path": target,
                   "durable_path": durable, "script_sha256": fsha(target)})

rows = boundary.read_map(MAP_IN)
assert not [r for r in rows if r["logical"] == LAUNCH]
rows.append({"logical": LAUNCH, "source": SCRIPTS,
             "sha": boundary.source_sha(SCRIPTS), "mode": "ro"})
bad = boundary.validate(rows)
assert not bad, bad
with io.open(MAP_OUT, "x", encoding="utf-8") as fh:
    fh.write("".join("\t".join(r[k] for k in ("logical", "source", "sha", "mode"))
                     + "\n" for r in rows))
print(json.dumps({"launch_dir": LAUNCH, "map": MAP_OUT,
                  "map_sha256": fsha(MAP_OUT),
                  "scripts_dir_sha256": boundary.source_sha(SCRIPTS),
                  "placed_count": len(placed), "placed": placed,
                  "launched": 0}, indent=1))
