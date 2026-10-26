"""Canonical process graphs, Mermaid export and evidence-level checks."""


def items(value):return value if isinstance(value,list) else []
def text(value):return isinstance(value,str) and bool(value.strip())

def edge_caption(diagram,edge,index):
    # Long labels and state self-loops share cramped routing space. Keep their full
    # meaning in the generated transition table instead of shrinking the diagram.
    if diagram.get('kind')=='state' or len(str(edge.get('label','')))>18:return 'T'+str(index+1).zfill(2)
    return edge.get('label','')


def mermaid(diagram):
    def label(value):return str(value).replace('&','&amp;').replace('"','&quot;').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
    nodes=items(diagram.get('nodes'));aliases={n['id']:'N'+str(i) for i,n in enumerate(nodes)}
    state=diagram.get('kind')=='state'
    out=['stateDiagram-v2' if state else 'flowchart TD']
    for node in nodes:
        name=aliases[node['id']];caption=label(node['label'])
        shape=node.get('type','process')
        if state:out.append(f'  state "{caption}" as {name}')
        elif shape=='decision':out.append(f'  {name}{{"{caption}"}}')
        elif shape in ('start','end'):out.append(f'  {name}(["{caption}"])')
        elif shape=='subprocess':out.append(f'  {name}[["{caption}"]]')
        else:out.append(f'  {name}["{caption}"]')
        if node.get('entry') and state:out.append('  [*] --> '+name)
        if node.get('terminal') and state:out.append('  '+name+' --> [*]')
    for i,edge in enumerate(items(diagram.get('edges'))):
        start,end=aliases[edge['from']],aliases[edge['to']];caption=label(edge_caption(diagram,edge,i))
        out.append(f'  {start} --> {end}'+(' : '+caption if caption else '') if state else f'  {start} -->'+(f'|"{caption}"|' if caption else '')+' '+end)
    return '\n'.join(out)


def markdown(diagram, all_diagrams=None, heading=4):
    index={d['id']:d for d in items(all_diagrams) if isinstance(d,dict) and text(d.get('id'))}
    out=['#'*heading+' '+diagram['title'],f"图编号：{diagram['id']} · "+('已确认' if diagram.get('status')=='confirmed' else '待确认')]
    if diagram.get('parent_id'):
        parent=index.get(diagram['parent_id'],{});node=next((n for n in parent.get('nodes',[]) if n.get('id')==diagram.get('parent_node')), {})
        out.append('上层流程：'+parent.get('title',diagram['parent_id'])+' → '+node.get('label',diagram.get('parent_node','')))
    if diagram.get('summary'):out.append(diagram['summary'])
    out.append('```mermaid\n'+mermaid(diagram)+'\n```')
    nodes={n['id']:n for n in items(diagram.get('nodes'))}
    edges=items(diagram.get('edges'))
    if diagram.get('kind')=='state' or any(edge_caption(diagram,e,i)!=e.get('label') or e.get('condition') or e.get('effect') for i,e in enumerate(edges)):
        def cell(v):return str(v).replace('|','｜').replace('\n','；')
        out.append('迁移说明：图中 T 编号对应下表；条件与副作用保留全文，不挤在连线上。')
        rows=['| 编号 / 连线 | 迁移 | 触发与条件 | 结果说明 / 规则 |','| --- | --- | --- | --- |']
        for i,e in enumerate(edges):
            trigger=e.get('label','')+('；条件：'+e['condition'] if e.get('condition') else '')
            effect='；'.join(v for v in (e.get('effect',''),'依据：'+'、'.join(e['rule_ids']) if e.get('rule_ids') else '') if v)
            rows.append('| '+' | '.join(cell(v) for v in (edge_caption(diagram,e,i),nodes[e['from']]['label']+' → '+nodes[e['to']]['label'],trigger,effect or '未单列结果说明；按本行完整触发描述执行'))+' |')
        out.append('\n'.join(rows))

    children=[d for d in index.values() if d.get('parent_id')==diagram['id']]
    if children:out.append('节点展开：'+'；'.join(d['title']+'（'+d['id']+'，见对应功能详情）' for d in children))
    return '\n\n'.join(out)


def evaluate(spec, has_prototype=True):
    issues=[]
    def issue(code,path,message,severity='error'):issues.append(dict(code=code,path=path,message=message,severity=severity))
    reqs={r['id']:r for r in items(spec.get('requirements')) if isinstance(r,dict) and text(r.get('id'))}
    diagrams={}
    for d in items(spec.get('diagrams')):
        if not isinstance(d,dict) or not text(d.get('id')):issue('diagram_invalid','diagrams','图需有稳定编号');continue
        did=d['id']
        if did in diagrams:issue('diagram_duplicate',did,'图编号重复')
        diagrams[did]=d
    modules={r.get('module') or '功能需求' for r in reqs.values()}
    pages={p['id']:p for p in items(spec.get('pages')) if isinstance(p,dict) and text(p.get('id'))}
    all_rules={rule.get('id') for req in reqs.values() for rule in items(req.get('rule_details')) if isinstance(rule,dict) and text(rule.get('id'))}
    for did,d in diagrams.items():
        if not text(d.get('title')) or d.get('kind') not in ('flow','state') or d.get('level') not in ('module','detail'):issue('diagram_metadata',did,'图需有标题、flow/state 类型和 module/detail 层级')
        if d.get('module') not in modules:issue('diagram_module',did,'图未关联本次业务模块')
        if d.get('source') not in ('origin','ai-inferred') or d.get('status') not in ('confirmed','pending'):issue('diagram_origin',did,'图需注明依据与确认状态')
        elif d['status']=='pending':issue('diagram_pending',did,'流程/状态图仍待业务确认','decision')
        if d.get('level')=='detail':
            req=reqs.get(d.get('requirement_id',''))
            if not req or (req.get('module') or '功能需求')!=d.get('module'):issue('diagram_requirement',did,'子图需关联同模块功能')
            parent=diagrams.get(d.get('parent_id',''));pn=d.get('parent_node')
            if (d.get('parent_id') or pn) and (not parent or parent.get('module')!=d.get('module') or not any(n.get('id')==pn for n in items(parent.get('nodes')) if isinstance(n,dict))):issue('diagram_parent',did,'有关联上层时需指向同模块图的具体节点；独立图无需虚构父流程')
        elif d.get('parent_id'):issue('diagram_parent',did,'模块图不应有上层图')
        nodes={}
        for n in items(d.get('nodes')):
            if not isinstance(n,dict) or not text(n.get('id')) or not text(n.get('label')):issue('diagram_node',did,'节点需有编号与可理解的名称');continue
            if n['id'] in nodes:issue('diagram_node_duplicate',did,'节点编号重复')
            nodes[n['id']]=n
            if d.get('kind')=='flow' and n.get('type','process') not in ('process','decision','start','end','subprocess'):issue('diagram_node_type',did+'/'+n['id'],'流程节点类型需为process/decision/start/end/subprocess')
            if d.get('kind')=='state' and n.get('type') not in (None,'state'):issue('diagram_state_node_type',did+'/'+n['id'],'状态图节点仅表示状态，不用流程判断节点')

            if any(rid not in reqs or (reqs[rid].get('module') or '功能需求')!=d.get('module') for rid in items(n.get('requirement_ids'))):issue('diagram_node_requirement',did,'节点功能关联不存在或跨模块')
            target=n.get('prototype')
            if target is not None and has_prototype:
                pg=pages.get(target.get('page','')) if isinstance(target,dict) else None
                if not pg or not any(st.get('id')==target.get('state') for st in items(pg.get('states'))):issue('diagram_prototype_state',did,'图节点引用的原型页面或状态不存在')
        if len(nodes)<2:issue('diagram_nodes_missing',did,'流程图至少需要起点与结果节点')
        edges=items(d.get('edges'));used=set()
        if not edges:issue('diagram_edges_missing',did,'图缺少流转关系')
        for edge in edges:
            if not isinstance(edge,dict) or edge.get('from') not in nodes or edge.get('to') not in nodes:issue('diagram_edge',did,'流转起止节点不存在');continue
            used.update((edge['from'],edge['to']))
            if not text(edge.get('label')):issue('diagram_condition',did,'流转连线需写明动作或条件')
            if any(r not in all_rules for r in items(edge.get('rule_ids'))):issue('diagram_rule',did,'流转引用的规则不存在')
            for field in ('condition','effect'):
                if field in edge and not text(edge[field]):issue('diagram_edge_detail',did,'连线条件/结果说明必须为非空文本')

        for nid in nodes.keys()-used:issue('diagram_disconnected',did+'/'+nid,'节点未连接到流程')
        roots=[n['id'] for n in nodes.values() if n.get('entry')]
        if not roots:issue('diagram_entry',did,'图需明确至少一个入口节点（entry=true）')
        reached=set(roots)
        for _ in nodes:
            for edge in edges:
                if isinstance(edge,dict) and edge.get('from') in reached and edge.get('to') in nodes:reached.add(edge['to'])
        if nodes.keys()-reached:issue('diagram_unreachable',did,'存在从入口无法到达的节点')
        if d.get('kind')=='flow' and not any(n.get('terminal') for n in nodes.values()):issue('diagram_terminal',did,'流程图需明确本次范围的结果/交接点；不强迫业务对象终止')
        outgoing={e.get('from') for e in edges if isinstance(e,dict)}
        for nid,n in nodes.items():
            if d.get('kind')=='flow' and nid not in outgoing and not n.get('terminal'):issue('diagram_deadend',did+'/'+nid,'非结束节点没有后续路径，需补分支或明确交接结果')

        for nid,n in nodes.items():
            branches=[e for e in edges if isinstance(e,dict) and e.get('from')==nid]
            if n.get('type')=='decision':
                if len(branches)<2:issue('diagram_decision_branches',did+'/'+nid,'判断节点至少有两条明确出口')
                labels=[str(e.get('label','')).strip() for e in branches]
                if len(set(labels))!=len(labels):issue('diagram_decision_labels',did+'/'+nid,'判断出口标签不能相同，需明确互斥条件')
            if d.get('kind')=='flow' and n.get('type')=='start' and not n.get('entry'):issue('diagram_start_entry',did+'/'+nid,'开始节点需声明entry')
            if d.get('kind')=='flow' and n.get('type')=='end' and not n.get('terminal'):issue('diagram_end_terminal',did+'/'+nid,'结束节点需声明terminal')
            if d.get('kind')=='flow' and n.get('terminal') and branches:issue('diagram_terminal_outgoing',did+'/'+nid,'结束/交接结果不应继续发出路径，需修正结果或节点类型')
        visited={did};parent=d.get('parent_id')
        while parent in diagrams:
            if parent in visited:issue('diagram_cycle',did,'子图层级不能循环引用');break
            visited.add(parent);parent=diagrams[parent].get('parent_id')
    module_reviews={r.get('module'):r for r in items((spec.get('quality') or {}).get('module_reviews')) if isinstance(r,dict) and text(r.get('module'))}
    for module in modules:
        check=(module_reviews.get(module,{}).get('flow') or {});status=check.get('status')
        if status=='covered':
            ids=check.get('diagram_ids')
            valid=isinstance(ids,list) and bool(ids) and all(isinstance(i,str) and i in diagrams and diagrams[i].get('module')==module and diagrams[i].get('kind')=='flow' and diagrams[i].get('level')=='module' for i in ids)
            if not valid:issue('module_flow_missing',module,'已登记存在模块流程，但缺少对应的整体流程图')
            overviews=[diagrams[i] for i in ids if isinstance(i,str) and i in diagrams] if isinstance(ids,list) else []
            participants=check.get('requirement_ids')
            if not isinstance(participants,list) or not participants or any(not isinstance(rid,str) or rid not in reqs or (reqs[rid].get('module') or '功能需求')!=module for rid in participants):
                issue('module_flow_participants',module,'需登记实际参与模块流程的功能，不把无流程的功能强行纳入');participants=[]
            covered={rid for d in overviews for n in items(d.get('nodes')) if isinstance(n,dict) for rid in items(n.get('requirement_ids'))}
            for rid in participants:
                if rid not in covered:issue('module_feature_unmapped',rid,'已登记参与模块流程，但图中未定位本功能节点')
        elif status=='not_applicable':
            if not text(check.get('reason')):issue('module_flow_na_reason',module,'无模块流程时说明理由，无需画图')
            if any(d.get('module')==module and d.get('level')=='module' and d.get('kind')=='flow' for d in diagrams.values()):issue('module_flow_conflict',module,'标记无模块流程，但仍交付模块流程图，需核对适用性')
        elif status=='pending':
            if not text(check.get('question')) or type(check.get('blocking')) is not bool:issue('diagram_decision',module,'流程适用性待确认时需说明问题与阻塞影响')
            else:issue('diagram_decision',module,check['question'],'error' if check['blocking'] else 'decision')
        else:issue('module_flow_review_missing',module,'先判断是否存在模块流程；存在才需要流程图')
    for rid,req in reqs.items():
        review=req.get('diagram_review') or {}
        for kind,label in [('flow','子流程'),('state','状态流转')]:
            check=review.get(kind,{}) if isinstance(review,dict) else {};status=check.get('status')
            path=rid+'/'+kind
            if status=='covered':
                ids=check.get('diagram_ids')
                if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in diagrams or diagrams[i].get('kind')!=kind or diagrams[i].get('requirement_id')!=rid or diagrams[i].get('level')!='detail' for i in ids):issue('detail_diagram_missing',path,'已登记存在'+label+'，但缺少关联到本功能的图')
            elif status=='not_applicable':
                if not text(check.get('reason')):issue('diagram_na_reason',path,'不需要'+label+'时需说明简短理由')
            elif status=='pending':
                if not text(check.get('question')) or type(check.get('blocking')) is not bool:issue('diagram_decision',path,'图待确认时需说明问题与阻塞影响')
                else:issue('diagram_decision',path,check['question'],'error' if check['blocking'] else 'decision')
            else:issue('diagram_review_missing',path,'未核对子流程/状态流转图是否适用')
    return issues
