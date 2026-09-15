"""Two source-rule corrections, preserving the frozen historical renderer.

The existing renderer still owns records, source views, grouping and output
shape. Only its rule prefix and the explicit new input-version pin change.
No call, verdict, key, model choice or scoring rule is implemented here.
"""
import a7_grading_input_correction_2114 as BASE

G = BASE.G
BASE_SHA256 = '32e2f650f56cb77b20c89199bc8cf120181dbc7ff92bdd60014d7abc95a16a2d'

# FINAL_DESIGN 5.2 and 7.1 respectively. These are general grading rules, not
# company/example exceptions. The frozen source clause must occur once.
CORRECTIONS = (
    ('   empty only for the whole company. A period is not a population.',
     '   empty only for the whole company on metric, guidance and surprise\n'
     '   records. For an action, empty means no applicable part; a source-stated\n'
     '   applicable part still belongs in this field. A period is not a population.'),
    ('   streak do not create one. Keep the primary comparison; where prior year and\n'
     '   sequential are both stated, prior year is the baseline. Own-target',
     "   streak do not create one. Keep the source's headline comparison;\n"
     '   use prior year before sequential only to break a tie. Own-target'),
)


def _rules(kind):
    if G._sha_file(BASE.__file__) != BASE_SHA256:
        raise ValueError('the frozen base grading renderer changed')
    if kind not in ('G2', 'G3'):
        raise ValueError('a grading contract is G2 or G3')
    old = BASE.meaning_rules() if kind == 'G2' else BASE.extras_rules()
    new = old
    for before, after in CORRECTIONS:
        new = BASE._replace_once(new, before, after)
    return old, new


def meaning_rules():
    return _rules('G2')[1]


def extras_rules():
    return _rules('G3')[1]


def _version(packet, kind, to_base=False):
    """Lossless rule-prefix conversion on an in-memory copy, never evidence."""
    old, new = _rules(kind)
    current_pin = G._sha_file(__file__)
    source, target = (new, old) if to_base else (old, new)
    expected_pin, target_pin = ((current_pin, BASE_SHA256) if to_base
                                else (BASE_SHA256, current_pin))
    prompt = packet.get('prompt')
    if (packet.get('input_correction_sha256') != expected_pin
            or not isinstance(prompt, str) or not prompt.startswith(source)
            or packet.get('prompt_sha256') != G._sha(prompt)):
        raise ValueError('the packet does not bind its grading rules and version')
    prompt = target + prompt[len(source):]
    return dict(packet, prompt=prompt, prompt_sha256=G._sha(prompt),
                input_correction_sha256=target_pin)


def meaning_packet(*args, **kwargs):
    return _version(BASE.meaning_packet(*args, **kwargs), 'G2')


def extras_packet(*args, **kwargs):
    return _version(BASE.extras_packet(*args, **kwargs), 'G3')


def batch_packet(kind, packets):
    # The same frozen batch owner requires its own input version. Reconstruct
    # that exact prefix on copies after checking OUR version, let it group the
    # unchanged evidence, then apply the two rules to the final batch. Neither
    # historical packets nor current inputs are relabelled or mutated on disk.
    base_packets = [_version(packet, kind, to_base=True) for packet in packets]
    return _version(BASE.batch_packet(kind, base_packets), kind)


# These concepts have one implementation, unchanged in the existing owner.
record_view = BASE.record_view
matched_inventory = BASE.matched_inventory
eligible_comparators = BASE.eligible_comparators
