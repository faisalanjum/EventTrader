"""The accepted-checkpoint inventory must reject every way it can be wrong.

The previous control only asked that `accepted_in` started with "archive_CODEX_". It did
not prove the archive existed, had fixed bytes, or accepted that exact 64-hex identity -
so it would have passed an inventory citing an archive that says nothing of the kind.
`logs/all_owners.txt` was hand-typed and unverified, and one of its rows was fabricated;
these controls exist so this file cannot go the same way.

Each control corrupts a COPY one way and requires a refusal.
"""
import io
import os
import shutil
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
import verify_accepted_checkpoints as V                        # noqa: E402

MAIL = "/home/faisal/.core827-orchestrator"


def _copy(tmp_path):
    dest = str(tmp_path / "ACCEPTED_CHECKPOINTS.tsv")
    shutil.copy(os.path.join(_R, "products", "ACCEPTED_CHECKPOINTS.tsv"), dest)
    return dest


def _lines(path):
    return [l.rstrip("\n") for l in io.open(path, encoding="utf-8") if l.strip()]


def _write(path, lines):
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def test_the_live_inventory_verifies():
    assert V.failures() == []


def test_it_REFUSES_a_missing_row(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    _write(p, lines[:-1])
    assert V.failures(p, MAIL, _R) != []


def test_it_REFUSES_an_extra_row(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    _write(p, lines + [lines[-1].replace("34187", "99999")])
    assert V.failures(p, MAIL, _R) != []


def test_it_REFUSES_a_duplicated_row(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    _write(p, lines + [lines[-1]])
    assert any("duplicate" in f for f in V.failures(p, MAIL, _R))


def test_it_REFUSES_an_altered_digest(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    f = lines[1].split("\t")
    f[2] = f[2][:-1] + ("0" if f[2][-1] != "0" else "1")
    lines[1] = "\t".join(f)
    _write(p, lines)
    assert V.failures(p, MAIL, _R) != []


def test_it_REFUSES_a_PREFIX_ONLY_digest(tmp_path):
    """An 8-hex prefix is not an identity; the old builder decided history with one."""
    p = _copy(tmp_path)
    lines = _lines(p)
    f = lines[1].split("\t")
    f[2] = f[2][:8]
    lines[1] = "\t".join(f)
    assert any("64-hex" in x for x in V.failures(
        _write(p, lines) or p, MAIL, _R))


def test_it_REFUSES_an_altered_byte_count(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    f = lines[1].split("\t")
    f[3] = str(int(f[3]) + 1)
    lines[1] = "\t".join(f)
    _write(p, lines)
    assert any("byte count" in x for x in V.failures(p, MAIL, _R))


def test_it_REFUSES_an_acceptance_archive_that_does_not_exist(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    f = lines[1].split("\t")
    f[7] = "archive_CODEX_000000.md"
    lines[1] = "\t".join(f)
    _write(p, lines)
    assert any("archive missing" in x for x in V.failures(p, MAIL, _R))


def test_it_REFUSES_an_acceptance_archive_whose_bytes_changed(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    f = lines[1].split("\t")
    f[8] = f[8][:-1] + ("0" if f[8][-1] != "0" else "1")
    lines[1] = "\t".join(f)
    _write(p, lines)
    assert any("bytes changed" in x for x in V.failures(p, MAIL, _R))


def test_it_REFUSES_an_archive_that_does_not_carry_the_tuple(tmp_path):
    """Cite a REAL archive with a real hash that simply does not accept this state."""
    import hashlib
    other = "archive_CODEX_1556.md"
    ob = io.open(os.path.join(MAIL, other), "rb").read()
    p = _copy(tmp_path)
    lines = _lines(p)
    f = lines[1].split("\t")
    f[7], f[8] = other, hashlib.sha256(ob).hexdigest()
    lines[1] = "\t".join(f)
    _write(p, lines)
    assert any("0 tuples with this digest" in x for x in V.failures(p, MAIL, _R))


def test_it_REFUSES_a_malformed_header(tmp_path):
    p = _copy(tmp_path)
    lines = _lines(p)
    lines[0] = lines[0].replace("owner", "ownerX", 1)
    _write(p, lines)
    assert V.failures(p, MAIL, _R) != []


# ---------------------------------------------------------------------------
# Codex SEQ 1559 item 3: the archive's exact tuple, not three independent substrings.
# ---------------------------------------------------------------------------
def test_the_real_archive_states_exactly_the_eight_tuples_one_to_one():
    """The real positive tuple control: every inventory row has exactly one archive
    tuple whose owner, cutoff, digest and byte count all equal the row's."""
    rows = V.rows()
    arch = io.open(os.path.join(V.MAIL, rows[0]["accepted_in"]), encoding="utf-8").read()
    tuples = V.accepted_tuples(arch)
    assert len(tuples) == len(rows) == 8
    for r in rows:
        hits = [t for t in tuples if t["sha256"] == r["sha256"]]
        assert len(hits) == 1
        assert (hits[0]["owner"], hits[0]["cutoff"], hits[0]["bytes"]) == \
            (r["owner"], r["cutoff"], r["bytes"])


def test_it_REFUSES_a_permutation_of_cutoffs_between_two_rows(tmp_path):
    """Codex's falsifier: swap the cutoffs of two rows, keep the archive untouched.
    Every token still occurs somewhere in the archive, so only a bound tuple refuses."""
    p = _copy(tmp_path)
    lines = _lines(p)
    a = [i for i, l in enumerate(lines) if l.startswith("audit_worker_access.py\t")][0]
    b = [i for i, l in enumerate(lines) if l.startswith("test_harness_guards.py\t23131\t")][0]
    fa, fb = lines[a].split("\t"), lines[b].split("\t")
    fa[1], fb[1] = fb[1], fa[1]
    lines[a], lines[b] = "\t".join(fa), "\t".join(fb)
    _write(p, lines)
    bad = V.failures(p)
    assert any("binds this digest to cutoff" in x for x in bad), bad


def test_it_REFUSES_an_archive_that_states_a_digest_twice(tmp_path):
    rows = V.rows()
    src = os.path.join(V.MAIL, rows[0]["accepted_in"])
    text = io.open(src, encoding="utf-8").read()
    line = [l for l in text.split("\n") if rows[0]["sha256"] in l and l.startswith("* ")][0]
    fake_mail = tmp_path / "mail"; fake_mail.mkdir()
    (fake_mail / rows[0]["accepted_in"]).write_text(text + "\n" + line + "\n", encoding="utf-8")
    p = _copy(tmp_path)
    # re-pin the altered archive honestly, so the digest check is not what refuses
    import hashlib
    new_sha = hashlib.sha256((fake_mail / rows[0]["accepted_in"]).read_bytes()).hexdigest()
    _write(p, [l.replace(rows[0]["accepted_in_sha256"], new_sha) for l in _lines(p)])
    bad = V.failures(p, str(fake_mail))
    assert any("2 tuples with this digest" in x for x in bad), bad


def test_the_unaccepted_intermediate_is_outside_the_package():
    """Codex SEQ 1559: the at26879 intermediate has no accepting archive; it lives beside
    the package, pinned there, and nothing in the package carries it."""
    import glob
    inside = [p for p in glob.glob(os.path.join(_R, "**", "*at26879*"), recursive=True)
              if "/logs/" not in p]
    assert inside == [], inside
    beside = os.path.join(os.path.dirname(_R), "unaccepted", "UNACCEPTED.tsv")
    assert os.path.isfile(beside)
    assert "at26879" in io.open(beside, encoding="utf-8").read()
