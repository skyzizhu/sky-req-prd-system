const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]),shots=path.resolve(process.argv[3]),repo=path.resolve(__dirname,'..');
 fs.mkdirSync(shots,{recursive:true});execFileSync('python3',[path.join(repo,'scripts/create_static_demo.py'),root]);
 const file=path.join(root,'versions/v0.1/content/spec.json'),spec=JSON.parse(fs.readFileSync(file)),req=spec.requirements[0];
 for(const [id,given,then] of [['READ','服务读取失败','保留当前内容并提供重试'],['ACCESS','记录不存在或无权查看','不展示记录摘要，仅提供返回入口']]){
  const aid='AC-SPECIAL-'+id;req.acceptance.push({id:aid,given,when:'查看当前结果',then,kind:'exception'});
  req.rule_details[0].acceptance_ids.push(aid);
  req.boundary_cases.push({id:'BC-SPECIAL-'+id,kind:'exception',acceptance_ids:[aid],rule_ids:[req.rule_details[0].id],presentation:{mode:'text',reason:'明确的特殊结果'}});
 }
 req.boundary_cases.push({id:'BC-SUPPLEMENT',kind:'exception',input:'保留字面文本 <img src=x onerror=alert(1)>',expected:'不执行标签；保留这项独立补充',acceptance_ids:['AC-SPECIAL-READ','AC-SPECIAL-ACCESS'],rule_ids:[req.rule_details[0].id],presentation:{mode:'text',reason:'独有条件与结果'}});
 fs.writeFileSync(file,JSON.stringify(spec));execFileSync('python3',[path.join(root,'build.py')]);
 execFileSync('python3',[path.join(repo,'scripts/project.py'),'new-version',root,'--version','v1.0','--from-version','v0.1']);
 const b=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined});
 const page=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(12000);
 const url=pathToFileURL(path.join(root,'site/index.html')).href+'#/v/v0.1/_prd/functions?requirement='+req.id+'&section=cases';
 try{
  await page.goto(url);await page.locator('.prd-boundaries[open]').waitFor();
  const row=page.locator('[data-case-id="BC-SPECIAL-READ"]'),access=page.locator('[data-case-id="BC-SPECIAL-ACCESS"]');
  assert.match(await row.innerText(),/服务读取失败/);assert.match(await row.innerText(),/保留当前内容并提供重试/);
  assert.doesNotMatch(await row.innerText(),/BC-SPECIAL|AC-SPECIAL|独有补充/);
  assert.match(await access.innerText(),/不展示记录摘要，仅提供返回入口/);
  assert.equal(await row.locator('td').count(),3);
  await row.getByText('定位信息',{exact:true}).click();assert.match(await row.innerText(),/BC-SPECIAL-READ/);
  await row.getByText('定位信息',{exact:true}).click();
  const supplement=page.locator('[data-case-id="BC-SUPPLEMENT"]');
  assert.match(await supplement.innerText(),/<img src=x onerror=alert\(1\)>/);assert.equal(await supplement.locator('img').count(),0);
  assert.equal(await supplement.getByRole('link').count(),2);assert.match(await supplement.innerText(),/不执行标签；保留这项独立补充/);
  await row.getByRole('link',{name:'查看验收：AC-SPECIAL-READ',exact:true}).press('Enter');
  await page.locator('[data-acceptance="AC-SPECIAL-READ"]').waitFor({state:'visible'});assert.match(page.url(),/v0.1/);
  assert.equal(await page.locator('.prd-ac-fold[open]').count(),1);
  // Change the only source; the displayed handling must update without a case copy.
  req.acceptance.find(a=>a.id==='AC-SPECIAL-READ').then='修订后：保留内容，重试前重新读取';
  fs.writeFileSync(file,JSON.stringify(spec));execFileSync('python3',[path.join(root,'build.py')]);
  await page.goto(url);await page.reload();await page.locator('.prd-boundaries[open]').waitFor();assert.match(await row.innerText(),/修订后：保留内容，重试前重新读取/);
  await row.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(shots,'special-cases.png')});
  await page.setViewportSize({width:390,height:844});assert.ok(await page.locator('#content').evaluate(el=>el.scrollWidth<=el.clientWidth));
  assert.ok(await page.locator('.prd-boundaries .prd-boundary-scroll').evaluate(el=>el.scrollWidth>el.clientWidth));
  const download=page.waitForEvent('download');await page.locator('#prd-export').click();const md=fs.readFileSync(await(await download).path(),'utf8');
  assert.ok(md.includes('服务读取失败；查看当前结果](#acceptance-AC-SPECIAL-READ)'));
  assert.equal(md.split('修订后：保留内容，重试前重新读取').length-1,1);
  assert.ok(md.includes('不执行标签；保留这项独立补充'));
  assert.deepEqual(errors,[]);console.log('PASS special cases: human-readable conditions/handling, distinct failures, canonical updates, independent supplement and multiple links, secondary IDs, historical exact acceptance, escaped text, narrow scrolling and nonduplicated export');
 }catch(e){await page.screenshot({path:path.join(shots,'failure.png')});throw e;}finally{await b.close();}
})();
