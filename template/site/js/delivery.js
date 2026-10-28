/* One model powers the delivery view and both exports. No network required. */
(function (root) {
  'use strict';
  var ROLE_LABELS={frontend:'前端',backend:'后端',qa:'测试',design:'设计'};
  function stable(value) {
    if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(function (k) { return JSON.stringify(k) + ':' + stable(value[k]); }).join(',') + '}';
    return JSON.stringify(value);
  }
  function sharedRules(requirement,spec){
    var rules={};((spec || {}).requirements || []).forEach(function(req){(req.rule_details || []).forEach(function(rule){rules[rule.id]=rule;});});
    return ((requirement || {}).shared_rule_ids || []).map(function(id){return rules[id] || {id:id};});
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
        if (p.type === 'spec' || mappings.some(function (page) { return page.id === p.id; })) links.push({title:p.title, type:p.type, route:p.type==='spec' ? ((bundle.prd_sections || []).some(function(s){return s.id==='functions';})?'#/v/'+encodeURIComponent(linkVersion)+'/_prd/functions':'#/v/'+[linkVersion,m.id,p.id].map(encodeURIComponent).join('/'))+'?requirement='+encodeURIComponent(id) : '#/v/' + [linkVersion,m.id,p.id].map(encodeURIComponent).join('/')});
      }); });
      var openChecks=(r.review && r.review.checks || []).filter(function(c){return c.status==='pending';});
      var sharedPending=(r.shared_rule_ids || []).some(function(id){return ((bundle.spec || {}).requirements || []).some(function(req){return (req.rule_details || []).some(function(rule){return rule.id===id && rule.status!=='confirmed';});});});
      var pending = sharedPending || !!openChecks.length || r.status !== 'confirmed' || (r.rule_details || []).some(function (rule) { return rule.status !== 'confirmed'; });
      var delivery = r.delivery || {};
      return {id:id, title:r.title, change:removed ? 'removed' : !before[id] ? 'added' : stable(before[id]) !== stable(r) || stable(sharedRules(before[id],base && base.spec)) !== stable(sharedRules(r,bundle.spec)) ? 'modified' : stable(interactions) !== stable(oldInteractions) || stable(mappings) !== stable(oldMappings) || files.length ? 'review' : 'unchanged',
        confirmation:pending ? 'pending' : 'confirmed', blocking:(!!r.blocking || openChecks.some(function(c){return c.blocking || c.impact!=='editorial';})) && pending,
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
    var lines = ['# '+pack.project+' · '+pack.version+' 交付清单', '比较基线：'+(pack.baseline || '首版'), '开发依据：'+(pack.basis || '尚无交接快照'), pack.notice];
    lines.push('导出范围：当前选择 '+tasks.length+' / '+pack.tasks.length+' 条需求；未包含的需求不代表不在项目范围内。');
    var cell=function(v){return String(v).replace(/\|/g,'\\|').replace(/[\r\n]+/g,' ');};
    lines.push('## 需求清单', '| 需求名称 | 编号 | 变更 | 确认状态 |\n| --- | --- | --- | --- |\n'+tasks.map(function(t){return '| '+[t.title,t.id,({added:'新增',modified:'修改',removed:'移除',review:'需复核',unchanged:'未变化'}[t.change] || t.change),t.confirmation==='pending'?'待确认':'已确认'].map(cell).join(' | ')+' |';}).join('\n'));
    tasks.forEach(function (t) {
      lines.push('## '+t.title, '追踪编号：'+t.id, '变化：'+({added:'新增',modified:'修改',removed:'移除',review:'关联变化待复核',unchanged:'未变化'}[t.change] || t.change)+'；确认：'+(t.confirmation==='confirmed'?'已确认':'待确认')+(t.blocking?'；阻塞开发':''), t.description,
        '来源：'+({origin:'原始需求','ai-inferred':'AI 推断'}[t.source] || t.source), '分工：'+(t.roles.map(function(r){return ROLE_LABELS[r] || r;}).join('、') || '待分工'), '依赖：'+(t.dependencies.join('；') || '未登记，需评审'));
      lines.push('验收引用：'+(t.acceptance.map(function(a){return a.id;}).join('、') || '尚未登记')+'；完整条件见下方功能原文。');
      lines.push('### 相关物料');
      t.links.forEach(function (l) { lines.push('- ['+l.title+']('+baseUrl+l.route+')'); });
    });
    lines.push('## 相关文件变化', pack.changed_files.join('\n') || '无记录');
    return lines.join('\n\n');
  }
  function render(container, data, vid, esc) {
    var pack = model(data, vid), selected = null;
    var names = {added:'新增',modified:'修改',removed:'移除',review:'关联变化待复核',unchanged:'未变化'};
    var tldr='<p>按变更、确认状态和分工检查交付准备情况；功能规则与验收条件统一查阅 PRD。</p>';
    var roles = ROLE_LABELS;
    var roleText = function(t){return t.roles.map(function(r){return roles[r] || r;}).join('、') || '待分工';};
    var status = function(t){return (t.confirmation==='pending'?'待确认':'已确认')+(t.blocking?' · 阻塞开发':'');};
    var para = function(s){return '<p>'+esc(s || '')+'</p>';};
    container.innerHTML = '<div class="scope-reader"><h1>交付清单</h1>' + tldr + '<dl class="scope-summary"><div><dt>当前版本</dt><dd>'+esc(vid+' · '+(pack.draft?'工作草稿':'交接/冻结物料'))+'</dd></div><div><dt>比较基线</dt><dd>'+esc(pack.baseline || '首版')+'</dd></div><div><dt>当前开发依据</dt><dd>'+esc(pack.basis || '尚无交接快照')+'</dd></div></dl><details class="scope-notice"><summary>交接说明与限制</summary>'+para(pack.notice)+'</details><h2>需求清单</h2><div class="delivery-filters"><label>搜索 <input id="delivery-query" type="search"></label><label>范围 <select id="delivery-change"><option value="changed">仅本次变化</option><option value="all">全部需求</option></select></label><label>状态 <select id="delivery-status"><option value="all">全部状态</option><option value="pending">待确认</option><option value="blocking">阻塞开发</option></select></label><label>关注方向 <select id="delivery-role"><option value="all">全部</option><option value="frontend">前端</option><option value="backend">后端</option><option value="qa">测试</option><option value="design">设计</option></select></label><button id="delivery-md">导出交接清单（Markdown）</button><button id="delivery-json">导出结构化数据（JSON）</button></div><p id="delivery-count" role="status"></p><div class="scope-table-wrap"><table class="scope-table"><caption>当前筛选的需求范围；确认不代表测试通过</caption><thead><tr><th scope="col">需求名称 / 编号</th><th scope="col">变更</th><th scope="col">确认状态</th><th scope="col">关注方向</th><th scope="col">依赖</th><th scope="col">详情</th></tr></thead><tbody id="delivery-rows"></tbody></table></div><h2>交付资料</h2><div id="delivery-tasks"></div></div>';
    var q = function(id){return container.querySelector('#delivery-'+id);};
    function visible(){return filter(pack,q('query').value,q('change').value,q('status').value,q('role').value);}
    function detail(t) {
      if(!t){q('tasks').innerHTML='<p>当前筛选无匹配需求。</p>';return;}
      var html='<article class="scope-detail" tabindex="-1"><header><h3>'+esc(t.title)+'</h3>'+para(t.id+' · '+names[t.change]+' · '+status(t))+'</header><section><h4>分工与依赖</h4>'+para('关注方向：'+roleText(t))+para('依赖：'+(t.dependencies.join('；') || '未登记，需评审'))+'</section><section><h4>功能与原型</h4><p>'+t.links.map(function(l){return '<a href="'+esc(l.route)+'">'+esc(l.type==='spec'?'查看功能规则':l.title)+'</a>';}).join(' · ')+'</p>';
      var source=t.links.find(function(l){return l.type==='spec';});
      html+='<p>'+(source?'<a href="'+esc(source.route+'&section=acceptance')+'">查看验收标准（'+t.acceptance.length+'）</a>':'验收入口尚未登记')+'</p></section></article>';
      q('tasks').innerHTML=html;
    }
    function draw(){
      var tasks=visible();
      if(!tasks.some(function(t){return t.id===selected;}))selected=tasks.length?tasks[0].id:null;
      q('count').textContent='显示 '+tasks.length+' / '+pack.tasks.length+' 条需求；表格与导出使用同一筛选范围。';
      q('rows').innerHTML=tasks.map(function(t){return '<tr'+(t.id===selected?' class="is-selected"':'')+'><th scope="row">'+esc(t.title)+'<small>'+esc(t.id)+'</small></th><td>'+esc(names[t.change])+'</td><td>'+esc(status(t))+'</td><td>'+esc(roleText(t))+'</td><td>'+esc(t.dependencies.join('；') || '未登记，需评审')+'</td><td><button data-task="'+esc(t.id)+'" aria-pressed="'+(t.id===selected)+'">查看详情</button></td></tr>';}).join('') || '<tr><td colspan="6">当前筛选无匹配需求。</td></tr>';
      detail(tasks.find(function(t){return t.id===selected;}));
    }
    q('rows').onclick=function(e){var button=e.target.closest('[data-task]');if(!button)return;selected=button.dataset.task;draw();var article=q('tasks').querySelector('article');if(article){article.focus({preventScroll:true});article.scrollIntoView({block:'start'});}};
    ['query','change','status','role'].forEach(function(id){q(id).addEventListener('input',draw);});
    ['md','json'].forEach(function(format){q(format).onclick=function(){var tasks=visible(), exported=Object.assign({},pack,{tasks:tasks,filtered:true,site_url:location.href.split('#')[0]});var body=format==='md'?markdown(pack,tasks,exported.site_url):JSON.stringify(exported,null,2);var url=URL.createObjectURL(new Blob([body],{type:format==='md'?'text/markdown;charset=utf-8':'application/json'}));var a=document.createElement('a');a.href=url;a.download=vid+'-handoff.'+(format==='md'?'md':'json');a.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);};});
    draw();
  }
  var api={model:model,filter:filter,markdown:markdown,render:render};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else root.PSDelivery=api;
})(typeof window !== 'undefined'?window:globalThis);
