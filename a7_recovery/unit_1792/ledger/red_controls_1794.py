# -*- coding: utf-8 -*-
"""RED before, GREEN after - the three proved false accepts (Codex SEQ 1794 item 1).

Runs the SAME forgeries the permanent suite uses (imported from it, so the two
can never drift) through the COMPLETE transcript input path `_g1_transcript` of
whichever owner is named - the preserved PRE-FIX owner, or the corrected one.

    ledger/red_controls_1794.py <owner.py> [<label>]

The pre-fix owner takes a run-wide LIST of allowed shas; the corrected owner
takes ONE per-lane expectation. The form is chosen from the owner's own
signature, so each is asked in the only language it has.
"""
import collections
import importlib.machinery
import importlib.util
import io
import inspect
import json
import os
import sys

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEW = U + "/view/harness_g1v3"
LOGS = U + "/logs"


def load(path, name):
    # an explicit source loader: the preserved pre-fix owner does not end in .py
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_file_location(name, path, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    owner_path = sys.argv[1] if len(sys.argv) > 1 else VIEW + "/audit_worker_access.py"
    label = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(owner_path)
    # the harness directory must be importable first: the owner imports its
    # siblings (raw_transport and the rest) by plain module name
    sys.path.insert(0, VIEW)
    owner = load(owner_path, "audit_worker_access")
    # the suite under test must see THIS owner, not the one beside it on disk
    sys.modules["audit_worker_access"] = owner
    T = load(VIEW + "/test_g1_declared_input_1792.py", "cases_1794")

    param = list(inspect.signature(owner._g1_transcript).parameters)[-1]
    spec = T.served_spec()
    #: the pre-fix owner knows only a run-wide list of allowed payload hashes
    as_owner_wants = (lambda s: [] if s is None else [s["payload_sha256"]]) \
        if param == "declared" else (lambda s: s)

    _served, cached, new = T.population()
    agent, cached_agent = new[0], cached[0]
    #: the forged transcripts each case actually fed to the owner, kept
    tmp = os.path.join(U, "evidence", "red_control_cases")
    cases = collections.OrderedDict()
    cases["control: the real served worker"] = (
        T.transcript(agent), agent, spec, False)
    cases["control: the real precall-cached worker"] = (
        T.transcript(cached_agent), cached_agent, None, False)
    for name in sorted(T.FORGERIES):
        forged_agent, forged = T.FORGERIES[name](spec)
        cases["forgery: " + name] = (forged, forged_agent, spec, True)
    donor = T.transcript(agent)[spec["record_index"]]
    base = T.transcript(cached_agent)
    cases["forgery: the payload injected into a cached worker"] = (
        T._relink(base[:1] + [json.loads(json.dumps(donor))] + list(base[1:])),
        cached_agent, None, True)

    rows, wrong = [], 0
    for n, (name, (recs, aid, want, must_refuse)) in enumerate(cases.items()):
        problems = T.judge(recs, aid, as_owner_wants(want),
                           os.path.join(tmp, "case%02d" % n))
        refused = bool(problems)
        ok = refused == must_refuse
        wrong += 0 if ok else 1
        rows.append(collections.OrderedDict([
            ("case", name), ("must_refuse", must_refuse),
            ("verdict", "REFUSED" if refused else "ACCEPTED"),
            ("correct", ok), ("first_problem", str(problems[0]) if problems else None)]))
        print("  %-52s %-8s %s" % (name, rows[-1]["verdict"],
                                   "ok" if ok else "<-- WRONG"))
    doc = collections.OrderedDict([
        ("owner", collections.OrderedDict([
            ("label", label), ("path", owner_path),
            ("declaration_parameter", param)])),
        ("agents", {"served": agent, "precall_cached": cached_agent}),
        ("wrong", wrong), ("cases", rows)])
    out = "%s/red_controls_%s.json" % (LOGS, label.replace("/", "_"))
    io.open(out, "w", encoding="utf-8").write(json.dumps(doc, indent=1) + "\n")
    print("  %d of %d wrong  -> %s" % (wrong, len(rows), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
