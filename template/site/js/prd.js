/* Business-first reading view; stable identifiers remain available for exact edits. */
window.PSPRD = {render:function (container, data, vid, page, query, esc) {
  var spec=data.versions[vid].spec, reqs=spec.requirements || [], pages=spec.pages || [], interactions=spec.interactions || [];
  var ruleIndex=Object.create(null), readingSearch='';
  reqs.forEach(function(req){(req.rule_details || []).forEach(function(rule){ruleIndex[rule.id]={rule:rule,requirement:req};});});
  function ruleHref(id,from){
    var target=ruleIndex[id], params=new URLSearchParams({requirement:target.requirement.id,rule:id});
    if(from && ruleIndex[from] && from!==id)params.set('from',from);
    return '#/v/'+encodeURIComponent(vid)+'/_prd/functions?'+params.toString();
  }
  function marked(text){
    text=String(text || '');if(!readingSearch)return esc(text);
    var lower=text.toLowerCase(),start=0,at,result='';
    while((at=lower.indexOf(readingSearch,start))>=0){result+=esc(text.slice(start,at))+'<mark>'+esc(text.slice(at,at+readingSearch.length))+'</mark>';start=at+readingSearch.length;}
    return result+esc(text.slice(start));
  }
  function ruleSearchText(rule){return JSON.stringify([rule.id,rule.title,rule.statement,rule.clauses,rule.table,rule.examples]).toLowerCase();}
  function requirementSearchText(req){
    return JSON.stringify([req.id,req.title,req.module,req.description,req.rules,req.acceptance,(req.review || {}).checks,(req.rule_details || []).map(ruleSearchText),(req.shared_rule_ids || []).map(function(id){return [id,((ruleIndex[id] || {}).rule || {}).title];})]).toLowerCase();
  }
  function ruleLink(id,from,sourceReq){
    var target=ruleIndex[id];if(!target)return esc(id);
    return '<a class="prd-rule-link" href="'+esc(ruleHref(id,from)+(sourceReq?'&from_requirement='+encodeURIComponent(sourceReq):''))+'">'+marked(target.rule.title || id)+(target.rule.title?' <small>'+marked(id)+'</small>':'')+'</a>'+(target.rule.status==='pending'?' <span class="sr-pending">待确认</span>':'');
  }
  function readText(text,from){
    text=String(text || '');var re=/\bRULE-[A-Za-z0-9_-]+\b/g,result='',start=0,match;
    while((match=re.exec(text))){result+=marked(text.slice(start,match.index));result+=ruleIndex[match[0]]?'<a class="prd-rule-link" href="'+esc(ruleHref(match[0],from))+'" title="'+esc(ruleIndex[match[0]].rule.title || match[0])+'">'+marked(ruleIndex[match[0]].rule.title || match[0])+'</a>':marked(match[0]);start=re.lastIndex;}
    return result+marked(text.slice(start));
  }
  var acLatest={};
  (data.outcomes || []).forEach(function (record) {
    var payload=record.payload || {};
    if (payload.kind !== 'execution' || record.superseded || payload.version !== vid || !payload.acceptance_id) return;
    if (!acLatest[payload.acceptance_id] || String(record.recorded_at || '') > String(acLatest[payload.acceptance_id].recorded_at || '')) acLatest[payload.acceptance_id]=record;
  });
  function acBadge(id) {
    var record=acLatest[id]; if (!record) return '';
    var names={passed:'通过',failed:'失败',blocked:'阻塞',not_run:'未执行'};
    var scope=record.payload.scope==='prototype'?'原型验证':'产品验收';
    var stale=record.stale?' · 基线已变化，需复核':'';
    return '<p class="prd-ac-badge'+(record.stale?' stale':'')+'">验证记录：'+esc(names[record.payload.result] || record.payload.result)+'（'+scope+'）· '+esc(String(record.payload.observed_at || '').slice(0,10))+stale+'；取自台账，有记录不代表当前仍通过</p>';
  }
  var category={entry:'入口与前提',fields:'数据与字段',display:'内容与展示',behavior:'操作与结果',validation:'输入校验',permission:'权限规则',state:'状态规则',data:'数据口径',feedback:'操作反馈',recovery:'异常与恢复',content:'固定内容'};
  function ruleTable(rule){var t=rule.table;if(!t)return '';return '<div class="prd-boundary-scroll" role="region" aria-label="规则明细表，窄屏可横向滚动" tabindex="0"><table><thead><tr>'+t.columns.map(function(c){return '<th scope="col">'+marked(c)+'</th>';}).join('')+'</tr></thead><tbody>'+t.rows.map(function(row){return '<tr>'+row.map(function(v){return '<td>'+readText(v,rule.id)+'</td>';}).join('')+'</tr>';}).join('')+'</tbody></table></div>';}
  function ruleItem(rule,index,requirement){
    var title=rule.title || '规则 '+(index+1);
    var clauses=(rule.clauses || []).map(function(item){return '<div><dt>'+marked(item.label)+'</dt><dd>'+readText(item.text,rule.id)+'</dd></div>';}).join('');
    var examples=(rule.examples || []).map(function(e){return '<div><dt>'+readText(e.input,rule.id)+'</dt><dd>'+readText(e.expected,rule.id)+'</dd></div>';}).join('');
    var acceptance=(rule.acceptance_ids || []).map(function(id){var ac=(requirement.acceptance || []).find(function(a){return a.id===id;});return '<a data-acceptance-link="'+esc(id)+'" title="'+esc(id)+'" href="#/v/'+encodeURIComponent(vid)+'/_prd/functions?requirement='+encodeURIComponent(requirement.id)+'&amp;section=acceptance&amp;acceptance='+encodeURIComponent(id)+'">'+esc(ac?(ac.title || ac.given+'；'+ac.when):id)+'</a>';}).join(' · ');
    return '<article class="prd-rule-item" tabindex="-1" data-rule-id="'+esc(rule.id)+'"><div class="prd-rule-heading"><h5>'+marked(title)+'</h5><a class="prd-rule-permalink" href="'+esc(ruleHref(rule.id))+'" aria-label="'+esc('定位规则：'+title+'（'+rule.id+'）')+'">'+marked(rule.id)+'</a>'+(rule.status==='pending'?'<span class="sr-pending">待确认</span>':'')+'</div><p class="prd-rule-summary">'+readText(rule.statement,rule.id)+'</p>'+(clauses?'<dl class="prd-rule-clauses">'+clauses+'</dl>':'')+ruleTable(rule)+((rule.related_rule_ids || []).length?'<p class="prd-related-rules">关联规则：'+rule.related_rule_ids.map(function(id){return ruleLink(id,rule.id);}).join(' · ')+'</p>':'')+(examples?'<div class="prd-rule-examples"><h6>说明示例</h6><dl>'+examples+'</dl></div>':'')+'<details class="prd-rule-evidence"><summary>依据与验收</summary><p>'+esc(rule.id+' · '+meta(rule))+'</p>'+(acceptance?'<p>关联验收：'+acceptance+'</p>':'')+'</details></article>';
  }
  function p(text) { return '<p>'+readText(text)+'</p>'; }
  function meta(item) { return (item.source==='ai-inferred'?'AI 推断':'原始需求')+' · '+(item.status==='confirmed'?'已确认':'待确认')+(((item.rule_details || []).some(function(r){return r.status!=='confirmed';}) || (item.shared_rule_ids || []).some(function(id){return ruleIndex[id] && ruleIndex[id].rule.status!=='confirmed';})?' · 含待确认规则':'')); }
  container.className='content';
  container.innerHTML='<div class="prd-reader"><header class="prd-reader-header"><div class="prd-reader-heading"><div><h1>功能需求与规则</h1><p>按模块查看功能，按分类阅读规则。</p></div><a class="prd-index-link" href="#/v/'+encodeURIComponent(vid)+'/_prd/scope">功能清单与范围 ↗</a></div><div class="prd-tools"><label>页面 <select id="prd-page"><option value="">全部页面</option>'+pages.map(function(x){return '<option value="'+esc(x.id)+'">'+esc(x.title)+'</option>';}).join('')+'</select></label><label>搜索标题、正文或编号 <input id="prd-search" type="search"></label><button id="prd-export">导出完整 PRD（Markdown）</button></div><p id="prd-count" role="status"></p></header><div class="prd-layout"><nav id="prd-toc" aria-label="需求目录"></nav><div id="prd-sections"></div></div><dialog id="prd-edit-context"><h2>交给 Agent 精确修改</h2><p>复制下面的定位信息并补充修改意图；不会自动提交，也不会重新生成项目。</p><textarea rows="7" aria-label="Agent 修改上下文" readonly></textarea><button>关闭</button></dialog></div>';
  function setActive(id){container.querySelectorAll('#prd-toc button').forEach(function(b){b.classList.toggle('on', b.dataset.jump===id);});}
  var spyBound=null;
  function watchSpy(list){
    if(spyBound){spyBound.el.removeEventListener('scroll',spyBound.fn);window.removeEventListener('scroll',spyBound.fn);}
    var scroller=container.closest('.content')||null;
    var fn=function(){
      var best=null,bestTop=-Infinity;
      list.forEach(function(r){var el=document.getElementById('prd-'+r.id);if(!el)return;var top=el.getBoundingClientRect().top;if(top<=150&&top>bestTop){bestTop=top;best=r.id;}});
      setActive(best||(list[0]||{}).id);
    };
    if(scroller)scroller.addEventListener('scroll',fn,{passive:true});
    window.addEventListener('scroll',fn,{passive:true});
    spyBound={el:scroller,fn:fn};
    fn();
  }
  function parentDiagramLink(d) {
    var parent=(spec.diagrams || []).find(function(item){return item.id===d.parent_id;});
    var path=parent && parent.level==='detail'?'functions?requirement='+encodeURIComponent(parent.requirement_id)+'&amp;diagram=':'users?diagram=';
    return '#/v/'+encodeURIComponent(vid)+'/_prd/'+path+encodeURIComponent(d.parent_id);
  }
  function caseView(c) {
    var view=c.presentation || {};
    if(view.mode!=='prototype')return '';
    return (view.targets || []).map(function(t){
      var pg=pages.find(function(p){return p.id===t.page;}), state=pg && (pg.states || []).find(function(s){return s.id===t.state;});
      var mod=(data.versions[vid].manifest.modules || []).find(function(m){return (m.pages || []).some(function(p){return p.id===t.page && p.type==='prototype';});});
      var label=(pg?pg.title:t.page)+' · '+(state?state.title:t.state);
      if(!mod)return esc(label);
      var annotation=interactions.find(function(i){return i.page===t.page && i.selector===t.selector && (i.rule_ids || []).some(function(id){return (c.rule_ids || []).includes(id);}) && (!(i.state_ids || []).length || i.state_ids.includes(t.state));});
      return '<a href="#/v/'+encodeURIComponent(vid)+'/'+encodeURIComponent(mod.id)+'/'+encodeURIComponent(t.page)+'?state='+encodeURIComponent(t.state)+(annotation?'&amp;rule='+encodeURIComponent(annotation.id):'')+'">'+esc(label)+'</a>';
    }).join('<br>');
  }
  function draw() {
    var pageId=container.querySelector('#prd-page').value, search=container.querySelector('#prd-search').value.trim().toLowerCase();
    readingSearch=search;
    var exactRule=Object.keys(ruleIndex).find(function(id){return id.toLowerCase()===search;});
    var exact=reqs.find(function(r){return r.id.toLowerCase()===search;});
    var selected=reqs.filter(function(r){return (!pageId || pages.some(function(pg){return pg.id===pageId && pg.requirement_ids.includes(r.id);})) && (!search || (exactRule?r.id===ruleIndex[exactRule].requirement.id:exact?r.id===exact.id:requirementSearchText(r).includes(search) || interactions.some(function(i){return i.requirement_ids.includes(r.id) && JSON.stringify(i).toLowerCase().includes(search);})));});
    container.querySelector('#prd-count').textContent='显示 '+selected.length+' / '+reqs.length+' 条需求；导出始终包含完整文档。';
    var modules=[]; selected.forEach(function(r){var name=r.module || '功能需求';if(!modules.includes(name))modules.push(name);});
    selected=modules.flatMap(function(name){return selected.filter(function(r){return (r.module || '功能需求')===name;});});
    container.querySelector('#prd-toc').innerHTML=modules.map(function(name){return '<h3>'+esc(name)+'</h3>'+selected.filter(function(r){return (r.module || '功能需求')===name;}).map(function(r){return '<button data-jump="'+esc(r.id)+'">'+marked(r.title)+'</button>';}).join('');}).join('');
    var lastModule=null;
    container.querySelector('#prd-sections').innerHTML=selected.map(function(r){
      var module=r.module || '功能需求';var groupTitle=module!==lastModule?'<h2 class="prd-module">'+esc(module)+'</h2>':'';lastModule=module;
      var blocked=r.blocking || (r.review && r.review.checks || []).some(function(c){return c.status==='pending' && (c.blocking || c.impact!=='editorial');});
      var html=groupTitle+'<article class="prd-requirement" id="prd-'+esc(r.id)+'"><header class="prd-feature-header"><div class="prd-feature-heading"><h3 class="prd-feature-title">'+marked(r.title)+'</h3><p class="prd-meta">'+esc(r.id+' · '+meta(r))+'</p></div><button data-edit="'+esc(r.id)+'">交给 Agent 修改此需求</button></header>'+(blocked?'<p class="prd-blocking">存在影响实现或验收的待明确事项</p>':'')+'<div class="prd-feature-description">'+p(r.description)+'</div>';
      var questions=(r.review && r.review.checks || []).filter(function(c){return c.status==='pending';});
      if(questions.length)html+='<section class="prd-rule prd-open-questions"><h4>待明确的实现口径</h4><ul>'+questions.map(function(c){return '<li>'+esc(c.question)+'<p class="prd-meta">'+esc(c.blocking || c.impact!=='editorial'?'影响实现/验收，需先明确':'仅文案校对，不改变实现/验收')+'</p></li>';}).join('')+'</ul></section>';
      if((r.shared_rule_ids || []).length)html+='<aside class="prd-shared-rules" aria-label="适用的共用规则"><strong>适用的共用规则</strong><p>'+r.shared_rule_ids.map(function(id){var owner=ruleIndex[id];return ruleLink(id,null,r.id)+' <span class="prd-rule-owner">'+esc(owner?owner.requirement.title:'')+'</span>';}).join(' · ')+'</p></aside>';
      var ruleKeys=Object.keys(r.rules || {});
      if(ruleKeys.length){html+='<h3>业务规则</h3>';ruleKeys.forEach(function(k){html+='<section class="prd-rule"><h4>'+esc(k)+'</h4>'+p(r.rules[k])+'</section>';});}
      var groups={};(r.rule_details || []).forEach(function(rule){var key=rule.category || '业务规则';(groups[key] || (groups[key]=[])).push(rule);});
      Object.keys(groups).sort(function(a,b){var keys=Object.keys(category);return (keys.includes(a)?keys.indexOf(a):keys.length)-(keys.includes(b)?keys.indexOf(b):keys.length);}).forEach(function(key){html+='<section class="prd-rule prd-rule-group"><h4>'+esc(category[key] || key)+'</h4><div class="prd-rule-items">'+groups[key].map(function(rule,index){return ruleItem(rule,index,r);}).join('')+'</div></section>';});
      (spec.diagrams || []).filter(function(d){return d.level==='detail' && d.requirement_id===r.id;}).forEach(function(d){html+='<section class="prd-diagram" id="diagram-'+esc(d.id)+'">'+(d.parent_id?'<p><a href="'+parentDiagramLink(d)+'">查看上层流程</a></p>':'')+window.PS.mdToHtml((data.versions[vid].diagrams || {})[d.id] || '')+'</section>';});
      if((r.boundary_cases || []).length){
        html+='<details class="prd-fold prd-boundaries"><summary>特殊情况与处理（'+r.boundary_cases.length+'）</summary><div class="prd-boundary-scroll" role="region" aria-label="特殊情况与处理表，窄屏可横向滚动" tabindex="0"><table><thead><tr><th>遇到的情况</th><th>应有的处理</th><th>详细验收</th></tr></thead><tbody>'+r.boundary_cases.map(function(c){
          var ids=c.acceptance_ids || [], ac=(r.acceptance || []).find(function(a){return a.id===ids[0];});
          var independent='input' in c || 'expected' in c;
          var condition=independent?readText(c.input || '未提供具体情况'):(ac?'<div class="prd-case-condition"><span>前提</span>'+readText(ac.given)+'</div><div class="prd-case-condition"><span>操作</span>'+readText(ac.when)+'</div>':'该场景缺少完整验收，请补充。');
          var expected=independent?c.expected:(ac && ac.then);
          var links=ids.map(function(id,index){return '<a aria-label="'+esc('查看验收：'+id)+'" href="#/v/'+encodeURIComponent(vid)+'/_prd/functions?requirement='+encodeURIComponent(r.id)+'&amp;section=acceptance&amp;acceptance='+encodeURIComponent(id)+'">查看验收'+(ids.length>1?' '+(index+1):'')+'</a>';}).join('<br>');
          var evidence='<details class="prd-case-evidence"><summary>定位信息</summary><p>'+esc('用例：'+c.id+' · '+({boundary:'边界',exception:'异常',normal:'正常'}[c.kind] || c.kind))+'</p>'+(ids.length?'<p>'+esc('关联验收：'+ids.join('、'))+'</p>':'')+'</details>';
          return '<tr data-case-id="'+esc(c.id)+'"><td>'+condition+evidence+'</td><td>'+readText(expected || '未提供处理结果，请补充。')+'</td><td>'+links+(caseView(c)?'<div class="prd-case-prototype">'+caseView(c)+'</div>':'')+'</td></tr>';
        }).join('')+'</tbody></table></div></details>';
      }
      html+='<details class="prd-fold prd-ac-fold" id="acceptance-'+esc(r.id)+'"><summary>验收标准（'+(r.acceptance || []).length+'）</summary><ol class="prd-acceptance">';
      (r.acceptance || []).forEach(function(a){html+='<li data-acceptance="'+esc(a.id)+'">'+p('前提：'+a.given)+p('操作：'+a.when)+p('预期：'+a.then)+acBadge(a.id)+'<small>'+esc(a.id)+'</small></li>';});
      html+='</ol></details><details class="prd-fold"><summary>关联原型</summary><p>';
      pages.filter(function(pg){return pg.requirement_ids.includes(r.id);}).forEach(function(pg){
        var mod=data.versions[vid].manifest.modules.find(function(m){return m.pages.some(function(p){return p.id===pg.id && p.type==='prototype';});});
        if(mod)html+='<a href="#/v/'+encodeURIComponent(vid)+'/'+encodeURIComponent(mod.id)+'/'+encodeURIComponent(pg.id)+'">'+esc(pg.title)+'</a> · ';
      });
      html+='</p></details>';
      var configured=(data.versions[vid].control_supplements || []).filter(function(i){return i.requirement_ids.includes(r.id);});
      if(configured.length){html+='<details class="prd-fold"><summary>控件属性补充</summary>';configured.forEach(function(i){html+='<section><h5>'+esc(i.title)+'</h5><p>'+esc(i.page+' · '+i.states)+'</p><dl class="prd-rule-clauses">'+i.items.map(function(item){return '<div><dt>'+esc(item.label)+'</dt><dd>'+esc(item.value)+'</dd></div>';}).join('')+'</dl><details><summary>定位信息</summary>'+p(i.id)+'</details></section>';});html+='</details>';}
      return html+'</article>';
    }).join('') || '<p>没有匹配需求，请调整筛选。编号不存在时不会自动定位到其他需求。</p>';
    var params=new URLSearchParams(query), targetRuleId=params.get('rule');
    var ruleTarget=targetRuleId?Array.from(container.querySelectorAll('[data-rule-id]')).find(function(el){return el.dataset.ruleId===targetRuleId;}):null;
    var sourceId=params.get('from');
    if(sourceId && ruleIndex[sourceId]){
      var back=document.createElement('p');back.className='prd-return-source';
      back.innerHTML='<a href="'+esc(ruleHref(sourceId))+'">← 返回来源规则：'+esc(ruleIndex[sourceId].rule.title || sourceId)+'</a>';
      (ruleTarget || container.querySelector('#prd-sections')).prepend(back);
    }
    if(!sourceId && reqs.some(function(r){return r.id===params.get('from_requirement');})){
      var sourceReq=reqs.find(function(r){return r.id===params.get('from_requirement');}),backReq=document.createElement('p');backReq.className='prd-return-source';
      backReq.innerHTML='<a href="#/v/'+encodeURIComponent(vid)+'/_prd/functions?requirement='+encodeURIComponent(sourceReq.id)+'">← 返回来源功能：'+esc(sourceReq.title)+'</a>';(ruleTarget || container.querySelector('#prd-sections')).prepend(backReq);
    }
    if(targetRuleId && !ruleTarget){var notice=document.createElement('p');notice.className='prd-target-notice';notice.setAttribute('role','status');notice.textContent='当前版本或筛选中未找到规则 '+targetRuleId+'，请核对定位信息。';container.querySelector('#prd-sections').prepend(notice);}
    var hits=[];
    if(search && !exact){
      container.querySelectorAll('.prd-rule-item').forEach(function(el){
        var rule=ruleIndex[el.dataset.ruleId].rule;
        if(ruleSearchText(rule).includes(search)){el.classList.add('prd-search-match');hits.push(el);}
      });
      if(hits.length){var matches=document.createElement('nav');matches.className='prd-search-results';matches.setAttribute('aria-label','命中的规则');matches.innerHTML='<strong>命中 '+hits.length+' 条规则</strong>'+hits.map(function(el){return '<button type="button" data-jump-rule="'+esc(el.dataset.ruleId)+'">'+marked(ruleIndex[el.dataset.ruleId].rule.title || el.dataset.ruleId)+'</button>';}).join('');container.querySelector('#prd-sections').prepend(matches);}
    }
    var caseTarget=params.get('section')==='cases'?container.querySelector('.prd-boundaries'):null;
    if(caseTarget)caseTarget.open=true;
    var targetAcceptance=new URLSearchParams(query).get('acceptance');
    var acceptanceTarget=targetAcceptance?Array.from(container.querySelectorAll('[data-acceptance]')).find(function(el){return el.dataset.acceptance===targetAcceptance;}):null;
    if(acceptanceTarget){acceptanceTarget.closest('details').open=true;requestAnimationFrame(function(){if(acceptanceTarget.isConnected)acceptanceTarget.scrollIntoView({block:'start'});});}
    else if(!targetAcceptance && new URLSearchParams(query).get('section')==='acceptance')container.querySelectorAll('.prd-ac-fold').forEach(function(el){el.open=true;});
    if(ruleTarget)ruleTarget.classList.add('prd-rule-target');
    window.PS.renderDiagrams(container).then(function(){
      var wanted=new URLSearchParams(query).get('diagram');
      var target=wanted?document.getElementById('diagram-'+wanted):acceptanceTarget || ruleTarget || caseTarget || (!targetAcceptance && new URLSearchParams(query).get('section')==='acceptance'?container.querySelector('.prd-ac-fold'):null);
      if(target && container.contains(target)){target.scrollIntoView({block:'start'});if(target===ruleTarget)target.focus({preventScroll:true});}
    });
    watchSpy(selected);
    setActive((selected[0] || {}).id);
  }
  container.querySelector('#prd-page').value=new URLSearchParams(query).get('page') || '';
  container.querySelector('#prd-search').value=new URLSearchParams(query).get('requirement') || ((ruleIndex[new URLSearchParams(query).get('rule')] || {}).requirement || {}).id || '';
  ['prd-page','prd-search'].forEach(function(id){container.querySelector('#'+id).addEventListener('input',function(){query='';draw();});});
  container.onclick=function(event){
    var jump=event.target.closest('[data-jump]'); if(jump){var target=document.getElementById('prd-'+jump.dataset.jump); if(target){target.scrollIntoView({block:'start'});setActive(jump.dataset.jump);}}
    var ruleJump=event.target.closest('[data-jump-rule]');if(ruleJump){var ruleEl=Array.from(container.querySelectorAll('[data-rule-id]')).find(function(el){return el.dataset.ruleId===ruleJump.dataset.jumpRule;});if(ruleEl){ruleEl.scrollIntoView({block:'start'});ruleEl.focus({preventScroll:true});}}
    var edit=event.target.closest('[data-edit]'); if(!edit)return;
    var r=reqs.find(function(x){return x.id===edit.dataset.edit;});
    var dialog=container.querySelector('#prd-edit-context');
    var entry=new URL(location.href);entry.hash='/v/'+encodeURIComponent(vid)+'/_prd/functions?'+new URLSearchParams({requirement:r.id}).toString();
    dialog.querySelector('textarea').value='请在既有项目中增量修改，不重新生成。\n项目：'+data.project.name+'（'+data.project.id+'）\n页面入口：'+entry.href+'\n版本：'+vid+'\n需求：'+r.title+'（'+r.id+'）\n定位键：req:'+r.id+'\n来源：versions/'+vid+'/content/spec.json'+(edit.dataset.control?'\n控件：'+edit.dataset.control:'')+'\n修改要求：【请填写】\n保留其他需求、编号、页面结构及历史；若此版已冻结，请先确认目标规划版本，不自动转到其他版本，也不修改冻结物料。';
    dialog.showModal();dialog.querySelector('textarea').select();
  };
  container.querySelector('#prd-edit-context button').onclick=function(){container.querySelector('#prd-edit-context').close();};
  container.querySelector('#prd-export').onclick=function(){var md=data.versions[vid].full_prd_markdown || data.versions[vid].files[page.id] || '';var url=URL.createObjectURL(new Blob([md],{type:'text/markdown;charset=utf-8'}));var a=document.createElement('a');a.href=url;a.download=data.project.name+'-'+vid+'-产品需求文档.md';a.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);};
  draw();
}};
