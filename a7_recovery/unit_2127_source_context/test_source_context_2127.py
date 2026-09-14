"""RED-first: the missing source-context sentence, on the LIVE served prefix.

Same discipline as `test_prefix_spans_2063`: every property lives in ONE
`problems()` function so the clean subject and each mutant are judged by the
same checks, and the new wording is quoted FROM ITS OWNER rather than retyped,
so a reworded owner makes the property miss rather than silently pass.

The subject is chosen by A7_CONTEXT_OWNER: unset -> the prefix served today
(RED), `new` -> the candidate (GREEN).
"""
import collections, json, os, sys, unittest
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2053_owner_retry',
            'unit_2061_settlement_connection', 'unit_2063_source_closeout',
            'unit_2127_source_context'):
    sys.path.insert(0, str(A7 / rel))
import a4_review_composite as R                                    # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_recovery as RECOV                                 # noqa: E402
import a4_source_taskv2 as V2                                      # noqa: E402
import a7_source_context_2127 as V3                                # noqa: E402
SK, K, F = R.SK, R.K, R.F
PKT = A7 / 'unit_2062_settlement_packet/packet_core_pkt2062_c'
saved = json.loads((PKT / 'FINDINGS_BY_EVENT.json').read_text())
findings = collections.OrderedDict(saved['by_event'])

#: the sections that must stay byte-identical on both sides of the change
SECTIONS = ('[RULES]\n', '[OUTPUT]\n', '[THE GATE]\n', '[TAG RULES]\n',
            '[A4 FINAL TASK]\n', '[A4 FINAL OUTPUT]\n', '[BOUNDARY]\n')


def _section(text, name):
    """One served section, from its own header to the next blank-line header."""
    i = text.index('\n' + name) + 1
    return text[i:]


def problems(p):
    """Every property the context-clarified prefix must have, as a list."""
    bad = []
    # the new instruction must be PRESENT, and exactly once - absence of old
    # wording is not a test (the SEQ 2064 lesson).
    if p.count(V3.CLARIFICATION_BLOCK) != 1:
        bad.append('the source-context sentence is served %d times, not once'
                   % p.count(V3.CLARIFICATION_BLOCK))
    if V3.SPAN_NEW not in p:
        bad.append('the clarified role span is not the one this version writes')
    # what the repair must NOT weaken: every sentence of the role paragraph
    # and the split cap survive word for word.
    if V3.TARGET_SENTENCE not in p:
        bad.append('the located-target-only scope was lost')
    if 'it is NOT a request to find other' not in p:
        bad.append('the ban on discovering adjacent facts was lost')
    if V2.SPAN_A_NEW not in p:
        bad.append('the split cap was lost')
    if 'never copy, choose,' not in p:
        bad.append('the fixed-location restriction was lost')
    if 'abstain instead' not in p:
        bad.append('the abstention restriction was lost')
    if V2.SPAN_B_NEW.split('\n\n')[1] not in p:
        bad.append("V2's completion instruction was lost")
    # the sections still appear exactly once each
    for s in SECTIONS + ('[ROLE]\n',):
        if ('\n' + p).count('\n' + s) != 1:
            bad.append('section %s appears %d times, not once'
                       % (s.strip(), ('\n' + p).count('\n' + s)))
    return bad


def served(owner=None):
    """The prefix this phase really serves, under the real bound scope."""
    if owner is None:
        owner = os.environ.get('A7_CONTEXT_OWNER')
    with R.final_scope(saved['review_run'], saved['review_package'],
                       bind_role=True), \
            C2023.input_scope(saved['input_binding']):
        bound = C2023.bind(SK.bound(saved['run'], saved['package']),
                           saved['corrections'])
        with RECOV.recovery_scope(saved['recovery'], bound, findings):
            return (V3.served_prefix(bound) if owner == 'new'
                    else V2.served_prefix(bound))


class SourceContextSpan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        #: the RED/GREEN subject, chosen by the environment
        cls.p = served()
        #: the two sides, ALWAYS built, so the span and refusal properties are
        #: judged on the same pair whichever subject is selected and a green
        #: run can never be green because a control was skipped.
        cls.base = served('v2')
        cls.new = served('new')

    # ------------------------------------------------------ the RED ---------
    def test_the_served_prefix_has_every_required_property(self):
        """Under A7_CONTEXT_OWNER=new this is clean; without it the prefix
        served today must FAIL - that is the RED."""
        self.assertEqual(problems(self.p), [])

    def test_the_prefix_served_today_lacks_the_clarification(self):
        """Stated on its own so a RED run names the defect."""
        self.assertNotIn(V3.CLARIFICATION_BLOCK, self.base)
        self.assertNotIn('The target fixes which fact you review', self.base)

    # ------------------------------------------------- exactly one span -----
    def test_exactly_one_span_changes_and_every_other_byte_is_identical(self):
        head, tail = self.base.split(V3.SPAN_OLD, 1)
        self.assertEqual(self.new, head + V3.SPAN_NEW + tail)
        self.assertEqual(len(self.new) - len(self.base),
                         len(V3.SPAN_NEW) - len(V3.SPAN_OLD))

    def test_every_other_served_section_is_byte_identical(self):
        for name in SECTIONS:
            self.assertEqual(_section(self.base, name), _section(self.new, name),
                             'section %s moved' % name.strip())

    def test_the_served_wording_is_the_approved_wording_word_for_word(self):
        """Wrapping may change whitespace and nothing else."""
        self.assertEqual(' '.join(V3.CLARIFICATION_BLOCK.split()),
                         ' '.join(V3.CLARIFICATION.split()))
        self.assertTrue(all(len(l) <= V3.WRAP
                            for l in V3.CLARIFICATION_BLOCK.split('\n')))

    def test_the_renderer_is_a_pure_function_of_its_base(self):
        """No semantic work: same base in, same bytes out, every time."""
        self.assertEqual(served('new'), self.new)
        self.assertEqual(problems(self.new), [])
        self.assertEqual(V3.served_prefix.__module__, V3.__name__)

    # --------------------------------------- the anchor refusals ------------
    def _refuses(self, base, why):
        """Every refusal runs after the intact positive control."""
        self.assertIn(V3.SPAN_NEW, V2._replace_once(
            self.base, V3.SPAN_OLD, V3.SPAN_NEW, 'positive control'))
        with self.assertRaises(ValueError, msg=why):
            V2._replace_once(base, V3.SPAN_OLD, V3.SPAN_NEW, why)

    def test_an_absent_anchor_refuses(self):
        self._refuses(self.base.replace(V3.SPAN_OLD, '', 1), 'absent')

    def test_a_duplicated_anchor_refuses(self):
        self._refuses(self.base.replace(V3.SPAN_OLD, V3.SPAN_OLD * 2, 1),
                      'duplicate')

    def test_a_drifted_anchor_refuses(self):
        """A reworded role sentence must miss, not silently serve the old task."""
        drifted = self.base.replace(V3.TARGET_SENTENCE,
                                    V3.TARGET_SENTENCE.replace('only', 'alone'), 1)
        self._refuses(drifted, 'drifted')

    def test_an_already_inserted_clarification_refuses(self):
        self._refuses(self.new, 'already inserted')

    def test_a_reworded_split_cap_owner_makes_the_anchor_miss(self):
        """The anchor quotes V2's own constant; if that owner moves, refuse."""
        self.assertIn(V2.SPAN_A_NEW.split('\n')[0], V3.SPAN_OLD)
        self._refuses(self.base.replace(V2.SPAN_A_NEW.split('\n')[0],
                                        'Any one of them may yield two facts', 1),
                      'reworded split cap')

    # ------------------------------- the real declaration, over real keys ---
    def test_the_key_declaration_still_names_exactly_the_keys_it_is_given(self):
        """The permitted body keys are DATA: every set below is built from the
        prefix's own declared keys at run time, never a written-out case."""
        with R.final_scope(saved['review_run'], saved['review_package'],
                           bind_role=True), \
                C2023.input_scope(saved['input_binding']):
            bound = C2023.bind(SK.bound(saved['run'], saved['package']),
                               saved['corrections'])
            with RECOV.recovery_scope(saved['recovery'], bound, findings), \
                    R._using(C2023, _served_prefix=V3.served_prefix):
                real = C2023.declared_keys(V3.served_prefix(bound))
                self.assertTrue(real)
                sets = [real, real[:1], list(reversed(real)),
                        real + ['%s_unseen_%d' % (real[0], n)
                                for n in range(len(real))]]
                for keys in sets:
                    p = C2023.correction_prefix(bound, keys)
                    self.assertEqual(C2023.declared_keys(p), keys)
                    self.assertEqual(problems(p), [], keys[:2])


if __name__ == '__main__':
    unittest.main(verbosity=2)
