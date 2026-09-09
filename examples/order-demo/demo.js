(function () {
  var api = window.PSPrototype;
  var state = api.readState();
  if (!state.orders) {
    state.orders = Array.from({length: 8}, function (_, n) { return {name: '示例订单 ' + (n + 1), status: '待处理'}; });
    api.writeState(state);
  }
  var rows = document.getElementById('rows');
  if (rows) document.getElementById('search').value = state.filter || '';
  function render() {
    state = api.readState();
    if (!rows) {
      var detail = document.getElementById('detail-content'); detail.textContent = '';
      var order = (state.orders || [])[0];
      detail.textContent = state.scenario === 'forbidden' ? '当前角色无权查看订单。' : state.scenario === 'error' ? '加载失败，请切换正常场景重试。' : state.scenario === 'loading' ? '正在加载订单详情…' : state.scenario === 'empty' || !order ? '暂无订单，请返回列表创建。' : order.name + ' · ' + order.status;
      return;
    }
    var scenario = state.scenario || 'normal';
    var feedback = document.getElementById('feedback');
    var values = {normal: '', empty: '暂无订单，点击新建订单开始。', loading: '正在加载订单…', error: '订单加载失败。可切换正常场景重试，或演示提交失败。', forbidden: '当前角色无权查看或创建订单。'};
    feedback.textContent = values[scenario]; rows.textContent = '';
    var filter = document.getElementById('search').value.toLowerCase();
    if (scenario === 'normal') (state.orders || []).filter(function (o) { return o.name.toLowerCase().includes(filter); }).forEach(function (o) {
      var row = document.createElement('div'); row.className = 'order-row';
      var name = document.createElement('span'); name.textContent = o.name;
      var status = document.createElement('span'); status.textContent = o.status; row.append(name, status); rows.append(row);
    });
    if (scenario === 'normal' && !rows.children.length) feedback.textContent = filter ? '没有符合条件的订单，请调整搜索词。' : '暂无订单，点击新建订单开始。';
    document.getElementById('create').disabled = state.role === 'viewer' || scenario === 'forbidden' || scenario === 'loading';
    document.getElementById('detail').disabled = scenario !== 'normal' || !(state.orders || []).length;
    var batch = document.getElementById('batch');
    batch.hidden = !window.PS_SPEC.spec.requirements.some(function (r) { return r.id === 'FR-ORDER-003'; });
    batch.disabled = state.role === 'viewer' || scenario !== 'normal' || !(state.orders || []).some(function (o) { return o.status === '待处理'; });
  }
  if (rows) {
    document.getElementById('search').addEventListener('input', function () { state = api.readState(); state.filter = this.value; api.writeState(state); render(); });
    document.getElementById('order-form').addEventListener('submit', function (event) {
      event.preventDefault();
      var input = document.getElementById('order-name'), error = document.getElementById('form-error');
      var name = input.value.trim();
      if (input.required && !name) { error.textContent = '请输入订单名称，不能仅填写空格。'; input.focus(); return; }
      if (input.maxLength > 0 && name.length > input.maxLength) { error.textContent = '订单名称最多 ' + input.maxLength + ' 字。'; input.focus(); return; }
      var button = document.getElementById('submit'); if (button.disabled) return;
      button.disabled = true; button.textContent = '提交中…'; error.textContent = '';
      setTimeout(function () {
        state = api.readState(); button.disabled = false; button.textContent = '提交订单';
        if (state.scenario === 'error') { error.textContent = '提交失败，请保留输入并重试。'; return; }
        if (state.role === 'viewer' || state.scenario === 'forbidden') { error.textContent = '权限已失效，无法提交。'; return; }
        if (state.scenario === 'empty') state.orders = [];
        state.scenario = 'normal'; state.orders.unshift({name: name, status: '待处理'}); api.writeState(state);
        document.getElementById('ps-scenario').value = 'normal';
        document.getElementById('create-dialog').close(); input.value = ''; render(); api.notify('订单已创建');
      }, 350);
    });
    document.getElementById('batch').addEventListener('click', function () {
      state = api.readState(); if (state.role === 'viewer' || state.scenario === 'forbidden') return; state.orders.forEach(function (o) { o.status = '已完成'; }); api.writeState(state); render(); api.notify('已完成全部待处理订单');
    });
  }
  document.addEventListener('ps:scenario', render);
  render();
})();
