"""XML route (agreement point 4): one `field` unit per element that carries text, from the standard library's strict XML parser (expat):
the element's expanded name `{namespace}local`, its ancestors' expanded names, the instance it belongs to (the nearest repeated ancestor: its
place among same-named siblings, "2 of 8", and the byte of its start tag, which tells two first children of two parents apart), the element's
own place among its siblings, its text, and the byte span from its start tag to the end of its text. Units stand in source order. An element whose
own text stands around child elements is read whole as prose (`mixed`) and its children stay fields of their own, each naming the prose unit it
stands `within`: the reading stream is the units held by no other, each source character once; field lookups see every unit (Codex R13 C4).
Attribute values are not read; their count is reported as `not_read` so the omission is visible. No field list, nothing inferred, nothing
repaired: a document that does not parse is reported FAILED with the parser's own message. The parser is the grader's own (`anchor.xml_parser`):
what stands outside the document is refused, so a reading that would need it fails instead of going on without it; an element the parser
makes from an entity's text has no bytes of its own, and the document is refused rather than given a position that is none."""
import xml.parsers.expat as expat

from driver.prepare.convert.anchor import xml_parser

NAME = 'xml-fields'


def clark(name):
    return '{' + name if '}' in name else name


def units_of(raw, facts=None):
    """Field units of one XML document; raises ExpatError, ValueError or LookupError for invalid XML or an unsupported encoding. `facts`, when
    given, receives what the route does not read (`attribute_values`)."""
    p = xml_parser(namespace_separator='}'); stack, leaves, root_counts, attrs = [], [], {}, 0
    def start(name, a):
        nonlocal attrs; attrs += sum(1 for v in a.values() if v.strip())
        parent = stack[-1]['counts'] if stack else root_counts; parent[name] = parent.get(name, 0) + 1
        stack.append({'name': name, 'index': parent[name], 'parent_counts': parent, 'counts': {}, 'own': [], 'parts': [], 'start_tag': p.CurrentByteIndex, 'mark': len(leaves)})
    def data(text):
        fr = stack[-1]; fr['own'].append(text); fr['parts'].append(text)
    def end(name):
        fr = stack.pop(); text = ''.join(fr['parts'])
        if p.CurrentByteIndex <= fr['start_tag']: raise expat.ExpatError('an element with no bytes of its own (markup from an entity) has no source position')
        if stack: stack[-1]['parts'].append(text)  # a parent that is prose sees its children's text in place
        if not ''.join(fr['own']).strip(): return  # no text of its own: a container of elements, or empty
        leaf = {'name': fr['name'], 'index': fr['index'], 'siblings': fr['parent_counts'], 'ancestors': [(a['name'], a['index'], a['parent_counts'], a['start_tag']) for a in stack], 'mixed': len(leaves) > fr['mark'],
                'text': text.strip(), 'anchor': {'byte_start': fr['start_tag'], 'byte_end_exclusive': p.CurrentByteIndex}}  # from the element's own start tag to the end of its text; an element with text of its own around child elements is read whole as prose AND its children stay fields of their own
        for child in leaves[fr['mark']:]: child.setdefault('within', leaf)  # the nearest prose ancestor reads the child's text in place
        leaves.append(leaf)
    p.StartElementHandler, p.EndElementHandler, p.CharacterDataHandler = start, end, data
    p.Parse(raw, True)
    if facts is not None: facts['attribute_values'] = attrs
    order = sorted(leaves, key=lambda leaf: leaf['anchor']['byte_start']); ids = {id(leaf): f'f{i}' for i, leaf in enumerate(order)}  # source order: prose before the fields inside it
    out = []
    for leaf in order:
        group = next(({'index': idx, 'count': counts[name], 'at': at} for name, idx, counts, at in reversed(leaf['ancestors']) if counts[name] > 1), None) \
            or {'index': 1, 'count': 1, 'at': leaf['ancestors'][0][3] if leaf['ancestors'] else leaf['anchor']['byte_start']}  # no repeated ancestor: the document is the instance
        out.append({'id': ids[id(leaf)], 'kind': 'field', 'name': clark(leaf['name']), 'path': [clark(n) for n, _, _, _ in leaf['ancestors']], 'group': group,
                    'siblings': {'index': leaf['index'], 'count': leaf['siblings'][leaf['name']]}, 'text': leaf['text'], 'anchor': leaf['anchor'],
                    **({'mixed': True} if leaf['mixed'] else {}), **({'within': ids[id(leaf['within'])]} if leaf.get('within') else {})})
    return out
