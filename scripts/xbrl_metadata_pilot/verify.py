"""Independent, read-only checks of exports against the saved publisher XML.

Uses lxml, not the extractor or Arelle. Does not claim to reimplement XBRL's
effective-relationship rules: raw/effective documentation differences are
reported for review, never silently treated as an extraction pass.
"""
import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urljoin, urldefrag
from lxml import etree

# Only immutable URL calculations are cached here; XML bytes are hash-checked.
urljoin = lru_cache(maxsize=65536)(urljoin)
urldefrag = lru_cache(maxsize=65536)(urldefrag)

LINK='http://www.xbrl.org/2003/linkbase'
XS='http://www.w3.org/2001/XMLSchema'
XL='{http://www.w3.org/1999/xlink}'
XML='{http://www.w3.org/XML/1998/namespace}'
DOC='http://www.xbrl.org/2003/role/documentation'
NS={'link':LINK,'xs':XS}


def contents(node):
    return ''.join(node.itertext())


@lru_cache(maxsize=192)
def document(path, modified, size):
    data=Path(path).read_bytes()
    root=etree.fromstring(data,etree.XMLParser(huge_tree=True,resolve_entities=False,no_network=True))
    ids=defaultdict(list)
    lines=defaultdict(list)
    for node in root.iter():
        if not isinstance(node.tag,str): continue
        if node.get('id'): ids[node.get('id')].append(node)
        lines[(node.tag,node.sourceline)].append(node)
    elements={n.get('name'):n for n in root.findall('{'+XS+'}element')}
    return {'sha256':hashlib.sha256(data).hexdigest(),'root':root,'ids':ids,'lines':lines,'elements':elements}


def verify(result):
    started=time.monotonic()
    errors=[]
    graph=[]
    counts=Counter()
    def check(ok,kind,detail):
        if not ok: errors.append({'kind':kind,'detail':detail})
    summary=result['summary']
    accession=summary['accession']
    if result.get('extraction_status')!='complete':
        return {'accession':accession,'source_status':'failed','graph_status':'not_checked',
                'errors':[{'kind':'extraction_incomplete','detail':{
                    'load_errors':result.get('error') or summary.get('load_errors',[]),
                    'unsupported_namespaces':summary.get('unsupported_namespaces',[]),
                    'failed_entrypoints':[s['entrypoint'] for s in result.get('documentation_entrypoints',[]) if not s['loaded']]}}],
                'graph_issues':[],'counts':{}}
    sources={s['url']:s for s in result['source_manifest']}
    docs={}
    for url,source in sources.items():
        path=Path(source['path']);stat=path.stat()
        doc=document(str(path),stat.st_mtime_ns,stat.st_size)
        check(doc['sha256']==source['sha256'],'source_checksum',url)
        docs[url]=doc
    counts['source_files']=len(docs)
    rows={r['key']:r for r in result['elements']}
    check(len(rows)==len(result['elements']),'duplicate_metadata_key',accession)
    @lru_cache(maxsize=None)
    def target(url,href):
        schema,fragment=urldefrag(urljoin(url,href))
        doc=docs.get(schema)
        nodes=doc['ids'].get(fragment,[]) if doc else []
        if len(nodes)!=1:return None
        if nodes[0].tag=='{'+XS+'}element':
            return '{'+doc['root'].get('targetNamespace')+'}'+nodes[0].get('name')
        # Instance footnotes locate facts, whose tags identify their concepts.
        if nodes[0].get('contextRef') is not None:return nodes[0].tag
        return None
    def href(node,url):
        for ancestor in list(node.iterancestors())[::-1]+[node]:
            if ancestor.get(XML+'base'):url=urljoin(url,ancestor.get(XML+'base'))
        return urljoin(url,node.get(XL+'href'))
    associations=set()
    raw_documentation=set()
    raw_structure=set()
    expected_inventory=set()
    company_base=summary['instance_url'].rsplit('/',1)[0]+'/'
    for url,doc in docs.items():
        root=doc['root']
        if url.startswith(company_base):
            if root.tag=='{'+XS+'}schema':
                expected_inventory.update('{'+root.get('targetNamespace')+'}'+n for n in doc['elements'])
            for loc in root.iter('{'+LINK+'}loc'):
                resolved=target(url,href(loc,url))
                check(resolved is not None,'unresolved_raw_locator',url+':'+str(loc.sourceline))
                if resolved:expected_inventory.add(resolved)
        for link in root.iter():
            if not isinstance(link.tag,str) or link.get(XL+'type')!='extended':continue
            locs=defaultdict(list);resources=defaultdict(list)
            for n in link:
                if n.get(XL+'type')=='locator':locs[n.get(XL+'label')].append(target(url,href(n,url)))
                elif n.get(XL+'type')=='resource':resources[n.get(XL+'label')].append(n)
            for arc in link:
                if arc.get(XL+'type')!='arc':continue
                if arc.get('use')=='prohibited':counts['raw_prohibited_arcs']+=1;continue
                for source_key in locs[arc.get(XL+'from')]:
                    for resource in resources[arc.get(XL+'to')]:
                        associations.add((source_key,url,resource.sourceline,resource.tag,
                                          resource.get(XL+'role'),resource.get(XML+'lang'),contents(resource)))
                        if resource.tag=='{'+LINK+'}label' and resource.get(XL+'role')==DOC:
                            raw_documentation.add(source_key)
                    if url.startswith(company_base):
                        for end in locs[arc.get(XL+'to')]:
                            raw_structure.add((source_key,end,arc.get(XL+'arcrole'),url,arc.sourceline,
                                               tuple(sorted(arc.attrib.items()))))
    for row in rows.values():
        k=row['key'];doc=docs[row['schema_url']];node=doc['elements'].get(row['local_name'])
        check(node is not None,'schema_declaration',k)
        if node is None:continue
        namespace=doc['root'].get('targetNamespace')
        check(k=='{'+namespace+'}'+node.get('name') and row['namespace']==namespace,'metadata_identity',k)
        check(row['qname'].rsplit(':',1)[-1]==node.get('name'),'metadata_qname',k)
        check(dict(node.attrib)==row['schema_attributes'],'schema_attributes',k)
        check(node.get('{http://www.xbrl.org/2003/instance}periodType')==row['period_type'],'period_type',k)
        check(node.get('{http://www.xbrl.org/2003/instance}balance')==row['balance'],'balance',k)
        if node.get('type'):
            check(node.get('type')==row['type'],'declared_type',k)
        check(row['schema_documentation']==[contents(n) for n in node.findall('.//{'+XS+'}documentation')],'schema_documentation',k)
        check(row['custom']==row['schema_url'].startswith(company_base),'company_classification',k)
        expected_docs=[l for l in row['labels'] if l['role']==DOC]
        check(row['documentation']==expected_docs,'documentation_label_subset',k)
        check(row['documentation_status']==('present' if expected_docs else 'absent'),'documentation_status',k)
        check(bool(expected_docs)==(k in raw_documentation),'raw_effective_documentation_difference',k)
        counts['metadata']+=1;counts['documentation_present' if expected_docs else 'documentation_absent']+=1
        counts['category_'+row['category']]+=1
        if row['custom']:counts['company_metadata']+=1
        if expected_docs and row['documentation_equals_label']:counts['documentation_repeats_label']+=1
        for label in row['labels']:
            candidates=docs[label['source_url']]['lines'].get(('{'+LINK+'}label',label['line']),[])
            matching=[n for n in candidates if contents(n)==label['text'] and
                      n.get(XL+'role','http://www.xbrl.org/2003/role/label')==label['role'] and n.get(XML+'lang')==label['language']]
            check(bool(matching),'label_resource',k)
            check(any((k,label['source_url'],n.sourceline,n.tag,n.get(XL+'role'),n.get(XML+'lang'),contents(n)) in associations for n in matching),'label_concept_association',k)
            counts['labels']+=1
        for ref in row['references']:
            candidates=docs[ref['source_url']]['lines'].get(('{'+LINK+'}reference',ref['line']),[])
            matching=[n for n in candidates if n.get(XL+'role','http://www.xbrl.org/2003/role/reference')==ref['role'] and
                      [{'name':etree.QName(p).localname,'text':contents(p)} for p in n]==ref['parts']]
            check(bool(matching),'reference_resource',k)
            check(any((k,ref['source_url'],n.sourceline,n.tag,n.get(XL+'role'),n.get(XML+'lang'),contents(n)) in associations for n in matching),'reference_concept_association',k)
            counts['references']+=1
        typed=row['typed_domain']
        declared=node.get('{http://xbrl.org/2005/xbrldt}typedDomainRef')
        check(bool(typed)==bool(declared),'typed_domain_presence',k)
        if typed:
            tdoc=docs[typed['source_url']];name=etree.QName(typed['key']);tnode=tdoc['elements'].get(name.localname)
            check(tnode is not None and tdoc['root'].get('targetNamespace')==name.namespace,'typed_domain_identity',k)
            if tnode is not None:
                check(etree.tostring(tnode,method='c14n')==etree.tostring(etree.fromstring(typed['xml'].encode()),method='c14n'),'typed_domain_xml',k)
            check(bool(declared) and target(row['schema_url'],declared)==typed['key'],'typed_domain_reference',k)
            counts['typed_dimensions']+=1
        for graph_node in row['graph_nodes']:
            suffix=namespace+':'+graph_node['qname']
            uid=graph_node['id'];prefix=uid[:-len(suffix)] if uid.endswith(suffix) else 'invalid'
            ok=(prefix=='' or (prefix.endswith(':') and prefix[:-1].isdigit()))
            ok=ok and graph_node['qname'].rsplit(':',1)[-1]==node.get('name')
            ok=ok and (not graph_node.get('namespace') or graph_node['namespace']==namespace)
            check(ok,'metadata_graph_identity',graph_node['id']);counts['graph_metadata_links']+=1
    published_docs={a for a in associations if a[0] in rows and a[3]=='{'+LINK+'}label' and a[4]==DOC}
    exported_docs={(r['key'],d['source_url'],d['line'],'{'+LINK+'}label',d['role'],d['language'],d['text'])
                   for r in rows.values() for d in r['documentation']}
    for missing in published_docs-exported_docs:
        check(False,'raw_effective_documentation_resource_difference',{'key':missing[0],'url':missing[1],'line':missing[2]})
    instance=docs[summary['instance_url']]
    source_facts=[n for n in instance['root'].iter() if n.get('contextRef') is not None]
    facts_by_concept_context=defaultdict(list)
    for n in source_facts:
        facts_by_concept_context[(n.tag,n.get('contextRef'))].append(n)
    expected_inventory.update(n.tag for n in source_facts)
    for member in instance['root'].iter():
        if member.tag not in ('{http://xbrl.org/2006/xbrldi}explicitMember','{http://xbrl.org/2006/xbrldi}typedMember'):continue
        values=[member.get('dimension')]
        if member.tag.endswith('explicitMember'):values.append(member.text)
        for value in values:
            prefix,local=value.split(':',1) if ':' in value else (None,value)
            expected_inventory.add('{'+member.nsmap[prefix]+'}'+local)
    check(set(rows)==expected_inventory,'filing_inventory',{'missing':sorted(expected_inventory-set(rows)),'extra':sorted(set(rows)-expected_inventory)})
    check(len(source_facts)==summary['source_facts'] and result['xml_instance_fact_count_matches_arelle'],'instance_fact_count',accession)
    for fact in result['facts']:
        nodes=instance['ids'].get(fact['source_id'],[])
        if fact['source_id'] in (None,'null') and (fact['source_id'] is None or not nodes):
            linked=fact['linked_concepts']
            nodes=[]
            if len(linked)==1 and linked[0].get('namespace') and linked[0].get('qname'):
                expanded='{'+linked[0]['namespace']+'}'+linked[0]['qname'].rsplit(':',1)[-1]
                nodes=facts_by_concept_context[(expanded,fact['context_id'])]
        ok=len(nodes)==1
        if ok:
            n=nodes[0];name=etree.QName(n)
            ok=(n.get('contextRef')==fact['context_id'] and name.localname==(fact['qname'] or '').rsplit(':',1)[-1]
                and len(fact['linked_concepts'])==1 and fact['concept_link_count']==1)
            ok=ok and all(c.get('namespace')==name.namespace and (c.get('qname') or '').rsplit(':',1)[-1]==name.localname for c in fact['linked_concepts'])
        if not ok:graph.append({'kind':'fact_identity','detail':fact['source_id']})
        check(bool(fact['issues'])==(not ok),'fact_audit_agreement',fact['source_id'])
        counts['stored_facts']+=1
    for passage in result['company_passages']:
        nodes=docs[passage['source_url']]['ids'].get(passage['fact_id'],[])
        if passage['fact_id'] is None:
            nodes=[n for n in docs[passage['source_url']]['lines'].get((passage['concept_key'],passage['source_line']),[])
                   if n.get('contextRef')==passage['context_id']]
        ok=len(nodes)==1
        if ok:
            n=nodes[0]
            ok=(n.tag==passage['concept_key'] and n.tag in rows and n.get('contextRef')==passage['context_id'] and contents(n)==passage['text'])
        check(ok and passage['association']=='explicit_fact_concept' and passage['accession']==accession,'company_passage',passage['fact_id'])
        counts['company_passages']+=1
    passage_coordinates=Counter((p['concept_key'],p['source_line'],p['context_id']) for p in result['company_passages'])
    expected_passages=Counter()
    # Independent completeness check for directly declared textBlockItemType.
    for fact in source_facts:
        row=rows.get(fact.tag)
        if row and (row['schema_attributes'].get('type') or '').rsplit(':',1)[-1]=='textBlockItemType' and fact.get('{http://www.w3.org/2001/XMLSchema-instance}nil') not in ('true','1'):
            expected_passages[(fact.tag,fact.sourceline,fact.get('contextRef'))]+=1
    for coordinate,count in expected_passages.items():
        check(passage_coordinates[coordinate]==count,'missing_company_passage',coordinate)
    for rel in result['relationships']:
        check((rel['from'],rel['to'],rel['arcrole'],rel['source_url'],rel['line'],tuple(sorted(rel['attributes'].items()))) in raw_structure,'filing_relationship',rel)
        counts['relationships']+=1
    for role in result['roles']:
        nodes=docs[role['source_url']]['lines'].get(('{'+LINK+'}roleType',role['line']),[])
        check(any(n.get('roleURI')==role['uri'] and contents(n.find('{'+LINK+'}definition'))==role['definition'] for n in nodes if n.find('{'+LINK+'}definition') is not None),'role_definition',role['uri'])
        counts['roles']+=1
    matched={n['id'] for row in rows.values() for n in row['graph_nodes']}
    unmatched=[n['id'] for n in result['direct_graph_metadata'] if n['id'] not in matched]
    check(set(unmatched)=={n['id'] for n in summary['unmatched_direct_graph_metadata']},'graph_unmatched_summary',accession)
    graph.extend({'kind':'unmatched_metadata','detail':uid} for uid in unmatched)
    if not result['facts']:graph.append({'kind':'no_stored_facts','detail':accession})
    for omitted in result['omitted_source_facts']:
        counts['omitted_'+omitted['reason']]+=1
        if omitted['reason']=='unexplained':graph.append({'kind':'unexplained_source_fact','detail':omitted['source_id']})
    return {'accession':accession,'source_status':'passed' if not errors else 'failed',
            'graph_status':'passed' if not graph else 'review','errors':errors,'graph_issues':graph,
            'counts':dict(counts),'seconds':round(time.monotonic()-started,3)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories',type=Path,nargs='+');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    validations=[]
    for folder in args.directories:
        for path in sorted(folder.glob('*_result.json')):
            try:validation=verify(json.loads(path.read_text()))
            except Exception as exc:
                validation={'accession':path.name.split('_')[0],'source_status':'failed','graph_status':'not_checked',
                            'errors':[{'kind':'verification_exception','detail':repr(exc)}],'graph_issues':[],'counts':{}}
            (args.out/(validation['accession']+'_validation.json')).write_text(json.dumps(validation,indent=2))
            validations.append(validation)
            print(validation['accession'],validation['source_status'],len(validation['errors']),validation['graph_status'],flush=True)
    counts=Counter()
    for v in validations:counts.update(v['counts'])
    summary={'reports':len(validations),'source_status':dict(Counter(v['source_status'] for v in validations)),
             'graph_status':dict(Counter(v['graph_status'] for v in validations)),
             'error_categories':dict(Counter(e['kind'] for v in validations for e in v['errors'])),
             'graph_categories':dict(Counter(e['kind'] for v in validations for e in v['graph_issues'])),
             'counts':dict(counts),'seconds':round(sum(v.get('seconds',0) for v in validations),3)}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
    return 0 if all(v['source_status']=='passed' for v in validations) else 1


if __name__=='__main__':raise SystemExit(main())
