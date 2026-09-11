# -*- coding: utf-8 -*-
"""Codex SEQ 2010 step 3: prove the originals are untouched and the private
copy is still the original. READ-ONLY; writes nothing, calls nothing.
"""
import collections, hashlib, io, json, os, sys
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
U = A + "/unit_2010_native_fixture"
BND = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
       "targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
sys.path.insert(0, BND)
import boundary                                                   # noqa: E402

fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
man = json.loads(io.open(U + "/NATIVE_FIXTURE_MANIFEST.json",
                         encoding="utf-8").read())

res = collections.OrderedDict()
res["manifest_sha256"] = fsha(U + "/NATIVE_FIXTURE_MANIFEST.json")
res["map_sha256"] = fsha(U + "/map_native_2010.tsv")
res["private_native_dir"] = boundary.dir_manifest_sha(U + "/native")
res["states_by_scope"] = man["states_by_scope"]
res["copied_files"] = man["copied_files"]

src_bytes = src_mtime = priv_bytes = 0
bad = []
for row in man["files"]:
    s, p = row["source"], row["private"]
    if not os.path.isfile(s):
        bad.append((s, "original gone")); continue
    if fsha(s) == row["sha256"]:
        src_bytes += 1
    else:
        bad.append((s, "original bytes moved"))
    if str(os.stat(s).st_mtime_ns) == row["source_mtime_ns"]:
        src_mtime += 1
    else:
        bad.append((s, "original mtime moved"))
    if os.path.isfile(p) and fsha(p) == row["sha256"]:
        priv_bytes += 1
    else:
        bad.append((p, "private copy is not the original"))

res["originals_bytes_unchanged"] = src_bytes
res["originals_mtime_ns_unchanged"] = src_mtime
res["private_equals_original"] = priv_bytes
res["problems"] = bad[:5]
# the private store holds ONLY what the manifest names
on_disk = sum(len(f) for _d, _s, f in os.walk(U + "/native"))
res["files_on_disk_under_private_root"] = on_disk
res["private_root_holds_only_manifest_files"] = on_disk == man["copied_files"]
res["ok"] = (not bad and src_bytes == src_mtime == priv_bytes
             == man["copied_files"]
             and res["private_root_holds_only_manifest_files"])
print(json.dumps(res, indent=1, default=str))
raise SystemExit(0 if res["ok"] else 3)
