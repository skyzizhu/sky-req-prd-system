const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const path=require('node:path'), fs=require('node:fs'), assert=require('node:assert/strict');
(async()=>{
  const root=path.resolve(process.argv[2]), shots=path.resolve(process.argv[3]);fs.mkdirSync(shots,{recursive:true});
  const browser=await chromium.launch({headless:true}), page=await browser.newPage({viewport:{width:1440,height:1000}}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try {
    await page.goto(pathToFileURL(path.join(root,'site/index.html')).href+'#/v/v1.1/_delivery/tasks');
    await page.getByRole('heading',{name:'需求范围与交接',exact:true}).waitFor();
    assert.ok(await page.locator('#delivery-rows [data-task]').count() > 1);
    await page.locator('[data-task="FR-ORDER-002"]').click();
    assert.equal(await page.locator('#delivery-tasks h3').innerText(),'查阅订单');
    assert.equal(await page.locator('#delivery-tasks pre').count(),0);
    await page.screenshot({path:path.join(shots,'scope-table.png'),fullPage:true});
    await page.locator('#delivery-status').selectOption('pending');
    await page.locator('#delivery-query').fill('FR-ORDER-003');
    assert.equal(await page.locator('#delivery-tasks article').count(),1);
    assert.equal(await page.locator('#delivery-rows [data-task]').count(),1);
    assert.equal(await page.locator('#delivery-tasks h3').innerText(),'批量完成订单');
    assert.match(await page.locator('#delivery-tasks').innerText(),/业务规则与实例/);
    const downloadPromise=page.waitForEvent('download'); await page.locator('#delivery-json').click();
    const download=await downloadPromise, stream=await download.createReadStream(); let text=''; for await(const chunk of stream) text+=chunk;
    const pack=JSON.parse(text);assert.equal(pack.tasks.length,1);assert.equal(pack.tasks[0].id,'FR-ORDER-003');assert.equal(pack.tasks[0].confirmation,'pending');
    assert.ok(pack.tasks[0].acceptance.length);
    const mdPromise=page.waitForEvent('download');await page.locator('#delivery-md').click();
    const mdStream=await (await mdPromise).createReadStream();let md='';for await(const chunk of mdStream)md+=chunk;
    assert.match(md,/需求范围与交接/);assert.match(md,/\| 需求名称 \| 编号/);assert.match(md,/批量完成订单/);
    await page.locator('#delivery-query').fill('no-such-requirement');
    assert.equal(await page.locator('#delivery-rows [data-task]').count(),0);
    assert.equal(await page.locator('#delivery-tasks article').count(),0);
    await page.locator('#delivery-query').fill('FR-ORDER-003');
    await page.screenshot({path:path.join(shots,'delivery.png'),fullPage:true});
    await page.locator('#delivery-tasks').getByRole('link',{name:'订单列表',exact:true}).click();
    await page.frameLocator('iframe').locator('#create').waitFor();
    assert.deepEqual(errors,[]);console.log('PASS: delivery filters, pending subrules, filtered JSON export, prototype links; no browser errors');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
