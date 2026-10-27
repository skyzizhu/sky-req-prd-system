/* Portable Agent context; no network, no implicit writes. */
document.addEventListener('DOMContentLoaded',function(){
 'use strict';
 var data=window.__PS_PROJECT,button=document.createElement('button');
 button.type='button';button.id='material-context';button.textContent='定位并交给 Agent';
 document.querySelector('.topbar').appendChild(button);
 var dialog=document.createElement('dialog');dialog.id='material-dialog';
 dialog.innerHTML='<h2>局部修改物料</h2><p>选择目标，复制上下文并附上修改要求。不会重新生成项目，也不会自动发送给 Agent。</p><label>检索<input id="material-search"></label><label>目标物料<select id="material-target"></select></label><textarea id="material-copy" aria-label="物料修改上下文" readonly rows="12"></textarea><button id="material-select-copy">选中上下文</button><button id="material-close">关闭</button>';
 document.body.appendChild(dialog);
 var items=[],vid,bundle,view={},serial=0,lastTarget=null;
 var search=dialog.querySelector('input'),select=dialog.querySelector('select'),copy=dialog.querySelector('textarea');
 // Keep an explicit reading target when returning to the top toolbar scrolls the page.
 function remember(event){
  var el=event.target,reader=el.closest('.prd-reader');if(!reader)return;
  var jump=el.closest('#prd-toc [data-jump]'),req=el.closest('.prd-requirement'),rule=el.closest('[data-rule-id]');
  if(jump || req)lastTarget={reader:reader,key:rule?'item:'+rule.dataset.ruleId:'req:'+(jump?jump.dataset.jump:req.id.slice(4))};
 }
 document.addEventListener('click',remember);document.addEventListener('focusin',remember);
 document.addEventListener('input',function(event){if(event.target.matches('#prd-search,#prd-page'))lastTarget=null;});
 function route(){
  var hash=location.hash.slice(2),split=hash.indexOf('?'),parts=[];
  try{parts=(split<0?hash:hash.slice(0,split)).split('/').map(decodeURIComponent);}catch(_){}
  return {parts:parts,query:new URLSearchParams(split<0?'':hash.slice(split+1))};
 }
 function manifestPage(id){
  var result;
  ((bundle.manifest || {}).modules || []).forEach(function(m){(m.pages || []).forEach(function(p){if(p.id===id)result={module:m.id,page:p};});});
  return result;
 }
 function targetLink(page,query){var url=new URL(location.href);url.hash='/v/'+encodeURIComponent(vid)+'/'+page+(query && query.toString()?'?'+query:'');return url.href;}
 function readSelection(frame,pid){
  if(!frame || !frame.contentWindow)return Promise.resolve(null);
  return new Promise(function(resolve){
   var request='material-'+Date.now()+'-'+(++serial),timer;
   function finish(value){clearTimeout(timer);window.removeEventListener('message',receive);resolve(value);}
   function receive(event){
    var msg=event.data;
    if(event.source!==frame.contentWindow || !msg || msg.type!=='ps-maintenance-context' || msg.request!==request)return;
    if(msg.project!==data.project.id || msg.version!==vid || msg.page!==pid)return;
    finish(msg);
   }
   window.addEventListener('message',receive);timer=setTimeout(function(){finish(null);},700);
   frame.contentWindow.postMessage({type:'ps-maintenance-context-request',request:request},'*');
  });
 }
 function update(){
  var item=items.find(function(i){return i.key===select.value;}),spec=bundle.spec || {},lines=[
   '请按轻量维护模式局部修改，不运行整套生成流程。',
   '项目：'+data.project.name+'（'+data.project.id+'）','版本：'+vid,
   '版本状态：'+((data.project.versions.find(function(v){return v.id===vid;}) || {}).status || '不存在'),
   '当前链接：'+view.href,'当前视图：'+view.title];
  if(item){
   var rootSource=['metadata','derived','ledger','attachment'].includes(item.kind);
   lines.push('目标：'+item.title,'定位键：'+item.key,'来源：'+(rootSource?item.source:'versions/'+vid+'/content/'+item.source));
   if(item.kind==='interaction'){
    var control=(spec.interactions || []).find(function(i){return i.id===item.id;});
    if(control){
     var pg=(spec.pages || []).find(function(p){return p.id===control.page;}),mp=manifestPage(control.page),query=new URLSearchParams();
     lines.push('页面：'+(pg?pg.title+'（'+pg.id+'）':control.page),'控件编号：'+control.id,'源选择器：'+control.selector,
      '关联需求：'+(control.requirement_ids || []).join('、'),'关联规则：'+(control.rule_ids || []).join('、'));
     var live=view.selection,st=live && live.page===control.page && (pg && pg.states || []).find(function(s){return s.id===live.state;});
     if(st && (!control.state_ids || !control.state_ids.length || control.state_ids.includes(st.id))){
      query.set('state',st.id);lines.push('目标状态：'+st.title+'（'+st.id+'）');
      if(live.interaction===control.id && live.selector)lines.push('当前状态元素：'+live.selector);
     }else if(control.state_ids && control.state_ids.length)lines.push('适用状态：'+control.state_ids.join('、'));
     if(control.properties && Object.keys(control.properties).length)lines.push('已登记控件属性：'+JSON.stringify(control.properties));
     query.set('rule',control.id);
     if(mp)lines.push('目标链接：'+targetLink(encodeURIComponent(mp.module)+'/'+encodeURIComponent(control.page),query));
    }
   }else if(item.kind==='requirement' || item.requirement){
    var req=item.requirement || item.id;lines.push('所属需求：'+req);
    var q=new URLSearchParams({requirement:req});if(item.kind==='acceptance')q.set('acceptance',item.id);
    lines.push('目标链接：'+targetLink('_prd/functions',q));
   }else if(item.kind==='page' && view.selection && item.page===view.selection.page){
    var page=(spec.pages || []).find(function(p){return p.id===item.page;}),state=page && (page.states || []).find(function(s){return s.id===view.selection.state;});
    if(state)lines.push('查看状态：'+state.title+'（'+state.id+'）');
   }
  }else lines.push('目标：未选定，请选择具体物料后补充修改要求；不自动选择其他条目。');
  if(view.note)lines.push('定位说明：'+view.note);
  lines.push('先找到本地源目录，核对项目标识、版本状态和修订指纹；冻结版本不可覆盖，不能自动转到其他版本。只修改目标及必要关联。','我的修改要求：');
  copy.value=lines.join('\n');
 }
 function filter(preferred){
  var key=typeof preferred==='string'?preferred:select.value,q=search.value.toLowerCase();select.replaceChildren();
  select.add(new Option('请选择具体物料',''));
  items.filter(function(i){return JSON.stringify(i).toLowerCase().includes(q);}).forEach(function(i){select.add(new Option(i.title+' · '+i.key,i.key));});
  select.value=Array.from(select.options).some(function(o){return o.value===key;})?key:'';update();
 }
 button.onclick=async function(){
  button.disabled=true;
  try{
   var parsed=route(),parts=parsed.parts,query=parsed.query,key='',href=location.href;
   vid=parts[0]==='v'?parts[1]:data.project.current_version;bundle=data.versions[vid] || {};items=bundle.material_index || [];
   view={href:href,title:parts.join('/'),selection:null,note:''};
   if(parts[0]==='project' || !parts[0]){key='project';view.title='项目总览与版本计划';}
   else if(parts[2]==='_delivery'){key='delivery';view.title='交付清单';}
   else if(parts[2]==='_outcomes'){key='outcomes';view.title='验收结果与上线复盘';}
   else if(parts[2]==='_changes'){view.title='版本变更与待确认';view.note='此视图由当前版本与基线生成，请选择具体源需求或文档，不直接修改汇总HTML。';}
   else if(parts[2]==='_prd'){
    var chapter=(bundle.prd_sections || []).find(function(s){return s.id===parts[3];});
    if(chapter){
     view.title=chapter.title;
     if(parts[3]==='functions'){
      var acceptance=query.get('acceptance'),rule=query.get('rule'),active=document.querySelector('#prd-toc button.on'),rid=active && active.dataset.jump;
      if(lastTarget && lastTarget.reader===document.querySelector('.prd-reader') && items.some(function(i){return i.key===lastTarget.key;}))key=lastTarget.key;
      else if(rule && items.some(function(i){return i.key==='item:'+rule;}))key='item:'+rule;
      else if(acceptance && items.some(function(i){return i.key==='item:'+acceptance;}))key='item:'+acceptance;
      else if(rid)key='req:'+rid;
      else key='doc:spec.json';
     }else if(chapter.sources.length===1)key='doc:'+chapter.sources[0];
     else view.note='本章节由多个来源生成：'+chapter.sources.join('、')+'。请选择要修改的具体源物料。';
    }
   }else{
    var mp=manifestPage(parts[3]);
    if(mp && mp.module===parts[2]){
     key='page:'+mp.page.id;view.title=mp.page.title;
     if(mp.page.type==='prototype'){
      var live=await readSelection(document.querySelector('#content iframe'),mp.page.id),pg=((bundle.spec || {}).pages || []).find(function(p){return p.id===mp.page.id;});
      if(live && pg && (pg.states || []).some(function(s){return s.id===live.state;})){
       view.selection=live;
       var control=((bundle.spec || {}).interactions || []).find(function(i){return i.id===live.interaction && i.page===mp.page.id && (!i.state_ids || !i.state_ids.length || i.state_ids.includes(live.state));});
       if(control)key='control:'+control.id;
       if(live.compare)view.note='当前为状态对照，定位到选中标注所在状态；跨状态改动请说明适用范围。';
      }else view.note='未读取到当前原型标注，仅定位页面；请补充状态、控件名称或编号，不从旧链接猜测当前选择。';
     }
    }
   }
   if(location.href!==href)return;
   search.value='';filter(key);dialog.showModal();
  }finally{button.disabled=false;}
 };
 search.oninput=function(){filter();};select.onchange=update;
 dialog.querySelector('#material-select-copy').onclick=function(){copy.focus();copy.select();};
 dialog.querySelector('#material-close').onclick=function(){dialog.close();button.focus();};
});
