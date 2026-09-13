"""Count the lines that differ between the two arms once noise is removed.

compare_arms_2099.py answers the question per module (exit and named-failure
count). This answers the stricter one: after masking the things that CANNOT be
the overlay's doing, does a single character of output differ?

Masked, and nothing else:
  * elapsed times      pytest prints its own duration
  * the run tag        the two arms are necessarily named differently
  * the ENVIRONMENT banner line, which carries the tag and the tree
  * object addresses   0x... repr addresses vary run to run
  * pytest temp dirs   pytest-N basetemp paths vary run to run

Every masking rule is listed here so the reader can judge whether one of them
could hide a real difference. None of them can hide a changed assertion, a
changed count or a changed traceback.
"""
import difflib
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(os.path.dirname(HERE), 'unit_1957/logs')
TREATMENT = os.path.join(LOGS, 'attempt_grader_core2099run2/stdout.txt')
CONTROL = os.path.join(LOGS, 'attempt_grader_core2099ctrl/stdout.txt')
MASKS = [
    (r'in [0-9.]+s', 'in Xs'),
    (r'\[[0-9.]+s\]', '[Xs]'),
    (r'core2099(?:run2|ctrl|base)', 'TAG'),
    (r'(?m)^ENVIRONMENT .*$', 'ENVIRONMENT MASKED'),
    (r'0x[0-9a-f]{6,}', '0xADDR'),
    (r'pytest-[0-9]+', 'pytest-N'),
    (r'/tmp/[^\s)"\']*pytest[^\s)"\']*', 'PYTEST_TMP'),
]


def normalised(path):
    text = io.open(path, encoding='utf-8', errors='replace').read()
    for pattern, repl in MASKS:
        text = re.sub(pattern, repl, text)
    return text.split('\n')


a, b = normalised(TREATMENT), normalised(CONTROL)
differing = [line for line in difflib.unified_diff(a, b, lineterm='')
             if line[:1] in '+-' and line[:3] not in ('---', '+++')]
# the masks must not have eaten the content: both arms still carry every module
assert sum(1 for l in a if l.startswith('===== MODULE ')) == 19, 'lost modules'
assert len(a) == len(b) or differing, 'unequal length with no reported diff'
print(len(differing))
