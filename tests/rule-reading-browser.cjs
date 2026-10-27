// Canonical rule navigation and search in an isolated two-version fixture.
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]),shots=path.resolve(process.argv[3]),repo=path.resolve(__dirname,'..');
 fs.mkdirSync(shots,{recursive:true});
 execFileSync('python3',[path.join(repo,'tests/fixtures/versioned_project.py'),root]);
 const file=path.join(root,'versions/v1.1/content/spec.json'),spec=JSON.parse(fs.readFileSync(file));
 const create=spec.requirements.find(r=>r.id==='FR-ORDER-001'),read=spec.requirements.find(r=>r.id==='FR-ORDER-002');
 const rule=create.rule_details[0];rule.title='名称输入';
 rule.clauses=[{label:'关联处理',text:'提交后的处理见 RULE-BATCH-COMPLETE；RULE-BATCH-COMPLETE-UNKNOWN 不是同一编号。'},
               {label:'输入示例',text:'保留文字 <demo> & 不执行 HTML。'}];
 rule.related_rule_ids=['RULE-BATCH-COMPLETE'];read.shared_rule_ids=[rule.id];
 fs.writeFileSync(file,JSON.stringify(spec));execFileSync('python3',[path.join(root,'build.py')]);
 execFileSync('python3',[path.join(repo,'scripts/project.py'),'new-version',root,'--version','v2.0','--from-version','v1.1']);
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(12000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=pathToFileURL(path.join(root,'site/index.html')).href+'?preview=reading';
 async function open(query=''){await page.goto(base+'#/v/v1.1/_prd/functions'+query);await page.locator('.prd-reader').waitFor();}
 try{
  await open('?requirement=FR-ORDER-002');
  assert.equal(await page.locator('.prd-rule-item').count(),0); // shared rule is a reference, not another body

  await page.locator('.prd-shared-rules').waitFor();
  await page.locator('.prd-shared-rules a').press('Enter');
  const name=page.locator('[data-rule-id="RULE-NAME-INPUT"]');await name.waitFor();
  await page.waitForFunction(()=>document.activeElement?.dataset.ruleId==='RULE-NAME-INPUT');
  assert.match(page.url(),/v1.1.*rule=RULE-NAME-INPUT/);
  assert.match(await page.locator('.prd-return-source').innerText(),/查阅订单/);
  assert.equal(await name.locator('demo').count(),0);
  assert.match(await name.locator('.prd-rule-clauses').innerText(),/<demo> &/);
  assert.equal(await name.locator('.prd-rule-clauses a').count(),1); // no prefix match on UNKNOWN
  await name.locator('.prd-related-rules a').click();
  const batch=page.locator('[data-rule-id="RULE-BATCH-COMPLETE"]');await batch.waitFor();
  await page.waitForFunction(()=>document.activeElement?.dataset.ruleId==='RULE-BATCH-COMPLETE');
  assert.match(page.url(),/v1.1/);assert.match(await page.locator('.prd-return-source').innerText(),/名称输入/);
  await page.locator('.prd-return-source a').click();await name.waitFor();
  await page.waitForFunction(()=>document.activeElement?.dataset.ruleId==='RULE-NAME-INPUT');
  await page.locator('#material-context').click();await page.locator('#material-dialog').waitFor({state:'visible'});
  assert.match(await page.locator('#material-copy').inputValue(),/定位键：item:RULE-NAME-INPUT/);
  await page.locator('#material-close').click();
  await page.locator('#prd-search').fill('RULE-NAME-INPUT');
  assert.equal(await page.locator('.prd-requirement').count(),1);assert.equal(await page.locator('.prd-search-match').count(),1);
  assert.equal(await page.locator('.prd-return-source').count(),0); // input clears stale navigation context
  assert.ok(await name.locator('mark').count());
  await page.locator('#prd-search').fill('保留文字');
  assert.equal(await page.locator('.prd-search-results button').count(),1);
  await page.locator('[data-jump-rule="RULE-NAME-INPUT"]').press('Enter');
  assert.equal(await name.evaluate(el=>el===document.activeElement),true);
  assert.ok(await name.locator('.prd-rule-clauses mark').count());
  await page.screenshot({path:path.join(shots,'rule-search.png')});
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.locator('#content').evaluate(el=>el.scrollWidth<=el.clientWidth));
  await page.screenshot({path:path.join(shots,'rule-search-narrow.png')});
  const download=page.waitForEvent('download');await page.locator('#prd-export').click();
  const md=fs.readFileSync(await(await download).path(),'utf8');
  assert.ok(md.includes('适用的共用规则：')&&md.includes('](#rule-RULE-BATCH-COMPLETE)'));
  await page.goto(base+'#/v/v1.0/_prd/functions?rule=RULE-NAME-INPUT');await page.locator('.prd-target-notice').waitFor();
  assert.equal(await page.locator('.prd-rule-target').count(),0);assert.match(page.url(),/v1.0/);
  assert.deepEqual(errors,[]);
  console.log('PASS rule reading: shared/related single-source links, historical deep links, return source, exact rule Agent context, escaped text, no prefix mislink, search highlight/jump/keyboard/narrow, export and missing-target notice');
 }catch(e){await page.screenshot({path:path.join(shots,'failure.png')});throw e;}finally{await browser.close();}
})();
