const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const assert=require('node:assert/strict');
(async()=>{
  const root=path.resolve(process.argv[2]);
  const command=path.join(__dirname,'../scripts/project.py');
  const handoff=r=>execFileSync('python3',[command,'handoff',root,'--revision',r]);
  handoff('r1');
  const file=path.join(root,'versions/v1.1/content/spec.json');
  const spec=JSON.parse(fs.readFileSync(file)); spec.requirements[0].title='第二轮交接标题'; fs.writeFileSync(file,JSON.stringify(spec));
  handoff('r2');
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage(); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  try {
    const base=pathToFileURL(path.join(root,'site/index.html')).href;
    await page.goto(base+'#/v/v1.1.r1/_changes/report');
    assert.match(await page.locator('#version-context').innerText(),/历史交接/);
    await page.locator('#content').getByRole('link',{name:'订单列表',exact:true}).click();
    assert.match(await page.locator('iframe').getAttribute('src'),/v1.1.r1/);
    await page.frameLocator('iframe').locator('#create').click();
    await page.frameLocator('iframe').locator('#create-dialog').waitFor({state:'visible'});
    await page.goto(base+'#/v/v1.1.r2/requirements/spec');
    assert.match(await page.locator('#version-context').innerText(),/当前开发依据/);
    assert.match(await page.locator('#content').innerText(),/第二轮交接标题/);
    await page.goto(base+'#/v/v1.1.r1/requirements/spec');
    assert.doesNotMatch(await page.locator('#content').innerText(),/第二轮交接标题/);
    assert.deepEqual(errors,[]);
    console.log('PASS: r1 deep link, old prototype interaction, r2 current basis, independent requirement snapshots');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
