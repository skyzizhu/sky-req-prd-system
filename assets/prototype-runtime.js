/* Same spec renders the PRD and standalone draggable page panel; no fetch. */
(function () {
  'use strict';
  var data = window.PS_SPEC;
  if (!data) return;
  var pid = document.body.dataset.pageId;
  var page = data.spec.pages.find(function (p) { return p.id === pid; });
  if (!page) return;
  var interactions = data.spec.interactions.filter(function (i) { return i.page === pid; });
  // PS_PROPERTY_RUNTIME_V1: declarative, allowlisted prototype attributes.
  interactions.forEach(function (it) {
    var el = document.querySelector(it.selector), p = it.properties || {};
    if (!el) return;
    if (Object.prototype.hasOwnProperty.call(p, 'text') && !el.children.length) el.textContent = p.text;
    if (Object.prototype.hasOwnProperty.call(p, 'placeholder')) el.setAttribute('placeholder', p.placeholder);
    if (Object.prototype.hasOwnProperty.call(p, 'maxLength')) el.maxLength = p.maxLength;
    if (Object.prototype.hasOwnProperty.call(p, 'required')) el.required = p.required;
    if (p.options && el.tagName === 'SELECT') {
      el.replaceChildren(); p.options.forEach(function (o) { el.add(new Option(o.label, o.value)); });
    }
    if (Object.prototype.hasOwnProperty.call(p, 'defaultValue')) {
      el.value = p.defaultValue;
      if (el.tagName === 'SELECT') Array.from(el.options).forEach(function (o) { o.defaultSelected = o.value === p.defaultValue; });
      else el.defaultValue = p.defaultValue;
    }
    if (p.width) el.style.width = {auto: 'auto', compact: '160px', full: '100%'}[p.width];
  });
  var notes = window.PSAnnotationStore ? window.PSAnnotationStore({project:data.project, version:data.version, page:pid, requirement_ids:page.requirement_ids}, interactions, {
    getItem: function (k) { return localStorage.getItem(k); }, setItem: function (k, v) { localStorage.setItem(k, v); }
  }) : null;
  var key = 'ps.demo.' + data.project + '.' + data.version;
  var memoryState = {};
  // PS_REPLAY_V1: URLs carry only a named synthetic fixture, never user data.
  var replayParams = new URLSearchParams(location.hash.slice(1));
  var replayId = replayParams.get('ps-case');
  var cases = (data.spec.replay_cases || []).filter(function (c) { return c.pages.includes(pid); });
  var replay = cases.find(function (c) { return c.id === replayId; });
  var replayError = replayId !== null && (!replay || replayParams.get('ps-project') !== data.project || replayParams.get('ps-version') !== data.version);
  var run = replayParams.get('ps-run');
  if (!run || !/^[a-z0-9-]{8,80}$/.test(run)) run = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
  var replayKey = key + '.replay.' + replayId + '.' + run;
  var replayStorageUnavailable = false;
  window.addEventListener('hashchange', function () {
    var next = new URLSearchParams(location.hash.slice(1));
    if (next.get('ps-case') !== replayParams.get('ps-case') || next.get('ps-project') !== replayParams.get('ps-project') || next.get('ps-version') !== replayParams.get('ps-version') || next.get('ps-run') !== replayParams.get('ps-run')) location.reload();
  });
  if (replay && !replayError) {
    memoryState = JSON.parse(JSON.stringify(replay.state));
    memoryState.role = replay.role; memoryState.scenario = replay.scenario;
    try { var prior = sessionStorage.getItem(replayKey); if (prior) memoryState = JSON.parse(prior); sessionStorage.setItem(replayKey, JSON.stringify(memoryState)); } catch (_) { replayStorageUnavailable = true; }
  }
  function replayHash(withRun) {
    var p = new URLSearchParams({'ps-case': replayId, 'ps-project': data.project, 'ps-version': data.version});
    if (withRun) p.set('ps-run', run);
    return p.toString();
  }
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
  var api = window.PSPrototype = {
    storageKey: key,
    readState: function () { if (replayId !== null) return JSON.parse(JSON.stringify(memoryState)); try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(memoryState)); } catch (_) { return memoryState; } },
    writeState: function (s) { memoryState = s; try { (replayId !== null ? sessionStorage : localStorage).setItem(replayId !== null ? replayKey : key, JSON.stringify(s)); } catch (_) {} },
    notify: function (message) { var n = document.createElement('div'); n.className = 'ps-notice'; n.setAttribute('role', 'status'); n.textContent = message; document.body.appendChild(n); setTimeout(function () { n.remove(); }, 3000); }
  };
  var tools = document.createElement('div');
  tools.className = 'ps-tools';
  tools.innerHTML = '<strong>' + esc(data.version + ' · ' + page.title) + '</strong><span class="ps-hint">模拟数据演示</span><button type="button" id="ps-mode" aria-pressed="false">标注模式</button><button type="button" id="ps-open">本页需求</button><label>场景 <select id="ps-scenario"><option value="normal">正常</option><option value="empty">空数据</option><option value="loading">加载中</option><option value="error">请求失败</option><option value="forbidden">无权限</option></select></label><button type="button" id="ps-reset">重置演示</button>';
  document.body.prepend(tools);
  if (cases.length || replayId !== null) {
    var caseLabel = document.createElement('label'); caseLabel.textContent = '复现场景 ';
    var caseSelect = document.createElement('select'); caseSelect.id = 'ps-replay-case';
    caseSelect.add(new Option('普通演示', ''));
    cases.forEach(function (c) { caseSelect.add(new Option(c.role + ' · ' + c.title + (c.status === 'pending' ? '（待确认）' : ''), c.id)); });
    caseSelect.value = replayId || ''; caseLabel.appendChild(caseSelect); tools.appendChild(caseLabel);
    caseSelect.onchange = function () {
      replayId = this.value; location.hash = replayId ? replayHash(false) : '';
    };
    var share = document.createElement('button'); share.id = 'ps-replay-share'; share.textContent = '复现链接'; tools.appendChild(share);
    var shareDialog = document.createElement('dialog'); shareDialog.id = 'ps-replay-dialog';
    shareDialog.innerHTML = '<h3>分享场景起点</h3><p>链接还原预设角色、状态和合成数据，不包含后续操作、输入或批注。工作版可能继续变化；正式交接请使用冻结修订链接。file:// 仅适用于有同路径文件的本机，团队访问需固定托管地址。</p><label>项目固定入口<textarea id="ps-replay-project-link" rows="3" readonly></textarea></label><label>独立原型<textarea id="ps-replay-direct-link" rows="3" readonly></textarea></label><button type="button">关闭</button>';
    document.body.appendChild(shareDialog); shareDialog.querySelector('button').onclick = function () { shareDialog.close(); };
    share.onclick = function () {
      if (!replay || replayError) { api.notify('请先选择有效的复现场景'); return; }
      var direct = new URL(location.href); direct.search = ''; direct.hash = replayHash(false);
      var fixed = new URL('../../../../site/index.html', location.href);
      fixed.hash = (data.pageRoutes || {})[pid] + '?' + replayHash(false);
      shareDialog.querySelector('#ps-replay-direct-link').value = direct.href;
      shareDialog.querySelector('#ps-replay-project-link').value = data.pageRoutes && data.pageRoutes[pid] ? fixed.href : '此版本未提供项目路由，请使用独立原型链接';
      shareDialog.showModal();
    };
    if (replayId !== null) {
      var replayStatus = document.createElement('span'); replayStatus.id = 'ps-replay-status'; replayStatus.setAttribute('role', 'status');
      replayStatus.textContent = replayError ? '复现失败：场景不存在或项目/版本不匹配；请切换普通演示。' : '隔离复现 · ' + replay.role + ' · ' + replay.scenario;
      tools.appendChild(replayStatus);
      if (replayStorageUnavailable) replayStatus.textContent += ' · 浏览器存储不可用，跨页修改无法保留';
      tools.querySelector('#ps-scenario').disabled = true;
      if (replayError) { var main = document.querySelector('main'); if (main) main.inert = true; }
    }
  }
  var editToggle = document.createElement('button'); editToggle.type = 'button'; editToggle.id = 'ps-edit-notes'; editToggle.textContent = '编辑标记';
  if (notes) tools.querySelector('#ps-open').after(editToggle);
  var panel = document.createElement('aside');
  panel.className = 'ps-panel'; panel.hidden = true; panel.setAttribute('aria-label', '本页需求');
  panel.innerHTML = '<div class="ps-panel-head"><strong>本页需求 · 拖动此处</strong><button type="button" id="ps-dock">停靠</button><button type="button" id="ps-close" aria-label="收起本页需求">收起</button></div><div class="ps-panel-content"></div>';
  document.body.appendChild(panel);
  var body = panel.querySelector('.ps-panel-content');
  var editor = document.createElement('aside'); editor.className = 'ps-note-editor'; editor.hidden = true; editor.setAttribute('aria-label', '编辑原型标记');
  editor.innerHTML = '<header><strong>管理原型标记</strong><button type="button" id="ps-notes-close">收起</button></header><p class="ps-hint">新增后直接点击原型控件或位置填写标注。删除标记不会删除需求。</p><div class="ps-note-actions"><button type="button" id="ps-note-add">新增标记</button><button type="button" id="ps-note-undo">撤销</button><button type="button" id="ps-note-export">导出</button><button type="button" id="ps-note-import">导入</button><input id="ps-note-file" type="file" accept="application/json,.json" hidden></div><p id="ps-note-status" role="status"></p><label class="ps-note-deleted"><input id="ps-note-show-deleted" type="checkbox">显示已删除标记</label><div id="ps-note-items"></div>';
  if (notes) document.body.appendChild(editor);
  var notePopover = document.createElement('aside'); notePopover.className = 'ps-note-popover'; notePopover.hidden = true; notePopover.setAttribute('aria-label', '原型标注');
  notePopover.innerHTML = '<div id="ps-note-view" hidden><header><strong>查看标注</strong><button type="button" data-note-close>关闭</button></header><span id="ps-note-view-level" class="ps-note-level"></span><p id="ps-note-view-text"></p><p id="ps-note-view-meta" class="ps-hint"></p><div class="ps-note-actions"><button type="button" id="ps-note-view-edit">编辑</button><button type="button" id="ps-note-view-delete">删除</button></div></div><form id="ps-note-form" hidden><header><strong id="ps-note-heading">新增标记</strong><button type="button" data-note-close>关闭</button></header><label>标注优先级<select id="ps-note-level"><option value="crit">P0 · 核心（红）</option><option value="warn">P1 · 重要/待确认（黄）</option><option value="info">P2 · 一般说明（蓝）</option><option value="ok">参考信息（绿）</option></select></label><label>说明内容<textarea id="ps-note-text" rows="4" maxlength="2000" required placeholder="例如：点击后打开退款弹框；超过 3 天时禁用。"></textarea></label><div class="ps-note-actions"><button type="submit">确认增加</button><button id="ps-note-cancel" type="button">取消</button><button id="ps-note-delete" type="button" hidden>删除此标记</button></div><p id="ps-note-form-status" role="status"></p></form>';
  if (notes) document.body.appendChild(notePopover);
  var reviewNames = {pending:'待处理',accepted:'已采纳',rejected:'已驳回',completed:'已完成'};
  var reviewForm = document.createElement('form'); reviewForm.id='ps-review-form'; reviewForm.hidden=true;
  reviewForm.innerHTML='<header><strong>处理批注</strong></header><label>处理状态<select id="ps-review-state"><option value="pending">待处理</option><option value="accepted">已采纳</option><option value="rejected">已驳回</option><option value="completed">已完成</option></select></label><label>处理说明<textarea id="ps-review-note" maxlength="2000"></textarea></label><label>关联需求（逗号分隔）<input id="ps-review-refs"></label><label>正式修改记录 ID<input id="ps-review-change" maxlength="200"></label><label>验证说明<textarea id="ps-review-evidence" maxlength="2000"></textarea></label><p>状态由评审人填写；采纳不会自动改 PRD。完成需关联修改记录及验证说明。</p><button type="submit">保存处理</button><button type="button" id="ps-review-cancel">取消</button><p id="ps-review-error" role="status"></p>';
  notePopover.appendChild(reviewForm);
  var reviewRead = document.createElement('div'); reviewRead.id='ps-review-read'; notePopover.querySelector('#ps-note-view').appendChild(reviewRead);
  var reviewButton=document.createElement('button');reviewButton.type='button';reviewButton.textContent='处理批注';reviewButton.id='ps-review-open';notePopover.querySelector('#ps-note-view').appendChild(reviewButton);
  var reviewFilter=document.createElement('select');reviewFilter.id='ps-review-filter';reviewFilter.setAttribute('aria-label','批注处理状态筛选');reviewFilter.add(new Option('全部处理状态','all'));Object.keys(reviewNames).forEach(function(k){reviewFilter.add(new Option(reviewNames[k],k));});editor.querySelector('#ps-note-items').before(reviewFilter);reviewFilter.onchange=function(){refreshEditor();};
  var deleteSelected = notePopover.querySelector('#ps-note-delete');
  var placement = document.createElement('div'); placement.className = 'ps-note-placement'; placement.hidden = true;
  placement.innerHTML = '<span>点击原型位置新增标记 · Esc 取消</span><button type="button">取消放置</button>';
  if (notes) document.body.appendChild(placement);
  var editingId = null, pendingAnchor = null, adding = false;
  var requirements = data.spec.requirements.filter(function (r) { return page.requirement_ids.includes(r.id); });
  body.innerHTML = '<h2>' + esc(page.title) + '</h2><p>' + esc(page.purpose || '') + '</p><p class="ps-hint">红：核心 · 黄：待确认 · 蓝：说明 · 绿：参考。标注模式点击控件可定位需求。</p><div class="ps-annotation-list">' + interactions.map(function (i, n) {
    return '<button type="button" data-interaction="' + esc(i.id) + '" data-level="' + esc(i.level || 'info') + '">' + (n + 1) + ' · ' + esc(i.description) + '</button>';
  }).join('') + '</div>' + requirements.map(function (r) {
    return '<article id="req-' + esc(r.id) + '"><h3>' + esc(r.id + ' · ' + r.title) + '</h3><p class="ps-hint">' + esc((r.source === 'origin' ? '原文依据' : 'AI 推断') + ' · ' + (r.status === 'confirmed' ? '已确认' : '待确认') + (r.blocking ? ' · 阻塞开发' : '')) + '</p><p>' + esc(r.description || '') + '</p><dl>' + Object.keys(r.rules || {}).map(function (k) { return '<dt>' + esc(k) + '</dt><dd>' + esc(r.rules[k]) + '</dd>'; }).join('') + '</dl><h4>验收标准</h4>' + r.acceptance.map(function (a) { return '<p>' + esc(a.id + ' · Given ' + a.given + '；When ' + a.when + '；Then ' + a.then) + '</p>'; }).join('') + '<button type="button" data-requirement="' + esc(r.id) + '">定位页面元素</button></article>';
  }).join('');
  requirements.forEach(function (r) {
    var article = document.getElementById('req-' + r.id);
    (r.rule_details || []).forEach(function (rule) {
      var section = document.createElement('section');
      section.innerHTML = '<h4>' + esc(rule.id + ' · ' + rule.category) + '</h4><p>' + esc(rule.statement) + '</p><p class="ps-hint">' + esc((rule.source === 'origin' ? '原文依据' : 'AI 推断') + ' · ' + (rule.status === 'confirmed' ? '已确认' : '待确认')) + '</p>' + (rule.examples || []).map(function (example) {
        return '<p>' + esc('实例：' + example.input + ' → 预期：' + example.expected) + '</p>';
      }).join('') + '<p>' + esc('关联验收：' + (rule.acceptance_ids || []).join('、')) + '</p>';
      article.insertBefore(section, article.querySelector('h4'));
    });
  });
  var inspectBox = document.createElement('section');
  inspectBox.className = 'ps-inspector';
  inspectBox.innerHTML = '<h3>控件与数据规则</h3><label>查看元素 <select id="ps-inspect-select"><option value="">选择元素（含隐藏或禁用控件）</option></select></label><label><input type="checkbox" id="ps-inspect-pending">仅看待确认规则</label><div id="ps-inspect-detail" aria-live="polite"></div>';
  body.prepend(inspectBox);
  var inspectSelect = inspectBox.querySelector('select');
  interactions.forEach(function (it) { var option = document.createElement('option'); option.value = it.id; option.textContent = it.id + ' · ' + it.description; inspectSelect.appendChild(option); });
  function inspect(it) {
    inspectSelect.value = it.id;
    var pending = inspectBox.querySelector('input').checked;
    var html = '<h4>' + esc(it.description) + '</h4><p>' + esc(it.selector + ' · ' + it.action + (it.target ? ' → ' + it.target : '')) + '</p>';
    var propertyNames = {text:'控件文案', placeholder:'占位提示', defaultValue:'默认值', maxLength:'最大长度', required:'必填', options:'选项', width:'宽度'};
    html += '<dl>' + Object.keys(it.properties || {}).map(function (key) { return '<dt>' + esc(propertyNames[key] || key) + '</dt><dd>' + esc(JSON.stringify(it.properties[key])) + '</dd>'; }).join('') + '</dl>';
    var matched = 0;
    requirements.filter(function (r) { return it.requirement_ids.includes(r.id); }).forEach(function (r) {
      var rules = (r.rule_details || []).filter(function (rule) { return (!it.rule_ids || it.rule_ids.includes(rule.id)) && (!pending || rule.status === 'pending'); });
      if (!it.rule_ids && (!pending || r.status === 'pending')) {
        html += '<p class="ps-hint">未指定控件级规则，以下为关联需求规则；请复核适用范围。</p><dl>' + Object.keys(r.rules || {}).map(function (key) { matched++; return '<dt>' + esc(key) + '</dt><dd>' + esc(r.rules[key]) + '</dd>'; }).join('') + '</dl>';
      }
      rules.forEach(function (rule) {
        matched++;
        html += '<h4>' + esc(rule.category + ' · ' + rule.id) + '</h4><p>' + esc(rule.statement) + '</p><p class="ps-hint">' + esc((rule.source === 'origin' ? '原文依据' : 'AI 推断') + ' · ' + (rule.status === 'confirmed' ? '已确认' : '待确认')) + '</p>';
        (rule.examples || []).forEach(function (e) { html += '<p>' + esc('实例：' + e.input + ' → ' + e.expected) + '</p>'; });
      });
      var acIds = rules.reduce(function (ids, rule) { return ids.concat(rule.acceptance_ids || []); }, []);
      (r.acceptance || []).filter(function (ac) { return it.rule_ids ? acIds.includes(ac.id) : (!pending || r.status === 'pending' || acIds.includes(ac.id)); }).forEach(function (ac) {
        html += '<p>' + esc(ac.id + ' · Given ' + ac.given + '；When ' + ac.when + '；Then ' + ac.then) + '</p>';
      });
    });
    if (!matched) html += '<p>当前筛选下没有规则；未填写不代表无约束。</p>';
    inspectBox.querySelector('#ps-inspect-detail').innerHTML = html;
    body.scrollTop = 0;
  }
  inspectSelect.onchange = function () { var it = interactions.find(function (i) { return i.id === inspectSelect.value; }); if (it) { inspect(it); highlight(it); } };
  inspectBox.querySelector('input').onchange = function () { var it = interactions.find(function (i) { return i.id === inspectSelect.value; }); if (it) inspect(it); };
  function highlight(it) {
    document.querySelectorAll('.ps-highlight').forEach(function (el) { el.classList.remove('ps-highlight'); });
    var el = document.querySelector(it.selector);
    if (el) {
      var dialog = el.closest('dialog');
      if (dialog && !dialog.open) dialog.showModal();
      if (dialog) dialog.appendChild(panel);
      el.classList.add('ps-highlight'); el.scrollIntoView({block: 'center', behavior: 'smooth'});
    }
  }
  function show(it) {
    if (notes) { stopAdding(); editor.hidden = true; }
    panel.hidden = false;
    if (it) {
      highlight(it);
      inspect(it);
    }
  }
  tools.querySelector('#ps-open').onclick = function () { show(); document.body.classList.toggle('ps-panel-docked', panel.classList.contains('ps-docked')); };
  panel.querySelector('#ps-close').onclick = function () { panel.hidden = true; document.body.classList.remove('ps-panel-docked'); tools.querySelector('#ps-open').focus(); };
  panel.querySelector('#ps-dock').onclick = function () {
    var docked = panel.classList.toggle('ps-docked'); document.body.classList.toggle('ps-panel-docked', docked);
    this.textContent = docked ? '浮动' : '停靠';
  };
  tools.querySelector('#ps-mode').onclick = function () {
    var active = document.body.classList.toggle('ps-annotate'); this.setAttribute('aria-pressed', String(active)); this.textContent = active ? '返回演示' : '标注模式';
    if (active) show(); else if (notes) { stopAdding(); editor.hidden = true; }
  };
  tools.querySelector('#ps-scenario').onchange = function () {
    var state = api.readState(); state.scenario = this.value; api.writeState(state);
    document.dispatchEvent(new CustomEvent('ps:scenario', {detail: this.value}));
  };
  tools.querySelector('#ps-scenario').value = api.readState().scenario || 'normal';
  tools.querySelector('#ps-reset').onclick = function () { try { if (replayId !== null) sessionStorage.removeItem(replayKey); else localStorage.removeItem(key); } catch (_) {} location.reload(); };
  body.addEventListener('click', function (event) {
    var button = event.target.closest('button'); if (!button) return;
    var it = interactions.find(function (i) { return i.id === button.dataset.interaction || i.requirement_ids.includes(button.dataset.requirement); });
    if (it) { highlight(it); if (button.dataset.interaction) show(it); }
  });
  var markers = document.createElement('div'); markers.className = 'ps-markers'; document.body.appendChild(markers);
  function visibleNotes() { return notes ? notes.list().filter(function (i) { return !i.hidden; }) : interactions.map(function (i, n) { return Object.assign({}, i, {number:String(n+1)}); }); }
  function targetOf(item) { try { var el = document.querySelector(item.selector); return el && !el.closest('.ps-tools,.ps-panel,.ps-note-editor,.ps-note-popover,.ps-markers,.ps-dialog-review') ? el : null; } catch (_) { return null; } }
  function rebuildMarkers() {
    markers.textContent = '';
    document.querySelectorAll('[data-ps-number]').forEach(function (el) { delete el.dataset.psNumber; });
    visibleNotes().forEach(function (it) {
      var el = targetOf(it); if (el) el.dataset.psNumber = it.number;
      var mark = document.createElement('button'); mark.type = 'button'; mark.className = 'ps-marker'; mark.dataset.level = it.level || 'info'; mark.dataset.noteId = it.id;
      mark.textContent = it.number; mark.title = it.description; mark.setAttribute('aria-label', '标注 ' + it.number + '：' + it.description);
      mark.onclick = function (event) { if (notes) openView(it, event.clientX, event.clientY); else show(it); }; markers.appendChild(mark);
    });
    var list = body.querySelector('.ps-annotation-list');
    list.innerHTML = visibleNotes().map(function (it) { return '<button type="button" data-note-id="' + esc(it.id) + '" data-level="' + esc(it.level || 'info') + '">' + esc(it.number + ' · ' + it.description) + '</button>'; }).join('');
    positionMarkers();
  }
  body.querySelector('.ps-annotation-list').addEventListener('click', function (event) {
    var button = event.target.closest('[data-note-id]'); if (!button) return;
    var it = visibleNotes().find(function (i) { return i.id === button.dataset.noteId; });
    if (it) { if (notes) openView(it); else show(it); }
  });
  function positionMarkers() {
    visibleNotes().forEach(function (it, index) {
      var el = targetOf(it), mark = markers.children[index]; if (!mark) return;
      var rect = el && el.getBoundingClientRect();
      mark.hidden = !rect || !rect.width || !rect.height || rect.bottom < 40 || rect.top > innerHeight || rect.right < 0 || rect.left > innerWidth;
      if (!mark.hidden) { mark.style.left = Math.max(0, rect.left + rect.width * (it.manual ? it.x : 1) - 9) + 'px'; mark.style.top = Math.max(40, rect.top + rect.height * (it.manual ? it.y : 0) - 11) + 'px'; }
    });
  }
  rebuildMarkers();
  window.addEventListener('resize', positionMarkers); document.addEventListener('scroll', positionMarkers, true);
  new ResizeObserver(positionMarkers).observe(document.body); positionMarkers();
  document.querySelectorAll('dialog:not(#ps-replay-dialog)').forEach(function (dialog) {
    var review = document.createElement('button'); review.type = 'button'; review.className = 'ps-dialog-review'; review.textContent = '查看弹框需求';
    review.onclick = function () { dialog.appendChild(panel); show(interactions.find(function (it) { var el = document.querySelector(it.selector); return el && dialog.contains(el); })); };
    dialog.appendChild(review);
    if (notes) {
      var editDialog = document.createElement('button'); editDialog.type = 'button'; editDialog.className = 'ps-dialog-review'; editDialog.textContent = '编辑弹框标记';
      editDialog.onclick = function () { if (editor.hidden) editToggle.onclick(); dialog.appendChild(editor); editor.hidden = false; };
      dialog.appendChild(editDialog);
    }
    dialog.addEventListener('close', function () { document.body.appendChild(panel); positionMarkers(); });
  });
  document.addEventListener('click', function (event) {
    if (tools.contains(event.target) || panel.contains(event.target) || markers.contains(event.target) || editor.contains(event.target) || notePopover.contains(event.target) || placement.contains(event.target) || event.target.closest('.ps-dialog-review,#ps-replay-dialog')) return;
    if (adding) {
      event.preventDefault(); event.stopImmediatePropagation();
      var target = event.target.closest('button,input,select,textarea,a,[role="button"],[id]') || event.target;
      if (!(target instanceof Element) || target === document.body || target === document.documentElement) return;
      var rect = target.getBoundingClientRect();
      pendingAnchor = {selector: selectorFor(target), x: Math.max(0, Math.min(1, (event.clientX - rect.left) / (rect.width || 1))), y: Math.max(0, Math.min(1, (event.clientY - rect.top) / (rect.height || 1)))};
      stopAdding(); var dialog = target.closest('dialog'); if (dialog) dialog.appendChild(notePopover);
      editingId = null; openForm('新增标记', '', 'info', event.clientX, event.clientY); return;
    }
    var it = interactions.find(function (i) { return event.target.closest(i.selector); });
    if (!it) return;
    if (document.body.classList.contains('ps-annotate')) { event.preventDefault(); event.stopImmediatePropagation(); show(it); return; }
    if (it.action === 'navigate') {
      event.preventDefault();
      var file = data.pageFiles[it.target];
      if (file) { var destination = new URL('../' + file, location.href); if (replayId !== null) destination.hash = replayHash(true); location.href = destination.href; }
    } else if (['dialog', 'close', 'toggle'].includes(it.action)) {
      event.preventDefault(); var target = document.getElementById(it.target);
      if (!target) return;
      if (it.action === 'dialog') { if (target.showModal) target.showModal(); else target.hidden = false; }
      if (it.action === 'close') { if (target.close) target.close(); else target.hidden = true; }
      if (it.action === 'toggle') target.hidden = !target.hidden;
    }
  }, true);
  document.addEventListener('submit', function (event) {
    if (editor.contains(event.target) || notePopover.contains(event.target)) return;
    if (document.body.classList.contains('ps-annotate')) { event.preventDefault(); event.stopImmediatePropagation(); show(); }
  }, true);
  function selectorFor(el) {
    var parts = [];
    while (el && el !== document.body) {
      if (el.id) { parts.unshift('#' + CSS.escape(el.id)); break; }
      var siblings = Array.from(el.parentElement.children).filter(function (s) { return s.tagName === el.tagName; });
      parts.unshift(el.tagName.toLowerCase() + ':nth-of-type(' + (siblings.indexOf(el) + 1) + ')'); el = el.parentElement;
    }
    return parts.join(' > ');
  }
  function status(message) { editor.querySelector('#ps-note-status').textContent = message; }
  function formStatus(message) { notePopover.querySelector('#ps-note-form-status').textContent = message || ''; }
  function stopAdding() { adding = false; placement.hidden = true; document.body.classList.remove('ps-adding-note'); }
  function positionPopover(x, y) {
    notePopover.hidden = false;
    var width = Math.min(360, innerWidth - 24), left = Number.isFinite(x) ? x + 14 : innerWidth / 2 - width / 2;
    var top = Number.isFinite(y) ? y + 14 : 64;
    notePopover.style.width = width + 'px';
    notePopover.style.left = Math.max(12, Math.min(innerWidth - width - 12, left)) + 'px';
    notePopover.style.top = Math.max(48, Math.min(innerHeight - notePopover.offsetHeight - 12, top)) + 'px';
  }
  function openForm(title, text, level, x, y) {
    reviewForm.hidden=true;
    deleteSelected.hidden = !editingId;
    notePopover.querySelector('#ps-note-view').hidden = true;
    var form = notePopover.querySelector('#ps-note-form'); form.hidden = false;
    notePopover.querySelector('#ps-note-heading').textContent = title;
    notePopover.querySelector('#ps-note-text').value = text; notePopover.querySelector('#ps-note-level').value = level;
    form.querySelector('button[type="submit"]').textContent = editingId ? '确认修改' : '确认增加';
    formStatus(''); positionPopover(x, y); notePopover.querySelector('#ps-note-text').focus();
  }
  function openEdit(it) {
    stopAdding(); pendingAnchor = null; editingId = it.id;
    panel.hidden = true; document.body.classList.remove('ps-panel-docked');
    var target = targetOf(it), dialog = target && target.closest('dialog'); if (dialog && dialog.open) dialog.appendChild(notePopover);
    var rect = target && target.getBoundingClientRect();
    openForm('编辑标记 ' + it.number, it.description, it.level || 'info', rect && rect.right, rect && rect.top);
  }
  function priorityLabel(level) {
    return {crit:'P0 · 核心', warn:'P1 · 重要/待确认', info:'P2 · 一般说明', ok:'参考信息'}[level] || 'P2 · 一般说明';
  }
  function openView(it, x, y) {
    reviewForm.hidden=true;
    stopAdding(); editingId = it.id; pendingAnchor = null;
    editor.hidden = true;
    var target = targetOf(it), dialog = target && target.closest('dialog'); if (dialog && dialog.open) dialog.appendChild(notePopover);
    notePopover.querySelector('#ps-note-form').hidden = true;
    var view = notePopover.querySelector('#ps-note-view'); view.hidden = false;
    var level = notePopover.querySelector('#ps-note-view-level'); level.textContent = priorityLabel(it.level); level.dataset.level = it.level || 'info';
    notePopover.querySelector('#ps-note-view-text').textContent = it.description;
    notePopover.querySelector('#ps-note-view-meta').textContent = (it.manual ? '手动标注' : '需求标注') + (it.requirement_ids && it.requirement_ids.length ? ' · ' + it.requirement_ids.join('、') : '');
    var review=it.review || {status:'pending',history:[]};
    reviewRead.textContent=reviewNames[review.status]+' · '+(review.note || '尚未处理')+(review.requirement_ids && review.requirement_ids.length?' · 关联 '+review.requirement_ids.join('、'):'')+(review.change_ref?' · 修改记录 '+review.change_ref:'')+(review.evidence?' · 验证：'+review.evidence:'');
    var history=document.createElement('details'), summary=document.createElement('summary'); summary.textContent='处理历史（本机记录）';history.appendChild(summary);(review.history || []).forEach(function(e){var p=document.createElement('p');p.textContent=e.at+' '+reviewNames[e.from]+' → '+reviewNames[e.to]+'：'+e.note;history.appendChild(p);});reviewRead.appendChild(history);
    reviewButton.onclick=function(){view.hidden=true;reviewForm.hidden=false;reviewForm.querySelector('#ps-review-state').value=review.status;reviewForm.querySelector('#ps-review-note').value=review.note || '';reviewForm.querySelector('#ps-review-refs').value=(review.requirement_ids || []).join(',');reviewForm.querySelector('#ps-review-change').value=review.change_ref || '';reviewForm.querySelector('#ps-review-evidence').value=review.evidence || '';reviewForm.querySelector('#ps-review-error').textContent='';positionPopover();};
    notePopover.querySelector('#ps-note-view-edit').onclick = function () { openEdit(it); };
    notePopover.querySelector('#ps-note-view-delete').onclick = function () { notes.hide(it.id); notePopover.hidden = true; editingId = null; refreshEditor('标记已删除，可撤销；对应需求仍保留。'); };
    var rect = target && target.getBoundingClientRect(); positionPopover(Number.isFinite(x) ? x : rect && rect.right, Number.isFinite(y) ? y : rect && rect.top);
  }
  function refreshEditor(message) {
    var all = notes.list(), showDeleted = editor.querySelector('#ps-note-show-deleted').checked;
    editor.querySelector('#ps-note-items').innerHTML = all.filter(function (it) { return (showDeleted || !it.hidden) && (reviewFilter.value==='all' || it.review.status===reviewFilter.value); }).map(function (it) {
      var target = targetOf(it);
      return '<article class="ps-note-item"><strong>' + esc(it.number + ' · ' + reviewNames[it.review.status] + (it.hidden ? ' · 已删除' : '')) + '</strong><p>' + esc(it.description) + '</p>' + (!target ? '<p class="ps-hint">目标元素暂不存在，可切换场景查找。</p>' : '') + '<div class="ps-note-actions">' + (it.hidden ? '<button type="button" data-note-action="restore" data-id="' + esc(it.id) + '">恢复</button>' : '<button type="button" data-note-action="edit" data-id="' + esc(it.id) + '">编辑</button><button type="button" data-note-action="delete" data-id="' + esc(it.id) + '">删除</button>') + '</div></article>';
    }).join('') || '<p>暂无标记。点击“新增标记”后在原型中选择位置。</p>';
    editor.querySelector('#ps-note-undo').disabled = !notes.canUndo();
    rebuildMarkers(); status(notes.warning() || message || '修改自动保存在当前浏览器。');
  }
  if (notes) {
    reviewForm.querySelector('#ps-review-cancel').onclick=function(){openView(notes.list().find(function(i){return i.id===editingId;}));};
    reviewForm.onsubmit=function(event){event.preventDefault();try{notes.review(editingId,{status:reviewForm.querySelector('#ps-review-state').value,note:reviewForm.querySelector('#ps-review-note').value,requirement_ids:reviewForm.querySelector('#ps-review-refs').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean),change_ref:reviewForm.querySelector('#ps-review-change').value,evidence:reviewForm.querySelector('#ps-review-evidence').value});refreshEditor();openView(notes.list().find(function(i){return i.id===editingId;}));}catch(e){reviewForm.querySelector('#ps-review-error').textContent=e.message;}};
    notePopover.querySelectorAll('[data-note-close]').forEach(function (button) { button.onclick = function () { notePopover.hidden = true; pendingAnchor = null; editingId = null; }; });
    deleteSelected.onclick = function () { if (!editingId) return; notes.hide(editingId); editingId = null; notePopover.hidden = true; refreshEditor('标记已删除，可撤销；对应需求仍保留。'); };
    editToggle.onclick = function () { editor.hidden = !editor.hidden; if (!editor.hidden) { document.body.classList.add('ps-annotate'); tools.querySelector('#ps-mode').textContent = '返回演示'; tools.querySelector('#ps-mode').setAttribute('aria-pressed', 'true'); panel.hidden = true; document.body.classList.remove('ps-panel-docked'); refreshEditor(); } else stopAdding(); };
    editor.querySelector('#ps-notes-close').onclick = function () { stopAdding(); editor.hidden = true; };
    editor.querySelector('#ps-note-add').onclick = function () { adding = true; editingId = null; pendingAnchor = null; notePopover.hidden = true; document.body.classList.add('ps-adding-note'); var dialog = editor.closest('dialog'); (dialog || document.body).appendChild(placement); placement.hidden = false; editor.hidden = true; };
    placement.querySelector('button').onclick = function () { stopAdding(); editor.hidden = false; status('已取消新增标记。'); };
    notePopover.querySelector('#ps-note-cancel').onclick = function () { stopAdding(); pendingAnchor = null; editingId = null; notePopover.hidden = true; };
    notePopover.querySelector('#ps-note-form').onsubmit = function (event) {
      event.preventDefault();
      var text = notePopover.querySelector('#ps-note-text').value.trim(), level = notePopover.querySelector('#ps-note-level').value;
      if (!text) { formStatus('请填写说明内容。'); return; }
      try {
        if (editingId) notes.edit(editingId, text, level);
        else if (pendingAnchor) notes.add(Object.assign({id: 'manual-' + (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2)), description:text, level:level}, pendingAnchor));
        else { status('请先选择原型上的标记位置。'); return; }
        pendingAnchor = null; editingId = null; notePopover.hidden = true; refreshEditor('标记已保存到当前浏览器。');
      } catch (error) { formStatus(error.message); }
    };
    editor.querySelector('#ps-note-items').onclick = function (event) {
      var button = event.target.closest('[data-note-action]'); if (!button) return;
      var item = notes.list().find(function (i) { return i.id === button.dataset.id; });
      if (button.dataset.noteAction === 'edit') openView(item);
      else { if (button.dataset.noteAction === 'delete') notes.hide(item.id); else notes.restore(item.id); refreshEditor('已更新标记，可撤销。需求文档未改变。'); }
    };
    editor.querySelector('#ps-note-show-deleted').onchange = function () { refreshEditor(); };
    editor.querySelector('#ps-note-undo').onclick = function () { notes.undo(); notePopover.hidden = true; pendingAnchor = null; editingId = null; refreshEditor('已撤销上一步标记修改。'); };
    editor.querySelector('#ps-note-export').onclick = function () {
      var blob = new Blob([JSON.stringify(notes.exportData(), null, 2)], {type:'application/json'}), url = URL.createObjectURL(blob);
      var a = document.createElement('a'); a.href = url; a.download = data.version + '-' + pid + '-annotations.json'; a.click(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000); status('已导出本页标记，原型和需求文件未修改。');
    };
    editor.querySelector('#ps-note-import').onclick = function () { editor.querySelector('#ps-note-file').click(); };
    editor.querySelector('#ps-note-file').onchange = async function () {
      var file = this.files[0]; this.value = ''; if (!file) return;
      if (file.size > 1024 * 1024) { status('标记文件不能超过 1MB。'); return; }
      try { var value = JSON.parse(await file.text()); notes.importData(value); notePopover.hidden = true; refreshEditor('已导入并替换本页标记，可点“撤销”恢复导入前状态。'); } catch (error) { status('导入失败：' + error.message); }
    };
    document.addEventListener('keydown', function (event) { if (event.key === 'Escape' && adding) { stopAdding(); editor.hidden = false; status('已取消新增标记。'); } });
    document.querySelectorAll('dialog').forEach(function (dialog) { dialog.addEventListener('close', function () { if (dialog.contains(editor)) document.body.appendChild(editor); if (dialog.contains(notePopover)) document.body.appendChild(notePopover); }); });
  }
  new MutationObserver(function () { positionMarkers(); }).observe(document.body, {childList:true, subtree:true});
  var head = panel.querySelector('.ps-panel-head');
  head.addEventListener('pointerdown', function (event) {
    if (event.target.closest('button') || panel.classList.contains('ps-docked')) return;
    var rect = panel.getBoundingClientRect(), dx = event.clientX - rect.left, dy = event.clientY - rect.top;
    head.setPointerCapture(event.pointerId);
    function move(e) {
      // Runtime geometry is necessary for dragging; authored HTML remains inline-free.
      panel.style.left = Math.max(0, Math.min(innerWidth - panel.offsetWidth, e.clientX - dx)) + 'px';
      panel.style.top = Math.max(0, Math.min(innerHeight - 60, e.clientY - dy)) + 'px'; panel.style.right = 'auto';
    }
    function end() { head.removeEventListener('pointermove', move); head.removeEventListener('pointerup', end); head.removeEventListener('pointercancel', end); }
    head.addEventListener('pointermove', move); head.addEventListener('pointerup', end); head.addEventListener('pointercancel', end);
  });
})();
