/* Same spec renders the PRD and standalone draggable page panel; no fetch. */
(function () {
  'use strict';
  // PS_ERROR_SURFACE_V1: 脚本错误必须可见；静默失败会让需求面板/场景切换悄悄失效，破坏评审信任。
  var errorSurface = document.createElement('div');
  errorSurface.className = 'ps-error-surface';
  errorSurface.setAttribute('role', 'alert');
  errorSurface.hidden = true;
  document.body.appendChild(errorSurface);
  function surfaceError(text) {
    var line = document.createElement('div');
    line.textContent = text + '；本页需求面板/场景切换可能不完整，请反馈维护者';
    errorSurface.appendChild(line);
    errorSurface.hidden = false;
  }
  window.addEventListener('error', function (event) {
    if (!event || !event.message) return;
    var where = (event.filename || '').split('/').pop();
    surfaceError('原型脚本错误：' + event.message + (where ? '（' + where + (event.lineno ? ':' + event.lineno : '') + '）' : ''));
  });
  window.addEventListener('unhandledrejection', function (event) {
    var reason = event && event.reason;
    surfaceError('未处理的 Promise 拒绝：' + ((reason && (reason.message || reason)) || '未知原因'));
  });
  var data = window.PS_SPEC;
  if (!data) return;
  var pid = document.body.dataset.pageId;
  var page = data.spec.pages.find(function (p) { return p.id === pid; });
  if (!page) return;
  var interactions = data.spec.interactions.filter(function (i) { return i.page === pid; });
  // PS_DISCOVER_V1: 查看说明模式下，带规则的控件以虚线框现形——开发不必盲点试探。
  interactions.forEach(function (i) { var el = document.querySelector(i.selector); if (el) el.classList.add('ps-declared'); });
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
    ['min', 'max', 'step', 'accept', 'pattern'].forEach(function (k) {
      if (Object.prototype.hasOwnProperty.call(p, k) && el.tagName === 'INPUT') el.setAttribute(k, p[k]);
    });
    if (Object.prototype.hasOwnProperty.call(p, 'unit')) el.setAttribute('data-unit', p.unit);
  });
  var savedNotes=(data.spec.review_notes || {})[pid];
  var savedFrom=savedNotes && savedNotes.version;
  if(savedNotes){savedNotes=JSON.parse(JSON.stringify(savedNotes));savedNotes.project=data.project;savedNotes.version=data.version;}
  var noteContext={project:data.project, version:data.version, page:pid, requirement_ids:page.requirement_ids,saved:savedNotes};
  var draftBaseRevision=(data.noteRevisions || {})[pid] || null;
  var notes = window.PSAnnotationStore ? window.PSAnnotationStore(noteContext, interactions, {
    getItem: function (k) { var local=localStorage.getItem(k);if(local)draftBaseRevision=JSON.parse(localStorage.getItem(k+'.base') || 'null');return local; }, setItem: function (k, v) { localStorage.setItem(k, v);localStorage.setItem(k+'.base',JSON.stringify(draftBaseRevision)); }
  }) : null;
  var draftNotes=notes, editingMode=false, movingId=null, hoverTarget=null, formOriginal='', returnFocus=null;
  var sharedNotes=window.PSAnnotationStore?window.PSAnnotationStore(noteContext,interactions,{getItem:function(){return null;},setItem:function(){}}):null;
  notes=sharedNotes;
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
  // PS_HOST_LAYOUT_V1: 工具栏 prepend 到 body 且 sticky 吸顶，要求 body 为常规块级流。
  // 页面 CSS 误用 body flex/grid 会把工具栏与画布并排（真实事故），这里加类供运行时 CSS 强制纠正。
  document.body.classList.add('ps-host');
  var tools = document.createElement('div');
  tools.className = 'ps-tools';
  tools.innerHTML = '<strong>' + esc(data.version + ' · ' + page.title) + '</strong><span class="ps-hint">模拟数据演示' + ((data.build && data.build.template) ? ' · 模板 v' + esc(data.build.template) : '') + ((data.build && data.build.generated_at) ? ' · 构建 ' + esc(String(data.build.generated_at).slice(0, 10)) : '') + '</span><button type="button" id="ps-mode" aria-pressed="false">查看说明</button><button type="button" id="ps-open">本页需求</button><label>场景 <select id="ps-scenario"><option value="normal">正常</option><option value="empty">空数据</option><option value="loading">加载中</option><option value="error">请求失败</option><option value="forbidden">无权限</option></select></label><button type="button" id="ps-reset">重置演示</button>';
  document.body.prepend(tools);
  var pageIdentity = document.createElement('code'); pageIdentity.id = 'ps-page-id';
  pageIdentity.textContent = '页面：' + pid;
  pageIdentity.title = '稳定页面编号；修改时同时提供项目和版本 ' + data.version;
  tools.querySelector('strong').after(pageIdentity);
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
  var manageButton=document.createElement('button');manageButton.type='button';manageButton.id='ps-note-manage';manageButton.textContent='管理批注';manageButton.hidden=true;editToggle.after(manageButton);manageButton.onclick=function(){if(editingMode && closeNote()){editor.hidden=false;refreshEditor();}};
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
  body.innerHTML = '<p class="ps-hint">「查看说明」模式下点击画布中带虚线框的控件，可直接定位它的规则与验收。</p><h2>' + esc(page.title) + '</h2><p>' + esc(page.purpose || '') + '</p><p class="ps-hint">红：核心 · 黄：待确认 · 蓝：说明 · 绿：参考。查看说明模式点击控件可定位需求。</p><div class="ps-annotation-list">' + interactions.map(function (i, n) {
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
      var h4Anchor = Array.prototype.find.call(article.children, function (c) { return c.tagName === 'H4'; });
      article.insertBefore(section, h4Anchor || null);
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
    var propertyNames = {text:'控件文案', placeholder:'占位提示', defaultValue:'默认值', maxLength:'最大长度', required:'必填', options:'选项', width:'宽度', min:'最小值', max:'最大值', step:'步进', unit:'单位', pattern:'格式校验', accept:'可接受文件类型'};
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
  if (window.innerWidth >= 1180 && !panel.classList.contains('ps-docked')) { panel.classList.add('ps-docked'); document.body.classList.add('ps-panel-docked'); panel.querySelector('#ps-dock').textContent = '浮动'; }
  tools.querySelector('#ps-open').onclick = function () { show(); document.body.classList.toggle('ps-panel-docked', panel.classList.contains('ps-docked')); };
  panel.querySelector('#ps-close').onclick = function () { panel.hidden = true; document.body.classList.remove('ps-panel-docked'); tools.querySelector('#ps-open').focus(); };
  panel.querySelector('#ps-dock').onclick = function () {
    var docked = panel.classList.toggle('ps-docked'); document.body.classList.toggle('ps-panel-docked', docked);
    this.textContent = docked ? '浮动' : '停靠';
  };
  tools.querySelector('#ps-mode').onclick = function () {
    if(!closeNote())return;
    editingMode=false;manageButton.hidden=true;notes=sharedNotes;editToggle.textContent='编辑标记';rebuildMarkers();
    var active = document.body.classList.toggle('ps-annotate'); this.setAttribute('aria-pressed', String(active)); this.textContent = active ? '返回演示' : '查看说明';
    if (active) show(); else if (notes) { stopAdding(); editor.hidden = true; }
  };
  // PS_SCENARIO_URL_V1: 普通演示支持 ?scenario= 深链直达（复现模式保持自身预设，不生效）。
  var scenarioSelect = tools.querySelector('#ps-scenario');
  var urlScenario = replayId === null ? new URLSearchParams(location.search).get('scenario') : null;
  if (urlScenario !== null && ['normal', 'empty', 'loading', 'error', 'forbidden'].indexOf(urlScenario) === -1) urlScenario = null;
  if (urlScenario !== null) {
    var linked = api.readState(); linked.scenario = urlScenario; api.writeState(linked);
  }
  scenarioSelect.value = api.readState().scenario || 'normal';
  scenarioSelect.addEventListener('change', function () {
    var state = api.readState(); state.scenario = this.value; api.writeState(state);
    document.dispatchEvent(new CustomEvent('ps:scenario', {detail: this.value}));
  });
  tools.querySelector('#ps-reset').onclick = function () { try { if (replayId !== null) sessionStorage.removeItem(replayKey); else localStorage.removeItem(key); } catch (_) {} location.reload(); };
  body.addEventListener('click', function (event) {
    var button = event.target.closest('button'); if (!button) return;
    var it = interactions.find(function (i) { return i.id === button.dataset.interaction || i.requirement_ids.includes(button.dataset.requirement); });
    if (it) { highlight(it); if (button.dataset.interaction) show(it); }
  });
  var markers = document.createElement('div'); markers.className = 'ps-markers'; document.body.appendChild(markers);
  function visibleNotes() { return notes ? notes.list().filter(function (i) { return !i.manual || !i.hidden; }).map(function(i){return i.manual?i:Object.assign({},i,interactions.find(function(original){return original.id===i.id;}),{hidden:false});}) : interactions.map(function (i, n) { return Object.assign({}, i, {number:String(n+1)}); }); }
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
      editDialog.onclick = function () { if (!editingMode) editToggle.onclick(); dialog.appendChild(editor); editor.hidden = false; };
      dialog.appendChild(editDialog);
    }
    dialog.addEventListener('close', function () { document.body.appendChild(panel); positionMarkers(); });
  });
  document.addEventListener('click', function (event) {
    var reqJump = event.target.closest('[data-req-jump]');
    if (reqJump) {
      var article = document.getElementById('req-' + reqJump.dataset.reqJump);
      if (article) {
        panel.hidden = false;
        article.scrollIntoView({ block: 'start', behavior: 'smooth' });
        article.style.boxShadow = '0 0 0 3px #2563eb55';
        setTimeout(function () { article.style.boxShadow = ''; }, 900);
      }
      return;
    }
    if (tools.contains(event.target) || panel.contains(event.target) || markers.contains(event.target) || editor.contains(event.target) || notePopover.contains(event.target) || placement.contains(event.target) || event.target.closest('.ps-dialog-review,#ps-replay-dialog')) return;
    if (adding) {
      event.preventDefault(); event.stopImmediatePropagation();
      var target = event.target.closest('button,input,select,textarea,a,[role="button"],[id]') || event.target;
      if (!(target instanceof Element) || target === document.body || target === document.documentElement) return;
      var rect = target.getBoundingClientRect();
      pendingAnchor = {selector: selectorFor(target), x: Math.max(0, Math.min(1, (event.clientX - rect.left) / (rect.width || 1))), y: Math.max(0, Math.min(1, (event.clientY - rect.top) / (rect.height || 1)))};
      if(movingId){notes.relocate(movingId,pendingAnchor);movingId=null;pendingAnchor=null;stopAdding();editor.hidden=false;refreshEditor('已重新定位，可撤销。');return;}
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
  function stopAdding() { adding = false; placement.hidden = true; document.body.classList.remove('ps-adding-note');if(hoverTarget)hoverTarget.classList.remove('ps-placement-target');hoverTarget=null; }
  function closeNote(){
    var form=notePopover.querySelector('#ps-note-form');
    if(!notePopover.hidden && !form.hidden && formOriginal!==JSON.stringify([notePopover.querySelector('#ps-note-text').value,notePopover.querySelector('#ps-note-level').value]) && !window.confirm('放弃尚未保存的标注内容？'))return false;
    notePopover.hidden=true;pendingAnchor=null;editingId=null;movingId=null;
    if(hoverTarget)hoverTarget.classList.remove('ps-placement-target');hoverTarget=null;
    if(returnFocus && returnFocus.isConnected)returnFocus.focus();return true;
  }
  function positionPopover(x, y) {
    notePopover.hidden = false;
    var width = Math.min(360, innerWidth - 24), left = Number.isFinite(x) ? x + 14 : innerWidth / 2 - width / 2;
    var top = Number.isFinite(y) ? y + 14 : 64;
    notePopover.style.width = width + 'px';
    notePopover.style.left = Math.max(12, Math.min(innerWidth - width - 12, left)) + 'px';
    notePopover.style.top = Math.max(48, Math.min(innerHeight - notePopover.offsetHeight - 12, top)) + 'px';
  }
  function openForm(title, text, level, x, y) {
    returnFocus=document.activeElement;
    reviewForm.hidden=true;
    deleteSelected.hidden = !editingId;
    notePopover.querySelector('#ps-note-view').hidden = true;
    var form = notePopover.querySelector('#ps-note-form'); form.hidden = false;
    notePopover.querySelector('#ps-note-heading').textContent = title;
    notePopover.querySelector('#ps-note-text').value = text; notePopover.querySelector('#ps-note-level').value = level;
    formOriginal=JSON.stringify([text,level]);
    form.querySelector('button[type="submit"]').textContent = editingId ? '确认修改' : '确认增加';
    formStatus(''); positionPopover(x, y); notePopover.querySelector('#ps-note-text').focus();
  }
  function openEdit(it) {
    if(!editingMode)return;
    if(!it.manual){window.prompt('正式规则请交给 Agent 局部修改，不能用批注覆盖 PRD。复制以下上下文：','项目：'+data.project+'\n版本：'+data.version+'\n页面：'+pid+'\n控件：'+it.id+'\n需求：'+it.requirement_ids.join(',')+'\n链接：'+location.href);return;}
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
    if(!closeNote())return;
    returnFocus=document.activeElement;
    reviewForm.hidden=true;
    stopAdding(); editingId = it.id; pendingAnchor = null;
    editor.hidden = true;
    var target = targetOf(it), dialog = target && target.closest('dialog'); if (dialog && dialog.open) dialog.appendChild(notePopover);
    notePopover.querySelector('#ps-note-form').hidden = true;
    var view = notePopover.querySelector('#ps-note-view'); view.hidden = false;
    view.querySelector('.ps-note-actions').hidden=!editingMode;
    reviewButton.hidden=!editingMode;
    notePopover.querySelector('#ps-note-view-edit').textContent=it.manual?'编辑':'交给 Agent 修改正式规则';
    notePopover.querySelector('#ps-note-view-delete').hidden=!it.manual;
    var move=view.querySelector('#ps-note-move');
    if(!move){move=document.createElement('button');move.type='button';move.id='ps-note-move';move.textContent='重新定位';view.querySelector('.ps-note-actions').appendChild(move);}
    move.hidden=!it.manual;move.onclick=function(){movingId=it.id;adding=true;placement.hidden=false;document.body.classList.add('ps-adding-note');notePopover.hidden=true;};
    var level = notePopover.querySelector('#ps-note-view-level'); level.textContent = priorityLabel(it.level); level.dataset.level = it.level || 'info';
    notePopover.querySelector('#ps-note-view-text').textContent = it.description;
    notePopover.querySelector('#ps-note-view-meta').innerHTML = (it.manual ? '手动标注' : '需求标注') + (it.requirement_ids && it.requirement_ids.length ? ' · ' + it.requirement_ids.map(function (id) { return '<button type="button" class="ps-req-jump" data-req-jump="' + esc(id) + '">' + esc(id) + '</button>'; }).join(' ') : '');
    var review=it.review || {status:'pending',history:[]};
    reviewRead.textContent=reviewNames[review.status]+' · '+(review.note || '尚未处理')+(review.requirement_ids && review.requirement_ids.length?' · 关联 '+review.requirement_ids.join('、'):'')+(review.change_ref?' · 修改记录 '+review.change_ref:'')+(review.evidence?' · 验证：'+review.evidence:'');
    if(savedFrom && savedFrom!==data.version)reviewRead.textContent+=' · 继承自 '+savedFrom+'，本版适用性与完成证据需重新复核';
    var history=document.createElement('details'), summary=document.createElement('summary'); summary.textContent='处理历史（本机记录）';history.appendChild(summary);(review.history || []).forEach(function(e){var p=document.createElement('p');p.textContent=e.at+' '+reviewNames[e.from]+' → '+reviewNames[e.to]+'：'+e.note;history.appendChild(p);});reviewRead.appendChild(history);
    reviewButton.onclick=function(){view.hidden=true;reviewForm.hidden=false;reviewForm.querySelector('#ps-review-state').value=review.status;reviewForm.querySelector('#ps-review-note').value=review.note || '';reviewForm.querySelector('#ps-review-refs').value=(review.requirement_ids || []).join(',');reviewForm.querySelector('#ps-review-change').value=review.change_ref || '';reviewForm.querySelector('#ps-review-evidence').value=review.evidence || '';reviewForm.querySelector('#ps-review-error').textContent='';positionPopover();};
    notePopover.querySelector('#ps-note-view-edit').onclick = function () { openEdit(it); };
    notePopover.querySelector('#ps-note-view-delete').onclick = function () { if(!editingMode || !it.manual)return;notes.hide(it.id); notePopover.hidden = true; editingId = null; editor.hidden=false;refreshEditor('批注已删除，可撤销；对应需求仍保留。'); };
    var rect = target && target.getBoundingClientRect(); positionPopover(Number.isFinite(x) ? x : rect && rect.right, Number.isFinite(y) ? y : rect && rect.top);
  }
  function refreshEditor(message) {
    manageButton.hidden=!editingMode;
    var all = notes.list(), showDeleted = editor.querySelector('#ps-note-show-deleted').checked;
    editor.querySelector('#ps-note-items').innerHTML = all.filter(function (it) { return (showDeleted || !it.hidden) && (reviewFilter.value==='all' || it.review.status===reviewFilter.value); }).map(function (it) {
      var target = targetOf(it);
      return '<article class="ps-note-item"><strong>' + esc(it.number + ' · ' + reviewNames[it.review.status] + (it.hidden ? ' · 已删除' : '')) + '</strong><p>' + esc(it.description) + '</p>' + (!target ? '<p class="ps-hint">目标元素暂不存在，可切换场景查找。</p>' : '') + '<div class="ps-note-actions">' + (it.hidden ? '<button type="button" data-note-action="restore" data-id="' + esc(it.id) + '">恢复</button>' : '<button type="button" data-note-action="edit" data-id="' + esc(it.id) + '">编辑</button><button type="button" data-note-action="delete" data-id="' + esc(it.id) + '">删除</button>') + '</div></article>';
    }).join('') || '<p>暂无标记。点击“新增标记”后在原型中选择位置。</p>';
    editor.querySelector('#ps-note-undo').disabled = !notes.canUndo();
    rebuildMarkers(); status(notes.warning() || message || '修改自动保存在当前浏览器。');
    editor.querySelectorAll('[data-note-action="delete"]').forEach(function(button){var it=all.find(function(i){return i.id===button.dataset.id;});if(it && !it.manual)button.hidden=true;});
  }
  if (notes) {
    tools.querySelector('#ps-mode').textContent='查看说明';
    var publishButton=document.createElement('button');publishButton.type='button';publishButton.id='ps-note-publish';publishButton.textContent='保存到项目…';editor.querySelector('.ps-note-actions').appendChild(publishButton);
    var loadSaved=document.createElement('button');loadSaved.type='button';loadSaved.id='ps-note-load-saved';loadSaved.textContent='载入项目已保存批注';editor.querySelector('.ps-note-actions').appendChild(loadSaved);
    loadSaved.onclick=function(){
      if(!window.confirm('将先导出当前草稿备份，再用此页面加载的项目批注替换草稿，清空撤销历史。需要最新保存内容请先刷新页面。继续？'))return;
      editor.querySelector('#ps-note-export').click();draftBaseRevision=(data.noteRevisions || {})[pid] || null;
      notes.importData(sharedNotes.exportData());
      if(!notes.warning())draftNotes=window.PSAnnotationStore(noteContext,interactions,{getItem:function(k){return localStorage.getItem(k);},setItem:function(k,v){localStorage.setItem(k,v);localStorage.setItem(k+'.base',JSON.stringify(draftBaseRevision));}});
      notes=draftNotes;refreshEditor('已载入项目批注，原草稿已导出备份。请继续编辑。');
    };
    publishButton.onclick=function(){editor.querySelector('#ps-note-export').click();status('已导出保存包，尚未落盘到项目。请在本机 PRD 编辑器选择“原型批注 · 保存到项目”，导入此文件并确认；或交给 Agent 使用 save_notes.py。');};
    document.addEventListener('pointermove',function(event){if(!adding)return;var target=event.target.closest('button,input,select,textarea,a,[role="button"],[id]') || event.target;if(hoverTarget && hoverTarget!==target)hoverTarget.classList.remove('ps-placement-target');hoverTarget=target;if(!target.closest('.ps-tools,.ps-note-editor,.ps-note-popover,.ps-placement'))target.classList.add('ps-placement-target');});
    reviewForm.querySelector('#ps-review-cancel').onclick=function(){openView(notes.list().find(function(i){return i.id===editingId;}));};
    reviewForm.onsubmit=function(event){event.preventDefault();try{notes.review(editingId,{status:reviewForm.querySelector('#ps-review-state').value,note:reviewForm.querySelector('#ps-review-note').value,requirement_ids:reviewForm.querySelector('#ps-review-refs').value.split(/[,，]/).map(function(s){return s.trim();}).filter(Boolean),change_ref:reviewForm.querySelector('#ps-review-change').value,evidence:reviewForm.querySelector('#ps-review-evidence').value});refreshEditor();openView(notes.list().find(function(i){return i.id===editingId;}));}catch(e){reviewForm.querySelector('#ps-review-error').textContent=e.message;}};
    notePopover.querySelectorAll('[data-note-close]').forEach(function (button) { button.onclick = closeNote; });
    deleteSelected.onclick = function () { if (!editingId) return; notes.hide(editingId); editingId = null; notePopover.hidden = true; refreshEditor('标记已删除，可撤销；对应需求仍保留。'); };
    editToggle.onclick = function () { if(!closeNote())return;editingMode=!editingMode;manageButton.hidden=!editingMode;notes=editingMode?draftNotes:sharedNotes;editor.hidden=!editingMode;editToggle.textContent=editingMode?'退出编辑 · 查看已保存':'编辑标记';stopAdding();if(editingMode){document.body.classList.add('ps-annotate');tools.querySelector('#ps-mode').textContent='返回演示';panel.hidden=true;document.body.classList.remove('ps-panel-docked');refreshEditor('产品编辑模式：当前为浏览器草稿，开发查看模式仅展示项目已保存批注。');}else rebuildMarkers(); };
    editor.querySelector('#ps-notes-close').onclick = function () { stopAdding(); editor.hidden = true; };
    editor.querySelector('#ps-note-add').onclick = function () { adding = true; editingId = null; pendingAnchor = null; notePopover.hidden = true; document.body.classList.add('ps-adding-note'); var dialog = editor.closest('dialog'); (dialog || document.body).appendChild(placement); placement.hidden = false; editor.hidden = true; };
    placement.querySelector('button').onclick = function () { movingId=null;stopAdding(); editor.hidden = false; status('已取消放置。'); };
    notePopover.querySelector('#ps-note-cancel').onclick = function () { if(closeNote())stopAdding(); };
    notePopover.querySelector('#ps-note-form').onsubmit = function (event) {
      event.preventDefault();
      var text = notePopover.querySelector('#ps-note-text').value.trim(), level = notePopover.querySelector('#ps-note-level').value;
      if (!text) { formStatus('请填写说明内容。'); return; }
      try {
        if (editingId) notes.edit(editingId, text, level);
        else if (pendingAnchor) notes.add(Object.assign({id: 'manual-' + (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2)), description:text, level:level}, pendingAnchor));
        else { status('请先选择原型上的标记位置。'); return; }
        pendingAnchor = null; editingId = null; notePopover.hidden = true; editor.hidden=false;refreshEditor('标记已保存到当前浏览器草稿，尚未保存到项目。');
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
      var exported=notes.exportData();exported.base_revision=draftBaseRevision;
      var blob = new Blob([JSON.stringify(exported, null, 2)], {type:'application/json'}), url = URL.createObjectURL(blob);
      var a = document.createElement('a'); a.href = url; a.download = data.version + '-' + pid + '-annotations.json'; a.click(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000); status('已导出本页标记，原型和需求文件未修改。');
    };
    editor.querySelector('#ps-note-import').onclick = function () { editor.querySelector('#ps-note-file').click(); };
    editor.querySelector('#ps-note-file').onchange = async function () {
      var file = this.files[0]; this.value = ''; if (!file) return;
      if (file.size > 1024 * 1024) { status('标记文件不能超过 1MB。'); return; }
      var oldBase=draftBaseRevision;
      try { var value = JSON.parse(await file.text()); if((value.base_revision || null)!==draftBaseRevision)throw new Error('导入文件基线不同，请先比较并合并，不直接替换当前草稿');notes.importData(value); notePopover.hidden = true; refreshEditor('已导入并替换本页标记，可点“撤销”恢复导入前状态。'); } catch (error) { draftBaseRevision=oldBase;status('导入失败：' + error.message); }
    };
    document.addEventListener('keydown', function (event) { if (event.key !== 'Escape')return;if(adding){movingId=null;stopAdding();editor.hidden=false;status('已取消放置。');}else if(!notePopover.hidden){event.preventDefault();closeNote();} });
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
