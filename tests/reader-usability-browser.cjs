// Read-only usability paths in isolated authored material; business rules remain unchanged.
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]),shots=path.resolve(process.argv[3]),repo=path.resolve(__dirname,'..');
 fs.mkdirSync(shots,{recursive:true});execFileSync('python3',[path.join(repo,'scripts/create_static_demo.py'),root]);
 const specFile=path.join(root,'versions/v0.1/content/spec.json'),spec=JSON.parse(fs.readFileSync(specFile));
 // Descriptive state labels must remain reachable without shortening or dropping them.
 const namedRule=spec.requirements[0].rule_details.find(r=>r.id==='RULE-ORDER-NAME');
 namedRule.clauses=[{label:'关联恢复',text:'提交失败后参见 RULE-ORDER-FAILURE；未知 RULE-MISSING 保留原文'}];
 spec.pages[0].states.forEach(s=>s.title='订单创建 · '+s.title+'状态及操作说明');fs.writeFileSync(specFile,JSON.stringify(spec));
 execFileSync('python3',[path.join(root,'build.py')]);
 execFileSync('python3',[path.join(repo,'scripts/project.py'),'new-version',root,'--version','v1.0','--from-version','v0.1']);
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined});
 const page=await browser.newPage({viewport:{width:960,height:800}});page.setDefaultTimeout(12000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const direct=pathToFileURL(path.join(root,'versions/v0.1/content/prototype/create-order.html')).href;
 async function check(scope){
  const picker=scope.locator('#sr-state-picker');await picker.waitFor({state:'visible'});
  assert.deepEqual(await picker.locator('option').evaluateAll(nodes=>nodes.map(n=>n.value)),spec.pages[0].states.map(s=>s.id));
  await scope.locator('#default-name').fill('局部交互值');
  await picker.selectOption('failed');
  assert.equal(await scope.locator('.sr-tabs [aria-pressed="true"]').getAttribute('data-state'),'failed');
  assert.equal(await scope.locator('.sr-state:visible').getAttribute('data-ps-state'),'failed');
  assert.equal(await scope.locator('.sr-pin-selected').count(),1);
  assert.match(await scope.locator('.sr-rules').innerText(),/订单创建 · 提交失败/);
  await picker.selectOption('default');assert.equal(await scope.locator('#default-name').inputValue(),'');
  await scope.locator('.sr-tabs [data-state="invalid"]').click();assert.equal(await picker.inputValue(),'invalid');
  await picker.focus();
  assert.equal(await picker.evaluate(el=>el===el.ownerDocument.activeElement),true);
  await scope.locator('.sr-tabs [data-state="submitting"]').press('Enter');
  assert.equal(await picker.inputValue(),'submitting');assert.equal(await scope.locator('.sr-state:visible').getAttribute('data-ps-state'),'submitting');
  await scope.getByRole('button',{name:'展开状态对照'}).click();assert.equal(await scope.locator('.sr-state:visible').count(),5);
  await scope.locator('[data-ps-state="success"] .sr-pin').first().click();assert.equal(await picker.inputValue(),'success');
  await picker.selectOption('submitting');assert.equal(await scope.locator('.sr-state:visible').count(),1);
  assert.equal(await scope.getByRole('button',{name:'展开状态对照'}).count(),1);
 }
 try{
  await page.goto(direct);
  const reference=page.locator('.sr-rule-body a[title="RULE-ORDER-FAILURE"]');
  assert.equal(await reference.count(),1);assert.doesNotMatch(await reference.innerText(),/^RULE-/);
  assert.match(await reference.getAttribute('href'),/v0.1.*requirement=FR-ORDER-001.*rule=RULE-ORDER-FAILURE/);
  assert.match(await page.locator('.sr-rule-body').innerText(),/RULE-MISSING/);
  await page.locator('.sr-card summary').first().click();
  assert.doesNotMatch(await page.locator('.sr-card [data-acceptance-link]').first().innerText(),/AC-ORDER/);
  await check(page);await page.screenshot({path:path.join(shots,'states-direct.png')});
  await page.setViewportSize({width:390,height:844});await page.goto(pathToFileURL(path.join(root,'site/index.html')).href+'#/v/v0.1/prototype/create-order');
  const frame=page.frameLocator('iframe');await frame.locator('#sr-state-picker').waitFor();await check(frame);
  assert.ok(await frame.locator('body').evaluate(el=>el.scrollWidth<=el.clientWidth));
  assert.equal(await frame.locator('.sr-tabs button').count(),5);await page.screenshot({path:path.join(shots,'states-narrow.png')});
  // The link must retain the viewed version even when another version is current.
  const base=pathToFileURL(path.join(root,'site/index.html')).href;
  await page.goto(base+'?preview=usability#/v/v0.1/_prd/functions?requirement=FR-ORDER-001');
  const rule=page.locator('[data-rule-id="RULE-ORDER-NAME"]');await rule.locator('summary').click();
  const links=rule.locator('[data-acceptance-link="AC-ORDER-MAX"]');assert.equal(await links.count(),1);
  const href=await links.getAttribute('href');assert.match(href,/#\/v\/v0.1\/_prd\/functions\?requirement=FR-ORDER-001&section=acceptance&acceptance=AC-ORDER-MAX/);
  await links.press('Enter');await page.locator('[data-acceptance="AC-ORDER-MAX"]').waitFor();
  assert.equal(await page.locator('.prd-ac-fold[open]').count(),1);assert.match(page.url(),/preview=usability#\/v\/v0.1/);
  assert.match(await page.locator('[data-acceptance="AC-ORDER-MAX"]').innerText(),/40字/);
  await page.screenshot({path:path.join(shots,'rule-acceptance.png')});
  await page.setViewportSize({width:1800,height:980});await page.goto(direct);
  assert.equal(await page.locator('.sr-state-picker-label').isVisible(),false);assert.equal(await page.locator('.sr-tabs button').count(),5);
  assert.deepEqual(errors,[]);
  console.log('PASS reader usability: overflow states all reachable, keyboard/tab/picker/compare sync, reset and exact historical acceptance links, no narrow overflow or unnecessary wide picker');
 }catch(error){await page.screenshot({path:path.join(shots,'failure.png')}).catch(()=>{});throw error;}finally{await browser.close();}
})();
