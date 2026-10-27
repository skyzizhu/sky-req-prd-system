const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {pathToFileURL}=require('node:url');
(async()=>{
  // A nonempty property supplement must survive deduplication.
  const specFile=path.join(process.argv[2],'versions/v1.1/content/spec.json');
  const spec=JSON.parse(fs.readFileSync(specFile));
  spec.interactions.find(i=>i.id==='INT-CREATE').properties={text:'新建订单'};
  fs.writeFileSync(specFile,JSON.stringify(spec));
  execFileSync('python3',[path.join(process.argv[2],'build.py')]);
  const browser=await chromium.launch({headless:true,channel:process.env.PW_CHANNEL || undefined,executablePath:process.env.PW_EXECUTABLE || undefined});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://**/*',r=>r.abort());
  const base=pathToFileURL(path.join(process.argv[2],'site/index.html')).href;
  try{
    await page.goto(base+'#/v/v1.1/requirements/spec');
    await page.locator('.prd-requirement').first().waitFor();
    assert.equal(await page.locator('.prd-requirement').count(),3);
    assert.equal(await page.locator('.prd-feature-title').first().innerText(),'创建订单');
    const star=page.locator('.page-link.key-material').first();
    assert.equal(await star.evaluate(el=>getComputedStyle(el,'::after').content),'"★"');
    assert.ok(['none','normal'].includes(await star.evaluate(el=>getComputedStyle(el,'::before').content)));
    const header=page.locator('.prd-feature-header').first();
    assert.equal(await header.evaluate(el=>getComputedStyle(el).display),'flex');
    // Title and action occupy disjoint areas, even with wrapping metadata.
    async function checkHeader(){assert.equal(await header.evaluate(el=>{const a=el.querySelector('.prd-feature-heading').getBoundingClientRect(),b=el.querySelector('button').getBoundingClientRect();return Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top);}),false);}
    await checkHeader();
    for(const width of [390,960,1440]){
      await page.setViewportSize({width,height:1000});
      assert.ok(await page.locator('#content').evaluate(el=>el.scrollWidth<=el.clientWidth));
      await checkHeader();
    }
    await page.setViewportSize({width:1440,height:1000});

    assert.equal(await page.locator('.prd-control[open]').count(),0);
    await page.screenshot({path:process.argv[3],fullPage:true});
    await page.locator('#prd-search').fill('RULE-NAME-INPUT');
    assert.equal(await page.locator('.prd-requirement').count(),1);
    await page.getByRole('button',{name:'交给 Agent 修改此需求',exact:true}).click();
    assert.match(await page.getByRole('textbox',{name:'Agent 修改上下文'}).inputValue(),/FR-ORDER-001/);
    await page.locator('#prd-edit-context button').click();
    const supplement=page.locator('.prd-fold').filter({has:page.getByText('控件属性补充',{exact:true})});
    await supplement.locator('summary').click();
    assert.match(await supplement.innerText(),/INT-CREATE/);
    assert.match(await supplement.innerText(),/新建订单/);
    assert.equal(await page.locator('.prd-control').count(),0);
    const related=page.locator('.prd-fold').filter({has:page.getByText('关联原型',{exact:true})});
    await related.locator('summary').click();
    assert.equal(await related.getByRole('link',{name:'订单列表',exact:true}).count(),1);
    const download=page.waitForEvent('download');await page.locator('#prd-export').click();
    const md=fs.readFileSync(await (await download).path(),'utf8');
    for(const text of ['## 创建订单','## 批量完成订单','前提：','预期：','RULE-NAME-INPUT'])assert.ok(md.includes(text));
    assert.ok(!md.includes('## FR-ORDER'));
    await page.goto(base+'#/v/v1.0/requirements/spec?requirement=FR-ORDER-002');
    await page.waitForFunction(()=>document.querySelector('#prd-search')?.value==='FR-ORDER-002');
    assert.equal(await page.locator('.prd-requirement').count(),1);
    await page.getByRole('button',{name:'交给 Agent 修改此需求',exact:true}).click();
    assert.match(await page.getByRole('textbox',{name:'Agent 修改上下文'}).inputValue(),/版本：v1.0/);
    assert.deepEqual(errors,[]);
    console.log('PASS PRD: business hierarchy, deduplicated page links and retained property supplement, stable-ID search, exact requirement Agent context, full readable export, history route');
  }finally{await browser.close();}
})();
