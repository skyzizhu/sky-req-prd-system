const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const fs = require('node:fs');
const root = path.resolve(process.argv[2]);
const prepare = spawnSync('python3', ['-c', `
import pathlib,sys
sys.path[:0]=['scripts','template']
from create_demo import generate
from record_outcome import append
from projectlib import compile_project
r=pathlib.Path(sys.argv[1]);generate(r)
p={'kind':'execution','version':'v1.0','scope':'prototype','result':'failed','requirement_id':'FR-ORDER-001','acceptance_id':'AC-ORDER-001','environment':'合成环境','build':'原型示例','actor':'自动化合成记录','observed_at':'2026-09-09T12:00:00+08:00','evidence':['示例证据，不是真实业务结果'],'notes':'<script>不应执行</script>','follow_up':{'target_version':'v1.1','owner':'产品示例','action':'复核重试规则'}}
append(r,p)
p={k:v for k,v in p.items() if k not in ('scope','result','requirement_id','acceptance_id','environment','build','follow_up')}
p.update(kind='measurement',goal='创建成功率',metric='成功/尝试',baseline='待补',target='待确认',actual='样本不足',window='七日示例',data_source='演示报表',decision='inconclusive')
append(r,p);compile_project(r)
`, root], {encoding:'utf8'});
assert.equal(prepare.status,0,prepare.stderr);
(async () => {
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://**/*',r=>r.abort());
  const base=pathToFileURL(path.join(root,'site/index.html')).href;
  try {
    await page.goto(base+'#/v/v1.0/_outcomes/results');
    await page.getByRole('heading',{name:'验收结果与上线复盘',exact:true}).waitFor();
    assert.equal(await page.locator('.outcome-record').count(),2);
    await page.locator('#outcome-filter').selectOption('product');
    assert.equal(await page.locator('.outcome-record').count(),0);
    assert.match(await page.locator('#outcome-results').innerText(),/AC-ORDER-001/);
    assert.match(await page.locator('#outcome-results').innerText(),/不能解释为已通过/);
    await page.locator('#outcome-filter').selectOption('measurement');
    assert.match(await page.locator('#outcome-results').innerText(),/证据不足/);
    await page.locator('#outcome-filter').selectOption('prototype');
    assert.match(await page.locator('#outcome-results').innerText(),/失败/);
    assert.equal(await page.locator('#outcome-results script').count(),0);
    await page.screenshot({path:process.argv[3],fullPage:true});
    await page.getByRole('link',{name:'v1.1',exact:true}).click();
    await page.locator('#outcome-incoming').waitFor();
    assert.match(await page.locator('#outcome-incoming').innerText(),/复核重试规则/);
    await page.getByText('填写结果草稿（导出后正式入库）',{exact:true}).click();
    let draft=JSON.parse(await page.locator('#outcome-draft').inputValue());
    assert.equal(draft.result,'not_run');
    draft.actor='手工草稿';
    await page.locator('#outcome-draft').fill(JSON.stringify(draft));
    const download=page.waitForEvent('download');
    await page.locator('#outcome-export').click();
    assert.equal(JSON.parse(fs.readFileSync(await (await download).path(),'utf8')).actor,'手工草稿');
    assert.match(await page.locator('#outcome-draft-status').innerText(),/尚未入库/);
    assert.deepEqual(errors,[]);
    console.log('PASS outcomes: scope separation, missing coverage, metrics, follow-up, safe rendering, draft export');
  } finally { await browser.close(); }
})();
