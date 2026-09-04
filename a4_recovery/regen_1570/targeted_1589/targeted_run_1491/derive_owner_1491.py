"""The exact targeted owner, DERIVED (Codex SEQ 1604/1605): the committed
phase-1 owner plus the literal replacement pairs recorded in the durable Core
transcript's Bash heredocs at lines 82289 and 82632, in that order. Each
heredoc calls patch(name, pairs); the pairs whose name is this owner's file
are applied with exactly one occurrence required before each replacement.
Writes the owner atomically beside this script and a derivation table."""
import ast, hashlib, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = os.environ.get("CORE_TRANSCRIPT", "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
BASE = os.environ.get("OWNER_BASE", os.path.join(HERE, "..", "phase1_targeted_1488", "inputs", "harness_g1v3", "build_kfields_key_targeted.py"))
OWNER_NAME = "build_kfields_key_targeted.py"
LINES = (82289, 82632)
sha = lambda b: hashlib.sha256(b).hexdigest()


def heredoc(command):
    return command.split("<<'PYEOF'\n", 1)[1].split("\nPYEOF", 1)[0]


def pairs_of(body):
    out = []
    for node in ast.walk(ast.parse(body)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "patch" \
                and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == OWNER_NAME:
            out.extend(ast.literal_eval(node.args[1]))
    return out


def derive(transcript=TRANSCRIPT, base=BASE, lines=LINES):
    with io.open(transcript, encoding="utf-8", errors="replace") as fh:
        rows = fh.readlines()
    text = io.open(base, encoding="utf-8", newline="").read()
    steps = [("base", 0, "-", 0, sha(text.encode("utf-8")), len(text.encode("utf-8")))]
    for ln in lines:
        rec = json.loads(rows[ln - 1])
        calls = [c for c in rec["message"]["content"] if c.get("type") == "tool_use" and c.get("name") == "Bash"]
        if len(calls) != 1:
            raise ValueError("line %d holds %d Bash calls" % (ln, len(calls)))
        pairs = pairs_of(heredoc(calls[0]["input"]["command"]))
        if not pairs:
            raise ValueError("line %d yields no replacement pair for %s" % (ln, OWNER_NAME))
        for old, new in pairs:
            n = text.count(old)
            if n != 1:
                raise ValueError("line %d: a pair's old text occurs %d times" % (ln, n))
            text = text.replace(old, new)
        steps.append(("apply", ln, rec.get("timestamp"), len(pairs), sha(text.encode("utf-8")), len(text.encode("utf-8"))))
    return text, steps


def main(argv):
    out = os.path.join(HERE, OWNER_NAME)
    text, steps = derive()
    tmp = out + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, out)
    with io.open(os.path.join(HERE, "OWNER_DERIVATION.tsv"), "w", encoding="utf-8") as fh:
        fh.write("step\ttranscript_line\ttimestamp\tpairs\tsha256\tbytes\n")
        for row in steps:
            fh.write("\t".join(str(c) for c in row) + "\n")
    print("\n".join("%s\t%s\t%s\t%s\t%s\t%s" % row for row in steps))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
