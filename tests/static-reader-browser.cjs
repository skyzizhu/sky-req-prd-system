// Synthetic preview: reading never requires a mode switch or opening a panel.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined});
 const page=await browser.newPage({viewport:{width:1440,height:980}});
 const root=path.resolve(process.argv[2]),shots=path.resolve(process.argv[3]);fs.mkdirSync(shots,{recursive:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=pathToFileURL(path.join(root,'site/index.html')).href;
 const direct=pathToFileURL(path.join(root,'versions/v0.1/content/prototype/create-order.html')).href;
 async function checkReader(scope){
   assert.equal(await scope.locator('.sr-state:visible').count(),1);
   assert.match(await scope.locator('.sr-rules').innerText(),/名称必填/);
   assert.equal(await scope.locator('.ps-panel,.ps-tools').count(),0);
   assert.equal(await scope.locator('.sr-pin').count(),2);
   await scope.getByRole('button',{name:'提交失败',exact:true}).click();
   assert.equal(await scope.locator('[data-ps-state="failed"]').isVisible(),true);
   assert.equal(await scope.locator('.sr-tabs button[aria-pressed="true"]:focus').count(),1);
   assert.match(await scope.locator('.sr-rules').innerText(),/失败后保留已填内容/);
   assert.doesNotMatch(await scope.locator('.sr-rules').innerText(),/提交中禁用/);
   await scope.locator('.sr-pin').last().click();
   assert.equal(await scope.locator('.sr-selected').count(),1);
   await scope.locator('[data-locate="INT-ORDER-NAME"]').click();
   assert.equal(await scope.locator('[data-ps-state="failed"] .sr-highlight').count(),1);
   await scope.getByRole('button',{name:'展开状态对照'}).click();
   assert.equal(await scope.locator('.sr-state:visible').count(),5);
   assert.equal(await scope.locator('[data-rule-card="INT-ORDER-NAME"]').count(),1);
   await scope.locator('#sr-numbers').uncheck();assert.equal(await scope.locator('.sr-pin').count(),0);
   await scope.getByRole('button',{name:'返回单状态'}).click();
 }
 try{
   await page.goto(direct);await checkReader(page);
   await page.locator('#sr-numbers').check();await page.screenshot({path:path.join(shots,'static-reader-desktop.png')});
   await page.reload();assert.equal(await page.locator('[data-ps-state="failed"]').isVisible(),true);
   await page.goto(base+'#/v/v0.1/prototype/create-order');
   const frame=page.frameLocator('iframe');await frame.locator('.sr-rules').waitFor();await checkReader(frame);
   await page.goto(base+'#/v/v0.1/_prd/functions');await page.locator('.prd-requirement').waitFor();
   assert.equal(await page.locator('.prd-module').innerText(),'订单管理');
   assert.equal(await page.locator('.prd-rule h4').count(),4);
   assert.match(await page.locator('.prd-requirement').innerText(),/名称必填/);
   assert.equal(await page.locator('.prd-fold[open]').count(),0);
   const download=page.waitForEvent('download');await page.locator('#prd-export').click();
   const md=fs.readFileSync(await(await download).path(),'utf8');
   assert.ok(md.includes('## 订单管理')&&md.includes('### 创建订单')&&md.includes('本次不做')&&md.includes('RULE-ORDER-FAILURE'));
   await page.screenshot({path:path.join(shots,'prd-desktop.png')});
   await page.setViewportSize({width:390,height:844});await page.goto(direct+'#state=failed');
   assert.equal(await page.locator('.sr-rules').isVisible(),true);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.join(shots,'static-reader-mobile.png'),fullPage:true});
   assert.deepEqual(errors,[]);
   console.log('PASS static reader: direct + iframe, default rules, 5 states, filtering, pins both ways, compare, persistence, standard PRD/export, mobile, no JS errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
