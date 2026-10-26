// Real packaged Mermaid, offline and from a cold document; no mocked diagram renderer.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
(async()=>{
 const root=path.resolve(process.argv[2]),shots=path.resolve(process.argv[3]);fs.mkdirSync(shots,{recursive:true});
 const server=http.createServer((req,res)=>{
  const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
  fs.readFile(file,(error,body)=>{if(error){res.writeHead(404);res.end();return;}const ext=path.extname(file);res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css'})[ext]||'application/octet-stream');res.end(body);});
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL||undefined,executablePath:process.env.PW_EXECUTABLE||undefined});
 const context=await browser.newContext({viewport:{width:1440,height:980}}),page=await context.newPage();await page.bringToFront();
 page.setDefaultTimeout(15000);page.setDefaultNavigationTimeout(30000);
 const errors=[],external=[];page.on('pageerror',e=>errors.push(e.message));
 await context.route('https://**/*',route=>{external.push(route.request().url());return route.abort();});
 let missing=false;
 await context.route('**/vendor/mermaid-*.min.js',async route=>{
  if(missing)return route.abort();
  await new Promise(resolve=>setTimeout(resolve,3500)); // longer than the removed 2.5s polling window
  return route.continue();
 });
 const base='http://127.0.0.1:'+server.address().port+'/site/index.html';
 try{
  await page.goto(base+'#/v/v0.1/_prd/users',{waitUntil:'domcontentloaded'});
  await page.locator('.mermaid-inline[data-diagram-status="rendered"] svg').waitFor();
  assert.equal(await page.locator('.callout.warn').count(),0);
  assert.equal(await page.locator('.mermaid-inline svg').count(),1);
  await page.locator('.mermaid-inline').screenshot({path:path.join(shots,'module.png')});
  await page.locator('.page-link[href="#/v/v0.1/_prd/functions"]').click({noWaitAfter:true});
  const status=await page.evaluate(()=>({fonts:document.fonts.status,diagrams:[...document.querySelectorAll('.mermaid-inline')].map(e=>e.dataset.diagramStatus)}));
  fs.writeFileSync(path.join(shots,'render-status.json'),JSON.stringify(status));
  await page.waitForFunction(()=>document.querySelectorAll('.mermaid-inline[data-diagram-status="rendered"] svg').length===2,{},{polling:100});
  const diagram=page.locator('.mermaid-inline').first();
  await diagram.locator('[data-zoom="out"]').click();await diagram.locator('[data-zoom="reset"]').click();
  assert.equal(await diagram.locator('[data-zoom="reset"]').innerText(),'100%');
  await page.setViewportSize({width:390,height:844});
  await diagram.locator('.diagram-viewport').focus();await page.keyboard.press('ArrowRight');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await diagram.screenshot({path:path.join(shots,'narrow.png')});
  // The renderer reports a syntax failure separately and retains the complete source.
  await page.evaluate(async()=>{const el=document.createElement('div');el.id='invalid-diagram';document.body.append(el);await PS.renderMermaid(el,'flowchart TD\n A[unterminated');});
  assert.equal(await page.locator('#invalid-diagram').getAttribute('data-diagram-status'),'error');
  assert.match(await page.locator('#invalid-diagram .callout').innerText(),/语法和数据/);
  assert.match(await page.locator('#invalid-diagram pre').innerText(),/unterminated/);
  // A new cold document with a missing local resource must give an actionable failure.
  missing=true;await page.reload({waitUntil:'domcontentloaded'});
  await page.locator('.mermaid-inline[data-diagram-status="error"]').first().waitFor();
  assert.match(await page.locator('.mermaid-inline .callout').first().innerText(),/本地图形库未加载/);
  assert.equal(await page.locator('.mermaid-inline pre').count(),2);
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  console.log('PASS diagrams: cold delayed local load, offline real SVGs, zoom + narrow + keyboard, missing library + invalid syntax diagnostics');
 }catch(error){fs.writeFileSync(path.join(shots,'failure.txt'),page.url()+'\n'+await page.locator('body').innerText({timeout:2000}).catch(()=>'<body unavailable>'));await page.screenshot({path:path.join(shots,'failure.png'),timeout:3000}).catch(()=>{});throw error;}finally{await context.close();await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exit(1)});
