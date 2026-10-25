"""Evidence-based delivery checks; no model calls and no readiness claims."""
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path

# These are review dimensions, not instructions to add functionality.
PROFILES = {
    'form': {'label':'表单','dimensions':{'fields':'字段含义与必填/默认值','validation':'校验与边界','submission':'提交及重复操作','result':'提交结果','recovery':'失败恢复','permissions':'使用权限'},'cases':{'validation':'boundary','recovery':'exception'}},
    'list': {'label':'列表','dimensions':{'data_scope':'数据范围','sorting':'排序','filtering':'筛选','pagination':'分页或加载范围','empty':'空数据/无结果','failure':'加载失败','permissions':'数据权限'},'cases':{'empty':'boundary','failure':'exception'}},
    'workflow': {'label':'流程/审批','dimensions':{'roles':'角色与职责','transitions':'状态转换','conditions':'流转前提','recovery':'退回/失败恢复','concurrency':'重复及冲突操作'},'cases':{'recovery':'exception'}},
    'batch': {'label':'批量操作','dimensions':{'selection':'选择范围','limits':'数量边界','partial_success':'部分成功','recovery':'失败重试','permissions':'操作权限'},'cases':{'limits':'boundary','partial_success':'exception'}},
    'metric': {'label':'指标','dimensions':{'definition':'定义/公式','unit':'单位/精度','time':'时间范围/时区','aggregation':'聚合/去重','empty':'空值/无数据'},'cases':{'empty':'boundary'}},
    'action': {'label':'单项操作','dimensions':{'preconditions':'前置条件','result':'操作结果','recovery':'失败恢复'},'cases':{'recovery':'exception'}},
    'display': {'label':'只读展示','dimensions':{'data_scope':'数据来源/范围','format':'显示口径','empty':'空值/无数据'},'cases':{'empty':'boundary'}},
}


def nonempty(value):
    return isinstance(value,str) and bool(value.strip())


def objects(value):
    return value if isinstance(value,list) else []


class Snapshot(HTMLParser):
    """Record ids inside authored snapshot regions, including hidden ancestors."""
    VOID={'input','img','br','hr','meta','link','source','area','base','col','embed','param','track','wbr'}
    def __init__(self):
        super().__init__(); self.stack=[]; self.ids={}; self.states=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);parent=self.stack[-1][1] if self.stack else {}
        context={'state':a.get('data-ps-state',parent.get('state')),
                 'snapshot':parent.get('snapshot',False) or 'sr-snapshot' in a.get('class','').split(),
                 'hidden':parent.get('hidden',False) or 'hidden' in a or a.get('aria-hidden')=='true'}
        if 'data-ps-state' in a:self.states.add(a['data-ps-state'])
        if a.get('id'):self.ids[a['id']]=context
        if tag not in self.VOID:self.stack.append((tag,context))
    def handle_endtag(self,tag):
        for n in range(len(self.stack)-1,-1,-1):
            if self.stack[n][0]==tag:del self.stack[n:];break


def evaluate(spec, content=None):
    """Inspect declared scope and evidence. Errors block strict delivery; decisions stay explicit."""
    issues=[];coverage=[];check_rows=[];case_rows=[]
    def issue(code,path,message,severity='error'):
        issues.append(dict(code=code,path=path,message=message,severity=severity))
    def refs(value,allowed,path,what,required=True):
        if value is None and not required:return []
        if not isinstance(value,list) or (required and not value) or any(not isinstance(x,str) or x not in allowed for x in value):
            issue('invalid_'+what,path,'缺少或无效的'+what+'关联');return []
        return value
    if not isinstance(spec,dict):
        issue('spec_missing','spec','缺少结构化需求');spec={}
    quality=spec.get('quality')
    if not isinstance(quality,dict) or quality.get('schema_version')!=1:
        issue('quality_contract','quality','缺少交付检查范围与输入条目登记（schema_version=1）');quality={}
    scope=quality.get('scope',{})
    if not isinstance(scope,dict) or any(type(scope.get(k)) is not bool for k in ('prd','prototype','acceptance')):
        issue('scope_missing','quality.scope','需明确本次 PRD、原型、验收的交付范围');scope={}
    has_prototype=scope.get('prototype',True)
    if scope and not any(scope.values()):issue('scope_empty','quality.scope','至少选择一种交付物')
    reqs={r['id']:r for r in objects(spec.get('requirements')) if isinstance(r,dict) and nonempty(r.get('id'))}
    if not reqs:issue('requirements_missing','requirements','本次未登记任何功能需求')
    inputs=quality.get('input_items')
    if not isinstance(inputs,list) or not inputs:issue('input_inventory_missing','quality.input_items','未登记已确定方案的输入条目，无法核对方案是否全部纳入或明确排除')
    input_ids=set();included=set()
    for n,item in enumerate(objects(inputs)):
        path=f'quality.input_items/{n}'
        if not isinstance(item,dict) or not nonempty(item.get('id')) or not nonempty(item.get('summary')):
            issue('input_invalid',path,'输入条目需有稳定编号与简短方案摘要');continue
        if item['id'] in input_ids:issue('input_duplicate',path,'输入条目编号重复')
        input_ids.add(item['id']);status=item.get('disposition')
        if status=='included':included.update(refs(item.get('requirement_ids'),reqs,path,'需求'))
        elif status=='excluded':
            if not nonempty(item.get('reason')):issue('exclusion_reason_missing',path,'排除条目需说明理由')
        elif status=='pending':
            if not nonempty(item.get('question')) or type(item.get('blocking')) is not bool:issue('decision_invalid',path,'待决策输入需有具体问题和是否阻塞的说明')
            else:issue('input_decision',path,item['question'],'error' if item['blocking'] else 'decision')
        else:issue('input_disposition',path,'输入条目需标 included、excluded 或 pending')
    for rid in reqs:
        if rid not in included:issue('requirement_without_input',rid,'功能未关联到输入方案条目；补充功能需有明确来源，不自动扩大范围')
    pages={p['id']:p for p in objects(spec.get('pages')) if isinstance(p,dict) and nonempty(p.get('id'))}
    states={};inventories={};dom={}
    for pid,page in pages.items():
        for state in objects(page.get('states')):
            if not isinstance(state,dict) or not nonempty(state.get('id')):continue
            key=(pid,state['id']);states[key]=state
            inventory=state.get('elements')
            if has_prototype and (not isinstance(inventory,list) or not inventory):issue('elements_missing',f'{pid}/{state["id"]}','缺少该状态的必要元素清单')
            inventories[key]={e['selector']:e for e in objects(inventory) if isinstance(e,dict) and nonempty(e.get('selector'))}
    if has_prototype and not states:issue('states_missing','pages','本次含原型，但未登记任何页面状态')
    if content is not None and has_prototype:
        try:
            content=Path(content).resolve();manifest=json.loads((content/'manifest.json').read_text(encoding='utf-8'))
            for module in manifest.get('modules',[]):
                for page in module.get('pages',[]):
                    if page.get('type')!='prototype':continue
                    file=(content/page['file']).resolve()
                    if not file.is_relative_to(content):raise ValueError('原型路径越界')
                    parser=Snapshot();parser.feed(file.read_text(encoding='utf-8'));dom[page['id']]=parser
            for (pid,sid),inventory in inventories.items():
                parser=dom.get(pid)
                if not parser or sid not in parser.states:issue('snapshot_missing',f'{pid}/{sid}','找不到该状态的原型画面');continue
                for selector in inventory:
                    element=parser.ids.get(selector.lstrip('#'),{})
                    if not selector.startswith('#') or element.get('state')!=sid or not element.get('snapshot') or element.get('hidden'):
                        issue('element_not_visible',f'{pid}/{sid}/{selector}','必要元素未出现在对应静态画面中，或被 HTML 隐藏')
        except (OSError,ValueError,KeyError,TypeError) as error:issue('prototype_read','prototype',str(error))
    elif has_prototype:
        issue('dom_not_checked','prototype','未提供原型源目录，本次只检查声明关系，未核对实际 HTML','warning')
    interaction_items=objects(spec.get('interactions'))
    rule_owners={}
    for rid,req in reqs.items():
        for rule in objects(req.get('rule_details')):
            if isinstance(rule,dict) and nonempty(rule.get('id')):rule_owners[rule['id']]=rid
    if has_prototype:
        for it in interaction_items:
            if not isinstance(it,dict):continue
            path=it.get('id','interaction')
            allowed={k for k,v in rule_owners.items() if v in objects(it.get('requirement_ids'))}
            refs(it.get('rule_ids'),allowed,path,'精确规则')
    def presentation(value,path,rule_ids,annotated):
        if not isinstance(value,dict):issue('presentation_missing',path,'未说明用原型画面还是文字表达');return 'missing',[]
        mode=value.get('mode');targets=objects(value.get('targets'))
        if mode=='text':
            if not nonempty(value.get('reason')):issue('text_reason_missing',path,'文字表达需解释为何不增加画面，例如同布局的数值边界或后台口径')
            return mode,[]
        if mode!='prototype':issue('presentation_mode',path,'表达方式仅支持 prototype 或 text');return 'missing',[]
        if not has_prototype:issue('prototype_outside_scope',path,'本次未交付原型，应使用文字说明并注明范围');return mode,[]
        if not targets:issue('targets_missing',path,'需要画面表达，但未关联页面、状态和必要元素')
        for target in targets:
            if not isinstance(target,dict):issue('target_invalid',path,'画面关联需包含 page/state/selector');continue
            if not all(nonempty(target.get(k)) for k in ('page','state','selector')):
                issue('target_invalid',path,'画面关联需包含 page/state/selector');continue
            key=(target['page'],target['state']);selector=target['selector']
            if key not in states or not isinstance(selector,str) or selector not in inventories.get(key,{}):
                issue('visual_target_missing',path,'所需画面、状态或必要元素未登记：'+str(target));continue
            page=pages[key[0]]
            if not any(r in objects(page.get('requirement_ids')) for r in rule_ids):issue('page_requirement_missing',path,'目标页面未关联该需求')
            if annotated:
                for rule_id in annotated:
                    linked=any(isinstance(it,dict) and it.get('page')==key[0] and rule_id in objects(it.get('rule_ids')) and rule_owners.get(rule_id) in objects(it.get('requirement_ids')) and (not it.get('state_ids') or key[1] in objects(it['state_ids'])) and it.get('selector')==selector for it in interaction_items)
                    if not linked:issue('visual_rule_unlinked',path,'画面规则未通过该状态的元素精确关联：'+rule_id)
        return mode,targets
    pending_rules=0;case_total=0
    for rid,req in reqs.items():
        rules={}
        for rule in objects(req.get('rule_details')):
            if not isinstance(rule,dict) or not nonempty(rule.get('id')):
                issue('rule_invalid',rid,'规则需有稳定编号');continue
            if rule['id'] in rules:issue('rule_duplicate',rid,'规则编号重复：'+rule['id'])
            rules[rule['id']]=rule
        acceptance={ac['id']:ac for ac in objects(req.get('acceptance')) if isinstance(ac,dict) and nonempty(ac.get('id'))}
        if not rules:issue('rules_missing',rid,'功能没有可核对的细粒度规则')
        if scope.get('acceptance',True) and not acceptance:issue('acceptance_missing',rid,'功能缺少可观察的验收条件')
        if req.get('blocking') and (req.get('status')=='pending' or any(rule.get('status')=='pending' for rule in rules.values())):
            issue('requirement_blocking',rid,'功能或其规则尚待确认，且已标记阻塞开发')
        used_ac=set()
        for rule_id,rule in rules.items():
            path=f'{rid}/{rule_id}'
            if not nonempty(rule.get('statement')) or not nonempty(rule.get('category')):issue('rule_incomplete',path,'规则缺少明确说明或分类')
            if rule.get('source') not in ('origin','ai-inferred') or rule.get('status') not in ('pending','confirmed'):issue('rule_origin',path,'规则来源或确认状态无效')
            if rule.get('status')=='pending':pending_rules+=1
            examples=rule.get('examples',[])
            if not isinstance(examples,list) or any(not isinstance(e,dict) or not nonempty(e.get('input')) or not nonempty(e.get('expected')) for e in examples):issue('example_invalid',path,'实例需有具体输入与预期；简单规则可不写实例')
            ac_refs=refs(rule.get('acceptance_ids'),acceptance,path,'验收',required=scope.get('acceptance',True));used_ac.update(ac_refs)
            mode,targets=presentation(rule.get('presentation'),path,[rid],[rule_id])
            coverage.append(dict(requirement=rid,feature=req.get('title',rid),rule=rule_id,mode=mode,targets=targets,acceptance_ids=ac_refs))
        for ac_id,ac in acceptance.items():
            if any(not nonempty(ac.get(k)) for k in ('given','when','then')):issue('acceptance_incomplete',f'{rid}/{ac_id}','验收需有前置、操作和可观察预期')
            if ac_id not in used_ac:issue('acceptance_orphan',f'{rid}/{ac_id}','验收未关联到任何规则')
        cases={};raw_cases=req.get('boundary_cases',[])
        if not isinstance(raw_cases,list):issue('cases_invalid',rid,'边界与异常用例需为列表')
        for case in objects(raw_cases):
            if not isinstance(case,dict) or not nonempty(case.get('id')):issue('case_invalid',rid,'边界用例缺少稳定编号');continue
            path=f'{rid}/{case["id"]}';case_total+=1
            if case['id'] in cases:issue('case_duplicate',path,'用例编号重复')
            cases[case['id']]=case
            if case.get('kind') not in ('boundary','exception','normal') or not nonempty(case.get('input')) or not nonempty(case.get('expected')):issue('case_incomplete',path,'用例需说明类型、具体输入和预期结果')
            case_rules=refs(case.get('rule_ids'),rules,path,'用例规则')
            case_ac=refs(case.get('acceptance_ids'),acceptance,path,'用例验收',required=scope.get('acceptance',True))
            supported={ac_id for rule_id in case_rules for ac_id in objects(rules[rule_id].get('acceptance_ids'))}
            if any(ac_id not in supported for ac_id in case_ac):issue('case_acceptance_mismatch',path,'用例验收不属于关联规则')
            view=case.get('presentation')
            mode,targets=presentation(view,path,[rid],case_rules if isinstance(view,dict) and view.get('mode')=='prototype' else [])
            case_rows.append(dict(requirement=rid,feature=req.get('title',rid),id=case['id'],kind=case.get('kind'),input=case.get('input',''),expected=case.get('expected',''),mode=mode,targets=targets,reason=view.get('reason','') if isinstance(view,dict) else ''))
        review=req.get('review',{});types=review.get('types') if isinstance(review,dict) else None
        if not isinstance(types,list) or not types or any(not isinstance(t,str) or t not in PROFILES for t in types):issue('feature_type_missing',rid,'需选择适用功能类型：'+', '.join(PROFILES));types=[]
        dimensions={};case_dimensions={}
        for kind in types:dimensions.update(PROFILES[kind]['dimensions']);case_dimensions.update(PROFILES[kind]['cases'])
        checks={}
        for check in objects(review.get('checks') if isinstance(review,dict) else None):
            if not isinstance(check,dict) or not nonempty(check.get('dimension')):issue('check_invalid',rid,'检查项需有维度编号');continue
            key=check['dimension']
            if key in checks:issue('check_duplicate',f'{rid}/{key}','同一维度重复登记')
            checks[key]=check
        for dimension,label in dimensions.items():
            path=f'{rid}/review/{dimension}';check=checks.get(dimension,{})
            status=check.get('status')
            if status=='covered':
                dimension_rules=refs(check.get('rule_ids'),rules,path,'检查规则')
                kind=case_dimensions.get(dimension)
                if kind:
                    case_refs=refs(check.get('case_ids'),cases,path,'边界用例')
                    if any(not set(objects(cases[cid].get('rule_ids'))).intersection(dimension_rules) for cid in case_refs):issue('check_case_unrelated',path,'用例未覆盖该检查项所关联的规则')
                    if not any(cases[cid].get('kind')==kind for cid in case_refs):issue('case_kind_missing',path,'该维度至少需有一个'+('边界' if kind=='boundary' else '异常')+'用例')
            elif status=='not_applicable':
                if not nonempty(check.get('reason')):issue('not_applicable_reason',path,'不适用需说明与本次范围有关的理由')
            elif status=='pending':
                if not nonempty(check.get('question')) or type(check.get('blocking')) is not bool:issue('decision_invalid',path,'待确认检查项需说明具体问题与是否阻塞')
                else:issue('feature_decision',path,check['question'],'error' if check['blocking'] else 'decision')
            else:issue('check_missing',path,'未核对适用检查项：'+label)
            check_rows.append(dict(requirement=rid,feature=req.get('title',rid),dimension=dimension,label=label,status=status or 'missing',rule_ids=objects(check.get('rule_ids')),question=check.get('question',''),reason=check.get('reason',''),blocking=check.get('blocking',False)))
        for key in checks.keys()-dimensions.keys():issue('unknown_dimension',f'{rid}/review/{key}','检查维度不属于选定功能类型，需校正类型或维度')
    if pending_rules:issue('rules_pending','requirements',f'{pending_rules} 条规则仍待业务确认','decision')
    if content is not None and scope.get('prd'):
        try:
            import prdlib
            registry=prdlib.registry(Path(content))
            if not registry:issue('prd_missing','prd.json','缺少标准 PRD 登记')
            for chapter in (registry or {}).get('sections',[]):
                for source in chapter['sources']:
                    doc=prdlib.document((Path(content)/source).read_text(encoding='utf-8'))
                    if doc['status']=='pending':issue('prd_pending',source,'章节仍待补充：'+chapter['title'],'decision')
        except (OSError,ValueError,KeyError,TypeError) as error:issue('prd_invalid','prd.json',str(error))
    if scope.get('prd'):
        import diagramlib
        issues.extend(diagramlib.evaluate(spec,has_prototype))
    counts=Counter(issue['severity'] for issue in issues)
    return {'status':'incomplete' if counts['error'] else 'review_required' if counts['decision'] else 'checks_passed',
            'counts':{'errors':counts['error'],'decisions':counts['decision'],'warnings':counts['warning'],'inputs':len(input_ids),'requirements':len(reqs),'rules':len(coverage),'states':len(states),'elements':sum(map(len,inventories.values())),'cases':case_total,'diagrams':len(objects(spec.get('diagrams')))},
            'diagrams':[{k:d.get(k,'') for k in ('id','title','kind','level','module','requirement_id','parent_id','parent_node')} for d in objects(spec.get('diagrams')) if isinstance(d,dict)],
            'issues':issues,'coverage':coverage,'checks':check_rows,'cases':case_rows,
            'limits':'仅验证已登记方案与证据的覆盖、适用性及关联。covered 表示已有说明，不表示业务已确认；无法发现从输入登记和规则中同时遗漏的业务事实，不代替语义复核、真实产品测试或开工决策。'}


def markdown(report):
    def cell(value):return str(value).replace('|','｜').replace('\n',' ')
    labels={'incomplete':'存在交付缺项','review_required':'结构覆盖通过，仍需业务评审','checks_passed':'已登记内容检查通过'}
    out=['# PRD 与原型交付检查',labels[report['status']],report['limits'],
         '## 检查结果',f"缺项/阻塞：{report['counts']['errors']}；待决策：{report['counts']['decisions']}；规则：{report['counts']['rules']}；边界与异常用例：{report['counts']['cases']}",
         '| 级别 | 定位 | 问题 |','| --- | --- | --- |']
    out += ['| '+' | '.join(cell(i[k]) for k in ('severity','path','message'))+' |' for i in report['issues']]
    out += ['','## 需求 → 规则 → 表达 → 验收','','| 功能 | 规则 | 表达 | 页面/状态/元素 | 验收 |','| --- | --- | --- | --- | --- |']
    out += ['| '+' | '.join(cell(v) for v in (r['feature'],r['rule'],r['mode'],'；'.join(f"{t.get('page')}/{t.get('state')}/{t.get('selector')}" for t in r['targets'] if isinstance(t,dict)),'、'.join(r['acceptance_ids'])))+' |' for r in report['coverage']]
    out += ['','## 功能类型检查','','| 功能 | 检查维度 | 结论 | 待决策/不适用理由 |','| --- | --- | --- | --- |']
    out += ['| '+' | '.join(cell(v) for v in (r['feature'],r['label'],r['status'],r['question'] or r['reason']))+' |' for r in report['checks']]
    out += ['','## 边界与状态表达','','| 用例 | 输入 | 预期 | 表达 | 文字表达理由 |','| --- | --- | --- | --- | --- |']
    out += ['| '+' | '.join(cell(r[k]) for k in ('id','input','expected','mode','reason'))+' |' for r in report['cases']]
    out += ['', '## 流程与状态图', '', '| 图 | 类型/层级 | 模块 | 上层图/节点 |', '| --- | --- | --- | --- |']
    out += ['| '+' | '.join(cell(v) for v in (d['title'],d['kind']+'/'+d['level'],d['module'],d['parent_id']+'/'+d['parent_node'] if d['parent_id'] else '模块全貌'))+' |' for d in report.get('diagrams',[])]
    return '\n\n'.join(out[:5])+'\n\n'+'\n'.join(out[5:])+'\n'
