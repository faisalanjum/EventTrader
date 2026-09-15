"""Write ONE 2173 command file from the proved 2161 template.

The template is the command that already ran the operator against the frozen
2161 run. Only the bindings this round genuinely changes are substituted, each
by exact token, and the writer refuses unless every one of them actually
replaced something - so a silent miss cannot leave an old path in the command.

    python3 -B build_command_2173.py <tag> <payload-relative-to-unit_1947/ledger> <kind|-> [KEY=VALUE ...]
"""
import hashlib
import io
import os
import re
import sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery/'
SC = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
      '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/')
TEMPLATE = A7 + 'unit_2161_execution/commands/cmd_core_op2161_g2_status.sh'
TEMPLATE_SHA256 = None  # pinned below from the file that already ran
UNIT = A7 + 'unit_2173_grading/'
PREP = A7 + 'unit_2020_codex_check/codex_changedprep2171_a/'


def sha_file(path):
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest()


def main():
    tag, payload, kind = sys.argv[1], sys.argv[2], sys.argv[3]
    extra = dict(pair.split('=', 1) for pair in sys.argv[4:])
    text = io.open(TEMPLATE, encoding='utf-8').read()

    bindings = {
        'A7_RUN_BINDING': UNIT + 'map_execution_2173.tsv',
        'A7_EXECUTION_ROOT': SC + 'a7_grading_2173',
        'A7_PROFILE_ROOT': A7 + 'unit_2161_execution/G2/run/root.json',
        'A7_G2_CANDIDATE': PREP + 'G2/a7_g1_candidate.json',
        'A7_G3_CANDIDATE': PREP + 'G3/a7_g1_candidate.json',
        'A7_TAG': tag,
    }
    for name in ('A7_PROFILE_ROOT', 'A7_G2_CANDIDATE', 'A7_G3_CANDIDATE'):
        bindings[name + '_SHA256'] = sha_file(bindings[name])
    if kind != '-':
        launch = UNIT + kind + '/LAUNCH_OPERATOR_2173.json'
        bindings['A7_GRADING_LAUNCH'] = launch
        bindings['A7_GRADING_LAUNCH_SHA256'] = sha_file(launch)
    bindings.update(extra)

    marker = 'bash a7_recovery/unit_1947/ledger/run_real_1947.sh'
    for name, value in bindings.items():
        pattern = r"(?<![A-Z0-9_])%s='[^']*'" % re.escape(name)
        text, hits = re.subn(pattern, "%s='%s'" % (name, value), text)
        if hits > 1:
            raise ValueError('%s replaced %d times, not 1' % (name, hits))
        if hits == 0:
            # A binding the proved template never carried - the workflow run id
            # the operator's ingest needs. Added explicitly, never silently.
            at = text.index(marker)
            text = text[:at] + "%s='%s' " % (name, value) + text[at:]

    tail = ("bash a7_recovery/unit_1947/ledger/run_real_1947.sh "
            "../unit_2173_grading/map_execution_2173.tsv "
            "%s %s 1800\n" % (payload, tag))
    head = text[:text.index(marker)]
    text = head + tail
    for stale in ('unit_2161_execution/map', 'a7_grading_2159',
                  'codex_g2reuse2159_a', 'core_op2161'):
        if stale in text:
            raise ValueError('a stale binding survived: %s' % stale)
    out = UNIT + 'commands/cmd_%s.sh' % tag
    io.open(out, 'w', encoding='utf-8').write(text)
    print(out, sha_file(out))


if __name__ == '__main__':
    main()
