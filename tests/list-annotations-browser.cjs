// Repeated rows reuse semantic annotations; state/permission differences remain separate.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const fs=require('fs'),os=require('os'),path=require('path'),{pathToFileURL}=require('url');
(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'prd-list-pins-')),out=process.argv[3] || temp;fs.mkdirSync(out,{recursive:true});
 const asset=name=>pathToFileURL(path.join(__dirname,'../assets',name)).href;
 const interactions=[
  {id:'INT-NAME',selector:'#default-name-heading',title:'名称列（全部行）',rule_ids:['NAME'],state_ids:['default','viewer']},
  {id:'INT-STATE',selector:'#default-state-heading',title:'状态列（全部行）',rule_ids:['STATE'],state_ids:['default','viewer']},
  {id:'INT-EDIT',selector:'#default-a-edit',title:'编辑（启用行）',rule_ids:['EDIT','STATE'],state_ids:['default']},
  {id:'INT-LOCKED',selector:'#default-c-edit',title:'停用行的禁用操作',rule_ids:['LOCKED'],state_ids:['default']},
  {id:'INT-VIEWER',selector:'#viewer-a-edit',title:'普通成员仅查看',rule_ids:['VIEWER','STATE'],state_ids:['viewer']}
 ].map(i=>({...i,page:'tags'}));
 const ruleText={NAME:'完整名称换行；此规则适用于全部标签行。',STATE:'显示启用或停用，不仅靠颜色表达。',EDIT:'编辑被点击行的稳定编号，其他启用行行为相同。',LOCKED:'停用行编辑禁用；说明标签已停用。',VIEWER:'仅管理员可编辑；普通成员只读，全部行按钮禁用。'};
 const states=['default','viewer'].map(id=>({id,title:id==='default'?'管理员列表':'普通成员只读',summary:'同列和同类操作只标一次，差异规则保留。'}));
 const body=states.map(s=>`<section data-ps-state="${s.id}"><h2>${s.title}</h2><div class="sr-snapshot"><div class="table-wrap"><table><thead><tr><th><span id="${s.id}-name-heading" data-rule-ref="INT-NAME">名称</span></th><th><span id="${s.id}-state-heading" data-rule-ref="INT-STATE">状态</span></th><th>操作</th></tr></thead><tbody>${['a','b','c'].map((row,index)=>{const ref=s.id==='viewer'?'INT-VIEWER':row==='c'?'INT-LOCKED':'INT-EDIT';return `<tr><td><span id="${s.id}-${row}-name" data-rule-ref="INT-NAME">${['重点客户','试用客户','旧活动客户'][index]}</span></td><td><span id="${s.id}-${row}-state" data-rule-ref="INT-STATE">${row==='c'?'停用':'启用'}</span></td><td><button id="${s.id}-${row}-edit" data-rule-ref="${ref}" type="button" ${row==='c'||s.id==='viewer'?'disabled':''}>编辑</button>${row==='c'||s.id==='viewer'?'<small>'+ (s.id==='viewer'?'仅管理员可操作':'标签已停用')+'</small>':''}</td></tr>`;}).join('')}</tbody></table></div></div></section>`).join('');
 fs.writeFileSync(path.join(temp,'spec.js'),'window.PS_SPEC='+JSON.stringify({schema_version:2,projectName:'重复列表标注',version:'QA',spec:{requirements:[{id:'FR',rule_details:Object.entries(ruleText).map(([id,statement])=>({id,title:id,statement}))}],pages:[{id:'tags',title:'列表标注去重',requirement_ids:['FR'],states}],interactions}})+';');
 // Hostile product button dimensions reproduce oversized oval annotation buttons.
 fs.writeFileSync(path.join(temp,'page.css'),'button{min-height:44px;padding:8px 14px;line-height:1.8;font-size:16px}table{width:100%;border-collapse:collapse;min-width:550px}th,td{text-align:left;padding:12px 30px;border-bottom:1px solid #ddd;width:33.3%}td span,th span{display:block}small{display:block;font-size:11px;color:#666}.table-wrap{padding:12px;overflow:auto}');
 fs.writeFileSync(path.join(temp,'index.html'),`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="${asset('prototype-runtime.css')}"><link rel="stylesheet" href="page.css"><body data-page-id="tags" data-prototype-mode="static"><main>${body}</main><script src="spec.js"></script><script src="${asset('prototype-runtime.js')}"></script></body></html>`);
 fs.writeFileSync(path.join(temp,'frame.html'),`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><iframe src="index.html" style="border:0;width:100%;height:96vh" title="列表原型"></iframe>`);
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined}),page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 async function check(scope){
  await scope.locator('.sr-pin-selected').waitFor();assert.equal(await scope.locator('.sr-state:visible .sr-pin').count(),4);
  assert.equal(await scope.locator('.sr-state:visible tbody tr').count(),3);
  const name=scope.locator('.sr-pin[data-interaction="INT-NAME"]');await name.press('Enter');assert.equal(await scope.locator('#default-name-heading').evaluate(el=>el.classList.contains('sr-highlight')),true);
  assert.match(await scope.locator('.sr-rules').innerText(),/全部标签行/);
  assert.equal(await scope.locator('#default-b-name').evaluate(el=>el.parentElement.classList.contains('sr-annotation-anchor')),false);
  const pins=await scope.locator('.sr-state:visible .sr-pin').evaluateAll(ns=>ns.map(n=>({w:n.getBoundingClientRect().width,h:n.getBoundingClientRect().height})));assert.ok(pins.every(p=>p.w===20&&p.h===20),JSON.stringify(pins));
  const before=await scope.locator('.sr-pin-selected').getAttribute('data-interaction');await scope.locator('#default-b-edit').click();assert.equal(await scope.locator('.sr-pin-selected').getAttribute('data-interaction'),before);
  await scope.locator('.sr-pin[data-interaction="INT-LOCKED"]').press('Enter');assert.match(await scope.locator('.sr-rules').innerText(),/停用行编辑禁用/);assert.equal(await scope.locator('#default-c-edit').isDisabled(),true);
  const overlap=await scope.locator('.sr-state:visible .sr-pin').evaluateAll(ns=>ns.flatMap(n=>[...n.ownerDocument.querySelectorAll('.sr-state:not([hidden]) .sr-snapshot button')].filter(el=>{const a=n.getBoundingClientRect(),b=el.getBoundingClientRect();return Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top);})));assert.equal(overlap.length,0);
  await scope.locator('.sr-tabs [data-state=viewer]').press('Enter');assert.equal(await scope.locator('.sr-state:visible .sr-pin').count(),3);assert.equal(await scope.locator('.sr-state:visible tbody button:disabled').count(),3);
  await scope.locator('.sr-pin[data-interaction="INT-NAME"]').press('Enter');assert.equal(await scope.locator('#viewer-name-heading').evaluate(el=>el.classList.contains('sr-highlight')),true);
  await scope.locator('#sr-compare').click();assert.equal(await scope.locator('.sr-state:visible').count(),2);assert.equal(await scope.locator('.sr-pin').count(),7);
  await scope.locator('[data-ps-state=viewer] .sr-pin[data-interaction=INT-STATE]').press('Enter');
  assert.equal(await scope.locator('.sr-rules [data-locate=INT-EDIT]').count(),0);
  await scope.locator('[data-ps-state=default] .sr-pin[data-interaction=INT-STATE]').press('Enter');
  assert.equal(await scope.locator('.sr-rules [data-locate=INT-VIEWER]').count(),0);
  await scope.locator('.sr-tabs [data-state=default]').click();
 }
 try{
  await page.goto(pathToFileURL(path.join(temp,'index.html')).href);await check(page);await page.screenshot({path:path.join(out,'list-annotations.png')});
  await page.locator('#default-a-edit').evaluate(el=>el.closest('tr').hidden=true);
  await page.evaluate(()=>dispatchEvent(new Event('resize')));
  await page.locator('.sr-pin[data-interaction=INT-EDIT]').press('Enter');
  assert.equal(await page.locator('#default-b-edit').evaluate(el=>el.classList.contains('sr-highlight')),true);
  assert.equal(await page.locator('#default-b-edit').evaluate(el=>el.parentElement.classList.contains('sr-annotation-anchor')),true);
  await page.goto(pathToFileURL(path.join(temp,'frame.html')).href);await check(page.frameLocator('iframe'));
  await page.setViewportSize({width:390,height:844});await page.goto(pathToFileURL(path.join(temp,'index.html')).href);await page.locator('.sr-pin-selected').waitFor();assert.equal(await page.locator('.sr-state:visible tbody tr').count(),3);assert.ok(await page.locator('body').evaluate(el=>el.scrollWidth<=el.clientWidth));
  const wrap=page.locator('.sr-state:visible .table-wrap');
  await wrap.evaluate(el=>{el.scrollLeft=el.scrollWidth;});
  await page.waitForFunction(()=>!document.querySelector('.sr-state:not([hidden]) .sr-pin[data-interaction="INT-NAME"]'));
  const editPin=page.locator('.sr-state:visible .sr-pin[data-interaction=INT-EDIT]');await editPin.waitFor();
  assert.ok(await editPin.evaluate(pin=>{const target=document.querySelector('#default-a-edit'),a=pin.getBoundingClientRect(),b=target.getBoundingClientRect();return Math.abs(a.right+4-b.left)<2;}));
  assert.deepEqual(errors,[]);console.log('PASS list annotations: shared column/actions, retained disabled/permission differences, complete rows, 20px round pins despite 44px product button min-height, keyboard, compare, iframe and narrow');
 }finally{await browser.close();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
