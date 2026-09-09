const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path'), fs=require('node:fs'), assert=require('node:assert/strict');
(async()=>{
  const root=path.resolve(process.argv[2]), shots=path.resolve(process.argv[3]);fs.mkdirSync(shots,{recursive:true});
  const browser=await chromium.launch({headless:true}), page=await browser.newPage({viewport:{width:1440,height:1000}}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try {
    await page.goto(pathToFileURL(path.join(root,'site/index.html')).href+'#/v/v1.1/_delivery/tasks');
    await page.getByRole('heading',{name:'开发交接',exact:true}).waitFor();
    await page.locator('#delivery-status').selectOption('pending');
    await page.locator('#delivery-query').fill('FR-ORDER-003');
    assert.equal(await page.locator('#delivery-tasks article').count(),1);
    const downloadPromise=page.waitForEvent('download'); await page.locator('#delivery-json').click();
    const download=await downloadPromise, stream=await download.createReadStream(); let text=''; for await(const chunk of stream) text+=chunk;
    const pack=JSON.parse(text);assert.equal(pack.tasks.length,1);assert.equal(pack.tasks[0].id,'FR-ORDER-003');assert.equal(pack.tasks[0].confirmation,'pending');
    assert.ok(pack.tasks[0].acceptance.length);
    await page.screenshot({path:path.join(shots,'delivery.png'),fullPage:true});
    await page.locator('#delivery-tasks').getByRole('link',{name:'订单列表',exact:true}).click();
    await page.frameLocator('iframe').locator('#create').waitFor();
    assert.deepEqual(errors,[]);console.log('PASS: delivery filters, pending subrules, filtered JSON export, prototype links; no browser errors');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
