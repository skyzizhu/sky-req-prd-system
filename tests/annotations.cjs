// Pure model tests: no browser, navigation or rendered page access.
const test = require('node:test');
const assert = require('node:assert/strict');
const createStore = require('../assets/annotation-store.js');
const context = {project:'project', version:'v1.1', page:'list'};
const original = [{id:'INT-CREATE',selector:'#create',description:'创建订单',level:'crit',requirement_ids:['FR-001']}];
test('review transitions, persistence, completion evidence and reopening',()=>{
  const disk=storage(), s=createStore({...context,requirement_ids:['FR-001']},original,disk);
  const record={status:'accepted',note:'采纳此意见',requirement_ids:['FR-001'],change_ref:'',evidence:''};
  assert.throws(()=>s.review('INT-CREATE',{...record,status:'completed'}));
  s.review('INT-CREATE',record);
  assert.throws(()=>s.review('INT-CREATE',{...record,status:'completed'}));
  s.review('INT-CREATE',{...record,status:'completed',change_ref:'abc',evidence:'已验证提交路径'});
  assert.equal(createStore(context,original,disk).list()[0].review.status,'completed');
  s.edit('INT-CREATE','新增边界规则','warn');assert.equal(s.list()[0].review.status,'pending');
  s.undo();assert.equal(s.list()[0].review.status,'completed');
  const imported=createStore(context,original,storage());imported.importData(s.exportData());assert.equal(imported.list()[0].review.history.length,2);
});
test('review wrong references and malformed import are atomic; legacy notes migrate',()=>{
  const s=createStore({...context,requirement_ids:['FR-001']},original,storage());
  const old=s.exportData();old.schema_version=1;delete old.reviews;s.importData(old);assert.equal(s.list()[0].review.status,'pending');assert.equal(s.exportData().schema_version,2);
  const before=s.exportData();assert.throws(()=>s.review('INT-CREATE',{status:'accepted',note:'同意',requirement_ids:['OTHER'],change_ref:'',evidence:''}));assert.deepEqual(s.exportData(),before);
  assert.throws(()=>s.importData({...before,reviews:[{id:'bad'}]}));assert.deepEqual(s.exportData(),before);
});
function storage() { const m = new Map(); return {getItem:k=>m.get(k)||null,setItem:(k,v)=>m.set(k,v)}; }
function manual(id='manual-test') { return {id,selector:'#label',description:'手动说明',level:'info',x:.25,y:.75}; }
test('add, edit, persist and reload a manual annotation',()=>{
  const disk=storage(),s=createStore(context,original,disk); s.add(manual()); s.edit('manual-test','修改后的说明','warn');
  const loaded=createStore(context,original,disk).list(); assert.equal(loaded[1].description,'修改后的说明'); assert.equal(loaded[1].number,'M1'); assert.equal(loaded[1].level,'warn');
});
test('deleting a generated annotation never changes its requirement or action',()=>{
  const before=JSON.stringify(original),s=createStore(context,original,storage()); s.hide('INT-CREATE');
  assert.equal(s.list()[0].hidden,true); assert.equal(JSON.stringify(original),before); s.restore('INT-CREATE'); assert.equal(s.list()[0].hidden,false);
});
test('deletion and restoration survive reloading',()=>{
  const disk=storage(),s=createStore(context,original,disk); s.add(manual()); s.hide('manual-test');
  const again=createStore(context,original,disk); assert.equal(again.list()[1].hidden,true); again.restore('manual-test'); assert.equal(createStore(context,original,disk).list()[1].hidden,false);
});
test('undo edits and deletions without renumbering remaining marks',()=>{
  const s=createStore(context,original,storage()); s.add(manual()); s.hide('INT-CREATE'); assert.equal(s.list()[1].number,'M1'); s.undo(); assert.equal(s.list()[0].hidden,false); s.undo(); assert.equal(s.list().length,1);
});
test('version and page storage are isolated',()=>{
  const disk=storage(),s=createStore(context,original,disk); s.add(manual());
  assert.equal(createStore({...context,page:'detail'},original,disk).list().length,1);
  assert.equal(createStore({...context,version:'v1.0'},original,disk).list().length,1);
});
test('export and import roundtrip is undoable',()=>{
  const s=createStore(context,original,storage()); s.add(manual()); s.edit('INT-CREATE','新说明','info');
  const t=createStore(context,original,storage()); t.importData(s.exportData()); assert.deepEqual(t.list(),s.list()); t.undo(); assert.equal(t.list().length,1);
});
test('wrong project import fails without overwriting notes',()=>{
  const s=createStore(context,original,storage()); s.add(manual()); const before=s.exportData();
  assert.throws(()=>s.importData({...before,project:'other'})); assert.deepEqual(s.exportData(),before);
});
test('invalid text, duplicate ids and out-of-range positions rejected atomically',()=>{
  const s=createStore(context,original,storage());
  for(const item of [{...manual(),description:''},{...manual(),x:2},{...manual(),level:'invalid'},{...manual(),description:'a'.repeat(2001)}]) assert.throws(()=>s.add(item));
  assert.equal(s.list().length,1); s.add(manual()); assert.throws(()=>s.add(manual())); assert.equal(s.list().length,2);
});
test('storage failure preserves in-memory changes with explicit warning',()=>{
  const s=createStore(context,original,{getItem:()=>null,setItem:()=>{throw Error('quota');}}); s.add(manual()); assert.equal(s.list().length,2); assert.match(s.warning(),/导出/);
});
test('import drops unknown fields and does not mutate its input',()=>{
  const s=createStore(context,original,storage()),v=s.exportData(); v.custom=[{...manual(),html:'<script>alert(1)</script>'}]; s.importData(v);
  assert.equal(s.exportData().custom[0].html,undefined); assert.ok(v.custom[0].html);
});
