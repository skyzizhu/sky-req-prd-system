const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const root=path.resolve(process.argv[2]);
 const proc=spawn('python3',[path.join(__dirname,'../scripts/edit_project.py'),root,'--version','v1.1']);
 const url=await new Promise((resolve,reject)=>{let s='';proc.stdout.on('data',d=>{s+=d;const m=s.match(/http:\/\/127\.0\.0\.1:\d+\/#token=[\w-]+/);if(m)resolve(m[0]);});proc.once('exit',c=>reject(Error('server '+c)));});
 const browser=await chromium.launch({headless:true}),page=await browser.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(url);await page.locator('#material').selectOption('attachments');
  await page.locator('#attachment-file').setInputFiles({name:'访谈.txt',mimeType:'text/plain',buffer:Buffer.from('用户访谈依据')});
  await page.locator('#attachment-description').fill('订单流程访谈');await page.locator('#attachment-share').check();
  await page.locator('#attachment-upload').click();
  await page.getByRole('status').filter({hasText:'附件已保存到项目'}).waitFor();
  assert.equal(fs.readdirSync(path.join(root,'attachments')).length,1);
  await page.reload();await page.locator('#material').selectOption('attachments');
  const download=page.waitForEvent('download');await page.locator('#attachment-list button').first().click();
  assert.equal(fs.readFileSync(await(await download).path(),'utf8'),'用户访谈依据');
  const base=pathToFileURL(path.join(root,'site/index.html')).href;
  await page.goto(base+'#/v/v1.1/_prd/appendix');await page.locator('.attachment-item').waitFor();
  assert.equal(await page.locator('input[type=file]').count(),0);
  assert.match(await page.locator('.attachment-item').innerText(),/访谈.txt/);
  const exp=page.waitForEvent('download');await page.locator('#standard-prd-export').click();
  const md=fs.readFileSync(await(await exp).path(),'utf8');
  for(const word of ['版本说明和范围','用户与业务流程','数据与埋点','非功能需求','验收与上线条件','里程碑与计划','风险与待决策','访谈.txt'])assert.ok(md.includes(word),word);
  await page.goto(base+'#/v/v1.1/_prd/functions');await page.locator('.prd-requirement').first().waitFor();
  assert.equal(await page.locator('.prd-requirement').count(),3);
  await page.goto(base+'#/v/v1.1/_prd/nonfunctional');await page.locator('.standard-prd').waitFor();
  if(process.argv[3])await page.screenshot({path:process.argv[3],fullPage:true});
  assert.deepEqual(errors,[]);console.log('PASS standard PRD: canonical functional view, chapters/export, real upload/reload/download, static appendix');
 }finally{await browser.close();proc.kill();}
})();
