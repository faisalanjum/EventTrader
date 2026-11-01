"""Read-only filing metadata pilot. Input is a report URL/accession, not a company rule.

All text comes from published XBRL resources. Arelle resolves schemas and effective
relationships. Additional documentation comes from the matching publisher/version
entry points. Numeric facts are used only to audit identity; tagged company text
blocks are exported separately and never promoted to unrelated definitions.
"""
import collections
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urldefrag

from arelle import Cntlr, ModelDocument, XbrlConst
from lxml import etree
from neo4j import READ_ACCESS, Query

OUT = Path(__file__).parent
NS = {'link':'http://www.xbrl.org/2003/linkbase','xlink':'http://www.w3.org/1999/xlink','xs':'http://www.w3.org/2001/XMLSchema'}
XL = '{'+NS['xlink']+'}'
DOC = XbrlConst.documentationLabel
FACT_QUERY = """
MATCH (r:Report {id:$accession, accessionNo:$accession})-[:HAS_XBRL]->(x:XBRLNode)<-[:REPORTS]-(f:Fact)
OPTIONAL MATCH (f)-[hc:HAS_CONCEPT]->(c)
RETURN f.id AS uid, f.fact_id AS source_id, f.qname AS qname, f.context_id AS context_id,
       count(hc) AS concept_link_count,
       collect(CASE WHEN c IS NOT NULL THEN {id:c.id,qname:c.qname,namespace:c.namespace} ELSE null END) AS linked_concepts
ORDER BY source_id
"""
NODE_QUERY = """
UNWIND $ids AS uid MATCH (n {id:uid})
WHERE n:Concept OR n:Abstract OR n:Dimension OR n:Domain OR n:Member OR n:HyperCube OR n:LineItems OR n:Other OR n:Guidance
RETURN DISTINCT labels(n) AS labels,n.id AS id,n.qname AS qname,n.namespace AS namespace,n.label AS label
"""
DIRECT_QUERY = """
MATCH (x:XBRLNode {id:$instance_url, accessionNo:$accession})<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT|FACT_DIMENSION|FACT_MEMBER]->(n)
RETURN DISTINCT labels(n) AS labels,n.id AS id,n.qname AS qname,n.namespace AS namespace,n.label AS label
"""

def key(concept):
    return concept.qname.clarkNotation

def same_expanded_name(source_key, graph_concept):
    name = etree.QName(source_key)
    return graph_concept.get('namespace')==name.namespace and (graph_concept.get('qname') or '').split(':')[-1]==name.localname

def graph_metadata_key(node):
    """Decode this project's existing IDs; company prefixes are storage scope.

    Used only for candidate nodes or nodes already linked to this report, never
    to search unrelated companies by a short label or local name alone.
    """
    qname, uid = node.get('qname'), node.get('id')
    if not isinstance(qname,str) or not isinstance(uid,str) or not uid.endswith(':'+qname):
        return None
    encoded_namespace = re.sub(r'^\d+:','',uid[:-len(qname)-1],count=1)
    namespace = node.get('namespace') or encoded_namespace
    if namespace != encoded_namespace or not namespace:
        return None
    return '{'+namespace+'}'+qname.rsplit(':',1)[-1]

def controller_for(name):
    controller = Cntlr.Cntlr(logFileName=str(OUT/(name+'_arelle.log')),disable_persistent_config=True)
    controller.webCache.httpUserAgent = 'EventTrader faianjum@gmail.com'
    controller.webCache.timeout = 30
    return controller

def standard_entrypoint(namespace, schema_url):
    match = re.fullmatch(r'https?://fasb.org/((?:us-gaap|srt)(?:-ebp|-sup)?)/([^/]+)',namespace)
    if match:
        family, version = match.groups()
        # Publisher supplementary packages are standalone schemas; their
        # published package indexes contain no separate "all" entry point.
        if family.endswith('-sup'):
            return schema_url
        return urljoin(schema_url,f'{family}-all-{version}.xsd')
    match = re.fullmatch(r'https?://xbrl.sec.gov/([a-z]+)/([^/]+)',namespace)
    if match:
        family, version = match.groups()
        return urljoin(schema_url,f'{family}-entire-{version}.xsd')
    return None

def filing_inventory(model, base):
    by_key = {key(c):c for c in model.qnameConcepts.values()}
    inventory = set()
    for doc in model.urlDocs.values():
        if not doc.uri.startswith(base):
            continue
        inventory.update(key(c) for c in model.qnameConcepts.values() if c.modelDocument is doc)
        for loc in doc.xmlRootElement.iterfind('.//link:loc',NS):
            url, fragment = urldefrag(urljoin(doc.uri,loc.get(XL+'href')))
            target = model.urlDocs.get(url)
            concept = target.idObjects.get(fragment) if target is not None else None
            if concept is None or not hasattr(concept,'qname'):
                raise ValueError(f'Unresolved filing locator: {doc.uri} {url}#{fragment}')
            inventory.add(key(concept))
    for fact in model.factsInInstance:
        if fact.concept is None:
            raise ValueError(f'Unresolved fact concept: {fact.id}')
        inventory.add(key(fact.concept))
    for context in model.contexts.values():
        for dim in context.qnameDims.values():
            inventory.add(dim.dimensionQname.clarkNotation)
            if dim.isExplicit:
                inventory.add(dim.memberQname.clarkNotation)
    if not inventory <= by_key.keys():
        raise ValueError('Unresolved dimensions or members: '+str(inventory-by_key.keys()))
    return {k:by_key[k] for k in sorted(inventory)}

def add_documentation_sources(model, concepts, company_base):
    namespaces = {}
    unsupported = []
    for c in concepts.values():
        if c.modelDocument.uri.startswith(company_base):
            continue
        namespaces[c.qname.namespaceURI] = c.modelDocument.uri
    sources = []
    for namespace, schema_url in sorted(namespaces.items()):
        url = standard_entrypoint(namespace,schema_url)
        if url is None:
            unsupported.append(namespace)
            continue
        print('Documentation: '+url,flush=True)
        # Entry points import other schemas with embedded labels. Discover the
        # complete supplemental tree, not just links embedded in its root.
        doc = ModelDocument.load(model,url,isSupplemental=True,isDiscovered=True)
        sources.append({'namespace':namespace,'entrypoint':url,'loaded':doc is not None})
    model.relationshipSets.clear()
    return sources, unsupported

def label_record(rel):
    resource = rel.toModelObject
    return {'text':resource.textValue,'role':resource.role,'language':resource.xmlLang,
            'source_url':resource.modelDocument.uri,'source_path':resource.modelDocument.filepath,
            'line':resource.sourceline,'resource_id':resource.id,
            'link_role':rel.linkrole,'arc_priority':rel.priority}

def filing_structure(model, base):
    relationships = []
    domains = set()
    for arcrole in [XbrlConst.dimensionDomain,XbrlConst.domainMember,XbrlConst.dimensionDefault,
                    XbrlConst.hypercubeDimension,XbrlConst.all,XbrlConst.notAll,XbrlConst.parentChild,XbrlConst.summationItem]:
        for rel in model.relationshipSet(arcrole).modelRelationships:
            if not rel.modelDocument.uri.startswith(base):
                continue
            parent, child = rel.fromModelObject, rel.toModelObject
            if parent is None or child is None or not hasattr(parent,'qname') or not hasattr(child,'qname'):
                raise ValueError('Unresolved filing relationship')
            if arcrole==XbrlConst.dimensionDomain:
                domains.add(key(child))
            relationships.append({'from':key(parent),'to':key(child),'arcrole':arcrole,'link_role':rel.linkrole,
                                  'target_role':rel.targetRole,'source_url':rel.modelDocument.uri,'line':rel.sourceline,
                                  'attributes':dict(rel.arcElement.attrib)})
    roles = [{'uri':uri,'definition':r.definition,'source_url':r.modelDocument.uri,'line':r.sourceline}
             for uri,items in model.roleTypes.items() for r in items if r.modelDocument.uri.startswith(base)]
    return relationships, roles, domains

def metadata_rows(model, concepts, base, cik, structure):
    relationships, roles, domains = structure
    labels = model.relationshipSet(XbrlConst.conceptLabel)
    refs = model.relationshipSet(XbrlConst.conceptReference)
    rows = []
    for k,c in concepts.items():
        category = ('dimension' if c.isDimensionItem else 'table' if c.isHypercubeItem else
                    'domain' if k in domains else 'member' if c.type is not None and c.type.isDomainItemType else
                    'abstract_or_line_items' if c.isAbstract else 'concept')
        label_rows = [label_record(rel) for rel in labels.fromModelObject(c)]
        documentation = [r for r in label_rows if r['role']==DOC]
        label_texts = {r['text'] for r in label_rows if r['role']==XbrlConst.standardLabel}
        reference_rows = []
        for rel in refs.fromModelObject(c):
            resource = rel.toModelObject
            reference_rows.append({'role':resource.role,'source_url':resource.modelDocument.uri,'line':resource.sourceline,
                                   'parts':[{'name':etree.QName(p).localname,'text':''.join(p.itertext())} for p in resource]})
        uid = c.qname.namespaceURI+':'+str(c.qname)
        typed = c.typedDomainElement if c.isTypedDimension else None
        row = {'key':k,'qname':str(c.qname),'namespace':c.qname.namespaceURI,'local_name':c.qname.localName,
               'custom':c.modelDocument.uri.startswith(base),'category':category,
               'schema_url':c.modelDocument.uri,'schema_path':c.modelDocument.filepath,'schema_line':c.sourceline,
               'schema_attributes':dict(c.attrib),'type':str(c.typeQname),'period_type':c.periodType,'balance':c.balance,
               'documentation':documentation,'documentation_status':'present' if documentation else 'absent',
               'documentation_equals_label':bool(documentation) and all(r['text'] in label_texts for r in documentation),
               'schema_documentation':[''.join(n.itertext()) for n in c.findall('.//xs:documentation',NS)],
               'labels':label_rows,'references':reference_rows,'candidate_graph_ids':[uid,str(int(cik))+':'+uid],
               'typed_domain':{'key':key(typed),'xml':etree.tostring(typed,encoding='unicode',with_tail=False),
                               'source_url':typed.modelDocument.uri,'line':typed.sourceline} if typed is not None else None}
        rows.append(row)
    return rows, relationships, roles

def audit_facts(model, facts, rows):
    tree = etree.parse(model.modelDocument.filepath,
                       etree.XMLParser(huge_tree=True, resolve_entities=False, no_network=True))
    source_facts = [e for e in tree.getroot().iter() if e.get('contextRef') is not None]
    by_id = collections.defaultdict(list)
    by_tuple = collections.defaultdict(list)
    by_concept_context = collections.defaultdict(list)
    arelle_by_line = collections.defaultdict(list)
    for e in source_facts:
        by_id[e.get('id')].append(e)
        by_tuple[(e.tag,e.get('contextRef'),e.get('unitRef'))].append(e)
        by_concept_context[(e.tag,e.get('contextRef'))].append(e)
    for original in model.factsInInstance:
        arelle_by_line[getattr(original,'sourceline',None)].append(original)
    by_key = {r['key']:r for r in rows}
    matched_source_objects = set()
    concept_groups = collections.defaultdict(lambda:{'source_ids':[],'namespaces':set(),'graph_concept_ids':set()})
    for fact in facts:
        issues = []
        matches = by_id[fact['source_id']]
        fact['source_match_method'] = 'xml_id'
        # XML fact IDs are optional. The graph stores absent IDs as "null".
        # Resolve only a unique exact concept/context; never select an arbitrary
        # duplicate or use this fallback to hide an incorrect nonempty ID.
        if fact['source_id'] in (None,'null') and (fact['source_id'] is None or not matches):
            linked = fact['linked_concepts']
            matches = []
            if len(linked)==1 and linked[0].get('namespace') and linked[0].get('qname'):
                expanded = '{'+linked[0]['namespace']+'}'+linked[0]['qname'].rsplit(':',1)[-1]
                matches = by_concept_context[(expanded,fact['context_id'])]
            fact['source_match_method'] = 'unique_concept_context'
        if len(matches)!=1:
            issues.append('source_id_not_unique_or_absent')
        if fact['concept_link_count']!=1:
            issues.append('missing_or_multiple_concept_links')
        if len(matches)==1:
            source = matches[0]
            matched_source_objects.add(id(source))
            fact['source_key'] = source.tag
            fact['source_line'] = source.sourceline
            if source.get('contextRef')!=fact['context_id']:
                issues.append('context_mismatch')
            if etree.QName(source).localname!=(fact['qname'] or '').split(':')[-1]:
                issues.append('fact_name_mismatch')
            for linked in fact['linked_concepts']:
                if not same_expanded_name(source.tag,linked):
                    issues.append('concept_name_or_version_mismatch')
            original = model.modelDocument.idObjects.get(fact['source_id'])
            if fact['source_match_method']=='unique_concept_context':
                candidates = [f for f in arelle_by_line[source.sourceline]
                              if f.qname.clarkNotation==source.tag and f.contextID==source.get('contextRef')]
                original = candidates[0] if len(candidates)==1 else None
            if original is None or original.qname.clarkNotation!=source.tag:
                issues.append('arelle_raw_xml_identity_disagrees')
            else:
                fact['schema_url'] = original.concept.modelDocument.uri
            metadata = by_key.get(source.tag)
            if metadata is None:
                issues.append('fact_concept_absent_from_inventory')
            fact['documentation_present'] = bool(metadata and metadata['documentation'])
            group = concept_groups[(fact['qname'] or '').split(':')[-1]]
            group['source_ids'].append(fact['source_id'])
            group['namespaces'].add(etree.QName(source).namespace)
            group['graph_concept_ids'].update(r['id'] for r in fact['linked_concepts'])
        fact['issues'] = issues
    omitted = []
    for source in source_facts:
        if id(source) in matched_source_objects:
            continue
        peers = [p for p in by_tuple[(source.tag,source.get('contextRef'),source.get('unitRef'))] if id(p) in matched_source_objects]
        same_value = [p for p in peers if ''.join(p.itertext())==''.join(source.itertext()) and p.get('{http://www.w3.org/2001/XMLSchema-instance}nil')==source.get('{http://www.w3.org/2001/XMLSchema-instance}nil')]
        reason = ('hidden_fact_excluded_by_importer' if (source.get('id') or '').startswith('hidden-fact') else
                  'exact_duplicate_of_stored_fact' if same_value else 'duplicate_key_with_different_value' if peers else 'unexplained')
        omitted.append({'source_id':source.get('id'),'source_key':source.tag,'reason':reason,
                        'stored_equivalent_ids':[p.get('id') for p in (same_value or peers)]})
    groups = []
    for name,group in sorted(concept_groups.items()):
        groups.append({'local_name':name,'source_ids':sorted(group['source_ids'],key=lambda value: str(value)),
                       'namespaces':sorted(group['namespaces']),'graph_concept_ids':sorted(group['graph_concept_ids'])})
    return {'facts':facts,'concept_to_facts':groups,'omitted_source_facts':omitted,'source_fact_count':len(source_facts),
            'xml_instance_fact_count_matches_arelle':len(source_facts)==len(model.factsInInstance)}

def run_report(report, driver, controller=None):
    ticker = report['ticker']
    print('Auditing '+ticker,flush=True)
    owns_controller = controller is None
    controller = controller or controller_for(report['accession'])
    model = None
    try:
        model = controller.modelManager.load(report['instance_url'])
        if model.modelDocument is None or model.errors:
            raise RuntimeError(f'Filing failed to load: {ticker}: {model.errors}')
        base = report['instance_url'].rsplit('/',1)[0]+'/'
        concepts = filing_inventory(model,base)
        # Supplemental packages can include standard networks. Keep the original
        # filing networks before adding publisher documentation and references.
        structure = filing_structure(model,base)
        supplement_sources, unsupported = add_documentation_sources(model,concepts,base)
        rows, relationships, roles = metadata_rows(model,concepts,base,report['cik'],structure)
        # A text block describes its explicitly tagged concept. Do not infer links
        # to other numeric concepts, dimensions or members from prose or proximity.
        passages = []
        for fact in model.factsInInstance:
            if fact.concept is not None and fact.concept.isTextBlock and not fact.isNil:
                passages.append({'concept_key':key(fact.concept),'fact_id':fact.id,
                                 'context_id':fact.contextID,'text':fact.value,
                                 'text_format':'xbrl_fact_value_may_contain_html',
                                 'source_url':fact.modelDocument.uri,'source_line':fact.sourceline,
                                 'accession':report['accession'],'association':'explicit_fact_concept'})
        with driver.session(default_access_mode=READ_ACCESS) as session:
            facts = session.run(Query(FACT_QUERY,timeout=45),accession=report['accession']).data()
            ids = sorted({i for r in rows for i in r['candidate_graph_ids']})
            graph_nodes = session.run(Query(NODE_QUERY,timeout=60),ids=ids).data()
            direct_nodes = session.run(Query(DIRECT_QUERY,timeout=45),accession=report['accession'],instance_url=report['instance_url']).data()
        nodes_by_id = {r['id']:r for r in graph_nodes+direct_nodes}
        nodes_by_key = collections.defaultdict(list)
        for node in nodes_by_id.values():
            nodes_by_key[graph_metadata_key(node)].append(node)
        for row in rows:
            row['graph_nodes'] = nodes_by_key[row['key']]
        matched_ids = {n['id'] for row in rows for n in row['graph_nodes']}
        fact_audit = audit_facts(model,facts,rows)
        source_manifest = []
        for doc in model.urlDocs.values():
            path = Path(doc.filepath)
            if path.exists():
                source_manifest.append({'url':doc.uri,'path':str(path),'bytes':path.stat().st_size,
                                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'filing_owned':doc.uri.startswith(base)})
        schema_imports = [{'source_url':doc.uri,'namespace':doc.targetNamespace,
                           'imports':[dict(n.attrib) for n in doc.xmlRootElement.findall('xs:import',NS)]}
                          for doc in model.urlDocs.values() if doc.uri.startswith(base) and doc.uri.endswith('.xsd')]
        missing = [r for r in rows if not r['documentation']]
        summary = {**report,'metadata_elements':len(rows),'company_elements':sum(r['custom'] for r in rows),
                   'documentation_present':len(rows)-len(missing),'documentation_absent':len(missing),
                   'company_documentation_present':sum(r['custom'] and bool(r['documentation']) for r in rows),
                   'company_documentation_equals_label':sum(r['custom'] and r['documentation_equals_label'] for r in rows),
                   'category_counts':dict(collections.Counter(r['category'] for r in rows)),
                   'coverage_by_category':{cat:dict(collections.Counter(r['documentation_status'] for r in rows if r['category']==cat)) for cat in sorted({r['category'] for r in rows})},
                   'missing_by_namespace':dict(collections.Counter(r['namespace'] for r in missing)),
                   'missing_with_reference':sum(bool(r['references']) for r in missing),
                   'missing_with_schema_documentation':sum(bool(r['schema_documentation']) for r in missing),
                   'role_count':len(roles),'relationship_count':len(relationships),'typed_dimension_count':sum(r['typed_domain'] is not None for r in rows),
                   'matched_graph_metadata':sum(bool(r['graph_nodes']) for r in rows),
                   'direct_graph_metadata_count':len(direct_nodes),'unmatched_direct_graph_metadata':[n for n in direct_nodes if n['id'] not in matched_ids],
                   'stored_facts':len(facts),'source_facts':fact_audit['source_fact_count'],
                   'fact_concepts':len(fact_audit['concept_to_facts']),
                   'fact_namespaces':dict(collections.Counter(etree.QName(f['source_key']).namespace for f in facts if 'source_key' in f)),
                   'fact_mismatches':sum(bool(f['issues']) for f in facts),
                   'source_omission_reasons':dict(collections.Counter(r['reason'] for r in fact_audit['omitted_source_facts'])),
                   'unexplained_source_facts':sum(r['reason']=='unexplained' for r in fact_audit['omitted_source_facts']),
                   'same_local_name_multiple_namespaces':[g for g in fact_audit['concept_to_facts'] if len(g['namespaces'])>1],
                   'facts_with_documentation':sum(f.get('documentation_present',False) for f in facts),
                   'load_errors':list(model.errors),'unsupported_namespaces':unsupported,'read_only':True}
        summary['company_passages'] = len(passages)
        summary['company_passage_concepts'] = len({p['concept_key'] for p in passages})
        result = {'summary':summary,'elements':rows,'relationships':relationships,'roles':roles,
                  'company_schema_imports':schema_imports,'documentation_entrypoints':supplement_sources,
                  'source_manifest':source_manifest,'direct_graph_metadata':direct_nodes,**fact_audit,
                  'company_passages':passages,
                  'notes':['Inventory includes filing-owned declarations, linkbase locators, fact concepts, and context dimensions/members.',
                           'Documentation is copied from effective documentation-role labels; absence is separate from load errors.',
                           'Taxonomy identity is namespace plus local name; company labels never replace standard source identities.',
                           'Numeric fact values are not exported. Tagged company text blocks are separate report passages, not universal definitions.',
                           'Source identity does not establish which historical parser software version executed.'],
                  'read_only_queries':[FACT_QUERY,NODE_QUERY,DIRECT_QUERY]}
        result['source_notices'] = json.loads(Path(__file__).with_name('source_notices.json').read_text())
        return result
    finally:
        try:
            if model is not None:
                controller.modelManager.close(model)
        finally:
            if owns_controller:
                controller.close()
