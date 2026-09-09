(function () {
  'use strict';
  var token = new URLSearchParams(location.hash.slice(1)).get('token') || '';
  var current, draft, dirty = false, undoId = null;
  var el = function (id) { return document.getElementById(id); };
  async function request(path, payload) {
    var response = await fetch('/api/' + path, {method: payload ? 'POST' : 'GET', headers: {'X-Editor-Token': token, 'Content-Type': 'application/json'}, body: payload ? JSON.stringify(payload) : undefined});
    var result = await response.json(); if (!response.ok) throw new Error(result.error); return result;
  }
  function changed() { dirty = true; el('dirty').textContent = '草稿未保存'; el('save').disabled = true; }
  function field(parent, label, object, key) {
    var wrap = document.createElement('label'); wrap.textContent = label;
    var input = document.createElement('textarea'); input.value = object[key] || ''; input.disabled = !current.editable;
    input.addEventListener('input', function () { object[key] = input.value; changed(); }); wrap.appendChild(input); parent.appendChild(wrap);
  }
  function group(title) { var box = document.createElement('fieldset'); var legend = document.createElement('legend'); legend.textContent = title; box.appendChild(legend); return box; }
  function prototypeForm(form, it) {
    var metadata = current.prototype_elements[it.page][it.selector.slice(1)];
    var title = document.createElement('h2'); title.textContent = it.description; form.appendChild(title);
    var hint = document.createElement('p'); hint.textContent = '布局预览：点击元素选择属性；此处不运行业务脚本。隐藏或禁用控件可从左侧列表选择。保存后请在实际原型验证。'; form.appendChild(hint);
    var frame = document.createElement('iframe'); frame.title = '原型布局预览'; frame.setAttribute('sandbox', 'allow-same-origin'); frame.className = 'prototype-canvas'; form.appendChild(frame);
    var source = current.prototype_previews[it.page];
    var doc = new DOMParser().parseFromString(source.html, 'text/html');
    doc.querySelectorAll('script,link,base,meta,iframe,object,embed,style').forEach(function (node) { node.remove(); });
    doc.querySelectorAll('*').forEach(function (node) { Array.from(node.attributes).forEach(function (attr) { if (/^on/i.test(attr.name) || ['src','srcset','href','action','formaction','style'].includes(attr.name)) node.removeAttribute(attr.name); }); });
    var csp = doc.createElement('meta'); csp.httpEquiv = 'Content-Security-Policy'; csp.content = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"; doc.head.appendChild(csp);
    var style = doc.createElement('style'); style.textContent = source.css; doc.head.appendChild(style);
    function paint() {
      var canvas = frame.contentDocument; if (!canvas) return;
      (draft.spec.interactions || []).filter(function (i) { return i.page === it.page; }).forEach(function (i) {
        var node = canvas.querySelector(i.selector), p = i.properties || {}; if (!node) return;
        var original = doc.querySelector(i.selector);
        if (original) {
          if (!node.children.length && !['INPUT','TEXTAREA','SELECT'].includes(node.tagName)) node.textContent = original.textContent;
          ['placeholder','maxlength','required'].forEach(function (attr) { if (original.hasAttribute(attr)) node.setAttribute(attr, original.getAttribute(attr)); else node.removeAttribute(attr); });
          if (node.tagName === 'SELECT') node.replaceChildren.apply(node, Array.from(original.children).map(function (o) { return o.cloneNode(true); }));
          if ('value' in node) node.value = original.value;
          node.style.width = '';
        }
        if ('text' in p && !node.children.length) node.textContent = p.text;
        if ('placeholder' in p) node.setAttribute('placeholder', p.placeholder);
        if ('defaultValue' in p) node.value = p.defaultValue;
        if (Number.isInteger(p.maxLength) && p.maxLength >= 1 && p.maxLength <= 10000) node.maxLength = p.maxLength;
        if ('required' in p) node.required = p.required;
        if (p.options && node.tagName === 'SELECT') { node.replaceChildren(); p.options.forEach(function (o) { node.add(new Option(o.label, o.value)); }); if ('defaultValue' in p) node.value = p.defaultValue; }
        if (p.width) node.style.width = {auto:'auto', compact:'160px', full:'100%'}[p.width];
      });
    }
    frame.onload = function () {
      paint();
      var canvas = frame.contentDocument, selected = canvas.querySelector(it.selector);
      if (selected) { var dialog = selected.closest('dialog'); if (dialog) dialog.setAttribute('open', ''); selected.style.outline = '3px solid #2563eb'; frame.contentWindow.scrollTo(0, selected.getBoundingClientRect().top + frame.contentWindow.scrollY - 120); }
      canvas.addEventListener('click', function (event) {
        event.preventDefault(); event.stopImmediatePropagation();
        var match = event.target.closest('[id]');
        var item = draft.spec.interactions.find(function (i) { return i.page === it.page && match && i.selector === '#' + match.id; });
        if (item && item.id !== it.id) { el('material').value = 'it:' + item.id; render(); }
      }, true);
    };
    frame.srcdoc = doc.documentElement.outerHTML;
    var props = it.properties || {};
    var fields = {width: '宽度'};
    if (!metadata._children && !['input','textarea','select'].includes(metadata.tag)) fields.text = '控件文案';
    if (['input','textarea'].includes(metadata.tag)) { fields.placeholder = '占位提示'; if (metadata.tag === 'textarea' || ['text','search','email','url','tel','password'].includes(metadata.type || 'text')) fields.maxLength = '最大长度'; }
    if (['input','textarea','select'].includes(metadata.tag)) { fields.required = '必填'; if (metadata.tag !== 'input' || !['file','checkbox','radio','submit','button','reset','image'].includes(metadata.type)) fields.defaultValue = '默认值'; }
    if (metadata.tag === 'select') fields.options = '选项（每行 value=显示文字）';
    Object.keys(fields).forEach(function (key) {
      var label = document.createElement('label'); label.textContent = fields[key];
      var input = document.createElement(['required','width'].includes(key) ? 'select' : key === 'options' ? 'textarea' : 'input'); input.disabled = !current.editable;
      if (key === 'maxLength') { input.type = 'number'; input.min = '1'; input.max = '10000'; }
      input.setAttribute('aria-label', fields[key]);
      if (key === 'required' || key === 'width') {
        input.add(new Option('沿用原型原值', ''));
        (key === 'required' ? [['true','必填'],['false','非必填']] : [['auto','自动'],['compact','紧凑 160px'],['full','占满容器']]).forEach(function (o) { input.add(new Option(o[1], o[0])); });
      }
      input.value = key === 'options' ? (props.options || []).map(function (o) { return o.value + '=' + o.label; }).join('\n') : String(props[key] == null ? '' : props[key]);
      input.placeholder = '未配置时沿用原型；移除覆盖请点击恢复';
      var originalControl = doc.querySelector(it.selector);
      var base = key === 'width' ? '页面默认布局' : key === 'text' ? originalControl.textContent : key === 'defaultValue' ? originalControl.value : key === 'options' ? Array.from(originalControl.options || []).map(function (o) { return o.value + '=' + o.textContent; }).join('；') : key === 'required' ? String(originalControl.required) : key === 'maxLength' ? String(originalControl.maxLength) : originalControl.getAttribute('placeholder');
      input.oninput = function () {
        it.properties = it.properties || {};
        if ((key === 'width' || key === 'required' || key === 'maxLength') && input.value === '') delete it.properties[key];
        else it.properties[key] = key === 'required' ? input.value === 'true' : key === 'maxLength' ? Number(input.value) : key === 'options' ? input.value.split('\n').map(function (line) { var n = line.indexOf('='); return {value: n < 0 ? line : line.slice(0,n), label: n < 0 ? line : line.slice(n+1)}; }) : input.value;
        changed(); paint();
      };
      label.appendChild(input); var baseHint = document.createElement('small'); baseHint.textContent = '原型原值：' + (base == null || base === '' ? '空' : base); label.appendChild(baseHint); form.appendChild(label);
    });
    if (['navigate','dialog','close','toggle'].includes(it.action)) {
      var wrap = document.createElement('label'); wrap.textContent = '跳转或弹框目标'; var select = document.createElement('select'); select.disabled = !current.editable;
      select.setAttribute('aria-label', '跳转或弹框目标');
      var targets = it.action === 'navigate' ? Object.keys(current.prototype_elements) : Object.keys(current.prototype_elements[it.page]).filter(function (id) { return !['dialog','close'].includes(it.action) || current.prototype_elements[it.page][id].tag === 'dialog'; });
      targets.forEach(function (id) { select.add(new Option(id,id)); }); select.value = it.target;
      select.onchange = function () { it.target = select.value; changed(); }; wrap.appendChild(select); form.appendChild(wrap);
    }
    var reset = document.createElement('button'); reset.textContent = '恢复此控件原始属性'; reset.type = 'button'; reset.disabled = !current.editable;
    reset.onclick = function () { delete it.properties; changed(); render(); }; form.appendChild(reset);
  }
  function render() {
    var form = el('form'); form.replaceChildren();
    var value = el('material').value;
    if (value.startsWith('it:')) { prototypeForm(form, draft.spec.interactions.find(function (i) { return i.id === value.slice(3); })); return; }
    if (value.startsWith('doc:')) { field(form, '正文（Markdown）', draft.documents, value.slice(4)); return; }
    var r = (draft.spec && draft.spec.requirements || []).find(function (r) { return r.id === value; });
    if (!r) { form.textContent = '没有可编辑需求；可选择左侧正文物料。'; return; }
    var title = document.createElement('h2'); title.textContent = r.id; form.appendChild(title);
    field(form, '需求标题', r, 'title'); field(form, '需求说明', r, 'description');
    Object.keys(r.rules || {}).forEach(function (key) { field(form, key, r.rules, key); });
    (r.rule_details || []).forEach(function (rule) {
      var box = group(rule.id + ' · ' + (rule.status === 'confirmed' ? '已确认' : '待确认'));
      field(box, '规则类别', rule, 'category'); field(box, '规则说明', rule, 'statement');
      (rule.examples || []).forEach(function (example) { field(box, '实例输入', example, 'input'); field(box, '实例预期', example, 'expected'); });
      form.appendChild(box);
    });
    (r.acceptance || []).forEach(function (ac) { var box = group(ac.id); field(box, '前置条件 Given', ac, 'given'); field(box, '操作 When', ac, 'when'); field(box, '预期结果 Then', ac, 'then'); form.appendChild(box); });
  }
  function adopt(s) {
    var selected = el('material').value;
    current = s; draft = structuredClone(s); dirty = false;
    el('title').textContent = s.project + ' · ' + s.version + (s.editable ? ' · 物料编辑' : ' · 历史只读');
    el('dirty').textContent = ''; el('save').disabled = true; el('preview').disabled = !s.editable;
    el('material').replaceChildren();
    (s.spec && s.spec.requirements || []).forEach(function (r) { var opt = new Option(r.id + ' · ' + r.title, r.id); el('material').add(opt); });
    Object.keys(s.documents).forEach(function (path) { el('material').add(new Option(path, 'doc:' + path)); });
    (s.spec && s.spec.interactions || []).forEach(function (it) { if (s.prototype_elements[it.page] && s.prototype_elements[it.page][it.selector.slice(1)]) el('material').add(new Option('原型 · ' + it.description, 'it:' + it.id)); });
    if (Array.from(el('material').options).some(function (o) { return o.value === selected; })) el('material').value = selected;
    render();
  }
  function payload() { return {revision: current.revision, spec: draft.spec, documents: draft.documents}; }
  function showImpact(report) {
    el('impact').replaceChildren();
    var heading = document.createElement('h3'); heading.textContent = '变更与待复核范围'; el('impact').appendChild(heading);
    var note = document.createElement('p'); note.textContent = report.notice; el('impact').appendChild(note);
    var list = document.createElement('p'); list.textContent = '页面：' + report.review_pages.join('、') + '；控件：' + report.review_interactions.join('、') + '；验收：' + report.review_acceptance.join('、'); el('impact').appendChild(list);
    report.changes.forEach(function (change) { var pre = document.createElement('pre'); pre.textContent = change.path + '\n修改前：' + JSON.stringify(change.before) + '\n修改后：' + JSON.stringify(change.after); el('impact').appendChild(pre); });
  }
  async function run(fn) { document.querySelector('main').inert = true; try { await fn(); } catch (e) { el('status').textContent = e.message + '。草稿仍保留，可先导出再重新载入。'; el('save').disabled = true; } finally { document.querySelector('main').inert = false; } }
  el('material').onchange = render;
  el('reload').onclick = function () { if (dirty && !confirm('重新载入将丢弃未保存草稿。是否继续？')) return; run(async function () { adopt(await request('state')); undoId = null; el('undo').disabled = true; el('status').textContent = '已载入'; }); };
  el('preview').onclick = function () { run(async function () { var result = await request('preview', payload()); showImpact(result.impact); el('save').disabled = !result.impact.changes.length; el('status').textContent = '请核对差异。保存前还会检查结构和项目冲突。'; }); };
  el('save').onclick = function () { el('save').disabled = true; run(async function () { var result = await request('save', payload()); adopt(result.state); undoId = result.undo_id || undoId; el('undo').disabled = !undoId; showImpact(result.impact); el('status').textContent = '已保存并重新编译；请复核受影响的原型行为和测试。' + (result.undo_id ? ' 修改记录 ID：' + result.undo_id : ''); }); };
  el('undo').onclick = function () { if (dirty && !confirm('撤销保存会替换当前未保存草稿。是否继续？')) return; run(async function () { var result = await request('undo', {revision: current.revision, undo_id: undoId}); adopt(result.state); undoId = null; el('undo').disabled = true; showImpact(result.impact); el('status').textContent = '已撤销上次保存并重新编译'; }); };
  el('export').onclick = function () { if (!draft) return; var url = URL.createObjectURL(new Blob([JSON.stringify(payload(), null, 2)], {type: 'application/json'})); var link = document.createElement('a'); link.href = url; link.download = 'prd-draft.json'; link.click(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000); };
  window.addEventListener('beforeunload', function (event) { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  run(async function () { adopt(await request('state')); });
}());
