/* Business-first reading view; stable identifiers remain available for exact edits. */
window.PSPRD = {render:function (container, data, vid, page, query, esc) {
  var spec=data.versions[vid].spec, reqs=spec.requirements || [], pages=spec.pages || [], interactions=spec.interactions || [];
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
  var category={validation:'输入校验',permission:'权限规则',state:'状态规则',data:'数据口径',feedback:'操作反馈'};
  function p(text) { return '<p>'+esc(text || '')+'</p>'; }
  function meta(item) { return (item.source==='ai-inferred'?'AI 推断':'原始需求')+' · '+(item.status==='confirmed'?'已确认':'待确认')+((item.rule_details || []).some(function(r){return r.status!=='confirmed';})?' · 含待确认规则':''); }
  container.className='content';
  container.innerHTML='<div class="prd-reader"><header><h1>功能需求与规则</h1><p>按业务模块查找功能；规则直接阅读，依据与验收按需展开。</p><div class="prd-tools"><label>页面 <select id="prd-page"><option value="">全部页面</option>'+pages.map(function(x){return '<option value="'+esc(x.id)+'">'+esc(x.title)+'</option>';}).join('')+'</select></label><label>搜索标题、正文或编号 <input id="prd-search" type="search"></label><button id="prd-export">导出完整 PRD（Markdown）</button></div><p id="prd-count" role="status"></p></header><p class="prd-index-link"><a href="#/v/'+encodeURIComponent(vid)+'/_prd/scope">查看本版功能清单与范围</a></p><div class="prd-layout"><nav id="prd-toc" aria-label="需求目录"></nav><div id="prd-sections"></div></div><dialog id="prd-edit-context"><h2>交给 Agent 精确修改</h2><p>复制下面的定位信息并补充修改意图；不会自动提交，也不会重新生成项目。</p><textarea rows="7" aria-label="Agent 修改上下文" readonly></textarea><button>关闭</button></dialog></div>';
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
    if(view.mode!=='prototype')return esc('文字：'+(view.reason || ''));
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
    var pageId=container.querySelector('#prd-page').value, search=container.querySelector('#prd-search').value.toLowerCase();
    var selected=reqs.filter(function(r){return (!pageId || pages.some(function(pg){return pg.id===pageId && pg.requirement_ids.includes(r.id);})) && (!search || JSON.stringify(r).toLowerCase().includes(search) || interactions.some(function(i){return i.requirement_ids.includes(r.id) && JSON.stringify(i).toLowerCase().includes(search);}));});
    container.querySelector('#prd-count').textContent='显示 '+selected.length+' / '+reqs.length+' 条需求；导出始终包含完整文档。';
    var modules=[]; selected.forEach(function(r){var name=r.module || '功能需求';if(!modules.includes(name))modules.push(name);});
    selected=modules.flatMap(function(name){return selected.filter(function(r){return (r.module || '功能需求')===name;});});
    container.querySelector('#prd-toc').innerHTML=modules.map(function(name){return '<h3>'+esc(name)+'</h3>'+selected.filter(function(r){return (r.module || '功能需求')===name;}).map(function(r){return '<button data-jump="'+esc(r.id)+'">'+esc(r.title)+'</button>';}).join('');}).join('');
    var lastModule=null;
    container.querySelector('#prd-sections').innerHTML=selected.map(function(r){
      var module=r.module || '功能需求';var groupTitle=module!==lastModule?'<h2 class="prd-module">'+esc(module)+'</h2>':'';lastModule=module;
      var html=groupTitle+'<article class="prd-requirement" id="prd-'+esc(r.id)+'"><header><h3 class="prd-feature-title">'+esc(r.title)+'</h3><p class="prd-meta">'+esc(r.id+' · '+meta(r)+(r.blocking?' · 阻塞开发':''))+'</p><button data-edit="'+esc(r.id)+'">交给 Agent 修改此需求</button></header>'+p(r.description);
      (spec.diagrams || []).filter(function(d){return d.level==='detail' && d.requirement_id===r.id;}).forEach(function(d){html+='<section class="prd-diagram" id="diagram-'+esc(d.id)+'">'+(d.parent_id?'<p><a href="'+parentDiagramLink(d)+'">查看上层流程</a></p>':'')+window.PS.mdToHtml((data.versions[vid].diagrams || {})[d.id] || '')+'</section>';});
      var ruleKeys=Object.keys(r.rules || {});
      if(ruleKeys.length){html+='<h3>业务规则</h3>';ruleKeys.forEach(function(k){html+='<section class="prd-rule"><h4>'+esc(k)+'</h4>'+p(r.rules[k])+'</section>';});}
      var groups={};(r.rule_details || []).forEach(function(rule){var key=rule.category || '业务规则';(groups[key] || (groups[key]=[])).push(rule);});
      Object.keys(groups).forEach(function(key){html+='<section class="prd-rule"><h4>'+esc(category[key] || key)+'</h4><ul>'+groups[key].map(function(rule){return '<li>'+esc(rule.statement)+(rule.status==='pending'?' <span class="sr-pending">待确认</span>':'')+'<details class="prd-rule-evidence"><summary>依据'+((rule.examples || []).length?'与实例':'')+'</summary><small>'+esc(rule.id+' · '+meta(rule))+'</small>'+(rule.examples || []).map(function(e){return p(e.input+' → '+e.expected);}).join('')+'</details></li>';}).join('')+'</ul></section>';});
      if((r.boundary_cases || []).length){
        html+='<details class="prd-fold prd-boundaries"><summary>边界与异常用例（'+r.boundary_cases.length+'）</summary><div class="prd-boundary-scroll" role="region" aria-label="边界与异常用例表，窄屏可横向滚动" tabindex="0"><table><thead><tr><th>输入 / 触发</th><th>预期结果</th><th>表达方式</th></tr></thead><tbody>'+r.boundary_cases.map(function(c){return '<tr><td>'+esc(c.input)+'<br><small>'+esc(c.id)+'</small></td><td>'+esc(c.expected)+'</td><td>'+caseView(c)+'</td></tr>';}).join('')+'</tbody></table></div></details>';
      }
      html+='<details class="prd-fold prd-ac-fold" id="acceptance-'+esc(r.id)+'"><summary>验收标准（'+(r.acceptance || []).length+'）</summary><ol class="prd-acceptance">';
      (r.acceptance || []).forEach(function(a){html+='<li>'+p('前提：'+a.given)+p('操作：'+a.when)+p('预期：'+a.then)+acBadge(a.id)+'<small>'+esc(a.id)+'</small></li>';});
      html+='</ol></details><details class="prd-fold"><summary>关联原型</summary><p>';
      pages.filter(function(pg){return pg.requirement_ids.includes(r.id);}).forEach(function(pg){
        var mod=data.versions[vid].manifest.modules.find(function(m){return m.pages.some(function(p){return p.id===pg.id && p.type==='prototype';});});
        if(mod)html+='<a href="#/v/'+encodeURIComponent(vid)+'/'+encodeURIComponent(mod.id)+'/'+encodeURIComponent(pg.id)+'">'+esc(pg.title)+'</a> · ';
      });
      html+='</p></details>';
      var configured=interactions.filter(function(i){return i.requirement_ids.includes(r.id) && Object.keys(i.properties || {}).length;});
      if(configured.length){html+='<details class="prd-fold"><summary>控件属性补充</summary>';configured.forEach(function(i){html+='<p>'+esc(i.description+' · '+i.id)+'</p>';Object.keys(i.properties).forEach(function(k){html+=p(k+'：'+JSON.stringify(i.properties[k]));});});html+='</details>';}
      return html+'</article>';
    }).join('') || '<p>没有匹配需求，请调整筛选。编号不存在时不会自动定位到其他需求。</p>';
    window.PS.renderDiagrams(container).then(function(){var wanted=new URLSearchParams(query).get('diagram');if(wanted){var target=document.getElementById('diagram-'+wanted);if(target && container.contains(target))target.scrollIntoView({block:'start'});}else if(new URLSearchParams(query).get('section')==='acceptance'){var ac=container.querySelector('.prd-ac-fold');if(ac)ac.scrollIntoView({block:'start',behavior:'instant'});}});
    if(new URLSearchParams(query).get('section')==='acceptance'){container.querySelectorAll('.prd-ac-fold').forEach(function(el){el.open=true;});}
    watchSpy(selected);
    setActive((selected[0] || {}).id);
  }
  container.querySelector('#prd-page').value=new URLSearchParams(query).get('page') || '';
  container.querySelector('#prd-search').value=new URLSearchParams(query).get('requirement') || '';
  ['prd-page','prd-search'].forEach(function(id){container.querySelector('#'+id).addEventListener('input',draw);});
  container.onclick=function(event){
    var jump=event.target.closest('[data-jump]'); if(jump){var target=document.getElementById('prd-'+jump.dataset.jump); if(target){target.scrollIntoView({block:'start'});setActive(jump.dataset.jump);}}
    var edit=event.target.closest('[data-edit]'); if(!edit)return;
    var r=reqs.find(function(x){return x.id===edit.dataset.edit;});
    var dialog=container.querySelector('#prd-edit-context');
    dialog.querySelector('textarea').value='请在既有项目中增量修改，不重新生成。\n页面入口：'+location.href.split('?')[0]+'?requirement='+encodeURIComponent(r.id)+'\n版本：'+vid+'\n需求：'+r.title+'（'+r.id+'）'+(edit.dataset.control?'\n控件：'+edit.dataset.control:'')+'\n修改要求：【请填写】\n保留其他需求、编号、页面结构及历史；若此版已冻结，请先定位对应规划版，不修改冻结物料。';
    dialog.showModal();dialog.querySelector('textarea').select();
  };
  container.querySelector('#prd-edit-context button').onclick=function(){container.querySelector('#prd-edit-context').close();};
  container.querySelector('#prd-export').onclick=function(){var md=data.versions[vid].full_prd_markdown || data.versions[vid].files[page.id] || '';var url=URL.createObjectURL(new Blob([md],{type:'text/markdown;charset=utf-8'}));var a=document.createElement('a');a.href=url;a.download=data.project.name+'-'+vid+'-产品需求文档.md';a.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);};
  draw();
}};
