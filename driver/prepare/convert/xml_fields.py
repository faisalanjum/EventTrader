"""XML route (agreement point 4): one `field` unit per element that carries text, from the standard library's strict XML parser (expat):
the element's expanded name `{namespace}local`, its ancestors' expanded names, the instance it belongs to (the nearest repeated ancestor: its
place among same-named siblings, "2 of 8", and the byte of its start tag, which tells two first children of two parents apart), the element's
own place among its siblings, its text, and the byte span from its start tag to the end of its text. Units stand in source order. An element whose
own text stands around child elements is read whole as prose (`mixed`) and its children stay fields of their own, each naming the prose unit it
stands `within`: the reading stream is the units held by no other, each source character once; field lookups see every unit (Codex R13 C4).
The same parse gives the structure the units stand in, `xml_elements`: every element in document order, containers and empty ones too, with
its expanded `name`; its `parent`, the parent's start byte (null for the root); its `anchor`, the units' convention (its start tag's first byte
to its end tag's first byte, or to the end of an empty-element tag); its `attributes` by expanded name as the parser reports them (references
replaced, white space normalized, a default the document's own DTD declares included: values, never byte slices of the source; an empty value
kept); the namespace bindings the parser reports for its start tag (`namespaces`: declared there, or by a default of the DTD; prefix '' the
default namespace, uri '' undeclared; the bindings in force are found through the parents); and its direct `content` in source order, where a string is a run of its own character data (adjacent parser
callbacks joined, CDATA as text; comments and processing instructions are not kept) and {"child": start byte} the child element standing
there. A key that would hold nothing is left out. The tree is given only for a complete parse. No field list, nothing inferred, nothing
repaired: a document that does not parse is reported FAILED with the parser's own message. The parser is the grader's own (`anchor.xml_parser`):
what stands outside the document is refused, so a reading that would need it fails instead of going on without it; an element the parser
makes from an entity's text has no bytes of its own, and the document is refused rather than given a position that is none."""
import time
from copy import deepcopy
import xml.parsers.expat as expat

from driver.prepare.convert.anchor import check_source, xml_parser

NAME = 'xml-fields'


def clark(name):
    return '{' + name if '}' in name else name


def units_of(raw, facts=None, *, elements=None):
    """Field units of one XML document; raises ExpatError, ValueError or LookupError for invalid XML or an unsupported encoding. `facts`, when
    given, receives what the route does not read (`attribute_values`: none once `elements` keeps them). `elements`, a list, receives the element
    tree of the module's description, only when the whole document parses."""
    p = xml_parser(namespace_separator='}'); stack, leaves, root_counts, attrs, tree, declared = [], [], {}, 0, [], {}
    p.StartNamespaceDeclHandler = lambda prefix, uri: declared.update({prefix or '': uri or ''})
    def start(name, a):
        nonlocal attrs; attrs += sum(1 for v in a.values() if v.strip())
        parent = stack[-1]['counts'] if stack else root_counts; parent[name] = parent.get(name, 0) + 1
        node = {'name': clark(name), 'parent': stack[-1]['start_tag'] if stack else None, 'anchor': {'byte_start': p.CurrentByteIndex}}
        if a: node['attributes'] = {clark(k): v for k, v in a.items()}
        if declared: node['namespaces'] = dict(declared); declared.clear()  # the bindings this start tag declares (the parser reports them just before it)
        if stack: stack[-1]['content'].append({'child': p.CurrentByteIndex})
        tree.append(node)
        stack.append({'name': name, 'index': parent[name], 'parent_counts': parent, 'counts': {}, 'own': [], 'parts': [], 'start_tag': p.CurrentByteIndex, 'mark': len(leaves), 'node': node, 'content': []})
    def data(text):
        fr = stack[-1]; fr['own'].append(text); fr['parts'].append(text)
        if fr['content'] and isinstance(fr['content'][-1], list): fr['content'][-1].append(text)  # pieces of one run, joined once at the end
        else: fr['content'].append([text])
    def end(name):
        fr = stack.pop(); text = ''.join(fr['parts'])
        if p.CurrentByteIndex <= fr['start_tag']: raise expat.ExpatError('an element with no bytes of its own (markup from an entity) has no source position')
        fr['node']['anchor']['byte_end_exclusive'] = p.CurrentByteIndex
        if fr['content']: fr['node']['content'] = [''.join(x) if isinstance(x, list) else x for x in fr['content']]
        if stack: stack[-1]['parts'].append(text)  # a parent that is prose sees its children's text in place
        if not ''.join(fr['own']).strip(): return  # no text of its own: a container of elements, or empty
        leaf = {'name': fr['name'], 'index': fr['index'], 'siblings': fr['parent_counts'], 'ancestors': [(a['name'], a['index'], a['parent_counts'], a['start_tag']) for a in stack], 'mixed': len(leaves) > fr['mark'],
                'text': text.strip(), 'anchor': {'byte_start': fr['start_tag'], 'byte_end_exclusive': p.CurrentByteIndex}}  # from the element's own start tag to the end of its text; an element with text of its own around child elements is read whole as prose AND its children stay fields of their own
        for child in leaves[fr['mark']:]: child.setdefault('within', leaf)  # the nearest prose ancestor reads the child's text in place
        leaves.append(leaf)
    p.StartElementHandler, p.EndElementHandler, p.CharacterDataHandler = start, end, data
    p.Parse(raw, True)
    if elements is not None: elements.extend(tree)
    if facts is not None: facts['attribute_values'] = attrs if elements is None else 0
    order = sorted(leaves, key=lambda leaf: leaf['anchor']['byte_start']); ids = {id(leaf): f'f{i}' for i, leaf in enumerate(order)}  # source order: prose before the fields inside it
    out = []
    for leaf in order:
        group = next(({'index': idx, 'count': counts[name], 'at': at} for name, idx, counts, at in reversed(leaf['ancestors']) if counts[name] > 1), None) \
            or {'index': 1, 'count': 1, 'at': leaf['ancestors'][0][3] if leaf['ancestors'] else leaf['anchor']['byte_start']}  # no repeated ancestor: the document is the instance
        out.append({'id': ids[id(leaf)], 'kind': 'field', 'name': clark(leaf['name']), 'path': [clark(n) for n, _, _, _ in leaf['ancestors']], 'group': group,
                    'siblings': {'index': leaf['index'], 'count': leaf['siblings'][leaf['name']]}, 'text': leaf['text'], 'anchor': leaf['anchor'],
                    **({'mixed': True} if leaf['mixed'] else {}), **({'within': ids[id(leaf['within'])]} if leaf.get('within') else {})})
    return out


ROUTE = {'name': NAME, 'tool': 'python xml.parsers.expat', 'version': expat.EXPAT_VERSION, 'settings': {'namespaces': True, 'recover': False},
         'adapter': 'driver/prepare/convert/xml_fields.py', 'linker': None}


def convert(raw, file_id, sha256):
    """One XML document into its route (`units_of`, the caller's bytes, with its element tree): a document that does not parse is a FAILED route
    with the parser's own message and no tree; bytes the hash does not name raise ValueError before any parse."""
    check_source(raw, sha256)
    t0 = time.time(); doc = {'schema': 'prepare-route-output/1', 'file_id': file_id, 'sha256': sha256, 'status': 'OK', 'error': None, 'route': deepcopy(ROUTE), 'units': []}
    try:
        tree = []; doc['units'] = units_of(raw, elements=tree); doc['xml_elements'] = tree  # every attribute kept in the tree: nothing left unread to state
    except (expat.ExpatError, ValueError, LookupError) as e: doc['status'], doc['error'] = 'FAILED', f'XML parse failed: {e}'
    doc['seconds'] = round(time.time() - t0, 3)
    return doc
