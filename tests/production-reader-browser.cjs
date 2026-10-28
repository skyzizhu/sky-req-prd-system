// Production-oriented regressions: native inputs, deterministic initial values and nested page links.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),{pathToFileURL}=require('url'),{execFileSync}=require('child_process');
(async()=>{
 const root=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]),content=path.join(root,'versions/v0.1/content');fs.mkdirSync(out,{recursive:true});
 const asset=n=>pathToFileURL(path.join(__dirname,'../assets',n)).href;
 const pairs=[['first',{defaultValue:'green',options:[{value:'blue',label:'蓝'},{value:'green',label:'绿'}]}],['last',{options:[{value:'blue',label:'蓝'},{value:'green',label:'绿'}],defaultValue:'green'}],['preserved',{options:[{value:'blue',label:'蓝'},{value:'green',label:'绿'}]}]];
 const interactions=pairs.map(([id,properties])=>({id:'INT-'+id,page:'native',selector:'#'+id,title:id,rule_ids:['RULE-CHOICE'],state_ids:['default'],properties}));
 let widgets=pairs.map(([id])=>`<label>${id}<select id="${id}" data-rule-ref="INT-${id}" data-ps-local="select"><option value="green" selected>旧绿</option></select></label>`).join('');
 for(const [type,value] of [['datetime-local','2026-10-28T09:00'],['month','2026-10'],['week','2026-W44']]){
  interactions.push({id:'INT-'+type,page:'native',selector:'#'+type,title:type,rule_ids:['RULE-DATE'],state_ids:['default']});widgets+=`<label>${type}<input id="${type}" type="${type}" value="${value}" data-rule-ref="INT-${type}" data-ps-local="input"></label>`;
 }
 const data={schema_version:2,projectName:'原生控件回归',version:'QA',spec:{requirements:[{id:'FR',rule_details:[{id:'RULE-CHOICE',title:'选择初值',statement:'测试绿色初值与JSON键顺序无关。'},{id:'RULE-DATE',title:'日期时间',statement:'仅本地试填，不提交。'}]}],pages:[{id:'native',title:'原生控件',requirement_ids:['FR'],states:[{id:'default',title:'默认',summary:'固定输入'},{id:'other',title:'其他状态',summary:'用于检查重置'}]}],interactions}};
 const dir=path.join(root,'native-fixture');fs.mkdirSync(dir);fs.writeFileSync(path.join(dir,'data.js'),'window.PS_SPEC='+JSON.stringify(data)+';');
 fs.writeFileSync(path.join(dir,'index.html'),`<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="${asset('prototype-runtime.css')}"><body data-page-id="native" data-prototype-mode="static"><main><section data-ps-state="default"><h2>默认</h2><div class="sr-snapshot" style="padding:20px"><div style="display:grid;gap:18px;max-width:500px">${widgets}</div></div></section><section data-ps-state="other"><h2>其他状态</h2><div class="sr-snapshot">其他画面</div></section></main><script src="data.js"></script><script src="${asset('prototype-runtime.js')}"></script>`);
 // A prototype may live below prototype/screens; all PRD and location links still target the project root.
 const original=path.join(content,'prototype/create-order.html'),nested=path.join(content,'prototype/screens/create-order.html');fs.mkdirSync(path.dirname(nested));fs.writeFileSync(nested,fs.readFileSync(original,'utf8').replaceAll('assets/','../assets/'));fs.unlinkSync(original);
 const manifest=path.join(content,'manifest.json'),m=JSON.parse(fs.readFileSync(manifest));m.modules.flatMap(m=>m.pages).find(p=>p.id==='create-order').file='prototype/screens/create-order.html';fs.writeFileSync(manifest,JSON.stringify(m));execFileSync('python3',[path.join(root,'build.py')]);
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 try{
  await page.goto(pathToFileURL(path.join(dir,'index.html')).href);await page.locator('.sr-pin-selected').waitFor();
  for(const [id] of pairs)assert.equal(await page.locator('#'+id).inputValue(),'green',id);
  await page.locator('#first').selectOption('blue');await page.locator('.sr-tabs [data-state=other]').click();await page.locator('.sr-tabs [data-state=default]').click();assert.equal(await page.locator('#first').inputValue(),'green');
  for(const type of ['datetime-local','month','week']){
   const el=page.locator('#'+type);assert.notEqual(await el.getAttribute('tabindex'),'-1');assert.equal(await el.evaluate(el=>el.dispatchEvent(new InputEvent('beforeinput',{bubbles:true,cancelable:true,inputType:'insertText',data:'2'}))),true);
   await el.click();await el.press('Escape');assert.equal(await el.evaluate(el=>el.ownerDocument.activeElement===el),true);
  }
  await page.goto(pathToFileURL(nested).href);await page.locator('.sr-pin-selected').waitFor();await page.locator('.sr-card summary').first().click();
  const expected=pathToFileURL(path.join(root,'site/index.html')).href,link=page.getByRole('link',{name:'查看 PRD 原文',exact:true});assert.ok((await link.getAttribute('href')).startsWith(expected+'#/v/v0.1/'));
  const popupPromise=page.waitForEvent('popup');await link.click();const popup=await popupPromise;await popup.locator('.prd-feature-title').first().waitFor();await popup.close();
  await page.locator('#sr-link').click();assert.ok((await page.locator('#sr-project-link').inputValue()).startsWith(expected+'#/v/v0.1/prototype/create-order?'));
  await page.locator('.sr-link-dialog button').click();await page.locator('#sr-handoff-toggle').click();assert.ok((await page.getByRole('link',{name:'版本范围',exact:true}).getAttribute('href')).startsWith(expected));
  await page.screenshot({path:path.join(out,'native-and-nested.png')});assert.deepEqual(errors,[]);
  console.log('PASS production reader: option/default key order, preserved value and reset; datetime/month/week local focus/input; nested prototype PRD, project and chapter links');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
