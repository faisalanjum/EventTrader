import hashlib, io, sys
H, S = sys.argv[1], sys.argv[2]
def reverse(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for old, new in pairs:  # reverse: new -> old
        assert s.count(new) == 1, (path.split("/")[-1], new[:50]); s = s.replace(new, old)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
aud = reverse(H + "/audit_worker_access.py", [
 ('''        prompts = blm.one_item_prompts(man.get("prompt_role"),
                                       man.get("contract_suffix"))''',
  '''        prompts = blm.one_item_prompts(man.get("prompt_role"),
                                       man.get("contract_suffix"),
                                       blm.plan_inventory(man))''')])
thg = reverse(H + "/test_harness_guards.py", [
 ('''    role = plan.get("prompt_role") if plan else None
    era = plan.get("contract_suffix") if plan else None
    got = subprocess.run(
        [_sys.executable, "-B", "-c",
         "import json,sys;sys.path.insert(0,%r);import build_launch_manifest as B;"
         "print(json.dumps(B.one_item_prompts(%r, %r)))" % (str(work), role, era)],''',
  '''    role = plan.get("prompt_role") if plan else None
    era = plan.get("contract_suffix") if plan else None
    inv = plan.get("inventory_path") if plan else None
    got = subprocess.run(
        [_sys.executable, "-B", "-c",
         "import json,sys;sys.path.insert(0,%r);import build_launch_manifest as B;"
         "print(json.dumps(B.one_item_prompts(%r, %r, %r)))" % (str(work), role, era, inv)],''')])
c1401 = reverse(H + "/test_a5_contract_1401.py", [
 ('''    real = BLM.INVENTORY
    doc = json.loads(io.open(real, encoding="utf-8").read())''',
  '''    real = A5.CORRECTED_INVENTORY_PATH                      # A5 serves the corrected inventory the key was built over
    doc = json.loads(io.open(real, encoding="utf-8").read())'''),
 ('''        BLM.INVENTORY = alt
        assert A5.inventory_problems(), "%s inventory was accepted" % how
        with pytest.raises(ValueError):
            A5.packets()
    finally:
        BLM.INVENTORY = real''',
  '''        A5.CORRECTED_INVENTORY_PATH = alt                  # a drifted corrected inventory no longer matches the provenance sha
        assert A5.inventory_problems(), "%s inventory was accepted" % how
        with pytest.raises(ValueError):
            A5.packets()
    finally:
        A5.CORRECTED_INVENTORY_PATH = real''')])
import json
io.open(S + "/pre_1514_reconstructed.json", "w").write(json.dumps({"audit_worker_access": aud, "test_harness_guards": thg, "test_a5_contract_1401": c1401}, indent=1))
print("audit_worker_access pre", aud[:16], "| test_harness_guards pre", thg[:16], "| test_a5_contract_1401 pre", c1401[:16])