#!/usr/bin/env python3
"""Build the V2 static-reader preview in an empty directory (synthetic data)."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

SKILL = Path(__file__).resolve().parents[1]

def state_elements(sid):
    if sid=='success':return [{'selector':'#success-focus','title':'成功结果'},{'selector':'#success-back','title':'返回订单列表'}]
    pairs=[(sid+'-name','订单名称'),(sid+'-amount','金额'),(sid+'-remark','备注'),(sid+'-cancel','取消按钮'),('submitting-focus' if sid=='submitting' else sid+'-submit','创建订单按钮')]
    if sid in ('invalid','failed'):pairs.append((sid+'-focus','名称错误提示' if sid=='invalid' else '失败提示'))
    return [{'selector':'#'+key,'title':title} for key,title in pairs]


def add_diagrams(spec):
    """Synthetic examples: module overview -> creation node -> flow and UI-state details."""
    rid='FR-ORDER-001'
    def node(key,label,**extra):return dict(id=key,label=label,**extra)
    def edge(start,end,label,rule=None):
        value={'from':start,'to':end,'label':label}
        if rule:value['rule_ids']=['RULE-ORDER-'+rule]
        return value
    def diagram(key,title,kind,level,nodes,edges,**extra):return dict(id=key,title=title,kind=kind,level=level,module='订单管理',source='ai-inferred',status='pending',nodes=nodes,edges=edges,**extra)
    spec['diagrams']=[
        diagram('FLOW-ORDER','订单管理 · 本次范围流程','flow','module',[
            node('entry','已登录且有创建权限',entry=True),node('create','创建订单',requirement_ids=[rid]),node('list','列表展示新订单（已有能力/交接点）',terminal=True),node('invalid','校验失败：提示并定位字段'),node('failed','请求失败：保留输入')],
            [edge('entry','create','进入创建页'),edge('create','invalid','校验失败','INVALID'),edge('invalid','create','修正后提交','INVALID'),edge('create','failed','请求失败','FAILURE'),edge('failed','create','重试','FAILURE'),edge('create','list','创建成功并返回列表','SUCCESS')],summary='覆盖本次创建功能及已有列表交接点；权限细节待确认，支付、审批、编辑、删除不在本图范围。'),
        diagram('FLOW-CREATE','创建订单 · 子流程','flow','detail',[
            node('fill','填写名称、金额、备注',entry=True),node('check','校验名称',type='decision'),node('error','显示字段错误并定位'),node('send','提交请求并禁用按钮'),node('fail','提示失败，保留输入'),node('done','创建成功，返回列表',terminal=True)],
            [edge('fill','check','点击创建订单'),edge('check','error','名称无效','INVALID'),edge('error','fill','修正名称'),edge('check','send','校验通过','NAME'),edge('send','fail','请求失败','FAILURE'),edge('fail','check','修改后重新校验','FAILURE'),edge('send','done','请求成功','SUCCESS')],
            requirement_id=rid,parent_id='FLOW-ORDER',parent_node='create',summary='字段其他限制与提交契约仍待确认；本图只展开示例已登记的名称校验与提交反馈。'),
        diagram('STATE-CREATE','创建页面 · 交互状态流转','state','detail',[
            node('idle','默认/填写',entry=True,prototype={'page':'create-order','state':'default'}),node('invalid','校验失败',prototype={'page':'create-order','state':'invalid'}),node('sending','提交中',prototype={'page':'create-order','state':'submitting'}),node('failed','提交失败',prototype={'page':'create-order','state':'failed'}),node('success','创建成功',terminal=True,prototype={'page':'create-order','state':'success'})],
            [edge('idle','invalid','提交且名称无效','INVALID'),edge('invalid','idle','修正名称'),edge('idle','sending','提交且校验通过','NAME'),edge('sending','failed','请求失败','FAILURE'),edge('failed','sending','有效输入下重新提交','FAILURE'),edge('sending','success','请求成功','SUCCESS'),edge('sending','sending','重复点击：禁用，不发起请求','SUBMITTING'),edge('failed','invalid','修改后重试且校验失败','INVALID')],
            requirement_id=rid,parent_id='FLOW-ORDER',parent_node='create',summary='这是页面交互状态，不是订单的支付或审批状态；状态画面见静态原型。')]
    # Review evidence refers to canonical GWT and stable edge IDs, never copies scenario prose.
    for d in spec['diagrams']:
        for i,e in enumerate(d['edges']):e['id']='E'+str(i+1).zfill(2)
    by_id={d['id']:d for d in spec['diagrams']}
    by_id['FLOW-ORDER']['path_reviews']=[
        {'id':'PATH-SUCCESS','acceptance_ids':['AC-ORDER-SUCCESS'],'edge_ids':['E01','E06']},
        {'id':'PATH-INVALID','acceptance_ids':['AC-ORDER-INVALID'],'edge_ids':['E02','E03']},
        {'id':'PATH-FAILURE','acceptance_ids':['AC-ORDER-FAILURE'],'edge_ids':['E04','E05']}]
    by_id['FLOW-CREATE']['path_reviews']=[
        {'id':'PATH-SUCCESS','acceptance_ids':['AC-ORDER-SUCCESS'],'edge_ids':['E01','E04','E07']},
        {'id':'PATH-INVALID','acceptance_ids':['AC-ORDER-INVALID'],'edge_ids':['E01','E02','E03']},
        {'id':'PATH-FAILURE','acceptance_ids':['AC-ORDER-FAILURE'],'edge_ids':['E04','E05','E06']},
        {'id':'PATH-RETRY-INVALID','acceptance_ids':['AC-ORDER-RETRYINVALID'],'edge_ids':['E06','E02','E03']}]
    by_id['STATE-CREATE']['path_reviews']=[
        {'id':'PATH-SUCCESS','acceptance_ids':['AC-ORDER-SUCCESS'],'edge_ids':['E03','E06']},
        {'id':'PATH-INVALID','acceptance_ids':['AC-ORDER-INVALID'],'edge_ids':['E01','E02']},
        {'id':'PATH-FAILURE','acceptance_ids':['AC-ORDER-FAILURE'],'edge_ids':['E03','E04','E05']},
        {'id':'PATH-DUPLICATE','acceptance_ids':['AC-ORDER-SUBMITTING'],'edge_ids':['E07']},
        {'id':'PATH-RETRY-INVALID','acceptance_ids':['AC-ORDER-RETRYINVALID'],'edge_ids':['E08']}]
    spec.setdefault('quality',{})['module_reviews']=[{'module':'订单管理','flow':{'status':'covered','diagram_ids':['FLOW-ORDER'],'requirement_ids':[rid]}}]
    spec['requirements'][0]['diagram_review']={
        'flow':{'status':'covered','diagram_ids':['FLOW-CREATE']},
        'state':{'status':'covered','diagram_ids':['STATE-CREATE']}}
    return spec


def add_quality(spec):
    """Synthetic review evidence; pending business decisions remain pending."""
    req=spec['requirements'][0]
    def text(reason):return {'mode':'text','reason':reason}
    def visual(sid,selector):return {'mode':'prototype','targets':[{'page':'create-order','state':sid,'selector':selector}]}
    targets={'INVALID':('invalid','#invalid-focus'),'SUBMITTING':('submitting','#submitting-focus'),'SUCCESS':('success','#success-focus'),'FAILURE':('failed','#failed-focus')}
    for rule in req['rule_details']:
        key=rule['id'].removeprefix('RULE-ORDER-')
        rule['presentation']=visual(*targets[key]) if key in targets else text('字段约束与数值口径通过文字说明；不增加布局或反馈类型。')
    # A boundary index references canonical GWT; no copied input/expected prose.
    extra=[('MAX','去除首尾空格后名称为40字','校验名称','长度校验通过'),('OVER','去除首尾空格后名称为41字','校验名称','长度校验不通过，具体提示文案待产品确认')]
    extra.append(('RETRYINVALID','创建请求明确失败，当前表单保留','将名称清空后重新提交','显示名称必填错误，不发起请求，其他已填字段保留'))
    for key,given,when,then in extra:
        req['acceptance'].append({'id':'AC-ORDER-'+key,'given':given,'when':when,'then':then,'kind':'boundary'})
    next(a for a in req['acceptance'] if a['id']=='AC-ORDER-INVALID')['then']='拒绝提交，不发起请求，显示“请输入订单名称”并定位该字段'
    name=next(r for r in req['rule_details'] if r['id']=='RULE-ORDER-NAME')
    name['acceptance_ids']+=['AC-ORDER-MAX','AC-ORDER-OVER','AC-ORDER-RETRYINVALID']
    for key in ('INVALID','FAILURE','CREATE'):
        next(r for r in req['rule_details'] if r['id']=='RULE-ORDER-'+key)['acceptance_ids'].append('AC-ORDER-RETRYINVALID')
    req['boundary_cases']=[]
    for cid,kind,key,aid,view in [
        ('EMPTY','boundary','INVALID','INVALID',visual('invalid','#invalid-focus')),
        ('MAX','boundary','NAME','MAX',text('同布局的数值上界由验收场景验证。')),
        ('OVER','boundary','NAME','OVER',text('复用字段错误布局，提示文案仍待确认。')),
        ('FAIL','exception','FAILURE','FAILURE',visual('failed','#failed-focus')),
        ('RETRYINVALID','boundary','NAME','RETRYINVALID',visual('invalid','#invalid-focus'))]:
        next(a for a in req['acceptance'] if a['id']=='AC-ORDER-'+aid)['kind']=kind
        req['boundary_cases'].append({'id':'BC-ORDER-'+cid,'kind':kind,'rule_ids':['RULE-ORDER-'+key],'acceptance_ids':['AC-ORDER-'+aid],'presentation':view})
    req['review']={'types':['form'],'checks':[
        {'dimension':'fields','status':'pending','question':'备注长度、金额必填及默认值需产品确认。','impact':'implementation','blocking':True},
        {'dimension':'validation','status':'covered','rule_ids':['RULE-ORDER-NAME','RULE-ORDER-INVALID'],'case_ids':['BC-ORDER-EMPTY','BC-ORDER-MAX','BC-ORDER-OVER']},
        {'dimension':'submission','status':'covered','rule_ids':['RULE-ORDER-SUBMITTING']},
        {'dimension':'result','status':'covered','rule_ids':['RULE-ORDER-SUCCESS']},
        {'dimension':'recovery','status':'covered','rule_ids':['RULE-ORDER-FAILURE'],'case_ids':['BC-ORDER-FAIL']},
        {'dimension':'permissions','status':'pending','question':'可创建订单的角色与无权限访问处理需确认。','impact':'implementation','blocking':True}]}
    spec['quality']={'schema_version':1,'scope':{'prd':True,'prototype':True,'acceptance':True},'input_items':[
        {'id':'INPUT-ORDER-001','summary':'合成演示方案：名称、金额、备注及创建结果反馈。','disposition':'included','requirement_ids':[req['id']],'constraints':[
            {'id':'INPUT-NAME','quote':'名称必填，去除首尾空格后1～40字。','rule_ids':['RULE-ORDER-NAME'],'literals':['1～40字']},
            {'id':'INPUT-AMOUNT','quote':'金额按人民币元展示，保留两位小数。','rule_ids':['RULE-ORDER-AMOUNT'],'literals':['人民币元','两位小数']},
            {'id':'INPUT-REMARK','quote':'备注选填，新建为空。','rule_ids':['RULE-ORDER-REMARK'],'literals':['选填']},
            {'id':'INPUT-RESULT','quote':'提交中防重复；明确失败保留输入，成功后列表新增记录。','rule_ids':['RULE-ORDER-SUBMITTING','RULE-ORDER-SUCCESS','RULE-ORDER-FAILURE']},
            {'id':'INPUT-CANCEL','quote':'取消丢弃本次未提交输入。','rule_ids':['RULE-ORDER-CANCEL'],'literals':['丢弃']}
        ]},
        {'id':'INPUT-ORDER-002','summary':'支付、审批、订单编辑与删除。','disposition':'excluded','reason':'不属于此次创建页演示范围。'}]}
    return add_diagrams(spec)


def example_spec():
    """Return fresh synthetic states and spec; shared by the preview and graph tests."""
    states=[('default','默认','打开创建页，尚未填写。'),('invalid','校验失败','提交时名称为空。'),('submitting','提交中','校验通过，正在提交。'),('success','创建成功','订单创建完成。'),('failed','提交失败','请求失败，保留已填内容。')]
    rules=[('NAME','validation','名称必填；去除首尾空格后为 1～40 字。'),('AMOUNT','data','金额使用人民币元，保留两位小数。'),('INVALID','validation','名称为空时显示“请输入订单名称”，定位该字段。'),('SUBMITTING','state','提交中禁用提交按钮，防止重复提交。'),('SUCCESS','feedback','成功后关闭创建页，列表新增该订单并置于首行。'),('FAILURE','feedback','失败后保留已填内容，显示失败提示，允许重新提交。')]
    rules[-1:-1]=[('REMARK','fields','备注选填，新建为空；填写内容随订单提交，长度限制待确认。'),('CREATE','behavior','点击创建订单时先校验填写内容；通过后发起创建并进入提交中。'),('CANCEL','behavior','取消时返回订单列表，丢弃本次未提交输入；提交中取消是否可用待确认。')]
    cases=[('NAME','位于创建页','输入仅含空格的名称并提交','拒绝提交，提示名称必填'),('AMOUNT','金额输入为 1280','提交并展示订单金额','显示 1,280.00 元'),('INVALID','名称为空','点击创建订单','显示“请输入订单名称”并定位该字段'),('SUBMITTING','请求正在处理中','再次点击提交','按钮不可用，不发起重复请求'),('SUCCESS','信息有效且请求成功','完成创建','关闭创建页，列表首行显示新订单'),('FAILURE','已填写有效信息','创建请求失败','保留全部输入，显示失败提示并允许重试')]
    cases[-1:-1]=[('REMARK','新建订单且备注为空','填写备注后创建成功','订单保留填写的备注'),('CREATE','填写内容有效','点击创建订单','发起创建并进入提交中'),('CANCEL','尚未提交订单','点击取消','返回订单列表，不保存本次输入')]
    ac=[{'id':'AC-ORDER-'+key,'given':given,'when':when,'then':then} for key,given,when,then in cases]
    req={'id':'FR-ORDER-001','title':'创建订单','module':'订单管理','description':'填写订单信息并创建订单。','source':'ai-inferred','status':'pending','blocking':False,'rule_details':[{'id':'RULE-ORDER-'+key,'category':cat,'statement':statement,'source':'ai-inferred','status':'pending','acceptance_ids':['AC-ORDER-'+key]} for key,cat,statement in rules],'acceptance':ac}
    titles={'NAME':'名称填写约束','AMOUNT':'金额展示口径','INVALID':'名称为空提示','SUBMITTING':'重复提交保护','SUCCESS':'创建成功结果','FAILURE':'明确失败恢复','REMARK':'备注填写','CREATE':'发起创建','CANCEL':'取消与未保存输入'}
    for rule in req['rule_details']:rule['title']=titles[rule['id'].removeprefix('RULE-ORDER-')]
    req['rule_details'][0]['category']='fields'
    req['rule_details'][0]['table']={'columns':['字段','来源 / 初值','编辑性'], 'rows':[['订单名称','新建为空','可编辑；校验见本规则']]}
    req['rule_details'][0]['examples']=[{'input':'名称仅含空格','expected':'拒绝提交，提示名称必填'}]
    interactions=[]
    def area(key, selector, title, state=None):
        it={'id':'INT-ORDER-'+key,'page':'create-order','selector':'#'+selector,'title':title,'description':title,'action':'inspect','requirement_ids':[req['id']],'rule_ids':['RULE-ORDER-'+key]}
        if state:it['state_ids']=[state]
        interactions.append(it)
    area('NAME','order-canvas','订单名称')
    area('AMOUNT','order-canvas','金额口径')
    area('REMARK','order-canvas','备注输入')
    area('CANCEL','order-canvas','取消与未保存输入')
    area('CREATE','order-canvas','创建与字段校验')
    interactions[-1]['id']='INT-ORDER-CREATE'
    interactions[-1]['state_ids']=['default','invalid','failed']
    for key, sid,title in [('INVALID','invalid','名称校验'),('SUBMITTING','submitting','提交保护'),('SUCCESS','success','成功结果'),('FAILURE','failed','失败反馈')]:area(key,sid+'-focus',title,sid)
    spec={'schema_version':2,'requirements':[req], 'pages':[{'id':'create-order','title':'创建订单','purpose':'查看订单创建页各状态及规则。','handoff':{'role':'产品运营'},'requirement_ids':[req['id']],'states':[{'id':sid,'title':title,'summary':summary,'elements':state_elements(sid),'next':{'default':'填写后提交；无效输入进入校验失败。','invalid':'修正名称后重新提交。','submitting':'请求成功进入成功状态，失败进入提交失败。','success':'返回订单列表，显示新订单。','failed':'保留输入；允许重试，进入提交中。'}[sid]} for sid,title,summary in states]}],'interactions':interactions}
    next(it for it in interactions if it['id']=='INT-ORDER-INVALID')['rule_ids']=['RULE-ORDER-INVALID','RULE-ORDER-NAME']
    spec['pages'][0]['state_review']=[{'dimension':'初始进入','status':'covered','state_ids':['default']},{'dimension':'校验错误','status':'covered','state_ids':['invalid']},{'dimension':'提交反馈','status':'covered','state_ids':['submitting','success','failed']},{'dimension':'本地填写','status':'local','selectors':['#default-name','#default-amount','#default-remark'],'reason':'输入后切换Tab，核对每个状态恢复预设内容'}]
    spec=add_quality(spec)
    for it in interactions:
        if not it.get('state_ids'):it['state_ids']=['default','invalid','submitting','failed']
    interactions.append({'id':'INT-ORDER-BACK','page':'create-order','selector':'#success-back','title':'返回订单列表','description':'成功后的返回入口','action':'inspect','requirement_ids':[req['id']],'rule_ids':['RULE-ORDER-SUCCESS'],'state_ids':['success']})
    return states, spec


def generate(root):
    subprocess.run([sys.executable, str(SKILL/'scripts/project.py'), 'init', str(root), '--name', '订单创建 · V2 重构预览', '--form', 'web', '--version', 'v0.1'], check=True)
    content = root/'versions/v0.1/content'
    def save(name, value):
        (content/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assets=content/'prototype/assets';assets.mkdir(parents=True,exist_ok=True)
    for name in ('prototype-runtime.js','prototype-runtime.css'):
        shutil.copy2(SKILL/'assets'/name, assets/name)
    shutil.copy2(SKILL/'examples/static-reader/page.css', assets/'page.css')
    states, spec = example_spec()
    save('spec.json',spec)
    snapshots=[]
    for sid,title,summary in states:
        if sid=='success':
            inside='<div id="success-focus" class="success-block"><span class="success-icon">✓</span><h3>订单创建成功</h3><p>列表已新增“秋季活动物料”。</p><button type="button" id="success-back" class="visual-button">返回订单列表</button></div>'
        else:
            name='' if sid in ('default','invalid') else '秋季活动物料'
            field='<input type="text" aria-label="订单名称" id="'+sid+'-name" data-rule-ref="INT-ORDER-NAME" data-ps-local="input" class="field '+('invalid' if sid=='invalid' else '')+'" value="'+name+'" placeholder="请输入订单名称"'+(' disabled' if sid=='submitting' else '')+'>'
            if sid=='invalid':field='<div id="invalid-focus">'+field+'<p class="field-error">请输入订单名称</p></div>'
            inside='<div class="form-body"><label>订单名称 <span>*</span></label>'+field+'<label>金额（元）</label><input type="text" inputmode="decimal" aria-label="金额（元）" id="'+sid+'-amount" data-rule-ref="INT-ORDER-AMOUNT" data-ps-local="input" class="field" value="'+('1,280.00' if name else '')+'" placeholder="0.00"'+(' disabled' if sid=='submitting' else '')+'><label>备注</label><textarea aria-label="备注" id="'+sid+'-remark" data-rule-ref="INT-ORDER-REMARK" data-ps-local="input" class="field multiline" placeholder="选填"'+(' disabled' if sid=='submitting' else '')+'>'+('活动用物料' if name else '')+'</textarea>'
            if sid=='failed':inside+='<div id="failed-focus" class="error-banner">提交失败，请重试。已保留填写内容。</div>'
            inside+='</div><div class="form-footer"><button type="button" id="'+sid+'-cancel" data-rule-ref="INT-ORDER-CANCEL" class="visual-button secondary">取消</button><button type="button" '+('id="submitting-focus" ' if sid=='submitting' else 'id="'+sid+'-submit" data-rule-ref="INT-ORDER-CREATE" ')+'class="visual-button '+('disabled' if sid=='submitting' else '')+'"'+(' disabled' if sid=='submitting' else '')+'>'+('提交中…' if sid=='submitting' else '创建订单')+'</button></div>'
        snapshots.append('<section data-ps-state="'+sid+'"><h2>'+title+' · '+summary+'</h2><div class="sr-snapshot"><div class="app-top"><strong>工作台</strong><span>订单 / 创建订单</span><span>林晓 · 产品运营</span></div><div class="app-content"><div class="form-card"><div class="form-heading"><h3>创建订单</h3><p>填写订单信息</p></div>'+inside+'</div></div></div></section>')
    html='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>创建订单 · 静态原型</title><link rel="stylesheet" href="assets/page.css"><link rel="stylesheet" href="assets/prototype-runtime.css"></head><body data-page-id="create-order" data-prototype-mode="static"><main id="order-canvas">'+''.join(snapshots)+'</main><script src="assets/spec-data.js"></script><script src="assets/prototype-runtime.js"></script></body></html>'
    (content/'prototype/create-order.html').write_text(html,encoding='utf-8')
    m=json.loads((content/'manifest.json').read_text());m['modules'] += [{'id':'requirements','title':'功能需求','pages':[{'id':'spec','title':'功能需求','type':'spec','source':'ai-inferred','status':'pending'}]},{'id':'prototype','title':'页面与状态','pages':[{'id':'create-order','title':'创建订单','type':'prototype','file':'prototype/create-order.html','source':'ai-inferred','status':'pending'}]}];save('manifest.json',m)
    (content/'overview/index.md').write_text('<!-- prd-status: provided -->\n<!-- prd-reason: 合成示例，用于评审阅读方式 -->\n# 本次概览与边界\n\n本示例用于评审 V2 的 PRD 层级和静态原型阅读方式，所有业务规则均为 AI 合成、待确认。\n\n## 本次做\n- 创建订单页面：名称、金额、备注及提交反馈。\n- 默认、校验失败、提交中、创建成功、提交失败五种静态状态。\n\n## 本次不做\n- 真实接口、支付、审批、订单编辑与删除。\n- 动态提交演示、进度模拟及批注管理。\n\n## 已有能力影响\n这是独立预览，不迁移或覆盖已有项目。\n',encoding='utf-8')
    documents={
      'users':('用户与业务流程','角色：产品运营，需有创建订单权限（演示方案，待确认）。\n\n主流程：填写信息 → 提交中 → 创建成功 → 返回列表。\n\n异常流程：名称校验失败时就地修正；请求失败时保留输入并重试。状态细节见静态原型，业务规则以功能章节为准。'),
      'tracking':('数据与埋点','目标指标：创建成功率 = 创建成功次数 / 发起创建次数；排除前端校验未通过的尝试，重试按请求计数。\n\n| 事件 | 触发时机 | 必要参数 |\n| --- | --- | --- |\n| order_create_submit | 校验通过、发起请求时 | request_id、结果状态 |\n| order_create_result | 请求返回成功或失败时 | request_id、result、error_type |\n\n不记录名称和备注正文。按 request_id 去重结果事件；采集授权、上报通道与观察周期待数据评审。指标基线及目标值待确认。'),
      'nonfunctional':('非功能需求','- 兼容：桌面浏览器矩阵及验证负责人待技术确认。\n- 可访问性：键盘可达，标签关联正确，错误反馈可被辅助技术感知；以键盘与读屏核对。\n- 性能：实际负载、响应和超时目标待技术评审，不编造已达标结论。\n- 业务恢复遵循第三章 RULE-ORDER-FAILURE；数据采集范围引用第四章，不重复维护口径。'),
      'acceptance':('验收与上线条件','验收按功能规则及其用例执行；正常、校验失败、重复提交、成功、失败重试均须覆盖。\n\n上线前：产品确认待决策规则，设计确认视觉稿，开发完成接口与权限校验，测试记录实际结果。发布窗口、观察时长、监控及回滚负责人待确定。\n\n本预览只验证交付文档与状态画面，不代表真实产品测试通过。'),
      'milestones':('里程碑与计划','| 阶段 | 交付物 | 完成条件 | 责任角色 |\n| --- | --- | --- | --- |\n| 方案评审 | PRD、静态原型 | 范围与阻塞问题明确 | 产品、设计、技术负责人 |\n| 实现与联调 | 功能及接口 | 规则实现并完成联调 | 开发 |\n| 验收与发布 | 测试结果、发布清单 | 缺陷处置与发布条件满足 | 测试、产品、发布负责人 |\n\n具体人员、日期和排期由团队评审后补充。'),
      'risks':('风险与待决策','| 待决策 | 影响 | 建议确认角色 |\n| --- | --- | --- |\n| 名称长度、金额上限及负数是否允许 | 校验与错误提示 | 产品 |\n| 请求超时、幂等和重复订单判定 | 接口及失败重试 | 技术负责人 |\n| 创建页关闭与返回后的数据刷新 | 页面状态一致性 | 产品、开发、测试 |\n\n以上均为演示方案的待确认项；未确认前不作为开工已就绪的证明。'),
      'appendix':('附录与参考资料','术语：订单金额以人民币元展示；request_id 用于关联一次创建请求。\n\n本示例为 AI 合成方案，用于评审技能产物；没有关联正式设计稿或已签署接口契约。画面用于布局与状态示意，视觉细节由设计交付。')
    }
    # Example context is synthetic; do not invent research evidence or a realized benefit.
    overview=content/'overview/index.md'
    overview.write_text(overview.read_text()+'\n## 背景与目标\n\n项目与版本见站点；产品负责人待指定，文档待人工评审，“规划中”仅表示版本进度。来源为脚本中的合成输入，真实现状、用户访谈和问题数据未提供。目标是让产品运营完成订单创建并理解成功/失败反馈；真实收益尚未验证。候选观察指标为创建成功率，口径见第四章，基线与目标值待确认。\n\n本次采用单页表单及明确反馈，依据是合成输入范围；未提供真实备选及选择理由，不编造方案比较。既有登录身份和订单列表能力需实际项目核实，不能把示例画面当作已具备的系统。\n',encoding='utf-8')
    title,body=documents['users']
    documents['users']=(title,body+'\n\n典型场景：产品运营需要登记一笔订单，任务是填写名称、金额和备注，提交后确认结果并返回列表。此场景由方案归纳，不作为用户调研结论。')
    title,body=documents['acceptance']
    documents['acceptance']=(title,body+'\n\n## 上线后效果验证\n\n真实上线后可按第四章口径观察创建成功率，目标是确认创建任务能稳定完成；它不代表营收或效率提升。试用对象、版本、观察窗口、比较基线、目标及实际复盘负责人待产品/数据确认。无可比基线时只报告观察值；发现失败集中先核对原因，再决定修复或继续观察。结果和决策进入复盘台账，示例不预填收益。')
    for name,(title,body) in documents.items():
      (content/'prd'/ (name+'.md')).write_text('<!-- prd-status: provided -->\n<!-- prd-reason: 合成方案，业务细节待评审确认 -->\n# '+title+'\n\n'+body+'\n',encoding='utf-8')
    subprocess.run([sys.executable,str(root/'build.py')],check=True)
    subprocess.run([sys.executable,str(SKILL/'scripts/validate.py'),str(root),'--structure-only'],check=True)
    sys.path.insert(0,str(SKILL/'scripts'))
    from audit_quality import project_report, save_report
    report=project_report(root);save_report(report,root/'quality-report')
    unexpected=[i for i in report['issues'] if i['severity']=='error' and i['code']!='feature_decision']
    if unexpected:raise ValueError(str(unexpected))
    print('交付检查：'+report['status']+'；示例为评审草稿，关键字段/权限未决事项须先明确。')
    subprocess.run([sys.executable,str(SKILL/'scripts/project.py'),'checkpoint',str(root)],check=True)

if __name__=='__main__':generate(Path(sys.argv[1]).resolve())
