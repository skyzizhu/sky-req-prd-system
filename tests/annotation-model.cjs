const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const code=fs.readFileSync(require('node:path').join(__dirname,'../assets/prototype-runtime.js'),'utf8').split('/* Static reader:')[0];
const context={window:{}};vm.runInNewContext(code,context);const model=context.window.PSAnnotationModel;
const states=[{id:'default'},{id:'failed'},{id:'success'}];
const reqs=[{id:'FR',rule_details:[{id:'COMMON',statement:'唯一正文'},{id:'FAIL',statement:'失败恢复'},{id:'DONE',statement:'成功结果'}]}];
const controls=[{id:'field',rule_ids:['COMMON'],state_ids:['default','failed']},{id:'submit',rule_ids:['COMMON'],state_ids:['default','failed']},{id:'error',rule_ids:['FAIL'],state_ids:['failed']},{id:'done',rule_ids:['DONE'],state_ids:['success']}];
test('shared rule appears once with every control reference',()=>{const result=model(reqs,controls,states,'default',false);assert.equal(result.common.length,1);assert.equal(result.common[0].controls.length,2);assert.equal(result.specific.length,0);});
test('state-specific rules precede shared constraints without leaking other states',()=>{const result=model(reqs,controls,states,'failed',false);assert.equal(result.specific[0].rule.id,'FAIL');assert.equal(result.common[0].rule.id,'COMMON');assert.equal(result.specific.some(x=>x.rule.id==='DONE'),false);});
test('compare deduplicates by ID and preserves applicable states',()=>{const result=model(reqs,controls,states,'default',true);assert.equal(result.common.length+result.specific.length,3);assert.equal(result.common[0].states.join(','),'default,failed');});
test('same text with distinct rule IDs is not merged',()=>{const result=model([{id:'FR',rule_details:[{id:'A',statement:'相同文本'},{id:'B',statement:'相同文本'}]}],[{id:'x',rule_ids:['A','B']}],states,'default',false);assert.equal(result.common.length,2);});
test('selecting a control collects all its rules without duplicating shared rules',()=>{const result=model(reqs,[...controls,{id:'field',rule_ids:['FAIL'],state_ids:['failed']}],states,'failed',false);const selected=context.window.PSAnnotationSelection(result,'field');assert.equal(selected.focused.length,2);assert.equal(selected.other.length,0);assert.equal(new Set(selected.focused.map(e=>e.rule.id)).size,2);});
test('other rules remain available and different-state rules stay excluded',()=>{const result=model(reqs,controls,states,'failed',false);const selected=context.window.PSAnnotationSelection(result,'error');assert.equal(selected.focused.map(e=>e.rule.id).join(','),'FAIL');assert.equal(selected.other.map(e=>e.rule.id).join(','),'COMMON');assert.equal(selected.other.some(e=>e.rule.id==='DONE'),false);});

test('selected annotation preserves authored rule order rather than moving shared rules behind other states',()=>{
 const result=model(reqs,[{id:'close',rule_ids:['COMMON','FAIL'],state_ids:['failed']},{id:'field',rule_ids:['COMMON'],state_ids:['default','failed']}],states,'failed',false);
 assert.equal(context.window.PSAnnotationSelection(result,'close').focused.map(e=>e.rule.id).join(','),'COMMON,FAIL');
});
