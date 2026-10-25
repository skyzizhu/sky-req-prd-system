/* Static reader: states are authored snapshots; spec remains the rule source. */
window.PSStaticReader = function (data, page, interactions) {
  'use strict';
  var canvas = document.querySelector('main');
  if (!canvas) throw new Error('静态原型缺少 main 画布');
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
  var states = page.states || [];
  var sections = Array.from(canvas.querySelectorAll('[data-ps-state]'));
  if (!states.length || states.some(function(s){ return !sections.some(function(el){return el.dataset.psState===s.id;}); })) throw new Error('静态原型状态声明与画布不一致');
  var params=new URLSearchParams(location.hash.slice(1));
  var selected=states.some(function(s){return s.id===params.get('state');})?params.get('state'):states[0].id;
  var selectedRule=params.get('rule') || '';
  var pendingCount=new Set(reqPending()).size;
  function reqPending(){return (data.spec.requirements || []).filter(function(r){return page.requirement_ids.includes(r.id);}).flatMap(function(r){var ids=(r.rule_details || []).filter(function(rule){return rule.status==='pending';}).map(function(rule){return rule.id;});return r.status==='pending' && !ids.length?[r.id]:ids;});}
  var compare = false, numbered = true;
  var reqs = data.spec.requirements || [];
  var header = document.createElement('header'); header.className='sr-header';
  header.innerHTML='<div><span class="sr-eyebrow">'+esc(data.projectName+' · '+data.version)+(pendingCount?' · '+pendingCount+' 项待确认':'')+'</span><h1>'+esc(page.title)+'</h1><p class="sr-caption">布局与状态示意 · 视觉细节以正式设计稿为准</p></div><div class="sr-actions"><label><input type="checkbox" id="sr-numbers" checked>显示编号</label><button type="button" id="sr-compare" aria-pressed="false">展开状态对照</button><button type="button" id="sr-link">定位链接</button></div>';
  var tabs=document.createElement('nav');tabs.className='sr-tabs';tabs.setAttribute('aria-label','页面状态');
  var layout=document.createElement('div');layout.className='sr-layout';
  var view=document.createElement('div');view.className='sr-view';
  var panel=document.createElement('aside');panel.className='sr-rules';panel.setAttribute('aria-label','规则说明');
  var handoff=document.createElement('details');handoff.className='sr-handoff';
  var info=page.handoff || {};
  function bullets(items,empty){return '<ul>'+((items && items.length)?items:[empty]).map(function(t){return '<li>'+esc(t)+'</li>';}).join('')+'</ul>';}
  handoff.innerHTML='<summary>本页交接 · 开发前提、测试验收、状态与元素</summary><div class="sr-handoff-grid"><section><h2>开发 · 使用前提</h2><p>适用角色：'+esc(info.role || '待确认')+'</p>'+bullets(info.preconditions,'前置条件待补充')+'<h3>范围</h3>'+bullets(info.scope,'范围见 PRD')+'<h3>不做</h3>'+bullets(info.out_of_scope,'排除项待确认')+'</section><section><h2>测试 · 验收入口</h2><p>每条规则下可展开“依据与验收”。静态图用于核对状态，实际产品执行结果单独登记。</p><h3>状态覆盖</h3><p>'+esc(states.map(function(st){return st.title;}).join('、'))+'</p></section><section><h2>设计 · 状态与元素</h2>'+bullets(info.design_notes,'状态和必要元素必须完整保留；布局及视觉由设计重新设计。')+'<ul>'+states.map(function(st){return '<li><strong>'+esc(st.title)+'</strong>：'+esc((st.elements || []).map(function(el){return el.title;}).join('、') || '必要元素待核对')+'</li>';}).join('')+'</ul></section></div>';
  canvas.before(header,handoff,tabs,layout);view.appendChild(canvas);layout.append(view,panel);
  document.body.classList.add('sr-host');
  sections.forEach(function(section){
    section.classList.add('sr-state');
    var snapshot=section.querySelector('.sr-snapshot');
    if (!snapshot) throw new Error('状态 '+section.dataset.psState+' 缺少 .sr-snapshot');
    snapshot.inert=true;
    var layer=document.createElement('div');layer.className='sr-pins';section.appendChild(layer);
  });
  function applicable(it){return !it.state_ids || !it.state_ids.length || compare || it.state_ids.includes(selected);}
  function target(it,section){var scope=section || sections.find(function(el){return !el.hidden && el.dataset.psState===selected;});var mapped=scope && scope.querySelector('[data-rule-ref="'+it.id+'"]');return mapped || canvas.querySelector(it.selector);}
  function focusRule(it,fromPin,section){
    document.querySelectorAll('.sr-highlight').forEach(function(el){el.classList.remove('sr-highlight');});
    var el=target(it,section), card=panel.querySelector('[data-rule-card="'+it.id+'"]');
    if(el){el.classList.add('sr-highlight');if(!fromPin)el.scrollIntoView({block:'center',behavior:'smooth'});}
    panel.querySelectorAll('.sr-card').forEach(function(c){c.classList.toggle('sr-selected',c===card);});
    var stateElement=el && el.closest('[data-ps-state]');if(stateElement){selected=stateElement.dataset.psState;tabs.querySelectorAll('[data-state]').forEach(function(button){button.setAttribute('aria-pressed',String(button.dataset.state===selected));});}
    selectedRule=it.id;updateHash();
    if(card && fromPin){card.scrollIntoView({block:'nearest',behavior:'smooth'});var button=card.querySelector('button');if(button)button.focus({preventScroll:true});}
  }
  function ruleText(it){
    var out='';
    reqs.filter(function(r){return (it.requirement_ids || []).includes(r.id);}).forEach(function(r){
      var rules=(r.rule_details || []).filter(function(rule){return !it.rule_ids || it.rule_ids.includes(rule.id);});
      rules.forEach(function(rule){out+='<li>'+esc(rule.statement)+(rule.status==='pending'?' <span class="sr-pending">待确认</span>':'')+'</li>';});
      if(!rules.length && !it.rule_ids)Object.keys(r.rules || {}).forEach(function(k){out+='<li>'+esc(k+'：'+r.rules[k])+'</li>';});
    });
    return out || '<li>'+esc(it.description)+'</li>';
  }
  function card(it){
    var n=interactions.indexOf(it)+1;
    var ruleIds=it.rule_ids || [];
    var ac=[], provenance=[];
    reqs.filter(function(r){return it.requirement_ids.includes(r.id);}).forEach(function(r){
      var ids=(r.rule_details || []).filter(function(rule){return !ruleIds.length || ruleIds.includes(rule.id);}).flatMap(function(rule){provenance.push(rule.id+' · '+(rule.source==='origin'?'方案依据':'AI 推断')+' · '+(rule.status==='confirmed'?'已确认':'待确认'));return rule.acceptance_ids || [];});
      (r.acceptance || []).filter(function(a){return !ruleIds.length || ids.includes(a.id);}).forEach(function(a){ac.push(a);});
    });
    return '<article class="sr-card" data-rule-card="'+esc(it.id)+'"><h3><button type="button" data-locate="'+esc(it.id)+'"><span class="sr-number">'+n+'</span>'+esc(it.title || it.description)+'</button></h3><ul>'+ruleText(it)+'</ul><details><summary>依据与验收</summary><p>'+esc(it.requirement_ids.join(' · '))+'</p><p>'+esc(provenance.join('；'))+'</p><p><a href="'+esc(prdLink(it.requirement_ids[0]))+'" target="_blank" rel="noopener">查看 PRD 原文</a></p>'+ac.map(function(a){return '<p>'+esc(a.id+' · 前提：'+a.given+'；操作：'+a.when+'；预期：'+a.then)+'</p>';}).join('')+'</details></article>';
  }
  function positionPins(){
    sections.forEach(function(section){
      var layer=section.querySelector('.sr-pins');layer.replaceChildren();
      if(section.hidden || !numbered)return;
      var box=section.getBoundingClientRect();
      interactions.filter(applicable).forEach(function(it){
        var el=target(it,section);if(!el || !section.contains(el) || !el.getClientRects().length)return;
        var rect=el.getBoundingClientRect(),pin=document.createElement('button');pin.type='button';pin.className='sr-pin';
        pin.textContent=String(interactions.indexOf(it)+1);pin.setAttribute('aria-label','查看规则 '+pin.textContent+'：'+(it.title || it.description));
        pin.style.left=Math.max(0,rect.left-box.left-12)+'px';pin.style.top=Math.max(0,rect.top-box.top-12)+'px';
        pin.onclick=function(){focusRule(it,true,section);};layer.appendChild(pin);
      });
    });
  }
  function draw(){
    if(!tabs.children.length)tabs.innerHTML=states.map(function(s){return '<button type="button" data-state="'+esc(s.id)+'" aria-pressed="'+(selected===s.id)+'">'+esc(s.title)+'</button>';}).join('');
    tabs.querySelectorAll('[data-state]').forEach(function(button){button.setAttribute('aria-pressed',String(button.dataset.state===selected));});
    sections.forEach(function(el){el.hidden=!compare && el.dataset.psState!==selected;});
    var current=states.find(function(s){return s.id===selected;});
    var common=interactions.filter(function(it){return !it.state_ids || !it.state_ids.length;});
    var specific=interactions.filter(function(it){return it.state_ids && it.state_ids.length && applicable(it);});
    panel.innerHTML='<header><span class="sr-eyebrow">规则说明</span><h2>'+esc(compare?'全部状态':current.title)+'</h2><p>'+esc(compare?'按编号对照画面；共用规则只写一次。':current.summary || '')+'</p>'+(!compare && current.next?'<p><strong>后续：</strong>'+esc(current.next)+'</p>':'')+'</header>'+(!compare && specific.length?'<h2 class="sr-group">当前状态</h2>'+specific.map(card).join(''):'')+(common.length?'<h2 class="sr-group">页面共用</h2>'+common.map(card).join(''):'')+(compare && specific.length?'<h2 class="sr-group">状态差异</h2>'+specific.map(card).join(''):'');
    header.querySelector('#sr-compare').textContent=compare?'返回单状态':'展开状态对照';
    header.querySelector('#sr-compare').setAttribute('aria-pressed',String(compare));
    positionPins();
    if(selectedRule){var it=interactions.find(function(i){return i.id===selectedRule && applicable(i);});if(it)focusRule(it,false);}
  }
  function prdLink(rid){var url=new URL('../../../../site/index.html',location.href);url.hash='/v/'+encodeURIComponent(data.version)+'/_prd/functions?requirement='+encodeURIComponent(rid);return url.href;}
  function updateHash(){var p=new URLSearchParams({state:selected});if(selectedRule)p.set('rule',selectedRule);history.replaceState(null,'','#'+p.toString());}
  var linkDialog=document.createElement('dialog');linkDialog.className='sr-link-dialog';linkDialog.innerHTML='<h2>定位当前状态与规则</h2><p>接收者打开同一份项目即可定位。file:// 地址需有相同本地文件路径；localhost 链接只适用于当前电脑。</p><label>项目入口<input readonly id="sr-project-link"></label><label>独立页面<input readonly id="sr-direct-link"></label><button type="button">关闭</button>';document.body.appendChild(linkDialog);linkDialog.querySelector('button').onclick=function(){linkDialog.close();};
  header.querySelector('#sr-link').onclick=function(){var direct=new URL(location.href);direct.hash=new URLSearchParams({state:selected,...(selectedRule?{rule:selectedRule}:{})}).toString();var project=new URL('../../../../site/index.html',location.href);project.hash=(data.pageRoutes || {})[page.id]+'?'+direct.hash.slice(1);linkDialog.querySelector('#sr-project-link').value=project.href;linkDialog.querySelector('#sr-direct-link').value=direct.href;linkDialog.showModal();linkDialog.querySelector('input').select();};
  var live=document.createElement('p');live.className='sr-live';live.setAttribute('role','status');live.setAttribute('aria-live','polite');header.appendChild(live);
  tabs.onclick=function(e){var b=e.target.closest('[data-state]');if(!b)return;selected=b.dataset.state;selectedRule='';compare=false;updateHash();draw();tabs.querySelector('[data-state="'+selected+'"]').focus({preventScroll:true});live.textContent='已切换到'+states.find(function(st){return st.id===selected;}).title+'状态，画面与规则已同步。';};
  panel.onclick=function(e){var b=e.target.closest('[data-locate]');if(b)focusRule(interactions.find(function(it){return it.id===b.dataset.locate;}),false);};
  header.querySelector('#sr-compare').onclick=function(){compare=!compare;draw();};
  header.querySelector('#sr-numbers').onchange=function(e){numbered=e.target.checked;positionPins();};
  window.addEventListener('hashchange',function(){var p=new URLSearchParams(location.hash.slice(1)),id=p.get('state');selectedRule=p.get('rule') || '';if(states.some(function(s){return s.id===id;})){selected=id;compare=false;draw();}});
  window.addEventListener('resize',positionPins);
  if(window.ResizeObserver)new ResizeObserver(positionPins).observe(canvas);
  draw();
};


(function(){
  'use strict';
  var surface=document.createElement('div');surface.className='sr-error';surface.hidden=true;surface.setAttribute('role','alert');document.body.appendChild(surface);
  function fail(message){surface.hidden=false;surface.textContent='原型加载失败：'+message;}
  window.addEventListener('error',function(e){fail(e.message);});
  window.addEventListener('unhandledrejection',function(e){fail(String(e.reason && (e.reason.message || e.reason)));});
  var data=window.PS_SPEC;
  if(!data || data.schema_version!==2){fail('缺少 V2 结构化数据，请重新构建。');return;}
  var page=data.spec.pages.find(function(p){return p.id===document.body.dataset.pageId;});
  if(!page){fail('页面未登记。');return;}
  // PS_STATIC_PROPERTIES: authored properties are applied before the snapshots become inert.
  var interactions=data.spec.interactions.filter(function(i){return i.page===page.id;});
  interactions.forEach(function(it){var el=document.querySelector(it.selector),props=it.properties || {};if(!el)return;
    Object.keys(props).forEach(function(k){var v=props[k];if(k==='text' && !el.children.length)el.textContent=v;
      else if(k==='defaultValue'){el.value=v;el.defaultValue=v;}
      else if(k==='options' && el.tagName==='SELECT'){el.replaceChildren();v.forEach(function(o){el.add(new Option(o.label,o.value));});}
      else if(k==='width')el.style.width={auto:'auto',compact:'160px',full:'100%'}[v];
      else if(k==='unit')el.dataset.unit=v;
      else if(k==='required')el.required=v;
      else el.setAttribute(k,v);
    });
  });
  window.PSStaticReader(data,page,interactions);
})();
