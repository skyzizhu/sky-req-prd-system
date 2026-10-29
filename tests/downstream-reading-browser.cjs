// Exercise business reading paths in a disposable project, including historical links.
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]),shots=path.resolve(process.argv[3]),repo=path.resolve(__dirname,'..');
 fs.mkdirSync(shots,{recursive:true});
 execFileSync('python3',[path.join(repo,'scripts/create_static_demo.py'),root]);
 const file=path.join(root,'versions/v0.1/content/spec.json'),spec=JSON.parse(fs.readFileSync(file));
 const rules=spec.requirements[0].rule_details,find=id=>rules.find(r=>r.id==='RULE-ORDER-'+id);
 find('CREATE').related_rule_ids=['RULE-ORDER-NAME','RULE-ORDER-SUCCESS','RULE-ORDER-FAILURE'];
 find('NAME').related_rule_ids=['RULE-ORDER-FAILURE']; // duplicate link must appear once
 find('FAILURE').related_rule_ids=['RULE-ORDER-SUBMITTING']; // must not recursively expand
 find('SUCCESS').title='完成 <检查> & 返回';
 spec.interactions.find(i=>i.id==='INT-ORDER-CREATE').rule_ids=['RULE-ORDER-CREATE','RULE-ORDER-NAME'];
 for(const state of spec.pages[0].states)for(const el of state.elements)el.title=el.selector;
 fs.writeFileSync(file,JSON.stringify(spec));execFileSync('python3',[path.join(root,'build.py')]);
 execFileSync('python3',[path.join(repo,'scripts/project.py'),'new-version',root,'--version','v0.2','--from-version','v0.1']);
 const browser=await chromium.launch({headless:true,executablePath:process.env.PW_EXECUTABLE,channel:process.env.PW_CHANNEL || undefined});
 const page=await browser.newPage({viewport:{width:1440,height:980}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=pathToFileURL(path.join(root,'site/index.html')).href;
 async function check(scope){
  await scope.locator('.sr-pin[data-interaction="INT-ORDER-CREATE"]').press('Enter');
  assert.deepEqual(await scope.locator('.sr-focused-rules [data-rule-id]').evaluateAll(es=>es.map(e=>e.dataset.ruleId)),['RULE-ORDER-CREATE','RULE-ORDER-NAME']);
  const links=scope.locator('.sr-related-rules a');assert.equal(await links.count(),2);
  assert.ok((await links.allTextContents()).includes('完成 <检查> & 返回'));
  assert.equal(await scope.locator('.sr-related-rules 检查').count(),0);
  const href=await links.first().getAttribute('href');assert.match(href,/v0.1/);assert.match(href,/rule=RULE-ORDER-SUCCESS/);
  const popupPromise=page.waitForEvent('popup');await links.first().press('Enter');const popup=await popupPromise;
  await popup.locator('[data-rule-id="RULE-ORDER-SUCCESS"]').waitFor();assert.match(popup.url(),/v0.1/);
  assert.match(await popup.locator('.prd-return-source').innerText(),/创建/);await popup.close();
  await scope.locator('[data-state="failed"]').press('Enter');
  assert.equal(await scope.locator('.sr-state-context').isVisible(),true);
  assert.match(await scope.locator('.sr-state-context').innerText(),/允许重试/);
  assert.doesNotMatch(await scope.locator('.sr-state-context').innerText(),/新增显示|不再显示|#failed|#default/);
  assert.ok(await scope.locator('.sr-rules').evaluate(el=>el.querySelector('.sr-state-context').compareDocumentPosition(el.querySelector('.sr-focused-rules'))&Node.DOCUMENT_POSITION_FOLLOWING));
  await scope.locator('#sr-compare').click();await scope.locator('[data-ps-state="success"] .sr-pin').first().press('Enter');
  assert.match(await scope.locator('.sr-state-context').innerText(),/订单创建完成/);
 }
 try{
  await page.goto(pathToFileURL(path.join(root,'versions/v0.1/content/prototype/create-order.html')).href);await check(page);
  await page.screenshot({path:path.join(shots,'standalone.png')});
  await page.goto(base+'#/v/v0.1/prototype/create-order');await check(page.frameLocator('iframe'));
  await page.screenshot({path:path.join(shots,'iframe.png')});
  await page.setViewportSize({width:390,height:844});
  await page.waitForTimeout(250); // reader fits its state picker after the iframe resize
  const frame=page.frameLocator('iframe');assert.ok(await frame.locator('body').evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(shots,'narrow.png'),fullPage:true});
  await page.goto(base+'#/v/v0.1/_prd/scope');
  const link=page.getByRole('link',{name:'创建订单',exact:true});assert.equal(await link.count(),1);
  await link.press('Enter');await page.locator('.prd-requirement').waitFor();assert.match(page.url(),/v0.1.*requirement=FR-ORDER-001/);
  assert.equal(await page.locator('.prd-requirement').count(),1);
  assert.deepEqual(errors,[]);
  console.log('PASS downstream reading: related results exact-version links, unique non-recursive references, escaped titles, state context before rules, no ID-based false diffs, compare/keyboard/narrow, scope-to-function; standalone + iframe');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
