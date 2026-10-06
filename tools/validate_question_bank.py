#!/usr/bin/env python3
"""Check 8 company scenarios, dependency edges, gold arithmetic and canonical hop DAGs."""
import argparse
import ast
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / 'question-bank'
FIELDS = {'id': str, 'question': str, 'type': str, 'answer': str,
          'scenario_id': str, 'workflow_step': int, 'total_steps': int,
          'hops': int, 'xbrl_concepts': list, 'filing_type': str,
          'filing_period': str, 'answer_type': str, 'tool_required': str,
          'source': str, 'reasoning': str, 'evidence': str}
COMPANIES = {'MU','STX','WDC','SNDK','NTAP','PSTG','RMBS','MRAM'}
WEIGHT = {'prior':0,'assumption':0,'alias':0,'retrieve':1,'calculate':1,'judge':1}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def arithmetic(expression, values):
    def visit(node):
        if isinstance(node, ast.Expression): return visit(node.body)
        if isinstance(node, ast.Name): return values[node.id]
        if isinstance(node, ast.Constant):
            return Decimal(str(node.value)) if type(node.value) in (int,float) else node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub): return -visit(node.operand)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return not visit(node.operand)
        if isinstance(node, ast.BinOp):
            a,b=visit(node.left),visit(node.right)
            if isinstance(node.op, ast.Add): return a+b
            if isinstance(node.op, ast.Sub): return a-b
            if isinstance(node.op, ast.Mult): return a*b
            if isinstance(node.op, ast.Div): return a/b
        if isinstance(node, ast.BoolOp):
            return all(visit(n) for n in node.values) if isinstance(node.op,ast.And) else any(visit(n) for n in node.values)
        if isinstance(node, ast.Compare):
            left=visit(node.left)
            for op,other in zip(node.ops,node.comparators):
                right=visit(other)
                if isinstance(op,ast.Eq): ok=left==right
                elif isinstance(op,ast.NotEq): ok=left!=right
                elif isinstance(op,ast.Gt): ok=left>right
                elif isinstance(op,ast.GtE): ok=left>=right
                elif isinstance(op,ast.Lt): ok=left<right
                elif isinstance(op,ast.LtE): ok=left<=right
                else: raise ValueError(type(op).__name__)
                if not ok:return False
                left=right
            return True
        raise ValueError(f'Unsupported expression: {ast.dump(node)}')
    return visit(ast.parse(expression,mode='eval'))


def typed_value(value, unit):
    if value is None or isinstance(value,bool) or unit in {'text','date','boolean'}:return value
    return Decimal(value)


class Locations(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.text=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.add(attrs['id'])
    def handle_data(self,data): self.text.append(data)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-cache',type=Path,help='Optional downloaded SEC HTML directory for source/hash/locator verification')
    args=parser.parse_args()
    files=sorted((BANK/'sets').glob('*.json'))
    sources=json.loads((BANK/'grading/sources.json').read_text())
    rubrics=json.loads((BANK/'grading/rubrics.json').read_text())
    scenarios=json.loads((BANK/'grading/scenarios.json').read_text())
    check(len(files)==8 and set(scenarios)==COMPANIES,'Expected 8 distinct companies')
    check({p.name for p in files}=={x['file'] for x in scenarios.values()},'Unexpected canonical sets')
    check({p.name for p in (BANK/'agent').glob('*.json')}=={p.name for p in files},'Public file mismatch')
    cache={}
    if args.source_cache:
        for key,s in sources.items():
            raw=(args.source_cache/(key+'.html')).read_bytes()
            check(hashlib.sha256(raw).hexdigest()==s['sha256'],f'{key}: source hash mismatch')
            p=Locations();p.feed(raw.decode('utf-8'));cache[key]=(p.ids,' '.join(' '.join(p.text).split()))
    ids=set();texts=set();company_counts=Counter();forms=Counter();hops_hist=Counter()
    outputs={};source_edges=0;recomputed=0;dependency_edges=0;locator_count=0
    for file in files:
        qs=json.loads(file.read_text());public=json.loads((BANK/'agent'/file.name).read_text())
        check(len(qs)==len(public)==5,f'{file.name}: expected five questions')
        check([q['workflow_step'] for q in qs]==[1,2,3,4,5],f'{file.name}: step ordering')
        tickers={rubrics[q['id']]['ticker'] for q in qs}
        check(len(tickers)==1,f'{file.name}: mixed companies')
        ticker=next(iter(tickers));company_counts[ticker]+=5
        check(len({q['scenario_id'] for q in qs})==1,f'{file.name}: mixed scenarios')
        check(qs[0]['scenario_id']==scenarios[ticker]['scenario_id'],f'{file.name}: scenario ID')
        for i,(q,p) in enumerate(zip(qs,public)):
            qid=q['id'];m=rubrics[qid];env={};var_nodes={};node_map={};depth={}
            check(set(q)==set(FIELDS),f'{qid}: example fields changed')
            for name,cls in FIELDS.items():check(type(q[name]) is cls,f'{qid}: type {name}')
            check(qid not in ids and q['question'] not in texts,f'{qid}: duplicate')
            ids.add(qid);texts.add(q['question']);forms[q['filing_type']]+=1;hops_hist[q['hops']]+=1
            check(q['total_steps']==5 and q['filing_type'] in {'10-K','10-Q','8-K'},f'{qid}: format')
            check(q['source']==m['evidence_records'][0]['url'],f'{qid}: source mismatch')
            check(p['id']==qid and p['question']==q['question'] and p['depends_on']==m['depends_on'],f'{qid}: public view mismatch')
            banned={'answer','reasoning','evidence','source','expected_answer','grading','input_bindings','derivations','hop_plan','evidence_records','xbrl_concepts'}
            check(not (set(p)&banned),f'{qid}: public view leaks grading fields')
            expected=m['grading']['expected_answer']
            check(json.loads(q['answer'])=={k:v['value'] for k,v in expected.items()},f'{qid}: answer mismatch')
            deps={b['question_id'] for b in m['input_bindings'].values() if b['kind']=='prior'}
            check(deps==set(m['depends_on']),f'{qid}: dependency metadata mismatch')
            if i==0:check(not deps,f'{qid}: first question has dependencies')
            else:check(qs[i-1]['id'] in deps,f'{qid}: does not consume immediately preceding step')
            check(deps<={x['id'] for x in qs[:i]},f'{qid}: forward or cross-company dependency')
            dependency_edges+=len(deps)
            for var,b in m['input_bindings'].items():
                value=typed_value(b['value'],b['unit']);env[var]=value
                if b['kind']=='prior':
                    check(outputs[b['question_id']][b['field']]==value,f'{qid}.{var}: previous output binding drift')
                elif b['kind']=='source':
                    matches=[e for e in m['evidence_records'] if e['source_id']==b['source_id'] and e['label']==b['evidence_label']]
                    check(any(typed_value(e['value'],e['unit'])==value for e in matches),f'{qid}.{var}: unsupported source value')
            for ev in m['evidence_records']:
                locator_count+=1;s=sources[ev['source_id']];u=urlparse(ev['url'])
                check(s['ticker']==ticker,f'{qid}: another company\'s evidence')
                check(u.scheme=='https' and u.hostname=='www.sec.gov' and u.path.startswith('/Archives/edgar/data/') and u.path.endswith(('.htm','.html')) and u.fragment,f'{qid}: not a precise SEC page')
                check(ev['url'].split('#')[0]==s['url'],f'{qid}: page mismatch')
                check(s['filed']<='2026-09-22',f'{qid}: future source')
                if 'fact_id' in ev:
                    raw=Decimal(ev['original_text'].replace(',','').replace('—','0'))
                    value=raw*Decimal(10)**(ev['scale']-6)*(-1 if ev['sign']=='-' else 1)
                    check(value==Decimal(ev['value']) and ev['unit']=='USD million',f'{qid}: XBRL scale/sign')
                    check(unquote(u.fragment)==ev['fact_id'],f'{qid}: wrong XBRL anchor')
                if cache:
                    ids_in_file,text=cache[ev['source_id']]
                    if 'fact_id' in ev:check(ev['fact_id'] in ids_in_file,f'{qid}: missing fact ID')
                    else:check(' '.join(ev['text_fragment'].split()) in text,f'{qid}: missing text locator')
            check(sorted(q['xbrl_concepts'])==sorted({e['concept'] for e in m['evidence_records'] if 'concept' in e}),f'{qid}: concept list')
            definitions={d['field']:d for d in m['derivations']}
            for node in m['hop_plan']:
                nid=node['id'];kind=node['kind']
                check(nid not in node_map and kind in WEIGHT,f'{qid}: invalid hop node')
                check(set(node['depends_on'])<=set(node_map),f'{qid}: non-topological DAG')
                if kind in {'prior','assumption','retrieve'}:
                    check(not node['depends_on'],f'{qid}: root node has hidden dependency')
                    for var in node['outputs']:
                        b=m['input_bindings'][var]
                        check(b['kind']==('source' if kind=='retrieve' else kind),f'{qid}: incorrect root weight')
                        if kind=='retrieve':check(b['source_id'] in node['source_ids'],f'{qid}: retrieval source')
                        if kind=='prior':check(node['question_id']==b['question_id'] and node['field']==b['field'],f'{qid}: prior hop reference')
                        var_nodes[var]=nid
                    if kind=='retrieve':source_edges+=1
                else:
                    check(len(node['outputs'])==1,f'{qid}: non-atomic derived node')
                    field=node['outputs'][0];definition=definitions[field]
                    check(node['expression']==definition['expression'],f'{qid}: graph formula mismatch')
                    refs={n.id for n in ast.walk(ast.parse(node['expression'],mode='eval')) if isinstance(n,ast.Name)}
                    check(set(node['depends_on'])=={var_nodes[r] for r in refs},f'{qid}: missing or inflated formula edge')
                    value=arithmetic(node['expression'],env);env[field]=value;var_nodes[field]=nid;recomputed+=1
                    if kind=='alias':check(isinstance(ast.parse(node['expression'],mode='eval').body,ast.Name),f'{qid}: zero-cost non-alias')
                    elif kind=='judge':check(type(value)is bool,f'{qid}: judge type')
                    else:check(type(value)is Decimal,f'{qid}: calculate type')
                d=WEIGHT[kind]+max((depth[x] for x in node['depends_on']),default=0)
                check(d==node['depth'],f'{qid}: incorrect node depth');depth[nid]=d;node_map[nid]=node
            check(set(m['output_nodes'])==set(expected),f'{qid}: missing output in graph')
            check(all(var_nodes[k]==v for k,v in m['output_nodes'].items()),f'{qid}: output node mismatch')
            measured=max(depth[n] for n in m['output_nodes'].values())
            check(measured==q['hops']==m['hops'],f'{qid}: hops not graph-derived')
            def ancestors(nid):
                return {nid}|set().union(*(ancestors(n) for n in node_map[nid]['depends_on']))
            used=set().union(*(ancestors(n) for n in m['output_nodes'].values()))
            for var,b in m['input_bindings'].items():
                if b['kind']=='prior':check(var_nodes[var] in used,f'{qid}: decorative dependency')
            outputs[qid]={}
            for field,spec in expected.items():
                actual=env[field];outputs[qid][field]=actual
                if spec['kind']=='number':
                    places=definitions.get(field,{}).get('decimal_places')
                    shown=actual.quantize(Decimal(10)**-places,rounding=ROUND_HALF_UP) if places is not None else actual
                    check(shown==Decimal(spec['value']),f'{qid}.{field}: arithmetic answer mismatch')
                else:check(actual==spec['value'],f'{qid}.{field}: logic answer mismatch')
            check(m['verification']['agent_run_performed'] is False,f'{qid}: unsupported agent run claim')
    check(ids==set(rubrics) and company_counts==dict.fromkeys(COMPANIES,5),'Question/company total mismatch')
    report={'status':'PASS','version':2,'companies':8,'sets':8,'questions_per_set':5,'questions':40,
            'dependency_edges':dependency_edges,'derived_outputs_checked':recomputed,
            'hops_distribution':dict(sorted(hops_hist.items())),'filing_types':dict(forms),
            'evidence_locations_checked':locator_count,'source_pages':len(sources),
            'source_html_verified':bool(cache),'model_calls':0}
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
