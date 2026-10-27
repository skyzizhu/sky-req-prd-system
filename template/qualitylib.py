"""Evidence-based delivery checks; no model calls and no readiness claims."""
from collections import Counter
from html.parser import HTMLParser
import json
import re
import prdlib
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


def text_content(value):
    if isinstance(value,str):return value
    if isinstance(value,dict):return ' '.join(text_content(v) for v in value.values())
    if isinstance(value,list):return ' '.join(text_content(v) for v in value)
    return ''


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
        if a.get('id'):self.ids[a['id']]=dict(context,rule_ref=a.get('data-rule-ref'))
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
    for error in prdlib.rule_reference_errors(spec):
        issue('rule_reference_invalid',error['path'],error['message'])
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
            else:
                if item.get('impact','implementation') not in ('implementation','acceptance','editorial'):issue('decision_impact',path,'待决策影响类型无效')
                if item.get('impact','implementation')!='editorial' and not item['blocking']:issue('decision_nonblocking',path,'影响范围/实现的待决策输入不能标为不阻塞')
                issue('input_decision',path,item['question'],'error' if item['blocking'] else 'decision')
        else:issue('input_disposition',path,'输入条目需标 included、excluded 或 pending')
    obligations=[]
    rule_text={rule['id']:text_content([rule.get(k) for k in ('statement','clauses','table')]) for req in reqs.values() for rule in objects(req.get('rule_details')) if isinstance(rule,dict) and nonempty(rule.get('id'))}
    for item in objects(inputs):
        if not isinstance(item,dict) or item.get('disposition')!='included':continue
        constraints=item.get('constraints')
        if not isinstance(constraints,list) or not constraints:
            issue('input_constraints_missing',item.get('id','input'),'需逐项登记输入中的独立约束及规则去向');continue
        seen=set();constrained_rules=set()
        allowed={rule['id'] for rid in objects(item.get('requirement_ids')) for rule in objects(reqs.get(rid,{}).get('rule_details')) if isinstance(rule,dict) and nonempty(rule.get('id'))}
        for constraint in constraints:
            if not isinstance(constraint,dict) or not nonempty(constraint.get('id')) or not nonempty(constraint.get('quote')):
                issue('input_constraint_invalid',item['id'],'约束需有稳定编号及输入原文片段');continue
            path=item['id']+'/'+constraint['id']
            if constraint['id'] in seen:issue('input_constraint_invalid',path,'输入约束编号重复')
            seen.add(constraint['id'])
            bound=refs(constraint.get('rule_ids'),allowed,path,'输入规则');constrained_rules.update(bound)
            literals=constraint.get('literals',[])
            if not isinstance(literals,list) or any(not nonempty(v) for v in literals):
                issue('input_literal_invalid',path,'关键字面值需为非空文本数组');literals=[]
            normalize=lambda text:''.join(text.split())
            prose=normalize(' '.join(rule_text.get(k,'') for k in bound))
            for value in literals:
                token=normalize(value);pattern=(r'(?<!\d)' if token[0].isdigit() else '')+re.escape(token)+(r'(?!\d)' if token[-1].isdigit() else '')
                if not re.search(pattern,normalize(constraint['quote'])):issue('input_literal_invalid',path,'关键值不在所引用的输入片段中：'+value)
                elif not re.search(pattern,prose):issue('input_literal_missing',path,'关联规则遗漏输入关键值：'+value)
            obligations.append(dict(id=constraint['id'],input=item['id'],quote=constraint['quote'],rule_ids=bound,literals=literals))
        for rid in objects(item.get('requirement_ids')):
            owned={r.get('id') for r in objects(reqs.get(rid,{}).get('rule_details')) if isinstance(r,dict)}
            if not owned.intersection(constrained_rules):issue('input_constraint_uncovered',item['id']+'/'+rid,'该功能没有独立输入约束的规则去向')
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
    for pid,page in pages.items():
        review=page.get('state_review')
        if review is None:
            if has_prototype:issue('state_review_missing',pid,'原型交付需登记页面状态与局部变化核对')
            continue
        if not isinstance(review,list) or not review:
            issue('state_review_invalid',pid,'页面状态核对需为非空数组');continue
        dimensions=set();reviewed_states=set()
        for item in review:
            if not isinstance(item,dict) or not nonempty(item.get('dimension')):
                issue('state_review_invalid',pid,'状态核对需明确维度');continue
            dimension=item['dimension'];path=f'{pid}/state_review/{dimension}'
            if dimension in dimensions:issue('state_review_invalid',path,'状态核对维度重复')
            dimensions.add(dimension)
            status=item.get('status')
            if status=='covered':
                ids=item.get('state_ids')
                if not isinstance(ids,list) or not ids or any(not isinstance(sid,str) or (pid,sid) not in states for sid in ids):
                    issue('state_review_invalid',path,'需关联本页面有效的页面状态')
                else:reviewed_states.update(ids)
            elif status=='local':
                selectors=item.get('selectors');parser=dom.get(pid)
                if not nonempty(item.get('reason')) or not isinstance(selectors,list) or not selectors or any(not isinstance(s,str) or not s.startswith('#') for s in selectors):
                    issue('state_review_invalid',path,'局部变化需有控件定位及可操作核对路径')
                elif parser and any(not parser.ids.get(s[1:],{}).get('snapshot') for s in selectors):
                    issue('state_review_invalid',path,'局部核对目标须位于本页面画面内')
            elif status=='not_applicable':
                if not nonempty(item.get('reason')):issue('state_review_invalid',path,'不适用状态需有本次范围理由')
            else:issue('state_review_invalid',path,'需区分页面状态、局部变化或不适用')
        if has_prototype:
            missing={sid for page_id,sid in states if page_id==pid}-reviewed_states
            if missing:issue('state_review_uncovered',pid,'页面状态未纳入核对：'+'、'.join(sorted(missing)))
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
    if has_prototype:
        for (pid,sid),inventory in inventories.items():
            for selector in inventory:
                parser=dom.get(pid)
                element=parser.ids.get(selector.lstrip('#'),{}) if parser else {}
                # A container annotation does not explain every child control.
                linked=any(isinstance(it,dict) and it.get('page')==pid and (not it.get('state_ids') or sid in objects(it['state_ids'])) and (it.get('selector')==selector or element.get('rule_ref')==it.get('id')) and any(rule_owners.get(rule) in objects(it.get('requirement_ids')) for rule in objects(it.get('rule_ids'))) for it in interaction_items)
                if parser and not linked:issue('element_annotation_missing',f'{pid}/{sid}/{selector}','必要业务元素缺少当前状态的精确标注，不能用外层区域说明代替')
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
                    linked=any(isinstance(it,dict) and it.get('page')==key[0] and rule_id in objects(it.get('rule_ids')) and rule_owners.get(rule_id) in objects(it.get('requirement_ids')) and (not it.get('state_ids') or key[1] in objects(it['state_ids'])) and (it.get('selector')==selector or (dom.get(key[0]) and dom[key[0]].ids.get(selector.lstrip('#'),{}).get('rule_ref')==it.get('id'))) for it in interaction_items)
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
            content_error=prdlib.rule_content_error(rule)
            if content_error:issue('rule_content_invalid',path,content_error)
            if 'table' in rule:
                error=prdlib.rule_table_error(rule['table'])
                if error:issue('rule_table_invalid',path,error)
            examples=rule.get('examples',[])
            if not isinstance(examples,list) or any(not isinstance(e,dict) or not nonempty(e.get('input')) or not nonempty(e.get('expected')) for e in examples):issue('example_invalid',path,'实例需有具体输入与预期；简单规则可不写实例')
            ac_refs=refs(rule.get('acceptance_ids'),acceptance,path,'验收',required=scope.get('acceptance',True));used_ac.update(ac_refs)
            mode,targets=presentation(rule.get('presentation'),path,[rid],[rule_id])
            coverage.append(dict(requirement=rid,feature=req.get('title',rid),rule=rule_id,mode=mode,targets=targets,acceptance_ids=ac_refs))
        for ac_id,ac in acceptance.items():
            if any(not nonempty(ac.get(k)) for k in ('given','when','then')):issue('acceptance_incomplete',f'{rid}/{ac_id}','验收需有前置、操作和可观察预期')
            if 'kind' in ac and ac['kind'] not in ('boundary','exception','normal'):issue('acceptance_kind',f'{rid}/{ac_id}','验收场景类型无效')
            if ac_id not in used_ac:issue('acceptance_orphan',f'{rid}/{ac_id}','验收未关联到任何规则')
        cases={};raw_cases=req.get('boundary_cases',[])
        if not isinstance(raw_cases,list):issue('cases_invalid',rid,'边界与异常用例需为列表')
        for case in objects(raw_cases):
            if not isinstance(case,dict) or not nonempty(case.get('id')):issue('case_invalid',rid,'边界用例缺少稳定编号');continue
            path=f'{rid}/{case["id"]}';case_total+=1
            if case['id'] in cases:issue('case_duplicate',path,'用例编号重复')
            cases[case['id']]=case
            if case.get('kind') not in ('boundary','exception','normal'):issue('case_incomplete',path,'用例类型无效')
            try:scenario=prdlib.case_scenario(case,req)
            except ValueError as error:
                issue('case_incomplete',path,str(error));scenario=case
            case_rules=refs(case.get('rule_ids'),rules,path,'用例规则')
            case_ac=refs(case.get('acceptance_ids'),acceptance,path,'用例验收',required=scope.get('acceptance',True))
            supported={ac_id for rule_id in case_rules for ac_id in objects(rules[rule_id].get('acceptance_ids'))}
            if any(ac_id not in supported for ac_id in case_ac):issue('case_acceptance_mismatch',path,'用例验收不属于关联规则')
            for ac_id in case_ac:
                ac_kind=acceptance[ac_id].get('kind')
                if 'input' not in case and ac_kind is None:issue('case_acceptance_kind',path,'引用场景需明确验收的 kind，避免空态关联到失败重试')
                elif ac_kind is not None and ac_kind!=case.get('kind'):issue('case_acceptance_kind',path,'用例类型与验收场景不一致')
            view=case.get('presentation')
            mode,targets=presentation(view,path,[rid],case_rules if isinstance(view,dict) and view.get('mode')=='prototype' else [])
            case_rows.append(dict(requirement=rid,feature=req.get('title',rid),id=case['id'],kind=case.get('kind'),input=scenario.get('input',''),expected=scenario.get('expected',''),mode=mode,targets=targets,reason=view.get('reason','') if isinstance(view,dict) else ''))
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
                impact=check.get('impact','implementation')
                if impact not in ('implementation','acceptance','editorial'):issue('decision_impact',path,'待决策影响需为 implementation、acceptance 或 editorial')
                if impact in ('implementation','acceptance') and check.get('blocking') is not True:issue('decision_nonblocking',path,'影响实现或验收的未决问题不能标为不阻塞')
                if not nonempty(check.get('question')) or type(check.get('blocking')) is not bool:issue('decision_invalid',path,'待确认检查项需说明具体问题与是否阻塞')
                else:issue('feature_decision',path,check['question'],'error' if check['blocking'] else 'decision')
            else:issue('check_missing',path,'未核对适用检查项：'+label)
            check_rows.append(dict(requirement=rid,feature=req.get('title',rid),dimension=dimension,label=label,status=status or 'missing',rule_ids=objects(check.get('rule_ids')),question=check.get('question',''),reason=check.get('reason',''),blocking=check.get('blocking',False)))
        for key in checks.keys()-dimensions.keys():issue('unknown_dimension',f'{rid}/review/{key}','检查维度不属于选定功能类型，需校正类型或维度')
    # Mobile delivery applicability is evidence, not another source of business rules.
    mobile_rows=[]; form=None
    if content is not None:
        try: form=json.loads((Path(content)/'manifest.json').read_text(encoding='utf-8')).get('product',{}).get('form')
        except (OSError,ValueError,TypeError): pass  # Existing structure validation reports malformed manifests.
    mobile=quality.get('mobile_review')
    if form in ('mobile','h5','miniapp') or mobile is not None:
        dimensions={'platform','navigation','interruption','authorization','network','components'}
        if not isinstance(mobile,list):
            issue('mobile_review_missing','quality.mobile_review','移动端交付需登记平台、导航、中断、授权、网络与组件适用性');mobile=[]
        known_rules={r['id']:r for req in reqs.values() for r in objects(req.get('rule_details')) if isinstance(r,dict) and nonempty(r.get('id'))}
        known_ac={a['id']:a for req in reqs.values() for a in objects(req.get('acceptance')) if isinstance(a,dict) and nonempty(a.get('id'))}
        seen=set()
        for check in mobile:
            if not isinstance(check,dict) or check.get('dimension') not in dimensions:
                issue('mobile_dimension_invalid','quality.mobile_review','移动检查维度无效');continue
            key=check['dimension'];path='quality.mobile_review/'+key
            if key in seen:issue('mobile_dimension_duplicate',path,'移动检查维度重复')
            seen.add(key);status=check.get('status')
            if status=='covered':
                rr=refs(check.get('rule_ids'),known_rules,path,'移动规则')
                aa=refs(check.get('acceptance_ids'),known_ac,path,'移动验收')
                supported={aid for rid in rr for aid in objects(known_rules[rid].get('acceptance_ids'))}
                if any(aid not in supported for aid in aa):issue('mobile_acceptance_unrelated',path,'移动验收未被关联规则支持')
            elif status=='not_applicable':
                if key=='platform' or not nonempty(check.get('reason')):issue('mobile_applicability_invalid',path,'需具体不适用理由；平台不能跳过')
            elif status=='pending':
                if not nonempty(check.get('question')) or check.get('impact') not in ('implementation','acceptance','editorial') or type(check.get('blocking')) is not bool:
                    issue('mobile_decision_invalid',path,'待决策需具体问题、影响与阻塞结论')
                else:
                    if check['impact']!='editorial' and not check['blocking']:issue('decision_nonblocking',path,'移动实现/验收问题不能降为不阻塞')
                    issue('mobile_decision',path,check['question'],'error' if check['blocking'] else 'decision')
            else:issue('mobile_check_invalid',path,'需covered、pending或not_applicable')
            mobile_rows.append(check)
        for key in sorted(dimensions-seen):issue('mobile_check_missing','quality.mobile_review/'+key,'缺少移动交付适用性检查')
    if pending_rules:issue('rules_pending','requirements',f'{pending_rules} 条规则仍待业务确认','decision')
    if content is not None and scope.get('prd'):
        try:
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
            'mobile_review':mobile_rows,'input_constraints':obligations,'issues':issues,'coverage':coverage,'checks':check_rows,'cases':case_rows,
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
    out += ['', '## 输入独立约束追溯', '', '| 约束 | 原文片段 | 规则 | 关键字面值 |', '| --- | --- | --- | --- |']
    out += ['| '+' | '.join(cell(v) for v in (c['id'],c['quote'],'、'.join(c['rule_ids']),'、'.join(c['literals'])))+' |' for c in report.get('input_constraints',[])]
    out += ['', '## 流程与状态图', '', '| 图 | 类型/层级 | 模块 | 上层图/节点 |', '| --- | --- | --- | --- |']
    out += ['| '+' | '.join(cell(v) for v in (d['title'],d['kind']+'/'+d['level'],d['module'],d['parent_id']+'/'+d['parent_node'] if d['parent_id'] else '模块全貌'))+' |' for d in report.get('diagrams',[])]
    return '\n\n'.join(out[:5])+'\n\n'+'\n'.join(out[5:])+'\n'
