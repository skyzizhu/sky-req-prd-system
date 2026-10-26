/* Build the reading model from rule IDs, never from matching prose. */
window.PSAnnotationModel = function(reqs,interactions,states,selected,compare){
  var rules=new Map(),groups={specific:[],common:[]},baseline=(states[0] || {}).id;
  (reqs || []).forEach(function(req){(req.rule_details || []).forEach(function(rule){rules.set(rule.id,{rule:rule,requirement:req.id});});});
  function applies(it,sid){return !(it.state_ids || []).length || it.state_ids.includes(sid);}
  var visible=interactions.filter(function(it){return compare || applies(it,selected);});
  var entries=new Map();
  visible.forEach(function(it){(it.rule_ids || []).forEach(function(id){var known=rules.get(id);if(!known)return;var entry=entries.get(id);if(!entry){entry={rule:known.rule,requirement:known.requirement,controls:[],states:[]};entries.set(id,entry);}if(!entry.controls.some(function(c){return c.id===it.id;}))entry.controls.push(it);});});
  entries.forEach(function(entry){
    entry.states=states.filter(function(st){return interactions.some(function(it){return (it.rule_ids || []).includes(entry.rule.id) && applies(it,st.id);});}).map(function(st){return st.id;});
    var common=entry.states.length>1 && entry.states.includes(baseline);
    groups[common?'common':'specific'].push(entry);
  });
  return groups;
};

window.PSAnnotationSelection = function(model,controlId){
  var all=model.specific.concat(model.common),focused=[],other=[];
  all.forEach(function(entry){(controlId && entry.controls.some(function(it){return it.id===controlId;})?focused:other).push(entry);});
  var order=[];focused.forEach(function(entry){entry.controls.filter(function(it){return it.id===controlId;}).forEach(function(it){(it.rule_ids || []).forEach(function(id){if(!order.includes(id))order.push(id);});});});
  focused.sort(function(a,b){return order.indexOf(a.rule.id)-order.indexOf(b.rule.id);});
  return {focused:focused,other:other};
};

/* Static reader: states are authored snapshots; spec remains the rule source. */
// Opt-in native widgets only. No request, storage, navigation or business transition.
window.PSLocalControls = function(snapshot,onLayout){
  'use strict';
  snapshot.inert=false;
  var controls=Array.from(snapshot.querySelectorAll('input,select,textarea,button,a,summary'));
  var initial=controls.map(function(el){return {el:el,value:el.value,checked:el.checked,selected:el.tagName==='SELECT'?Array.from(el.options).map(function(o){return o.selected;}):null};});
  var disclosures=Array.from(snapshot.querySelectorAll('details')).map(function(el){return {el:el,open:el.open};});
  function owner(el){var node=el && el.closest('[data-ps-local]');return node && snapshot.contains(node)?node:null;}
  function allowed(el){
    if(!el || el.disabled)return false;
    var node=owner(el),mode=node && node.dataset.psLocal,type=(el.type || '').toLowerCase();
    return (mode==='choice' && el.tagName==='INPUT' && ['checkbox','radio'].includes(type)) ||
      (mode==='select' && el.tagName==='SELECT') ||
      (mode==='input' && (el.tagName==='TEXTAREA' || (el.tagName==='INPUT' && ['text','password','email','number','date','time','search','tel','url','range'].includes(type)))) ||
      (mode==='disclosure' && el.tagName==='SUMMARY');
  }
  controls.forEach(function(el){if(!allowed(el) && !el.disabled)el.setAttribute('tabindex','-1');});
  function sourceValue(key){
    var node=Array.from(snapshot.querySelectorAll('[data-ps-key]')).find(function(el){return el.dataset.psKey===key;});
    if(!node)return null;
    if(node.matches('input[type=checkbox]'))return String(node.checked);
    if(node.matches('input,select,textarea'))return node.value;
    var radio=node.querySelector('input[type=radio]:checked');if(radio)return radio.value;
    var box=node.querySelector('input[type=checkbox]');return box?String(box.checked):null;
  }
  function refresh(){
    snapshot.querySelectorAll('[data-ps-when-key]').forEach(function(el){
      var show=sourceValue(el.dataset.psWhenKey)===el.dataset.psWhenValue;
      if(!show && !el.hidden && el.hasAttribute('data-ps-clear-hidden')){
        el.querySelectorAll('input,select,textarea').forEach(function(c){if(c.matches('[type=checkbox],[type=radio]'))c.checked=false;else if(c.tagName==='SELECT')c.selectedIndex=-1;else c.value='';});
        el.querySelectorAll('[data-ps-local-error]').forEach(function(message){message.hidden=true;});
      }
      el.hidden=!show;
    });
    if(onLayout)onLayout();
  }
  function controlFor(e){var el=e.target.closest('input,select,textarea,button,a,summary');if(el)return el;var label=e.target.closest('label');return label && (label.control || label.querySelector('input,select,textarea'));}
  function block(e){e.preventDefault();e.stopImmediatePropagation();}
  ['click','pointerdown','beforeinput','keydown'].forEach(function(type){snapshot.addEventListener(type,function(e){
    var el=controlFor(e);if(!el)return;
    if(!allowed(el)){if(type!=='keydown' || e.key!=='Tab')block(e);return;}
    if(type==='keydown' && e.key==='Enter' && el.tagName==='INPUT')e.preventDefault();
  },true);});
  snapshot.addEventListener('submit',block,true);
  snapshot.addEventListener('change',function(e){
    if(!allowed(e.target))return;
    var group=e.target.closest('[data-ps-max]');
    if(group){
      var limit=Number(group.dataset.psMax),boxes=group.querySelectorAll('input[type=checkbox]:checked'),invalid=boxes.length>limit;
      if(invalid && e.target.type==='checkbox')e.target.checked=false;
      var feedback=Array.from(snapshot.querySelectorAll('[id]')).find(function(el){return el.id===group.dataset.psFeedback;});
      if(feedback)feedback.hidden=!invalid;
    }
    refresh();
  });
  snapshot.querySelectorAll('details[data-ps-local="disclosure"]').forEach(function(el){el.addEventListener('toggle',function(){if(onLayout)onLayout();});});
  function reset(){initial.forEach(function(row){var el=row.el;if(row.selected)Array.from(el.options).forEach(function(o,i){o.selected=row.selected[i];});else if(row.value!==undefined)el.value=row.value;if(row.checked!==undefined)el.checked=row.checked;});disclosures.forEach(function(row){row.el.open=row.open;});snapshot.querySelectorAll('[data-ps-local-error]').forEach(function(el){el.hidden=true;});refresh();}
  refresh();
  return {reset:reset,refresh:refresh};
};

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
  header.innerHTML='<div class="sr-identity"><h1 title="'+esc(page.title)+'">'+esc(page.title)+'</h1><span class="sr-eyebrow" title="'+esc(data.projectName+' · '+data.version)+'">'+esc(data.projectName+' · '+data.version)+(pendingCount?' · '+pendingCount+' 项待确认':'')+'</span></div><div class="sr-actions"><label><input type="checkbox" id="sr-numbers" checked>显示编号</label><button type="button" id="sr-compare" aria-pressed="false">展开状态对照</button><button type="button" id="sr-handoff-toggle" aria-expanded="false" aria-controls="sr-handoff">页面信息</button><button type="button" id="sr-link">定位链接</button></div>';
  var tabs=document.createElement('nav');tabs.className='sr-tabs';tabs.setAttribute('aria-label','页面状态');
  var layout=document.createElement('div');layout.className='sr-layout';
  var view=document.createElement('div');view.className='sr-view';
  var panel=document.createElement('aside');panel.className='sr-rules';panel.setAttribute('aria-label','规则说明');
  var handoff=document.createElement('section');handoff.className='sr-handoff';handoff.id='sr-handoff';handoff.hidden=true;handoff.setAttribute('aria-label','页面补充与必要元素');
  var info=page.handoff || {};
  function bullets(items,empty){return '<ul>'+((items && items.length)?items:[empty]).map(function(t){return '<li>'+esc(t)+'</li>';}).join('')+'</ul>';}
  var prdRoot=new URL('../../../../site/index.html',location.href);
  function chapter(id,query){var url=new URL(prdRoot);url.hash='/v/'+encodeURIComponent(data.version)+'/_prd/'+id+(query?'?'+query:'');return url.href;}
  handoff.innerHTML='<p>页面状态由顶部切换；控件仅提供局部交互。点击编号查看规则，正式视觉由设计交付。</p><div class="sr-handoff-grid"><section><h2>页面补充</h2>'+(info.role?'<p>适用角色：'+esc(info.role)+'</p>':'')+['preconditions','scope','out_of_scope','design_notes','dependencies','decisions'].filter(function(k){return info[k] && info[k].length;}).map(function(k){return '<h3>'+({preconditions:'本页前提',scope:'本页范围',out_of_scope:'本页排除项',design_notes:'设计补充',dependencies:'本页依赖',decisions:'待决策'}[k])+'</h3>'+bullets(info[k],'');}).join('')+'<p><a href="'+esc(chapter('scope'))+'" target="_blank" rel="noopener">版本范围</a> · <a href="'+esc(chapter('functions','page='+encodeURIComponent(page.id)+'&section=acceptance'))+'" target="_blank" rel="noopener">本页功能与验收</a></p></section><section><h2>必要元素</h2><div id="sr-elements"></div></section></div>';
  canvas.before(header,handoff,tabs,layout);view.appendChild(canvas);layout.append(view,panel);
  document.body.classList.add('sr-host');
  sections.forEach(function(section){
    section.classList.add('sr-state');
    var state=states.find(function(s){return s.id===section.dataset.psState;}), title=section.querySelector('h2');
    if(title && state && title.textContent.trim()===state.title+' · '+(state.summary || ''))title.textContent=state.title;
    var snapshot=section.querySelector('.sr-snapshot');
    if (!snapshot) throw new Error('状态 '+section.dataset.psState+' 缺少 .sr-snapshot');
    // Reserve a separate annotation gutter; pins must not cover widget hit areas.
    interactions.forEach(function(it){
      var el=target(it,section);if(!el || !snapshot.contains(el) || el.parentElement.classList.contains('sr-annotation-anchor'))return;
      if(['TR','TD','TH','TBODY','THEAD','OPTION','SUMMARY'].includes(el.tagName))return;
      var anchor=document.createElement('div');anchor.className='sr-annotation-anchor'+(el.tagName==='BUTTON' || el.tagName==='A'?' sr-anchor-inline':'');
      el.before(anchor);anchor.appendChild(el);
    });
    var layer=document.createElement('div');layer.className='sr-pins';section.appendChild(layer);
  });
  var localControls=sections.map(function(section){return window.PSLocalControls(section.querySelector('.sr-snapshot'),function(){positionPins();});});
  function applicable(it){return !it.state_ids || !it.state_ids.length || compare || it.state_ids.includes(selected);}
  function target(it,section){var scope=section || sections.find(function(el){return !el.hidden && el.dataset.psState===selected;});var mapped=scope && scope.querySelector('[data-rule-ref="'+it.id+'"]');return mapped || canvas.querySelector(it.selector);}
  function focusRule(it,fromPin,section,automatic){
    if(!it)return;
    document.querySelectorAll('.sr-highlight').forEach(function(el){el.classList.remove('sr-highlight');});
    var el=target(it,section);
    if(el){el.classList.add('sr-highlight');if(!fromPin && !automatic)el.scrollIntoView({block:'center',behavior:'smooth'});}
    var stateElement=el && el.closest('[data-ps-state]');
    if(stateElement){selected=stateElement.dataset.psState;tabs.querySelectorAll('[data-state]').forEach(function(button){button.setAttribute('aria-pressed',String(button.dataset.state===selected));});}
    selectedRule=it.id;renderRules();
    var button=panel.querySelector('[data-locate="'+it.id+'"]'),card=panel.querySelector('.sr-card');
    if(card)card.classList.add('sr-selected');
    markSelection();updateHash();
    if(fromPin && window.matchMedia('(max-width:640px)').matches)panel.scrollIntoView({block:'start',behavior:'smooth'});
    if(button && !automatic)button.focus({preventScroll:true});
  }
  function ruleDetails(rule){
    var html=esc(rule.statement)+(rule.status==='pending'?' <span class="sr-pending">待确认</span>':'');
    if(rule.clauses && rule.clauses.length)html+='<dl class="sr-clauses">'+rule.clauses.map(function(item){return '<div><dt>'+esc(item.label)+'</dt><dd>'+esc(item.text)+'</dd></div>';}).join('')+'</dl>';
    if(rule.table){var table=rule.table;html+='<div class="sr-table-wrap"><table><thead><tr>'+table.columns.map(function(c){return '<th scope="col">'+esc(c)+'</th>';}).join('')+'</tr></thead><tbody>'+table.rows.map(function(row){return '<tr>'+row.map(function(c){return '<td>'+esc(c)+'</td>';}).join('')+'</tr>';}).join('')+'</tbody></table></div>';}
    if(rule.examples && rule.examples.length)html+='<dl class="sr-examples">'+rule.examples.map(function(e){return '<dt>例如：'+esc(e.input)+'</dt><dd>'+esc(e.expected)+'</dd>';}).join('')+'</dl>';
    return html;
  }
  function controlButton(it){var n=interactions.indexOf(it)+1;return '<button type="button" class="sr-control-link" data-locate="'+esc(it.id)+'"><span class="sr-number">'+n+'</span>'+esc(it.title || it.description)+'</button>';}
  function card(entry,index){
    var rule=entry.rule,controls=entry.controls,first=controls[0];
    var title=rule.title || (controls.length===1?(first.title || first.description):(first.title || first.description)+'等 '+controls.length+' 个控件');
    var heading=panelRuleCount>1?'<h3>'+esc(title)+'</h3>':'';
    return '<article class="sr-card" data-rule-card="'+esc(first.id)+'" data-rule-id="'+esc(rule.id)+'">'+heading+'<div class="sr-rule-body">'+ruleDetails(rule)+'</div>'+(compare?'<p class="sr-applies">适用状态：'+esc(entry.states.map(function(id){var st=states.find(function(s){return s.id===id;});return st?st.title:id;}).join('、'))+'</p>':'')+'<details><summary>依据与验收</summary><p>'+esc(rule.id+' · '+(rule.source==='origin'?'方案依据':'AI 推断')+' · '+(rule.status==='confirmed'?'已确认':'待确认'))+'</p><p><a href="'+esc(prdLink(entry.requirement))+'" target="_blank" rel="noopener">查看 PRD 原文</a></p>'+(rule.acceptance_ids || []).map(function(id){return '<p><a href="'+esc(prdLink(entry.requirement)+'&section=acceptance&acceptance='+encodeURIComponent(id))+'" target="_blank" rel="noopener">验收 '+esc(id)+'</a></p>';}).join('')+'</details></article>';
  }
  function markSelection(){
    document.body.classList.toggle('sr-has-selection',!!selectedRule);
    document.querySelectorAll('.sr-pin[data-interaction]').forEach(function(pin){var on=pin.dataset.interaction===selectedRule;pin.classList.toggle('sr-pin-selected',on);pin.setAttribute('aria-pressed',String(on));});
    panel.querySelectorAll('[data-locate]').forEach(function(button){var on=button.dataset.locate===selectedRule;button.classList.toggle('sr-control-selected',on);button.setAttribute('aria-pressed',String(on));});
  }
  function stateChanges(current){
    if(compare)return '';
    var baseline=states[0];
    if(current.id===baseline.id)return '<p class="sr-state-context">基准画面 · 以下列出适用约束。</p>'+(current.summary?'<p class="sr-state-context">'+esc(current.summary)+'</p>':'')+(current.next?'<p class="sr-state-context"><strong>后续：</strong>'+esc(current.next)+'</p>':'');
    var names=function(st){return (st.elements || []).map(function(e){return e.title;});};
    var before=names(baseline),after=names(current),added=after.filter(function(n){return !before.includes(n);}),removed=before.filter(function(n){return !after.includes(n);});
    return '<section class="sr-state-changes"><h3>本状态变化</h3><p class="sr-change-baseline">相对「'+esc(baseline.title)+'」画面</p><p>'+esc(current.summary || '状态差异以对应画面和专属规则为准。')+'</p>'+(added.length?'<p><strong>新增显示：</strong>'+esc(added.join('、'))+'</p>':'')+(removed.length?'<p><strong>不再显示：</strong>'+esc(removed.join('、'))+'</p>':'')+(current.next?'<p><strong>后续：</strong>'+esc(current.next)+'</p>':'')+'</section>';
  }
  var panelRuleCount=0;
  function renderRules(){
    var current=states.find(function(st){return st.id===selected;});
    var model=window.PSAnnotationModel(reqs,interactions,states,selected,compare);
    var partition=window.PSAnnotationSelection(model,selectedRule);
    var control=interactions.find(function(it){return it.id===selectedRule;});
    if(control && partition.focused.length){
      panelRuleCount=partition.focused.length;
      var related=new Map();partition.focused.forEach(function(entry){entry.controls.forEach(function(it){if(it.id!==control.id)related.set(it.id,it);});});
      var n=interactions.indexOf(control)+1;
      var locate='<button type="button" class="sr-control-link" data-locate="'+esc(control.id)+'" aria-label="'+esc('定位：'+(control.title || control.description))+'"><span class="sr-number">'+n+'</span></button>';
      panel.innerHTML='<header class="sr-focus-heading"><span class="sr-eyebrow">当前控件 · '+esc(current.title)+'</span><div class="sr-focus-title"><h2>'+esc(control.title || control.description)+'</h2>'+locate+'</div><div class="sr-focus-actions"><span>'+panelRuleCount+' 条关联规则</span></div></header><div class="sr-focused-rules">'+partition.focused.map(card).join('')+'</div>'+(related.size?'<details class="sr-related-controls"><summary>关联控件（'+related.size+'）</summary><div class="sr-control-links">'+Array.from(related.values()).map(controlButton).join('')+'</div></details>':'')+(!compare?'<details class="sr-state-context-fold"><summary>本状态说明</summary>'+stateChanges(current)+'</details>':'');
    }else{
      panel.innerHTML='<header><h2>'+esc(current.title)+'</h2></header><p>本状态暂无可查看的标注。</p>'+stateChanges(current);
    }
    panel.scrollTop=0;
  }
  function positionPins(){
    sections.forEach(function(section){
      var layer=section.querySelector('.sr-pins');layer.replaceChildren();
      if(section.hidden || !numbered)return;
      var box=section.getBoundingClientRect(), occupied=[];
      interactions.filter(applicable).forEach(function(it){
        var el=target(it,section);if(!el || !section.contains(el) || !el.getClientRects().length)return;
        var rect=el.getBoundingClientRect(),pin=document.createElement('button');pin.type='button';pin.className='sr-pin';
        pin.dataset.interaction=it.id;pin.textContent=String(interactions.indexOf(it)+1);pin.setAttribute('aria-label','查看规则 '+pin.textContent+'：'+(it.title || it.description));
        var size=24,x=Math.max(0,Math.min(box.width-size,rect.left-box.left-28)),y=Math.max(0,rect.top-box.top+Math.max(0,(Math.min(rect.height,28)-size)/2));
        while(occupied.some(function(p){return Math.abs(p.x-x)<size+2 && Math.abs(p.y-y)<size+2;})){y+=size+2;}
        occupied.push({x:x,y:y});pin.style.left=x+'px';pin.style.top=y+'px';
        pin.onclick=function(e){e.preventDefault();e.stopPropagation();focusRule(it,true,section);};layer.appendChild(pin);
      });
    });
    markSelection();
  }
  function draw(){
    document.querySelectorAll('.sr-highlight').forEach(function(el){el.classList.remove('sr-highlight');});
    document.body.classList.toggle('sr-comparing',compare);
    if(!tabs.children.length)tabs.innerHTML=states.map(function(s){return '<button type="button" data-state="'+esc(s.id)+'" aria-pressed="'+(selected===s.id)+'">'+esc(s.title)+'</button>';}).join('');
    tabs.querySelectorAll('[data-state]').forEach(function(button){button.setAttribute('aria-pressed',String(button.dataset.state===selected));});
    sections.forEach(function(el){el.hidden=!compare && el.dataset.psState!==selected;});
    // Resolve a missing/stale link against the current snapshot, never another state.
    var currentSection=sections.find(function(el){return el.dataset.psState===selected;});
    function selectable(it){var el=target(it,currentSection);return (!it.state_ids || !it.state_ids.length || it.state_ids.includes(selected)) && (it.rule_ids || []).length && el && currentSection.contains(el) && el.getClientRects().length;}
    var chosen=interactions.find(function(it){return it.id===selectedRule && selectable(it);}) || interactions.find(selectable);
    selectedRule=chosen?chosen.id:'';
    var current=states.find(function(s){return s.id===selected;});
    var inventories=(compare?states:[current]).map(function(st){return '<details'+(!compare?' open':'')+'><summary>'+esc(st.title)+'</summary><p>'+esc((st.elements || []).map(function(el){return el.title;}).join('、'))+'</p></details>';});
    handoff.querySelector('#sr-elements').innerHTML=inventories.join('');
    renderRules();
    header.querySelector('#sr-compare').textContent=compare?'返回单状态':'展开状态对照';
    header.querySelector('#sr-compare').setAttribute('aria-pressed',String(compare));
    positionPins();
    if(chosen)focusRule(chosen,false,currentSection,true);else{markSelection();updateHash();}
  }
  function prdLink(rid){var url=new URL('../../../../site/index.html',location.href);url.hash='/v/'+encodeURIComponent(data.version)+'/_prd/functions?requirement='+encodeURIComponent(rid);return url.href;}
  function updateHash(){var p=new URLSearchParams({state:selected});if(selectedRule)p.set('rule',selectedRule);history.replaceState(null,'','#'+p.toString());}
  // Reply only to this frame's parent, on demand; supports file:// opaque origins.
  window.addEventListener('message',function(event){
    var msg=event.data;
    if(window.parent===window || event.source!==window.parent || !msg || msg.type!=='ps-maintenance-context-request' || typeof msg.request!=='string')return;
    var it=interactions.find(function(i){return i.id===selectedRule;}),section=sections.find(function(s){return s.dataset.psState===selected;}),el=it && target(it,section);
    event.source.postMessage({type:'ps-maintenance-context',request:msg.request,project:data.project,version:data.version,page:page.id,state:selected,interaction:it?it.id:null,selector:el && el.id?'#'+el.id:null,compare:compare},'*');
  });
  var linkDialog=document.createElement('dialog');linkDialog.className='sr-link-dialog';linkDialog.innerHTML='<h2>定位当前状态与规则</h2><p>接收者打开同一份项目即可定位。file:// 地址需有相同本地文件路径；localhost 链接只适用于当前电脑。</p><label>项目入口<input readonly id="sr-project-link"></label><label>独立页面<input readonly id="sr-direct-link"></label><button type="button">关闭</button>';document.body.appendChild(linkDialog);linkDialog.querySelector('button').onclick=function(){linkDialog.close();};
  header.querySelector('#sr-handoff-toggle').onclick=function(){handoff.hidden=!handoff.hidden;this.setAttribute('aria-expanded',String(!handoff.hidden));positionPins();};
  header.querySelector('#sr-link').onclick=function(){var direct=new URL(location.href);direct.hash=new URLSearchParams({state:selected,...(selectedRule?{rule:selectedRule}:{})}).toString();var project=new URL('../../../../site/index.html',location.href);project.hash=(data.pageRoutes || {})[page.id]+'?'+direct.hash.slice(1);linkDialog.querySelector('#sr-project-link').value=project.href;linkDialog.querySelector('#sr-direct-link').value=direct.href;linkDialog.showModal();linkDialog.querySelector('input').select();};
  var live=document.createElement('p');live.className='sr-live';live.setAttribute('role','status');live.setAttribute('aria-live','polite');header.appendChild(live);
  tabs.onclick=function(e){var b=e.target.closest('[data-state]');if(!b)return;selected=b.dataset.state;selectedRule='';compare=false;localControls.forEach(function(local){local.reset();});view.scrollTop=0;updateHash();draw();tabs.querySelector('[data-state="'+selected+'"]').focus({preventScroll:true});live.textContent='已切换到'+states.find(function(st){return st.id===selected;}).title+'状态，画面与规则已同步。';};
  panel.onclick=function(e){var b=e.target.closest('[data-locate]');if(b)focusRule(interactions.find(function(it){return it.id===b.dataset.locate;}),false);};
  header.querySelector('#sr-compare').onclick=function(){compare=!compare;draw();};
  header.querySelector('#sr-numbers').onchange=function(e){numbered=e.target.checked;positionPins();};
  window.addEventListener('hashchange',function(){var p=new URLSearchParams(location.hash.slice(1)),id=p.get('state');selectedRule=p.get('rule') || '';if(states.some(function(s){return s.id===id;})){selected=id;compare=false;localControls.forEach(function(local){local.reset();});draw();}});
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
