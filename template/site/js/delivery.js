/* One model powers the delivery view and both exports. No network required. */
(function (root) {
  'use strict';
  function stable(value) {
    if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(function (k) { return JSON.stringify(k) + ':' + stable(value[k]); }).join(',') + '}';
    return JSON.stringify(value);
  }
  function model(data, vid) {
    var version = data.project.versions.find(function (v) { return v.id === vid; });
    var current = data.versions[vid], baseId = version.handoff_parent ? version.base : version.current_handoff || version.base;
    var base = data.versions[baseId], before = {}, after = {};
    ((base && base.spec && base.spec.requirements) || []).forEach(function (r) { before[r.id] = r; });
    ((current.spec && current.spec.requirements) || []).forEach(function (r) { after[r.id] = r; });
    var oldHashes = base && base.content_hashes || {}, newHashes = current.content_hashes || {};
    var files = base ? Array.from(new Set(Object.keys(oldHashes).concat(Object.keys(newHashes)))).filter(function (f) { return oldHashes[f] !== newHashes[f] && !['spec.json','manifest.json'].includes(f); }) : [];
    var tasks = Array.from(new Set(Object.keys(before).concat(Object.keys(after)))).sort().map(function (id) {
      var removed = !after[id], r = after[id] || before[id], bundle = removed ? base : current, linkVersion = removed ? baseId : vid;
      var interactions = ((bundle.spec || {}).interactions || []).filter(function (i) { return i.requirement_ids.includes(id); });
      var oldInteractions = ((base && base.spec || {}).interactions || []).filter(function (i) { return i.requirement_ids.includes(id); });
      var mappings = ((bundle.spec || {}).pages || []).filter(function (p) { return p.requirement_ids.includes(id); });
      var oldMappings = ((base && base.spec || {}).pages || []).filter(function (p) { return p.requirement_ids.includes(id); });
      var links = [];
      bundle.manifest.modules.forEach(function (m) { m.pages.forEach(function (p) {
        if (p.type === 'spec' || mappings.some(function (page) { return page.id === p.id; })) links.push({title:p.title, type:p.type, route:'#/v/' + [linkVersion,m.id,p.id].map(encodeURIComponent).join('/')});
      }); });
      var pending = r.status !== 'confirmed' || (r.rule_details || []).some(function (rule) { return rule.status !== 'confirmed'; });
      var delivery = r.delivery || {};
      return {id:id, title:r.title, change:removed ? 'removed' : !before[id] ? 'added' : stable(before[id]) !== stable(r) ? 'modified' : stable(interactions) !== stable(oldInteractions) || stable(mappings) !== stable(oldMappings) || files.length ? 'review' : 'unchanged',
        confirmation:pending ? 'pending' : 'confirmed', blocking:!!r.blocking && pending,
        roles:Array.isArray(delivery.roles) ? delivery.roles : [], dependencies:Array.isArray(delivery.dependencies) ? delivery.dependencies : [],
        source:r.source || 'unknown', description:r.description || '', rules:r.rules || {}, rule_details:r.rule_details || [], acceptance:r.acceptance || [], interactions:interactions, links:links};
    });
    var owner = version.handoff_parent ? data.project.versions.find(function (v) { return v.id === version.handoff_parent; }) : version;
    return {project:data.project.name, version:vid, baseline:baseId || null, basis:owner.current_handoff || null,
      draft:version.status === 'planning', tasks:tasks, total_tasks:tasks.length, changed_files:files,
      notice:'确认状态仅来自需求记录，不代表技术评审或实际测试通过。共享资源或正文变化保守标为需复核。未分工、未登记依赖不等于无工作或无依赖。'};
  }
  function filter(pack, query, change, status, role) {
    return pack.tasks.filter(function (t) { return (!query || (t.id+' '+t.title+' '+t.description).toLowerCase().includes(query.toLowerCase())) && (change !== 'changed' || t.change !== 'unchanged') && (status !== 'pending' || t.confirmation === 'pending') && (status !== 'blocking' || t.blocking) && (role === 'all' || !t.roles.length || t.roles.includes(role)); });
  }
  function markdown(pack, tasks, baseUrl) {
    var lines = ['# '+pack.project+' · '+pack.version+' 开发任务包', '比较基线：'+(pack.baseline || '首版'), '开发依据：'+(pack.basis || '尚无交接快照'), pack.notice];
    lines.push('导出范围：当前选择 '+tasks.length+' / '+pack.tasks.length+' 条需求；未包含的需求不代表不在项目范围内。');
    tasks.forEach(function (t) {
      lines.push('## '+t.id+' · '+t.title, '变化：'+t.change+'；确认：'+t.confirmation+(t.blocking?'；阻塞开发':''), t.description,
        '来源：'+t.source, '分工：'+(t.roles.join('、') || '待分工'), '依赖：'+(t.dependencies.join('；') || '未登记，需评审'));
      Object.keys(t.rules).forEach(function (k) { lines.push('- '+k+'：'+t.rules[k]); });
      t.rule_details.forEach(function (r) { lines.push('- '+r.id+' ['+r.status+'] '+r.statement); (r.examples || []).forEach(function (e) { lines.push('  - '+e.input+' → '+e.expected); }); });
      t.interactions.forEach(function (i) { lines.push('- 控件 '+i.id+' '+i.selector+'：'+i.action+' → '+(i.target || '本页')+'；'+i.description, '  - 属性：'+JSON.stringify(i.properties || {})); });
      t.acceptance.forEach(function (a) { lines.push('- '+a.id+'：Given '+a.given+'；When '+a.when+'；Then '+a.then); });
      t.links.forEach(function (l) { lines.push('- ['+l.title+']('+baseUrl+l.route+')'); });
    });
    lines.push('## 相关文件变化', pack.changed_files.join('\n') || '无记录');
    return lines.join('\n\n');
  }
  function render(container, data, vid, esc) {
    var pack = model(data, vid);
    container.innerHTML = '<div class="doc"><h1>开发交接</h1><p>'+esc(vid+' · '+(pack.draft?'工作草稿':'交接/冻结物料')+' · 比较基线：'+(pack.baseline || '首版'))+'</p><p>'+esc('当前开发依据：'+(pack.basis || '尚无交接快照'))+'</p><p>'+esc(pack.notice)+'</p><div class="delivery-filters"><label>搜索 <input id="delivery-query" type="search"></label><label>范围 <select id="delivery-change"><option value="changed">仅本次变化</option><option value="all">全部需求</option></select></label><label>状态 <select id="delivery-status"><option value="all">全部状态</option><option value="pending">待确认</option><option value="blocking">阻塞开发</option></select></label><label>关注方向 <select id="delivery-role"><option value="all">全部</option><option value="frontend">前端</option><option value="backend">后端</option><option value="qa">测试</option></select></label><button id="delivery-md">导出 Markdown</button><button id="delivery-json">导出 JSON</button></div><p id="delivery-count" role="status"></p><div id="delivery-tasks"></div></div>';
    var q = function (id) { return container.querySelector('#delivery-'+id); };
    var names = {added:'新增',modified:'修改',removed:'移除',review:'关联变化待复核',unchanged:'未变化'};
    function visible() { return filter(pack,q('query').value,q('change').value,q('status').value,q('role').value); }
    function draw() {
      var tasks=visible(); q('count').textContent='显示 '+tasks.length+' / '+pack.tasks.length+' 条需求；导出当前筛选结果';
      q('tasks').innerHTML=tasks.map(function (t) { return '<article class="project-card"><h2>'+esc(t.id+' · '+t.title)+'</h2><p>'+esc(names[t.change]+' · '+(t.confirmation==='pending'?'待确认':'规则已确认（未做技术就绪判定）')+(t.blocking?' · 阻塞开发':''))+'</p><p>'+esc(t.description)+'</p><p>'+esc('分工：'+(t.roles.join('、') || '待分工')+'；依赖：'+(t.dependencies.join('；') || '未登记，需评审'))+'</p><p>'+t.links.map(function (l) { return '<a href="'+esc(l.route)+'">'+esc(l.title)+'</a>'; }).join(' · ')+'</p><details><summary>规则、控件及验收</summary><pre>'+esc(markdown(pack,[t],location.href.split('#')[0]))+'</pre></details></article>'; }).join('') || '<p>当前筛选无匹配需求。</p>';
    }
    ['query','change','status','role'].forEach(function (id) { q(id).addEventListener('input',draw); });
    ['md','json'].forEach(function (format) { q(format).onclick=function () { var tasks=visible(), exported=Object.assign({},pack,{tasks:tasks, filtered:true, site_url:location.href.split('#')[0]}); var body=format==='md'?markdown(pack,tasks,exported.site_url):JSON.stringify(exported,null,2); var url=URL.createObjectURL(new Blob([body],{type:format==='md'?'text/markdown;charset=utf-8':'application/json'})); var a=document.createElement('a'); a.href=url; a.download=vid+'-tasks.'+(format==='md'?'md':'json'); a.click(); setTimeout(function(){URL.revokeObjectURL(url);},1000); }; });
    draw();
  }
  var api={model:model,filter:filter,markdown:markdown,render:render};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else root.PSDelivery=api;
})(typeof window !== 'undefined'?window:globalThis);
