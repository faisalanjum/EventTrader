import io, sys
p = sys.argv[1] + "/lock/check_final_key_candidate.py"; s = io.open(p, encoding="utf-8").read()
old = '''    for sid in composed:
        assert json.dumps(prov[sid]["base_row_order"]) in head and json.dumps(prov[sid]["targeted_row_order"]) in head
'''
new = '''    shown = json.loads(head.split("[COMPOSITION MAP]\\n", 1)[1].split("\\n\\n[ROLE]", 1)[0])   # the trusted map, exactly as the signer reads it
    assert list(shown) == composed
    for sid in composed:
        assert shown[sid]["base_row_order"] == prov[sid]["base_row_order"] and shown[sid]["targeted_row_order"] == prov[sid]["targeted_row_order"]
        assert shown[sid]["replaced"] == prov[sid]["replaced"] and shown[sid]["base_raw_sha256"] == prov[sid]["base_raw_sha256"] and shown[sid]["targeted_raw_sha256"] == prov[sid]["targeted_raw_sha256"]
'''
assert s.count(old) == 1; io.open(p, "w", encoding="utf-8").write(s.replace(old, new)); print("test fixed")
