// Exercise copied context against actual rendered sources; never edit a delivered project.
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]),shots=path.resolve(process.argv[3]),repo=path.resolve(__dirname,'..');
 fs.mkdirSync(root,{recursive:true});fs.mkdirSync(shots,{recursive:true});
 const demo=path.join(root,'demo'),versions=path.join(root,'versioned');
 execFileSync('python3',[path.join(repo,'scripts/create_static_demo.py'),demo]);
 execFileSync('python3',[path.join(repo,'tests/fixtures/versioned_project.py'),versions]);
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined});
 const page=await browser.newPage({viewport:{width:1440,height:980}});page.setDefaultTimeout(12000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const project=JSON.parse(fs.readFileSync(path.join(demo,'project.json'))),spec=JSON.parse(fs.readFileSync(path.join(demo,'versions/v0.1/content/spec.json')));
 async function open(expected){await page.locator('#material-context').click();await page.locator('#material-dialog').waitFor();assert.equal(await page.locator('#material-target').inputValue(),expected);return page.locator('#material-copy').inputValue();}
 async function close(){await page.locator('#material-close').click();assert.equal(await page.locator('#material-context').evaluate(el=>el===document.activeElement),true);}
 async function checkPrototype(base){
  await page.goto(base+'?preview=context-audit#/v/v0.1/prototype/create-order');
  const frame=page.frameLocator('iframe');await frame.locator('.sr-pin-selected').waitFor();
  await frame.getByRole('button',{name:'校验失败',exact:true}).click();await frame.locator('.sr-pin[data-interaction="INT-ORDER-INVALID"]').click();
  const context=await open('control:INT-ORDER-INVALID');
  for(const text of [project.id,'版本：v0.1','invalid','INT-ORDER-INVALID','RULE-ORDER-INVALID','versions/v0.1/content/spec.json','当前状态元素：#invalid-focus','页面：创建订单（create-order）'])assert.ok(context.includes(text),text);
  const target=context.split('\n').find(t=>t.startsWith('目标链接：')).slice(5),url=new URL(target);
  assert.equal(url.search,'?preview=context-audit');assert.match(url.hash,/state=invalid&rule=INT-ORDER-INVALID/);
  const control=spec.interactions.find(i=>i.id==='INT-ORDER-INVALID');assert.ok(context.includes('源选择器：'+control.selector));
  await page.locator('#material-target').selectOption('control:INT-ORDER-SUCCESS');
  const changed=await page.locator('#material-copy').inputValue();
  assert.match(changed,/INT-ORDER-SUCCESS/);assert.doesNotMatch(changed,/目标状态：.*invalid|当前状态元素：#invalid-focus/);
  await page.locator('#material-search').fill('NO-SUCH-MATERIAL-XYZ');
  assert.equal(await page.locator('#material-target').inputValue(),'');assert.match(await page.locator('#material-copy').inputValue(),/目标：未选定/);
  await close();
  await frame.getByRole('button',{name:'提交失败',exact:true}).click();await frame.locator('.sr-pin[data-interaction="INT-ORDER-FAILURE"]').click();
  const next=await open('control:INT-ORDER-FAILURE');assert.match(next,/目标状态：.*failed/);assert.doesNotMatch(next,/INT-ORDER-INVALID|当前状态元素：#invalid-focus/);
  await page.locator('#material-select-copy').click();assert.ok(await page.locator('#material-copy').evaluate(el=>el.selectionEnd===el.value.length));
  await page.screenshot({path:path.join(shots,base.startsWith('file:')?'file-context.png':'http-context.png')});await close();
  await page.goto(base+'#/project');assert.match(await open('project'),/来源：project.json/);await close();
  await page.goto(base+'#/v/v0.1/_delivery/tasks');assert.match(await open('delivery'),/spec.json \/ project.json/);await close();
  await page.goto(base+'#/v/v0.1/_outcomes/results');assert.match(await open('outcomes'),/来源：outcomes\//);await close();
  await page.goto(base+'#/v/v0.1/_changes/report');assert.match(await open(''),/目标：未选定/);await close();
  await page.goto(base+'#/v/nonexistent/_prd/functions');assert.match(await open(''),/版本状态：不存在/);await close();
 }
 let server;
 try{
  await checkPrototype(pathToFileURL(path.join(demo,'site/index.html')).href);
  server=http.createServer((req,res)=>{let file=path.join(demo,decodeURIComponent(new URL(req.url,'http://localhost').pathname));if(!file.startsWith(demo+path.sep)){res.writeHead(403);return res.end();}try{res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(file));}catch(_){res.writeHead(404);res.end();}});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));await checkPrototype('http://127.0.0.1:'+server.address().port+'/site/index.html');
  const vb=pathToFileURL(path.join(versions,'site/index.html')).href;
  await page.goto(vb+'?preview=separate-artboards#/v/v1.0/_prd/functions?requirement=FR-ORDER-002');await page.locator('.prd-requirement').first().waitFor();
  assert.match(await open('req:FR-ORDER-002'),/版本：v1.0\n版本状态：released/);await close();
  await page.getByRole('button',{name:'交给 Agent 修改此需求',exact:true}).click();
  const text=await page.locator('#prd-edit-context textarea').inputValue(),link=text.split('\n').find(l=>l.startsWith('页面入口：')).slice(5),target=new URL(link);
  assert.equal(target.search,'?preview=separate-artboards');assert.equal(target.hash,'#/v/v1.0/_prd/functions?requirement=FR-ORDER-002');
  assert.match(text,/来源：versions\/v1.0\/content\/spec.json/);assert.match(text,/不自动转到其他版本/);
  await page.locator('#prd-edit-context button').click();await page.goto(link);await page.locator('.prd-requirement').first().waitFor();assert.equal(await page.locator('.prd-requirement').count(),1);
  await page.goto(vb+'#/v/v1.1/_prd/functions');await page.locator('.prd-requirement').first().waitFor();
  await page.locator('#prd-toc button[data-jump="FR-ORDER-003"]').click();
  assert.match(await open('req:FR-ORDER-003'),/版本：v1.1/);await close();
  await page.goto(vb+'#/v/v1.1/_prd/functions?requirement=FR-ORDER-001&acceptance=AC-ORDER-001');await page.locator('.prd-requirement').first().waitFor();
  assert.match(await open('item:AC-ORDER-001'),/所属需求：FR-ORDER-001/);await close();
  await page.setViewportSize({width:390,height:844});await open('item:AC-ORDER-001');
  const box=await page.locator('#material-dialog').boundingBox();assert.ok(box.x>=0 && box.x+box.width<=391);await page.screenshot({path:path.join(shots,'narrow-context.png')});await close();
  // Missing/older frame runtime must explicitly fall back to the page, not stale hash IDs.
  await page.route('**/prototype-runtime.js',r=>r.fulfill({body:'',contentType:'text/javascript'}));
  await page.goto(pathToFileURL(path.join(demo,'site/index.html')).href+'#/v/v0.1/prototype/create-order?state=invalid&rule=INT-ORDER-INVALID');await page.frameLocator('iframe').locator('#default-name').waitFor();
  assert.match(await open('page:create-order'),/未读取到当前原型标注，仅定位页面/);await close();
  assert.deepEqual(errors,[]);
  console.log('PASS maintenance context: live controls/state/rules, scoped sources, file/HTTP, manual targets, empty results, derived views, frozen/active requirements, preview links, keyboard and narrow screen, missing-runtime fallback');
 }catch(error){await page.screenshot({path:path.join(shots,'failure.png')}).catch(()=>{});throw error;}
 finally{await browser.close();if(server)await new Promise(resolve=>server.close(resolve));}
})();
