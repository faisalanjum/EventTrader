# -*- coding: utf-8 -*-
"""Codex SEQ 1663/1664: exact three-epoch recovery of the persistent harness_g1v3/a7_g1_build.py owner
(sha256 e4fa07d0) plus complete, fail-closed derivation evidence, in a no-real-I/O in-memory state.
No recursive sibling resolver in any epoch: every owner mutation is the exact recorded target operation
(Edit/Write/program/heredoc splice/sed) or, for a multi-file record whose program reads an unreconstructable
sibling, the single exact recorded owner replacement (Codex-selected index, derived by AST literal eval).
Gates VALIDATE only (full 64-char equality), never select. Result identities are bound exactly: every
same-id tool result is collected, and a manifest/mention row requires a nonempty id with exactly one later
same-id result (no duplicate/earlier). Fail-closed: any gate/length/anchor/binding/census mismatch writes no
candidate and reports the first gap. Imports no recovered/live harness module; edits no A3 engine or prior unit."""
import ast, hashlib, io, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
LG = "/home/faisal/EventMarketDB-driver-recovery/a3_recovery/regen_1541/ledger"
CACHE = "/home/faisal/EventMarketDB-driver-recovery/a3_recovery/regen_1541/sibling_cache"
ENGINE = {"chrono_replay.py": "72d19c4333990c6349dae8aad7fc53615e99f5386d999307e8aa7706184cac1a",
          "replay_transcript.py": "48ba1c900f90e9f9d5fe2199c166791c78c8587e683fdf128b279668c1e09d0a"}
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
OWN = "a7_g1_build.py"
LOG = []
def note(m): LOG.append(m)
def fail(gap):
    note("FAIL: " + gap)
    io.open(HERE + "/DERIVATION_REPORT.txt", "w").write("\n".join(LOG) + "\n")
    print("FAIL CLOSED:", gap); sys.exit(2)

# ---------- Codex-adjudicated record sets; expected per-record hashes are full 64-char, compared by equality ----------
E1_SEQ = [57521,57530,57534,57609,57613,57650,57918,57923,57935,57960,57967,57979,57983,58050,58265,
          58274,58328,58584,58588,58613,58629,58658,58853,58861,58902,59198,59214,59225,59246,59273,
          59767,60334,60525,60592]                       # 58853 is the side producer (no owner change)
E1_CHAIN = {57521:"bb31131f733a34b0945bc6b138acf0081080eeb5ce2166f1597fc47f20a45a2c", 57530:"5f5aac5db8b71aa0843591ec020270edd2d4bdaebf4b92e138fe1fae0e2f5990", 57534:"4c9a915d53095801a435651d6ad82cb707e8de49f9cebccd4feb88fa0e48e905", 57609:"0831f8f7a2d4f52bc98667ec8cb399a4101180425fb0d3566d2f80e1fc2b498f", 57613:"02d710d217a8850ac443516195dc0ecff23f2cd0f1d1af22099c76154178ab13", 57650:"8a9c677eb525c0bb9cc0d9f7d6af04b18a921d2a8a5e19a97e4a68969c4dffe9", 57918:"1c1b166c13b33456f6ad8b4ce6a4aa9ba891b05592de266edcb8ca014344ee48", 57923:"f20dd8566f615c82b1e1ab7fb7b2f35d79c5fac0c16f8016788bf248ec7354bf", 57935:"cafd53b8422c314bf07e4797a47ff8325deca5e55bd1419c58516f6b68453de0", 57960:"ab37fb6f70e8a432d49b12700e41618b9c430c057d98c9801053859957d73609", 57967:"0878f07433c6044758ca0937131b746e6c3aff73d370f2154661c91bfb5cd95d", 57979:"14d028deb7c2b9a9764c61c1b3f2f7d550f7650aa1348a99bdf0849a4b2e25c7", 57983:"4b3a66b6154842a4018e1b05b4a45d309de99a0914d7bb50f173bbaba381d3bb", 58050:"b6baa9e49f16d972b5d59d27b002496e7f5ef0be6050c5f69422bca0b166113f", 58265:"6830e823b19a1557c82cd159696efd16d8ff4479570ce318df1637ad9f88b54a", 58274:"982db5ae2a0b3091dfdf8694d18a32438129c72202fe0cf8abc2193033ee843d", 58328:"f91c832365802485d1ed3b42ce823427ccb2264751ba4591ec6cc51948708290", 58584:"73afe5c0c1a021996c9837e9d56dcb501349ca23c412fad2267877b2b5c2ca96", 58588:"ea2abba7b1ef56f0b97097a310dfaf05ecec7c0c183a31fcfbc95b2cb855cb16", 58613:"f95f99964364cd648380ed3020656697ba5c0bbc49181ab6e0da851ed31d2b34", 58629:"38b221ae889cc64f2ba96ad7cf2d5f9bcffeceaca9fefb8d8b9448e65b36d266", 58658:"5b462a2e2ec33de415df3a427bd90e5110c1c968a422675f1a7168d00083dd18", 58853:"5b462a2e2ec33de415df3a427bd90e5110c1c968a422675f1a7168d00083dd18", 58861:"c1aa3bc23e3afc62f582a20e10ec44c67595a102cc3ebf6accf3b3f667938f70", 58902:"b6d2f45a882fd06308643bfa2ab92fdd53ea925d0a38ceba1197fd0b60ad7028", 59198:"3832fce08c2cf5753f1248ec2daf9cd4d755cfcd359042e1a4469e72d06a56ab", 59214:"3d526b9027d0c6bea296f3a808278022ab787e6b2a020e3ca01ae2a7050ee6f0", 59225:"99f03b51a09eaddd20bcea8529456cfbdb8ba38a25052e55b819ec62b23e5a09", 59246:"791c61a7fbe62fd76074edf653832a5badcc29b3a5186481288a90d3cc33b52c", 59273:"43a18d2ff00c2ee9386c9b16f2ab14d03e4622fbdb4735fac0049dd4c1c7687b", 59767:"1d957fa4f59187d36cc55421a1da933fe477a63c09d596f9a87e5a1ff2198c10", 60334:"c7dc99b47288fa0ed66d3c8f0c88211d812ddd9a9560732fd216e53614ed25b7", 60525:"a7d9979d6b049b728bea07f8fa641873b50593d28c58358792a2fdd34a142f36", 60592:"7044621e31949c759158cc1e11fca91fbe1f333baa70d9f00a994a90d9277a9c"}
E2_SEQ = [64267,64287,64447,64457,64460,64465,64584,64802,64805]
E2_CHAIN = {64267:"6854dc8243bd34092e75318a0a7c30f60c3a99ab3a0d1ee10faa9d9c6556d06c", 64287:"7b6de7dda232e64dd09871136913272d33a078854c2446b56c25c79d3dc102cf", 64447:"2d3443b348f8e014e9a56d86dc2658d6061f1262377ab517f3cd2645422988d3", 64457:"2f15070b47c4f483e9abea504436f8ff3b9786430bff40cced86540caa59ba26", 64460:"890ddf33f97ee6bb2965ed7dc2ceab91b79db58c99760f347026b0ef123b45e5", 64465:"3c355963fb8cf3f43f59d3ad4e0d96c616e8070f6b43415115160a398ea016db", 64584:"04d0b04d0498af783500b95de1698b22cad98d1c695ad8819824eb40aca64398", 64802:"23abce08c9237645c978b71c95cc0af2768afff78f1b2216c7622dc0a939cb0e", 64805:"f308259b74a245d3402f4e8dc9d45e930ee2754736ef6367cc9bb8635594de8d"}
E3_ROUTE = [67915,67933,68440,69830,70321,70494,70514,71187,71224,71269,71319,71714,71719,71723,71803,
  72020,72083,72088,72959,72964,72982,73344,73448,73534,73619,73624,73762,73810,74070,74186,74294]
E3_SEQ = sorted(E3_ROUTE + [72933])
SEL5 = {70321:2,71803:2,73534:2,74070:1,74294:1}          # Codex exact owner-replace index (sibling-blocked)
LEN5 = {70321:(55,51),71803:(162,772),73534:(491,319),74070:(111,272),74294:(438,482)}
GATE_E1 = E1_CHAIN[60592]; GATE_E2 = E2_CHAIN[64805]
GATE_PRE = "0a13a27dc6abba89220429766082e7379e802a91467c0c1914e65715ee9a02fb"
GATE_FIN = "e4fa07d07dfdf9ca46e7485477ddf1b88f3dfb76661c7f416ce874c2c1337f86"
RESET = "2a44e90d3a092ed9e0db4e533216d413a502c9849fc5f6505675f5e5cdce225c"
CARRY = {57484,64178,64216,64252,65932}
TRANSIENT = {64277,64602,64673,64678,64713,64718,64841}
SIDE_PRODUCER = {58853}
CENSUS_LO, CENSUS_HI = 57484, 75913
PYC_REVIEW = ["recover_a7g1_1663.cpython-310.pyc", "a7_g1_build.cpython-310.pyc"]  # Codex review py_compile bytecode

def build():
    for n, want in ENGINE.items():
        if fsha(LG + "/" + n) != want: fail("engine %s altered" % n)
    sys.path.insert(0, LG)
    import chrono_replay as CR, replay_transcript as RT
    CR.DISK_CACHE_WRITES = False       # no cache writes
    RT.SIBLING_RESOLVER = None         # no recursive sibling replay, in any epoch
    lines = io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace").readlines()
    def rec(n): return json.loads(lines[n - 1])
    # ---- one linear pass: id -> ALL tool_result occurrences (line, is_error) ----
    results = {}
    for i, raw in enumerate(lines, 1):
        try: d = json.loads(raw)
        except ValueError: continue
        for b in (d.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                tid = b.get("tool_use_id")
                if tid: results.setdefault(tid, []).append((i, bool(b.get("is_error"))))
    def tool_uses(n):
        return [b for b in (rec(n).get("message") or {}).get("content") or []
                if isinstance(b, dict) and b.get("type") == "tool_use"]
    def cmd_of(n):
        for b in tool_uses(n):
            return b.get("input", {}).get("command", "") or ""
        return ""
    def bind_block(block, n):
        """(result_line, class) for THIS tool-use block: exactly one later same-id result required for ok/error;
        else waiting (none)/nonunique (duplicate)/earlier/no_id. Never the first-of-many shortcut."""
        tid = block.get("id")
        if not tid: return (None, "no_id")
        occ = results.get(tid, [])
        if len(occ) == 0: return (None, "waiting")
        if len(occ) > 1: return (occ[-1][0], "nonunique")
        line, err = occ[0]
        if line <= n: return (line, "earlier")
        return (line, "error" if err else "ok")
    def owner_block(n):
        """The record's single tool-use block (fail closed if not exactly one)."""
        tu = tool_uses(n)
        if len(tu) != 1: fail("record %d: expected exactly one tool-use block, found %d" % (n, len(tu)))
        return tu[0]
    # ---- heredoc seeding + exact owner-edit extractors (AST literal eval) ----
    HD = re.compile(r"cat\s+(>>?)\s+(\S+)\s+<<\s*'?([A-Za-z0-9_]+)'?\n(.*?)\n\3\b", re.S)
    def seed_heredocs(n, side):
        for op, path, tag, body in HD.findall(cmd_of(n)):
            p = path.strip("\"'")
            if p.endswith(OWN): continue
            side[p] = (side.get(p, "") + body) if op == ">>" else body
    def _consts(tree):
        return {t.targets[0].id: t.value.value for t in ast.walk(tree)
                if isinstance(t, ast.Assign) and len(t.targets) == 1 and isinstance(t.targets[0], ast.Name)
                and isinstance(t.value, ast.Constant) and isinstance(t.value.value, str)}
    def _rs(a, consts):
        if isinstance(a, ast.Constant) and isinstance(a.value, str): return a.value
        if isinstance(a, ast.Name) and a.id in consts: return consts[a.id]
        if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Add):
            l, r = _rs(a.left, consts), _rs(a.right, consts)
            return (l + r) if (l is not None and r is not None) else None
        return None
    def owner_old_new(n):
        """(old,new) applied to the owner: read->replace->write chain; edit(owner,old,new[,why]);
        or `for (f,old,new) in (tuples)` picking the owner tuple. Strings via const/concat resolution."""
        for _a, _b, prog in RT.program_spans(cmd_of(n), env=RT.shell_vars(cmd_of(n))):
            try: tree = ast.parse(prog)
            except SyntaxError: continue
            consts = _consts(tree); rs = lambda a: _rs(a, consts)
            ownervars = {k for k, v in consts.items() if v.endswith(OWN)}
            rv = set()
            for nd in ast.walk(tree):
                if isinstance(nd, ast.Assign) and len(nd.targets) == 1 and isinstance(nd.targets[0], ast.Name) \
                   and isinstance(nd.value, ast.Call) and isinstance(nd.value.func, ast.Attribute) \
                   and nd.value.func.attr == "read" and isinstance(nd.value.func.value, ast.Call):
                    oc = nd.value.func.value; a0 = oc.args[0] if oc.args else None
                    if (isinstance(a0, ast.Name) and a0.id in ownervars) or \
                       (isinstance(a0, ast.Constant) and str(getattr(a0, "value", "")).endswith(OWN)):
                        rv.add(nd.targets[0].id)
            for nd in ast.walk(tree):
                if isinstance(nd, ast.Assign) and isinstance(nd.value, ast.Call) and isinstance(nd.value.func, ast.Attribute) \
                   and nd.value.func.attr == "replace" and len(nd.value.args) >= 2 \
                   and isinstance(nd.value.func.value, ast.Name) and nd.value.func.value.id in rv:
                    o, nw = rs(nd.value.args[0]), rs(nd.value.args[1])
                    if o is not None and nw is not None: return o, nw
            for nd in ast.walk(tree):
                if isinstance(nd, ast.For) and isinstance(nd.target, ast.Tuple) and len(nd.target.elts) == 3 \
                   and isinstance(nd.iter, ast.Tuple):
                    for elt in nd.iter.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) == 3:
                            fv = rs(elt.elts[0])
                            if fv and fv.endswith(OWN):
                                o, nw = rs(elt.elts[1]), rs(elt.elts[2])
                                if o is not None and nw is not None: return o, nw
            for nd in ast.walk(tree):
                if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id == "edit" and len(nd.args) >= 3:
                    tgt = rs(nd.args[0])
                    if tgt and tgt.endswith(OWN):
                        o, nw = rs(nd.args[1]), rs(nd.args[2])
                        if o is not None and nw is not None: return o, nw
        return None
    def nth_owner_replace(n, idx):
        for _a, _b, prog in RT.program_spans(cmd_of(n), env=RT.shell_vars(cmd_of(n))):
            if OWN not in prog: continue
            try: tree = ast.parse(prog)
            except SyntaxError: continue
            consts = _consts(tree); rs = lambda a: _rs(a, consts); reps = []
            for nd in ast.walk(tree):
                if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute) and nd.func.attr == "replace" and len(nd.args) >= 2:
                    o, nw = rs(nd.args[0]), rs(nd.args[1])
                    if o is not None and nw is not None: reps.append((nd.lineno, nd.col_offset, o, nw))
            reps.sort()
            if idx < len(reps): return reps[idx][2], reps[idx][3]
        return None
    def splice_58584(text):
        cmd = cmd_of(58584)
        m = re.search(r"cat > /tmp/g1_exec_section\.py <<'SECTION'\n(.*?)\nSECTION\b", cmd, re.S)
        if not m: fail("58584 SECTION heredoc not found")
        body = m.group(1) + "\n\n"
        mA = "# ------------------------------------------- the loader and the call packet --"
        mB = "# ----------------------------------------------------------- 4. the freeze --"
        L = text.splitlines(keepends=True)
        iA = [i for i, l in enumerate(L) if l.startswith(mA)]; iB = [i for i, l in enumerate(L) if l.startswith(mB)]
        if len(iA) != 1 or len(iB) != 1: fail("58584 markers not unique (%d,%d)" % (len(iA), len(iB)))
        return "".join(L[:iA[0]]) + body + "".join(L[iB[0]:])
    def _cat_body(n, op, path):
        cl = cmd_of(n).split("\n")
        st = [i for i, l in enumerate(cl) if l.strip() == "cat %s %s <<'SECTION'" % (op, path)]
        if not st: fail("%d: cat %s %s heredoc not found" % (n, op, path))
        en = [i for i in range(st[0] + 1, len(cl)) if cl[i] == "SECTION"][0]
        return "\n".join(cl[st[0] + 1:en]) + "\n"
    def splice_58861(text):
        v2 = _cat_body(58853, ">", "/tmp/g1_exec_v2.py") + _cat_body(58861, ">>", "/tmp/g1_exec_v2.py")
        L = text.split("\n")
        i = [k for k, l in enumerate(L) if l.startswith("# --------------------------------------- the published execution chain")]
        j = [k for k, l in enumerate(L) if l.startswith("# ----------------------------------------------------------- 4. the freeze --")]
        if len(i) != 1 or len(j) != 1: fail("58861 markers not unique")
        return "\n".join(L[:i[0]] + v2.split("\n") + L[j[0]:])
    # ---------- MANIFEST rows (with tool_use_id, exact result binding) ----------
    MAN = [("epoch", "line", "kind", "tool_use_id", "result_line", "result_class", "before_sha256", "after_sha256", "bytes")]
    def step(epoch, n, kind, before, after):
        blk = owner_block(n); tid = blk.get("id"); rl, rc = bind_block(blk, n)
        if rc not in ("ok", "error"): fail("record %d result binding ambiguous: %s" % (n, rc))
        MAN.append((epoch, n, kind, tid, rl, rc, sha(before), sha(after), len(after.encode())))
    # ================= EPOCH 1 =================
    body = None
    for c in tool_uses(57484):
        if (c.get("input", {}).get("file_path", "") or "").endswith("harness/" + OWN): body = c.get("input", {}).get("content", "")
    if body is None or sha(body) != RESET: fail("57484 reset body != 2a44e90d")
    step("carry", 57484, "reset-write", body, body)
    text = body; side = {}
    for n in E1_SEQ: seed_heredocs(n, side)
    for n in E1_SEQ:
        before = text
        if n == 58584: text = splice_58584(text); kind = "heredoc-section-splice"
        elif n == 58613:
            oe = owner_old_new(n); kind = "owner-tuple"
            if not oe: fail("58613 owner tuple")
            old, new = oe
            if text.count(old) != 1: fail("58613 anchor count %d" % text.count(old))
            text = text.replace(old, new, 1)
        elif n == 58853: kind = "side-producer(no-change)"
        elif n == 58861: text = splice_58861(text); kind = "append+section-splice"
        else:
            text, _s = RT.apply_saved_edits(text, {n: rec(n)}, "harness/" + OWN, side=side); kind = "program"
        if sha(text) != E1_CHAIN[n]: fail("epoch1 %d: %s != %s" % (n, sha(text), E1_CHAIN[n]))
        step("1", n, kind, before, text)
    if sha(text) != GATE_E1: fail("epoch1 end != 7044621e")
    note("EPOCH 1 ok: 34 rows, 60592=%s bytes=%d" % (sha(text)[:16], len(text.encode())))
    # ================= EPOCH 2 (carries) =================
    for n in (64178, 64216, 64252): step("carry", n, "same-byte-carry", text, text)
    side2 = {}
    for n in E2_SEQ: seed_heredocs(n, side2)
    for n in E2_SEQ:
        before = text
        text, _s = RT.apply_saved_edits(text, {n: rec(n)}, "harness_g1v2/" + OWN, side=side2)
        if sha(text) != E2_CHAIN[n]: fail("epoch2 %d: %s != %s" % (n, sha(text), E2_CHAIN[n]))
        step("2", n, "program", before, text)
    if sha(text) != GATE_E2: fail("epoch2 end != f308259b")
    note("EPOCH 2 ok: 9 rows, 64805=%s bytes=%d" % (sha(text)[:16], len(text.encode())))
    t2 = HERE + "/.a7_g1_build.g1v2.py.tmp"
    io.open(t2, "w", encoding="utf-8", newline="").write(text)
    os.replace(t2, HERE + "/a7_g1_build.g1v2.py")
    if fsha(HERE + "/a7_g1_build.g1v2.py") != GATE_E2: fail("materialized g1v2 != f308259b")
    note("PUBLISHED a7_g1_build.g1v2.py == f308259b (%d bytes)" % os.path.getsize(HERE + "/a7_g1_build.g1v2.py"))
    # ================= EPOCH 3 (carry 65932) =================
    step("carry", 65932, "same-byte-carry", text, text)
    side3 = {}
    for n in E3_SEQ: seed_heredocs(n, side3)
    for n in E3_SEQ:
        before = text
        if n in SEL5:
            oe = nth_owner_replace(n, SEL5[n]); kind = "owner-replace[idx%d]" % SEL5[n]
            if not oe: fail("%d owner replace idx %d" % (n, SEL5[n]))
            old, new = oe
            if (len(old), len(new)) != LEN5[n]: fail("%d len %d/%d != %s" % (n, len(old), len(new), LEN5[n]))
            if text.count(old) != 1: fail("%d owner anchor count %d" % (n, text.count(old)))
            text = text.replace(old, new, 1)
        elif n == 72933:
            oe = owner_old_new(n); kind = "owner-loop-tuple"
            if not oe: fail("72933 tuple")
            old, new = oe
            if text.count(old) != 1: fail("72933 anchor count %d" % text.count(old))
            text = text.replace(old, new, 1)
        else:
            text, _s = RT.apply_saved_edits(text, {n: rec(n)}, "harness_g1v3/" + OWN, side=side3); kind = "program"
        step("3", n, kind, before, text)
        if n == 69830:
            g23 = "48d8b32812e9e799d9d550174a2c7a4a7b2febb70aa814e2eb390ccd23d71d5d"
            t3 = HERE + "/.a7_g1_build.g23.py.tmp"
            io.open(t3, "w", encoding="utf-8", newline="").write(text)
            os.replace(t3, HERE + "/a7_g1_build.g23.py")
            if fsha(HERE + "/a7_g1_build.g23.py") != g23: fail("materialized g23 != 48d8b328")
            note("PUBLISHED a7_g1_build.g23.py == 48d8b328 (%d bytes)"
                 % os.path.getsize(HERE + "/a7_g1_build.g23.py"))
    if sha(text) != GATE_PRE: fail("pre-75912 %s != 0a13a27d" % sha(text))
    if len(text.encode()) != 99073: fail("pre-75912 bytes %d != 99073" % len(text.encode()))
    note("EPOCH 3 pre-75912 ok: 0a13a27d bytes=%d" % len(text.encode()))
    before = text
    oe = owner_old_new(75912)
    if not oe: fail("75912 edit tuple")
    old, new = oe
    if text.count(old) != 1: fail("75912 anchor count %d" % text.count(old))
    text = text.replace(old, new, 1)
    if sha(text) != GATE_FIN: fail("final %s != e4fa07d0" % sha(text))
    if len(text.encode()) != 99321: fail("final bytes %d != 99321" % len(text.encode()))
    step("3", 75912, "edit-tuple", before, text)
    try: ast.parse(text)
    except SyntaxError as exc: fail("final not ast.parse: %s" % exc)
    note("EPOCH 3 final ok: e4fa07d0 bytes=%d; ast.parse ok" % len(text.encode()))
    return CR, RT, rec, tool_uses, cmd_of, bind_block, results, text, MAN

def census(rec, tool_uses, cmd_of, bind_block, RT):
    """One deterministic scan of every record in [57484,75913]; one row per OWNER-BASENAME MENTION BLOCK,
    each bound to its own tool_use_id. Category by effect; result-outcome tracked independently."""
    PERSIST = set(E1_SEQ) - SIDE_PRODUCER | set(E2_SEQ) | set(E3_SEQ) | {75912}
    rows = [("line", "category", "tool", "tool_use_id", "result_line", "result_class")]
    counts = {k: 0 for k in ("persistent", "reset_carry", "transient_restored", "side_producer",
                             "read_only", "other_file_only", "failed_refused_waiting", "unexpected_writer")}
    outcomes = {k: 0 for k in ("ok", "error", "waiting", "ambiguous")}
    def writes_owner(b):
        nm = b.get("name"); inp = b.get("input") or {}
        fp = inp.get("file_path", "") or ""
        if nm in ("Write", "Edit") and fp.endswith(OWN): return True
        cmd = inp.get("command", "") or ""
        if not cmd: return False
        ex = RT.expand(cmd, RT.shell_vars(cmd))
        pats = [r">>?\s*\S*" + re.escape(OWN), r"sed\s+-i\S*\s[^\n]*" + re.escape(OWN),
                r"\b(?:cp|mv)\b[^\n]*" + re.escape(OWN) + r"\s*(?:$|[\"';&|)])",
                r"open\(\s*[^\n,]*" + re.escape(OWN) + r"[^\n,]*,\s*[\"'][wa]"]
        if any(re.search(p, ex) for p in pats): return True
        for _a, _b, prog in RT.program_spans(cmd, env=RT.shell_vars(cmd)):
            try: tree = ast.parse(prog)
            except SyntaxError: continue
            consts = {t.targets[0].id: t.value.value for t in ast.walk(tree)
                      if isinstance(t, ast.Assign) and len(t.targets) == 1 and isinstance(t.targets[0], ast.Name)
                      and isinstance(t.value, ast.Constant) and isinstance(t.value.value, str)}
            ov = {k for k, v in consts.items() if v.endswith(OWN)}
            for nd in ast.walk(tree):
                if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Attribute) and nd.func.attr == "open" \
                   and len(nd.args) >= 2 and isinstance(nd.args[1], ast.Constant) and isinstance(nd.args[1].value, str) \
                   and any(c in nd.args[1].value for c in "wa"):
                    a0 = nd.args[0]
                    if (isinstance(a0, ast.Name) and a0.id in ov) or \
                       (isinstance(a0, ast.Constant) and str(getattr(a0, "value", "")).endswith(OWN)): return True
        return False
    def reads_owner(b):
        if b.get("name") == "Read": return True
        cmd = (b.get("input") or {}).get("command", "") or ""
        if not cmd: return False
        ex = RT.expand(cmd, RT.shell_vars(cmd))
        pats = [r"(?:cat|grep|egrep|head|tail|less|wc|nl|diff|sha256sum|md5sum|sort|python3?)\b[^\n]*" + re.escape(OWN),
                r"open\(\s*[^\n,]*" + re.escape(OWN) + r"[^\n,]*\)(?!\s*,\s*[\"'][wa])",
                r"\.read\(\)|ast\.parse", r"<\s*\S*" + re.escape(OWN)]
        return any(re.search(p, ex) for p in pats)
    total = 0
    for n in range(CENSUS_LO, CENSUS_HI + 1):
        for b in tool_uses(n):
            inp = b.get("input") or {}
            if OWN not in ((inp.get("command") or "") + " " + (inp.get("file_path") or "")): continue
            total += 1; tid = b.get("id"); rl, rc = bind_block(b, n)
            outcomes["ok" if rc == "ok" else "error" if rc == "error"
                     else "waiting" if rc == "waiting" else "ambiguous"] += 1
            if n in PERSIST: cat = "persistent"          # a real owner mutation, whatever its (preserved) result class
            elif n in CARRY: cat = "reset_carry"
            elif n in TRANSIENT: cat = "transient_restored"
            elif n in SIDE_PRODUCER: cat = "side_producer"
            elif rc in ("waiting", "error", "no_id", "nonunique", "earlier"): cat = "failed_refused_waiting"
            elif writes_owner(b): cat = "unexpected_writer"
            elif reads_owner(b): cat = "read_only"
            else: cat = "other_file_only"
            counts[cat] += 1
            rows.append((n, cat, b.get("name"), tid, rl, rc))
    return rows, counts, outcomes, total

def correction_proof(outcome_totals):
    """Deterministic RED (old checks accept a wrong hash / miss a duplicate id / omit outcomes) and
    GREEN (the corrected checks reject them). No timestamps; byte-identical across runs."""
    P = []
    # (a) 8-char startswith accepts a wrong 64-char hash sharing the prefix; full equality rejects it.
    good = GATE_FIN; wrong = good[:8] + ("0" if good[8] != "0" else "1") * 56
    old_a = wrong.startswith(good[:8]); new_a = (wrong == good)
    P.append("(a) prefix-vs-equality gate:")
    P.append("    a wrong 64-char hash sharing the 8-char prefix %s -> old startswith accepts=%s (RED); new equality accepts=%s (GREEN: rejected)."
             % (good[:8], old_a, new_a))
    assert old_a is True and new_a is False
    # (b) first/setdefault binding masks a duplicate same-id result; the corrected binding flags nonunique.
    dup = [(100, False), (200, False)]
    old_first = dup[0]; new_class = "nonunique" if len(dup) > 1 else "ok"
    P.append("(b) duplicate same-id binding:")
    P.append("    two results for one id -> old first-only returns %s with no error flag (RED); new returns class=%s (GREEN: rejected)."
             % (old_first, new_class))
    assert new_class == "nonunique"
    # (c) old counts had no independent result-outcome total; the corrected counts add it, live over 335 rows.
    P.append("(c) result-outcome accounting:")
    P.append("    old CENSUS_COUNTS carried category counts only (RED); new adds outcomes over all mentions: %s (GREEN)."
             % json.dumps(outcome_totals, sort_keys=True))
    assert outcome_totals["ok"] + outcome_totals["error"] + outcome_totals["waiting"] \
        + outcome_totals["ambiguous"] == outcome_totals["total"]
    return "\n".join(P) + "\n"

def main():
    # remove ONLY the two review-created bytecode files + the now-empty __pycache__ dir (Codex SEQ 1664 item 5)
    pc = HERE + "/__pycache__"
    if os.path.isdir(pc):
        for name in PYC_REVIEW:
            fp = os.path.join(pc, name)
            if os.path.isfile(fp): os.remove(fp)
        if not os.listdir(pc): os.rmdir(pc)
    CR, RT, rec, tool_uses, cmd_of, bind_block, results, text, MAN = build()
    rows, counts, outcomes, total = census(rec, tool_uses, cmd_of, bind_block, RT)
    if counts["unexpected_writer"] != 0:
        bad = [r[0] for r in rows[1:] if r[1] == "unexpected_writer"]
        fail("census found owner writers outside adjudicated sets: %s" % bad[:8])
    if total != 335: fail("census total %d != 335" % total)
    if sum(counts.values()) != 335: fail("category counts sum %d != 335" % sum(counts.values()))
    if sum(outcomes.values()) != 335: fail("outcome counts sum %d != 335" % sum(outcomes.values()))
    if (outcomes["ok"], outcomes["error"], outcomes["waiting"], outcomes["ambiguous"]) != (332, 3, 0, 0):
        fail("outcome accounting %s != ok332/error3/waiting0/ambiguous0" % outcomes)
    note("CENSUS: %d mentions; categories %s; outcomes %s"
         % (total, {k: v for k, v in counts.items() if v}, outcomes))
    # ---- candidate (atomic) ----
    tmp = HERE + "/.a7_g1_build.py.tmp"; io.open(tmp, "w", encoding="utf-8", newline="").write(text)
    os.replace(tmp, HERE + "/a7_g1_build.py")
    if fsha(HERE + "/a7_g1_build.py") != GATE_FIN: fail("materialized != e4fa07d0")
    note("CANDIDATE a7_g1_build.py == e4fa07d0 (%d bytes)" % os.path.getsize(HERE + "/a7_g1_build.py"))
    # ---- evidence ----
    io.open(HERE + "/MANIFEST_epochs.tsv", "w").write("".join("\t".join(str(x) for x in r) + "\n" for r in MAN))
    io.open(HERE + "/CENSUS.tsv", "w").write("".join("\t".join(str(x) for x in r) + "\n" for r in rows))
    io.open(HERE + "/CENSUS_COUNTS.json", "w").write(json.dumps(
        {"total": total, "counts": counts, "outcomes": outcomes}, indent=1) + "\n")
    io.open(HERE + "/CORRECTION_PROOF.txt", "w").write(correction_proof(dict(outcomes, total=total)))
    io.open(HERE + "/DERIVATION_REPORT.txt", "w").write("\n".join(LOG) + "\n")
    # ---- SHA256 manifest of every durable artifact ----
    man = []
    for rel in ("recover_a7g1_1663.py", "a7_g1_build.py", "a7_g1_build.g1v2.py", "a7_g1_build.g23.py", "MANIFEST_epochs.tsv", "CENSUS.tsv",
                "CENSUS_COUNTS.json", "CORRECTION_PROOF.txt", "DERIVATION_REPORT.txt"):
        p = HERE + "/" + rel
        if os.path.isfile(p): man.append((rel, fsha(p), os.path.getsize(p)))
    for n2 in ENGINE: man.append(("ENGINE:" + n2, ENGINE[n2], os.path.getsize(LG + "/" + n2)))
    io.open(HERE + "/SHA256_MANIFEST.tsv", "w").write("path\tsha256\tbytes\n" + "".join("%s\t%s\t%d\n" % r for r in man))
    # ---- no unmanifested top-level file except the evidence/ subdir ----
    manifested = {r[0] for r in man} | {"SHA256_MANIFEST.tsv"}
    for name in sorted(os.listdir(HERE)):
        if name == "evidence" and os.path.isdir(HERE + "/evidence"): continue
        if os.path.isfile(HERE + "/" + name) and name not in manifested:
            fail("unmanifested file in unit: %s" % name)
    print("OK candidate e4fa07d0; %d epoch rows; census %d; categories %s; outcomes %s" %
          (len(MAN) - 1, total, {k: v for k, v in counts.items() if v}, outcomes))

if __name__ == "__main__":
    main()
