const test=require('node:test'), assert=require('node:assert/strict');
const delivery=require('../template/site/js/delivery.js');
function fixture(){
  const req=id=>({id,title:id,status:'confirmed',rules:{权限:'管理员'},rule_details:[],acceptance:[{id:'AC-'+id,given:'有效输入',when:'提交',then:'成功'}]});
  const bundle=reqs=>({spec:{requirements:reqs,pages:[{id:'list',requirement_ids:reqs.map(r=>r.id)}],interactions:[]},manifest:{modules:[{id:'prd',pages:[{id:'spec',title:'需求',type:'spec'}]},{id:'prototype',pages:[{id:'list',title:'列表',type:'prototype'}]}]},content_hashes:{}});
  return {project:{name:'测试',versions:[{id:'v1',status:'planning',base:'v0'},{id:'v0',status:'frozen'}]},versions:{v0:bundle([req('A'),req('B')]),v1:bundle([req('A'),req('C')])}};
}
test('新增移除与旧链接，导出保留验收',()=>{const pack=delivery.model(fixture(),'v1');assert.equal(pack.tasks.find(t=>t.id==='B').change,'removed');assert.match(pack.tasks.find(t=>t.id==='B').links[0].route,/v0/);assert.equal(delivery.filter(pack,'','changed','all','all').length,3);assert.match(delivery.markdown(pack,pack.tasks,'https://example.com/site'),/AC-A/);});
test('子规则待确认不能被需求确认掩盖；未分工保留',()=>{const d=fixture(); d.versions.v1.spec.requirements[0].blocking=true;d.versions.v1.spec.requirements[0].rule_details=[{id:'R',status:'pending',statement:'规则'}];const p=delivery.model(d,'v1');assert.equal(delivery.filter(p,'','all','blocking','backend')[0].id,'A');});
test('交互变更、共享文件变化触发复核',()=>{const d=fixture();d.versions.v0=structuredClone(d.versions.v1);d.versions.v1.spec.interactions=[{id:'I',requirement_ids:['A'],selector:'#a',action:'custom'}];assert.equal(delivery.model(d,'v1').tasks[0].change,'review');d.versions.v1.content_hashes['prototype/assets/page.js']='new';assert.ok(delivery.model(d,'v1').tasks.every(t=>t.change==='review'));});
test('历史包保持自身基线，当前依据独立',()=>{const d=fixture();d.project.versions[0].current_handoff='v1.r2';d.project.versions.push({id:'v1.r1',handoff_parent:'v1',base:'v0',status:'frozen'});d.versions['v1.r1']=d.versions.v0;const p=delivery.model(d,'v1.r1');assert.equal(p.basis,'v1.r2');assert.equal(p.baseline,'v0');});
