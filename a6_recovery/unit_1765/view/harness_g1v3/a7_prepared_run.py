"""THE one prepared-run identity for A7 (Codex SEQ 1468 item 2).

Every A7 owner used to reach for a module-level path to the ONE run that
happened to exist. A default is not a binding: it meant a helper could be
handed a fresh run and still answer about the old one, and nothing in the
outputs said which run they described. A foreign path failing to open is not
proof that a valid run controls the system - two valid runs are.

`load` returns the identity, or raises. It binds what the run IS: its A5
manifest and the era that manifest was built for, its bundle, its receipt and
the exact schedule that receipt allows, its re-derived A6 launch freeze, and -
once it has been executed - its finalizations and its whole-run digest. A
consumer holding this identity cannot silently be answering about another run.
"""

import collections
import hashlib
import io
import json
import os

SCHEMA = "a7_prepared_run/1"

#: what the A5 preparer persists inside a run. Named once, here, so a consumer
#: cannot invent its own idea of what a prepared run looks like.
PLAN_DIRNAME = "plan"
A5_MANIFEST = "a5_exp5_reader.manifest.json"
A5_BUNDLE = "a5_launcher.bundle.json"
RECEIPT = "receipt.json"

#: the keys an A5 reader manifest must carry to BE one. A directory holding
#: some other json under the right name is not a prepared run.
A5_REQUIRED = ("pins", "ordered_calls", "prompt_sha256", "arm_of_lane")


def _sha(path):
    with io.open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _read_json(path, what):
    if not os.path.isfile(path):
        raise ValueError("%s: no %s at %s" % (SCHEMA, what, path))
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError as exc:
        raise ValueError("%s: the %s at %s is not readable json: %s"
                         % (SCHEMA, what, path, exc))


def load(run_dir, expect_freeze_sha=None):
    """-> the identity of ONE lawful prepared run. Raises on anything else."""
    if not run_dir or not isinstance(run_dir, str):
        raise ValueError("%s: no run was supplied" % SCHEMA)
    run_dir = os.path.abspath(run_dir)
    if not os.path.isdir(run_dir):
        raise ValueError("%s: no run directory at %s" % (SCHEMA, run_dir))

    plan_dir = os.path.join(run_dir, PLAN_DIRNAME)
    if not os.path.isdir(plan_dir):
        raise ValueError("%s: %s has no %s/" % (SCHEMA, run_dir, PLAN_DIRNAME))
    if not os.listdir(plan_dir):
        # AN EXISTING BUT EMPTY PLAN DIRECTORY. Checking only that the
        # directory exists accepted this, and the K-fields fallback then
        # lawfully answered from somewhere else entirely.
        raise ValueError("%s: the plan directory at %s is empty"
                         % (SCHEMA, plan_dir))

    manifest_path = os.path.join(plan_dir, A5_MANIFEST)
    manifest = _read_json(manifest_path, "A5 reader manifest")
    missing = [k for k in A5_REQUIRED
               if not isinstance(manifest, dict) or k not in manifest]
    if missing:
        raise ValueError("%s: %s is not an A5 reader manifest; it has no %s"
                         % (SCHEMA, manifest_path, ", ".join(missing)))

    receipt_path = os.path.join(run_dir, RECEIPT)
    receipt = _read_json(receipt_path, "receipt")
    allowed = receipt.get("allowed")
    if not isinstance(allowed, list) or not allowed:
        raise ValueError("%s: %s allows no calls" % (SCHEMA, receipt_path))

    # THE A6 LAUNCH FREEZE, RE-DERIVED FROM THIS RUN. A recorded freeze proves
    # only that a freeze was once written; re-deriving proves it still
    # describes this run.
    # THE GUARDED LOADER, not a bare import. `a7_g1_build._a6()` already
    # refuses an `a6_launch_freeze` that resolved to another directory,
    # because that owner derives its pointer paths from its own file location
    # - a byte-identical copy elsewhere silently yields a different bound()
    # and a different every-count. A bare import here walked straight past
    # that guard and picked up a stale copy.
    import a7_g1_build as _G
    A6 = _G._a6()
    frozen = A6.freeze(run_dir)
    bad = A6.problems(frozen)
    executed = _executed(run_dir)
    if executed:
        # AN EXECUTED RUN HAS SPENT SOMETHING - that is what executed means,
        # and A6 says so as a problem because A6 exists to guard a PRE-launch
        # freeze. Which problems those are is DERIVED, not named: re-ask A6
        # about the same freeze with its spend counters at zero, and the
        # problems that disappear are exactly the ones the spend caused. Any
        # problem that survives is a real mismatch and still refuses.
        import copy
        probe = copy.deepcopy(frozen)
        probe["zeros"] = dict.fromkeys(probe["zeros"], 0)
        still = set(A6.problems(probe))
        bad = [x for x in bad if x in still]
    if bad:
        raise ValueError("%s: the A6 freeze of %s does not hold: %s"
                         % (SCHEMA, run_dir, bad[:2]))
    freeze_sha = hashlib.sha256(
        json.dumps(frozen, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")).hexdigest()
    if expect_freeze_sha is not None and expect_freeze_sha != freeze_sha:
        raise ValueError("%s: %s freezes to %s, not the required %s"
                         % (SCHEMA, run_dir, freeze_sha, expect_freeze_sha))

    # THE MIDDLE STATE IS REFUSED. A run that saved answers but has no
    # finalization is neither uncalled nor complete: the trace owner would
    # read a finalization that is not there. It is a real state of a real run,
    # so it is named rather than left to raise later (Codex SEQ 1469 item 3).
    finalizations = _finalizations(run_dir)
    if executed and "primary" not in finalizations:
        raise ValueError(
            "%s: %s holds %d saved files but no finalization; its answers "
            "cannot be selected, so it is refused rather than read"
            % (SCHEMA, run_dir, executed["run_files"]))

    bundle_path = os.path.join(plan_dir, A5_BUNDLE)
    ident = collections.OrderedDict([
        ("schema", SCHEMA),
        ("run_dir", run_dir),
        # THE ERA THIS RUN WAS PREPARED FOR. A run whose plan names no era is
        # an A1-era run, and saying so is the point: the two must never be
        # mistaken for one another.
        ("contract_suffix", manifest.get("contract_suffix")),
        ("a5_manifest_sha256", _sha(manifest_path)),
        ("a5_bundle_sha256", _sha(bundle_path)
         if os.path.isfile(bundle_path) else None),
        ("receipt_sha256", _sha(receipt_path)),
        ("scheduled_calls", len(allowed)),
        ("a6_freeze_sha256", freeze_sha),
        ("finalizations", finalizations),
        ("executed", executed),
    ])
    return ident


def _finalizations(run_dir):
    """The run's own finalizations, by name -> sha256, VALIDATED.

    Hashing these files only proved they had not changed since someone looked;
    it did not prove they are internally consistent. A record whose
    classifications derive an owed retry beside an empty `retry` list was
    accepted, and `effective_slots` then trusted those fields and selected an
    answer from a run that contradicts itself. THE ONE finalization validator
    runs here, at the boundary, before any answer can be selected
    (Codex SEQ 1471 item 2).
    """
    import raw_transport as RT
    out = collections.OrderedDict()
    ppath = os.path.join(run_dir, "finalization.json")
    if not os.path.isfile(ppath):
        return out
    plan = RT.a1_plan_for_run(run_dir)
    # THE LIVE RECEIPT CONTRACT TOO, through its existing owner. The
    # finalization binds the receipt only by HASH, so a receipt with a changed
    # or added field plus a recomputed `receipt_sha256` was self-consistent and
    # accepted (Codex SEQ 1472 item 2). The rules are not copied here.
    receipt = _read_json(os.path.join(run_dir, RECEIPT), "receipt")
    bad = RT.a1_run_contract_problems(receipt, run_dir, plan)
    if bad:
        raise ValueError("%s: the receipt of %s does not hold: %s"
                         % (SCHEMA, run_dir, bad[:2]))
    pf = _read_json(ppath, "primary finalization")
    bad = RT.a1_finalization_problems(pf, plan, run_dir, 1)
    if bad:
        raise ValueError("%s: the primary finalization of %s does not hold: %s"
                         % (SCHEMA, run_dir, bad[:2]))
    out["primary"] = _sha(ppath)

    owed = [tuple(c) for c in pf.get("retry") or []]
    rdir = os.path.join(run_dir, RT.RETRY_DIRNAME)
    rpath = os.path.join(rdir, "finalization.json")
    if os.path.isfile(rpath):
        rreceipt = _read_json(os.path.join(rdir, RECEIPT), "retry receipt")
        bad = RT.a1_run_contract_problems(rreceipt, rdir, plan)
        if bad:
            raise ValueError("%s: the retry receipt of %s does not hold: %s"
                             % (SCHEMA, rdir, bad[:2]))
        rf = _read_json(rpath, "retry finalization")
        bad = RT.a1_finalization_problems(rf, plan, rdir, 2, owed)
        if bad:
            raise ValueError("%s: the retry finalization of %s does not hold: "
                             "%s" % (SCHEMA, run_dir, bad[:2]))
        out["retry"] = _sha(rpath)
    return out


def _executed(run_dir):
    """-> the whole-run digest and file count once the run has answers, else
    None. This is the number an outside reviewer measures with
    `find -exec sha256sum | sort | sha256sum`, through the ONE existing owner.
    """
    answers = os.path.join(run_dir, "answers")
    if not os.path.isdir(answers) or not os.listdir(answers):
        return None
    import a7_g1_complete_v2 as CV
    digest, files = CV.run_digest(run_dir)
    return collections.OrderedDict([("run_digest", digest),
                                    ("run_files", files)])


def require_current_era(run_dir, got):
    """THE era gate, in one place. `current` and the ledger both ask HERE, so
    there is one rule and one place a historical proof can relax it."""
    import build_launch_manifest as BLM
    want = BLM.PRODUCER_CONTRACT_SUFFIX
    if got != want:
        raise ValueError(
            "%s: %s was prepared for era %r, not the current producer era %r; "
            "the current route refuses a run from another era"
            % (SCHEMA, run_dir, got, want))


def current(run_dir, expect_freeze_sha=None):
    """The identity of a run prepared for the CURRENT producer era.

    `load` accepts ANY lawful prepared run, including the old v1 one - that is
    what makes it useful for reading history. The CURRENT A7 route must not
    accept history: grading the run that is about to be called is the whole
    point, and a v1 run silently standing in for it is exactly the substitution
    this identity exists to prevent (Codex SEQ 1469 item 3).
    """
    return current_era(load(run_dir, expect_freeze_sha))


def current_era(identity):
    """THE live era gate over an already-loaded identity: `current` asks it
    after loading, and a warm trace asks it before trusting the trace, so a
    historical run is refused at every live use whether or not its trace is
    cached (Codex SEQ 1473; SEQ 1489 item D). A historical proof relaxes
    exactly this one name."""
    require_current_era(identity["run_dir"], identity["contract_suffix"])
    return identity


def cli_run(argv):
    """-> the CURRENT run named on the command line, or a refusal.

    NO CLI MAY DEFAULT TO A RUN. Each of these printed a full report about
    whichever run happened to be at the module default, which reads as a
    successful answer about the run the operator meant.
    """
    run = None
    for i, arg in enumerate(argv):
        if arg == "--run" and i + 1 < len(argv):
            run = argv[i + 1]
        elif arg.startswith("--run="):
            run = arg.split("=", 1)[1]
    if not run:
        raise ValueError(
            "%s: name the prepared run with --run <dir>. A7 binds evidence to "
            "ONE run and has no default." % SCHEMA)
    return current(run)
