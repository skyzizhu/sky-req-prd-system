// Run against an isolated fixture; never submit a real product operation.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path'),fs=require('node:fs'),os=require('node:os');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined});
 const page=await browser.newPage({viewport:{width:1280,height:720}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const direct=pathToFileURL(path.join(__dirname,'fixtures/local-controls.html')).href;
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'ps-local-frame-'));
 fs.writeFileSync(path.join(temp,'frame.html'),'<iframe title="控件交互校对" src="'+direct+'" style="width:100%;height:96vh;border:0"></iframe>');
 const rule=scope=>scope.locator('.sr-pin-selected').getAttribute('data-interaction');
 const overlaps=scope=> scope.locator('.sr-pin').evaluateAll(pins=>{
     const doc=pins[0].ownerDocument,targets=[...doc.querySelectorAll('.sr-state:not([hidden]) .sr-snapshot :is(input,select,textarea,button,label,summary)')].filter(e=>e.getClientRects().length);
     return pins.flatMap(pin=>targets.filter(el=>{const a=pin.getBoundingClientRect(),b=el.getBoundingClientRect();return Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top);}).map(el=>el.id||el.tagName));
   });
 async function check(scope){
   assert.equal(await scope.locator('.sr-tabs button').count(),2);
   assert.equal(await rule(scope),'INT-SESSION');
   await scope.locator('#default-session').selectOption('s3');
   await scope.locator('#default-online').click();
   assert.equal(await scope.locator('#default-email-region').isVisible(),true);
   assert.equal(await rule(scope),'INT-SESSION');
   await scope.locator('#default-email').fill('reader@example.com');
   await scope.locator('#default-onsite').click();
   assert.equal(await scope.locator('#default-email-region').isVisible(),false);
   assert.equal(await scope.locator('#default-email').inputValue(),'');
   await scope.locator('#default-support-switch').click();
   await scope.locator('#default-part-1').click();await scope.locator('#default-part-2').click();
   assert.deepEqual(await overlaps(scope),[]);
   await scope.locator('#default-part-3').click();
   assert.equal(await scope.locator('#default-parts input:checked').count(),2);
   assert.equal(await scope.locator('#default-limit').isVisible(),true);
   assert.equal(await rule(scope),'INT-SESSION');
   const partPin=scope.locator('.sr-pin[data-interaction="INT-PARTS"]');
   await partPin.focus();
   await partPin.evaluate(el=>el.ownerDocument.defaultView.dispatchEvent(new Event('resize')));
   assert.equal(await partPin.evaluate(el=>el===el.ownerDocument.activeElement),true);
   await partPin.press('Enter');
   assert.equal(await rule(scope),'INT-PARTS');
   assert.equal(await scope.locator('#default-parts input:checked').count(),2);
   assert.equal(await scope.locator('#default-support-switch').isChecked(),true);
   assert.deepEqual(await overlaps(scope),[]);
   await scope.locator('#default-support-switch').click();await scope.locator('#default-support-switch').click();
   assert.equal(await scope.locator('#default-parts input:checked').count(),0);
   assert.equal(await scope.locator('#default-limit').isVisible(),false);
   const before=await scope.locator('body').evaluate(el=>el.ownerDocument.location.href);
   await scope.locator('#default-submit').click();
   assert.equal(await scope.locator('body').evaluate(el=>el.ownerDocument.location.href),before);
   await scope.locator('.sr-tabs [data-state="failed"]').press('Enter');
   await scope.locator('.sr-tabs [data-state="default"]').press('Enter');
   assert.equal(await scope.locator('#default-session').inputValue(),'s1');
   assert.equal(await scope.locator('#default-parts-region').isVisible(),false);
   assert.equal(await scope.locator('#default-parts input:checked').count(),0);
   await scope.locator('#default-support-switch').press('Space');
   assert.equal(await scope.locator('#default-parts-region').isVisible(),true);
   assert.equal(await rule(scope),'INT-SESSION');
 }
 await page.route('https://**/*',route=>route.abort());
 try{
   await page.goto(direct);await check(page);
   await page.goto(pathToFileURL(path.join(temp,'frame.html')).href);await check(page.frameLocator('iframe'));
   await page.setViewportSize({width:390,height:844});await page.goto(direct);await check(page);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   assert.deepEqual(errors,[]);
   console.log('PASS local controls: independent pins, no hit-area overlap, values/visibility/reset, submit blocked, direct + iframe + keyboard + narrow');
 }finally{await browser.close();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1);});
