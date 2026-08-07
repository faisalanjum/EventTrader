"""XML NCName / QName grammar — THE one shared standards owner (#827 B8, SEQ 340).

Two functions, moved verbatim from the renderer (driver/relocation/inline_html.py)
because Core and relocation both need this grammar and neither should import a heavy
rendering module — or restate the standard as a regex — to ask it. XML NCName/QName
legality is this module's single responsibility.
"""
from lxml import etree


def xml_name_ok(name):
    """Is `name` a lawful XML NCName? ASKED OF THE XML LIBRARY, never re-graphed.

    THE HANDWRITTEN ASCII REGEX THAT STOOD HERE WAS WRONG, not merely
    duplicated: the NCName production permits Unicode, so `Ünïcode` and `Wért`
    are lawful names that `[A-Za-z_][A-Za-z0-9_.\\-]*` rejects. Legality is the
    standard's to define and the parser's to enforce, so it is asked here rather
    than restated — one grammar, and it is not ours.
    """
    try:
        etree.QName(None, name)
        return True
    except ValueError:
        return False


def graph_qname_parts(qname):
    """A QName the GRAPH stores, split into (prefix, local), or None.

    THE ONE OWNER of what a stored qname may look like, so every consumer asks
    the same question of the same grammar instead of restating it. The grammar
    itself is not ours: every half must be a lawful NCName, and that is asked
    of the XML library (`xml_name_ok`), never re-graphed as a regex.

    A PREFIX IS OPTIONAL, and requiring one was a corpus-shaped rule, not the
    contract. The writer stores `str(qname)` and Arelle's `QName.__str__` emits
    the LOCAL NAME ALONE when there is no prefix — verified against the
    installed version: `str(QName(None, 'urn:example', 'Revenue')) == 'Revenue'`.
    Every row in today's graph happening to carry a prefix prices that shape; it
    does not make one mandatory. An unprefixed stored qname loses nothing,
    because the namespace lives independently in the composite id.

    The local part is everything after the QName's single colon — Namespaces in
    XML 1.0 3e §4, an NCName may not contain one — so `a:b:c` is not a QName at
    all, and neither is `a: b` or a name padded with whitespace. A divide unit's
    concatenated name is not invertible and is never split this way.
    """
    if not isinstance(qname, str):
        return None
    prefix, sep, local = qname.partition(':')
    if not sep:                                   # lawful: no prefix at all
        return ('', qname) if xml_name_ok(qname) else None
    if not xml_name_ok(prefix) or not xml_name_ok(local):
        return None
    return (prefix, local)
