/* Pure annotation model. Notes are local review overlays, never PRD mutations. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.PSAnnotationStore = factory;
})(typeof window !== 'undefined' ? window : globalThis, function (context, originals, storage) {
  'use strict';
  var levels = ['crit', 'warn', 'info', 'ok'];
  var key = 'ps.annotations.' + [context.project, context.version, context.page].map(encodeURIComponent).join('.');
  var base = new Map(originals.map(function (item) { return [item.id, item]; }));
  var history = [], warning = '';
  var reviewStates = ['pending', 'accepted', 'rejected', 'completed'];
  function empty() { return {schema_version: 2, project: context.project, version: context.version, page: context.page, hidden: [], overrides: [], custom: [], reviews: []}; }
  function copy(value) { return JSON.parse(JSON.stringify(value)); }
  function text(value, max) { return typeof value === 'string' && value.trim().length > 0 && value.length <= max; }
  function validate(value) {
    if (!value || ![1,2].includes(value.schema_version) || ['project', 'version', 'page'].some(function (k) { return value[k] !== context[k]; })) throw new Error('标记文件格式不支持或不属于当前项目、版本和页面。');
    if (!Array.isArray(value.hidden) || !Array.isArray(value.overrides) || !Array.isArray(value.custom) || value.hidden.length + value.overrides.length + value.custom.length > 1000) throw new Error('标记数据格式或数量不合法。');
    var result = empty(), used = new Set();
    value.custom.forEach(function (item) {
      if (!item || !/^manual-[a-zA-Z0-9-]+$/.test(item.id) || item.id.length > 120 || base.has(item.id) || used.has(item.id) || !text(item.selector, 2000) || !text(item.description, 2000) || !levels.includes(item.level) || !Number.isFinite(item.x) || !Number.isFinite(item.y) || item.x < 0 || item.x > 1 || item.y < 0 || item.y > 1) throw new Error('手动标记内容、落点或编号不合法。');
      used.add(item.id);
      result.custom.push({id: item.id, selector: item.selector, description: item.description.trim(), level: item.level, x: item.x, y: item.y});
    });
    var overrides = new Set();
    value.overrides.forEach(function (item) {
      if (!item || !base.has(item.id) || overrides.has(item.id) || !text(item.description, 2000) || !levels.includes(item.level)) throw new Error('原始标记已变化，或修改数据不合法。');
      overrides.add(item.id);
      result.overrides.push({id: item.id, description: item.description.trim(), level: item.level});
    });
    value.hidden.forEach(function (id) {
      if ((!base.has(id) && !used.has(id)) || result.hidden.includes(id)) throw new Error('已删除标记的编号不存在或重复。');
      result.hidden.push(id);
    });
    var reviews = value.reviews || [], reviewIds = new Set();
    if (!Array.isArray(reviews) || reviews.length > 1000) throw new Error('批注处理记录格式不合法。');
    reviews.forEach(function (r) {
      if (!r || (!base.has(r.id) && !used.has(r.id)) || reviewIds.has(r.id) || !reviewStates.includes(r.status) || typeof r.note !== 'string' || r.note.length > 2000 || !Array.isArray(r.requirement_ids) || r.requirement_ids.length > 100 || r.requirement_ids.some(function (id) { return typeof id !== 'string' || !/^[A-Za-z0-9_-]+$/.test(id) || (Array.isArray(context.requirement_ids) && !context.requirement_ids.includes(id)); }) || typeof r.change_ref !== 'string' || r.change_ref.length > 200 || typeof r.evidence !== 'string' || r.evidence.length > 2000 || !text(r.updated_at, 80)) throw new Error('批注状态、说明或需求关联不合法。');
      if (r.status !== 'pending' && !r.note.trim()) throw new Error('处理批注必须填写说明。');
      if (['accepted','completed'].includes(r.status) && !r.requirement_ids.length) throw new Error('采纳批注必须关联需求。');
      if (r.status === 'completed' && (!r.change_ref.trim() || !r.evidence.trim())) throw new Error('完成批注必须填写正式修改记录和验证说明。');
      var events = r.history || [];
      if (!Array.isArray(events) || events.length > 30 || events.some(function (e) { return !e || !reviewStates.includes(e.from) || !reviewStates.includes(e.to) || !text(e.at,80) || !text(e.note,2000); })) throw new Error('处理历史格式不合法。');
      reviewIds.add(r.id);
      result.reviews.push({id:r.id,status:r.status,note:r.note.trim(),requirement_ids:Array.from(new Set(r.requirement_ids)),change_ref:r.change_ref.trim(),evidence:r.evidence.trim(),updated_at:r.updated_at,history:events.map(function(e){return {from:e.from,to:e.to,at:e.at,note:e.note};})});
    });
    return result;
  }
  var state = empty();
  try { var saved = storage.getItem(key); if (saved) state = validate(JSON.parse(saved)); }
  catch (_) { warning = '无法读取已存标记；当前使用原始标记。请先保留已有导出文件。'; }
  function persist() {
    try { storage.setItem(key, JSON.stringify(state)); warning = ''; }
    catch (_) { warning = '浏览器无法保存标记，本次修改仅在当前页面有效，请导出备份。'; }
  }
  function commit(next) {
    next = validate(next);
    history.push(copy(state)); if (history.length > 30) history.shift();
    state = next; persist();
  }
  function list() {
    return originals.map(function (item, index) {
      var override = state.overrides.find(function (o) { return o.id === item.id; });
      return Object.assign({}, item, override || {}, {number: String(index + 1), manual: false, hidden: state.hidden.includes(item.id)});
    }).concat(state.custom.map(function (item, index) {
      return Object.assign({}, item, {number: 'M' + (index + 1), manual: true, hidden: state.hidden.includes(item.id), requirement_ids: []});
    })).map(function (item) { item.review = copy(state.reviews.find(function (r) { return r.id === item.id; }) || {id:item.id,status:'pending',note:'',requirement_ids:item.requirement_ids || [],change_ref:'',evidence:'',history:[]}); return item; });
  }
  return {
    key: key,
    list: list,
    warning: function () { return warning; },
    canUndo: function () { return history.length > 0; },
    exportData: function () { return copy(state); },
    importData: function (value) { commit(value); },
    review: function (id, update) {
      var item = list().find(function (i) { return i.id === id; }); if (!item) throw new Error('标记不存在。');
      var previous = item.review, allowed = {pending:['pending','accepted','rejected'],accepted:['pending','accepted','completed','rejected'],rejected:['pending','rejected'],completed:['pending','completed']};
      if (!allowed[previous.status].includes(update.status)) throw new Error('请先采纳后完成；重新处理已关闭批注请先设为待处理。');
      var now = new Date().toISOString();
      var record = Object.assign({},update,{id:id,updated_at:now,history:(previous.history || []).concat([{from:previous.status,to:update.status,at:now,note:update.note || '重新标记为待处理'}]).slice(-30)});
      var next=copy(state); next.reviews=next.reviews.filter(function(r){return r.id!==id;}); next.reviews.push(record); commit(next);
    },
    add: function (item) { var next = copy(state); next.custom.push(item); commit(next); },
    edit: function (id, description, level) {
      var next = copy(state), custom = next.custom.find(function (i) { return i.id === id; });
      var before = list().find(function(i){return i.id===id;});
      if (custom) { custom.description = description; custom.level = level; }
      else if (base.has(id)) { next.overrides = next.overrides.filter(function (i) { return i.id !== id; }); next.overrides.push({id:id, description:description, level:level}); }
      else throw new Error('标记不存在。');
      var review = next.reviews.find(function(r){return r.id===id;});
      if (review && before && (before.description!==description.trim() || before.level!==level)) {
        var now=new Date().toISOString();review.history=(review.history || []).concat([{from:review.status,to:'pending',at:now,note:'批注内容已修改，需要重新处理'}]).slice(-30);
        review.status='pending';review.note='批注内容已修改，需要重新处理';review.change_ref='';review.evidence='';review.updated_at=now;
      }
      commit(next);
    },
    hide: function (id) { if (!list().some(function (i) { return i.id === id; })) throw new Error('标记不存在。'); var next = copy(state); if (!next.hidden.includes(id)) next.hidden.push(id); commit(next); },
    restore: function (id) { var next = copy(state); next.hidden = next.hidden.filter(function (i) { return i !== id; }); commit(next); },
    undo: function () { if (history.length) { state = history.pop(); persist(); } }
  };
});
