"""Standard PRD registry: reference source documents, never copy their prose."""
import json
import pathlib
import re
import diagramlib

CHAPTERS = [
    ('scope', '版本说明和范围', 'overview/index.md', '问题、目标用户、目标、包含/排除范围、版本变化与待决策。'),
    ('users', '用户与业务流程', 'prd/users.md', '角色、使用场景、主流程、异常流程、权限边界与跨页规则。'),
    ('functions', '功能需求与规则', None, ''),
    ('tracking', '数据与埋点', 'prd/tracking.md', '数据口径、事件名、触发时机、属性及类型、去重、用户授权、验证与负责人。'),
    ('nonfunctional', '非功能需求', 'prd/nonfunctional.md', '逐项检查性能、安全、兼容性、可用性、无障碍、隐私与合规；填写场景、可验证目标、验证方式与负责人，未知阈值待确认。'),
    ('acceptance', '验收与上线条件', 'prd/acceptance.md', '验收范围、发布前置条件、灰度/放量、暂停与回滚、监控和负责人；功能验收自动引用 spec。'),
    ('milestones', '里程碑与计划', 'prd/milestones.md', '阶段、交付物、负责人、依赖、计划日期与退出条件；未知日期不编造。'),
    ('risks', '风险与待决策', 'prd/risks.md', '风险/未决事项、影响、应对措施、责任人、决策期限和处理状态。'),
    ('appendix', '附录与参考资料', 'prd/appendix.md', '术语、参考依据、补充说明；文件附件通过本机编辑服务上传并持久保存。')
]


def within(root, relative):
    path = (root / relative).resolve()
    if pathlib.Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError('PRD 来源路径越界')
    return path


def initialize(content):
    registry = content / 'prd.json'
    if registry.exists():
        return
    entries = []
    for cid, title, file, hint in CHAPTERS:
        entries.append({'id': cid, 'title': title, 'sources': [file] if file else []})
        if file:
            path = within(content, file)
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<!-- prd-status: pending -->\n<!-- prd-reason: 尚未提供本章资料 -->\n\n<!-- material: DOC-'+cid+' -->\n# '+title+'\n\n待补充：'+hint+'\n', encoding='utf-8')
    registry.write_text(json.dumps({'schema_version': 1, 'sections': entries}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def registry(content):
    file = content / 'prd.json'
    if not file.exists(): return None
    value = json.loads(file.read_text(encoding='utf-8'))
    sections = value.get('sections')
    if value.get('schema_version') != 1 or not isinstance(sections, list) or [s.get('id') for s in sections] != [x[0] for x in CHAPTERS]:
        raise ValueError('prd.json 需要九个标准章节（固定 ID 和顺序）')
    for section in sections:
        if not isinstance(section.get('title'), str) or not section['title'].strip(): raise ValueError('PRD 章节缺少标题')
        sources = section.get('sources')
        if not isinstance(sources, list) or any(not isinstance(f, str) or not f.endswith('.md') for f in sources): raise ValueError('PRD 来源必须是 Markdown 路径列表')
        if section['id'] != 'functions' and not sources: raise ValueError('非功能正文章节必须登记来源')
        if section['id'] == 'functions' and sources: raise ValueError('功能章节只能引用 spec，不得登记第二份正文')
        for source in sources:
            if not within(content, source).is_file(): raise ValueError('PRD 来源不存在：'+source)
    return value


def document(text):
    status = re.search(r'^<!-- prd-status: (provided|pending|not_applicable) -->\s*$', text, re.M)
    reason = re.search(r'^<!-- prd-reason: ([^\n]*) -->\s*$', text, re.M)
    state = status.group(1) if status else 'pending'
    explanation = reason.group(1).strip() if reason else '未声明章节状态，需复核'
    body = re.sub(r'^<!-- prd-(?:status|reason):[^\n]*-->\s*\n?', '', text, flags=re.M).strip()
    body = re.sub(r'^<!-- material: [A-Za-z0-9_.-]+ -->\s*$', '', body, flags=re.M).strip()
    if state == 'not_applicable' and (not reason or not explanation): raise ValueError('不适用章节必须填写原因')
    if state == 'provided' and not re.sub(r'^#+[^\n]*', '', body, flags=re.M).strip(): raise ValueError('已提供章节不能只有标题或空正文')
    if '<!-- prd-status:' in text and not status: raise ValueError('章节状态只能是 provided/pending/not_applicable')
    return {'status': state, 'reason': explanation, 'markdown': body}


def chapter_body(markdown):
    """Sources have document titles; compiled chapters already supply that title."""
    lines=markdown.strip().splitlines()
    if lines and re.match(r'^# ',lines[0]):lines=lines[1:]
    return re.sub(r'^(#+)(?= )',r'#\1','\n'.join(lines).strip(),flags=re.M)


def feature_list(spec, baseline=None):
    """Version overview index. Confirmation metadata is not a functional change."""
    def business(item,source):
        keys=('title','module','description','rules','rule_details','acceptance')
        def clean(value):
            if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in ('source','status','blocking')}
            if isinstance(value,list):return [clean(v) for v in value]
            return value
        value={key:item.get(key) for key in keys}
        value['diagrams']=[d for d in (source or {}).get('diagrams',[]) if d.get('requirement_id')==item['id']]
        return clean(value)
    before={item['id']:item for item in (baseline or {}).get('requirements',[])}
    after={item['id']:item for item in (spec or {}).get('requirements',[])}
    def confirmation(item):
        return 'pending' if item.get('status')!='confirmed' or any(rule.get('status')!='confirmed' for rule in item.get('rule_details',[])) else 'confirmed'
    rows=[]
    for rid,item in after.items():
        change='新增' if rid not in before else '沿用' if business(item,spec)==business(before[rid],baseline) else '修改'
        rows.append(dict(id=rid,module=item.get('module') or '功能需求',title=item['title'],summary=item.get('description',''),change=change,priority=item.get('priority') or '待定',status=confirmation(item)))
    for rid,item in before.items():
        if rid not in after:rows.append(dict(id=rid,module=item.get('module') or '功能需求',title=item['title'],summary=item.get('description',''),change='移除',priority=item.get('priority') or '待定',status=confirmation(item)))
    return rows


def feature_markdown(items):
    def cell(value):return str(value).replace('|','\\|').replace('\n',' ')
    rows=['### 本版功能清单','按模块列出本版功能；类型区分新增、修改、移除和沿用。此处仅列范围摘要，具体规则见功能章节。',
          '| 模块 | 功能 | 变更类型 | 范围摘要 | 优先级 | 确认状态 | 编号 |','| --- | --- | --- | --- | --- | --- | --- |']
    for item in items:
        rows.append('| '+' | '.join(cell(v) for v in (item['module'],item['title'],item['change'],item['summary'],item['priority'],'已确认' if item['status']=='confirmed' else '待确认',item['id']))+' |')
    if not items:rows.append('尚未登记功能，不能据此判断本版没有功能。')
    return '\n\n'.join(rows[:2])+'\n\n'+'\n'.join(rows[2:])


def compile_sections(content, spec, functional_markdown, feature_items=None):
    value = registry(content)
    if not value: return None
    sections = []
    for entry in value['sections']:
        docs = [document(within(content, f).read_text(encoding='utf-8')) for f in entry['sources']]
        status = 'pending' if not docs or any(d['status']=='pending' for d in docs) else 'not_applicable' if all(d['status']=='not_applicable' for d in docs) else 'provided'
        body = '\n\n'.join(chapter_body(d['markdown']) for d in docs)
        if entry['id'] == 'scope':
            overview_index=feature_markdown(feature_items if feature_items is not None else feature_list(spec))
            first_section=re.search(r'^#{1,6} ',body,re.M)
            at=first_section.start() if first_section else len(body)
            body=body[:at].rstrip()+'\n\n'+overview_index+'\n\n'+body[at:]
        if entry['id'] == 'users':
            diagrams=(spec or {}).get('diagrams',[])
            for diagram in diagrams:
                if diagram.get('level')=='module':body+='\n\n'+diagramlib.markdown(diagram,diagrams,3)
        if entry['id'] == 'functions':
            status = 'provided' if (spec or {}).get('requirements') else 'pending'
            if status == 'provided':
                lines=functional_markdown.splitlines()
                if lines and lines[0]=='# 产品需求文档':lines=lines[1:]
                # This is chapter 3 inside a complete PRD: module h3, feature h4, group h5.
                body=re.sub(r'^(#+)(?= )',r'#\1','\n'.join(lines).strip(),flags=re.M)
            else:body='尚未提供功能需求。'
        if entry['id'] == 'acceptance':
            body += '\n\n### 功能验收索引\n\n完整条件在功能章节维护，此处仅引用编号：\n\n'
            for req in (spec or {}).get('requirements', []):
                body += '- '+req['title']+'：'+ '、'.join(ac['id'] for ac in req.get('acceptance', []))+'\n'
        sections.append(dict(entry, status=status, reason='；'.join(d['reason'] for d in docs) if docs else '正文存在不代表需求已确认', markdown=body))
    return sections
