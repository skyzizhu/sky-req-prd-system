# 原型规范：画布、线框组件、连线式四色标注

原型是低保真线框：灰阶占位表达结构，不表达视觉细节。标注是原型的核心价值。

## 画布（按产品形态选择）

| 形态 | 画布结构 | 总宽 |
|---|---|---|
| desktop | 窗口 760（标题栏三圆点）+ 标注栏 220 + 间距 20 | 1000 |
| web | 浏览器窗框 760（地址栏占位）+ 标注栏 220 + 间距 20 | 1000 |
| mobile / h5 | 手机框 375（h5 顶部加浏览器栏）+ 标注栏 220 + 间距 20 | 615 |
| miniapp | 手机框 375（顶部胶囊/导航栏）+ 标注栏 220 + 间距 20 | 615 |
| tv | 16:9 大屏 960 + 标注栏 220 + 间距 20 | 1200 |

`.wf-page` 固定宽度（`flex:none`），SVG 标注坐标因此稳定。每个线框页引用共享 `content/prototype/assets/wireframe.css`（初始化时已从 skill assets 复制）。移动端形态可自行追加少量组件类，但保持灰阶线框风格。

## 线框组件（wireframe.css 提供）

- 窗口骨架：`.wf-window` `.wf-titlebar` `.wf-dot` `.wf-title`
- 工具栏：`.wf-toolbar` `.wf-input` `.wf-kbd` `.wf-btn`
- 筛选：`.wf-chips` `.wf-chip(.on)`
- 列表：`.wf-list` `.wf-item(.on)` `.wf-num` `.wf-thumb` `.wf-lines` `.wf-line(.w-30~.w-90)` `.wf-tag` `.wf-star`
- 面板：`.wf-row` `.wf-pane` `.wf-preview` `.wf-actions` `.wf-statusbar` `.wf-label`
- 表单：`.wf-tabs` `.wf-tab(.on)` `.wf-form` `.wf-field` `.wf-field-label` `.wf-field-hint` `.wf-switch(.on)` `.wf-select` `.wf-hotkey` `.wf-ignore-list` `.wf-ignore-item`
- 交互说明文字一律不写进线框内部，全部走标注。

## 连线式标注（强制规范）

结构：SVG 覆盖层（`.wf-lines`）画引导线与**序号徽章**（目标点），标注框与图例放在右侧标注栏。

**铁律：标注栏从上到下的顺序 = 目标元素在线框中从上到下的顺序 = 序号顺序（1 最上）。** 先排序目标再排标注框，确保连线互不交叉。

**序号徽章**：目标点不是普通圆点，而是 r=9 的圆形徽章，中心白色加粗序号，颜色随重要程度级别。序号同时作为标注框首行前缀（`1 · 说明文字`），徽章与标注框靠虚线 + 同序号双重关联。

四色分级（重要程度从高到低）：

| 级别 | class | 颜色 | 语义 | 典型用途 |
|---|---|---|---|---|
| crit | `.wf-ann.crit` | 红 | 核心 / 必须 | 核心交互路径、P0 功能行为 |
| warn | `.wf-ann.warn` | 黄 | 待确认 / 注意 | 策略待评审、边界场景、风险点 |
| info | `.wf-ann.info` | 蓝 | 一般说明 | 常规功能说明、交互细节 |
| ok | `.wf-ann.ok` | 绿 | 参考信息 | 状态栏、辅助信息、布局说明 |

每个标注是一个 `<g class="wf-ann 级别">`（绘制顺序：线 → 徽章底圆 → 序号 → 标注框 → 文字，徽章盖住线端）：

```html
<g class="wf-ann crit">
  <line class="wf-ann-line" x1="783" y1="238" x2="37" y2="161"/>   <!-- 从标注框左缘到目标点 -->
  <circle class="wf-ann-dot" cx="33" cy="164" r="9"/>               <!-- 序号徽章，落在目标元素上 -->
  <text class="wf-ann-num" x="33" y="168">2</text>                 <!-- y = cy + 4，居中白字序号 -->
  <rect class="wf-ann-box" x="785" y="215" width="205" height="46" rx="6"/>
  <text class="wf-ann-label" x="795" y="233">2 · 第一行（前缀序号）</text>
  <text class="wf-ann-label" x="795" y="251">第二行（可选）</text>
</g>
```

坐标约定（以 desktop 1000 宽画布为例）：

- 标注栏图例固定在 `left:785px; top:36px`（HTML div `.wf-legend`，四色圆点 + 文字，每个线框页都要有）
- 序号数字 = 标注栏行号（第一个标注框为 1，依次递增）；`.wf-ann-num` 的 y = 徽章 cy + 4
- 标注框 x=785、宽 205；起始 y=130，每个间隔 85（一行高 28，两行高 46）
- 引导线 x1=783，y1 = 标注框垂直中点；x2/y2 = 目标点坐标 ± 4（避免遮住圆点）
- 每页标注 3~5 个，按目标 y 排序后再分配标注框位置

写完标注后**必须自查交叉**：任意两条线的 y1 与对应目标 y2 的顺序一致（同为升序或降序）则必不交叉。不确定时在浏览器截图确认。

## 线框页骨架

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>页面名 · 低保真线框</title>
  <link rel="stylesheet" href="assets/wireframe.css">
</head>
<body>
  <div class="wf-page">
    <div class="wf-window"> …线框内容… </div>
    <div class="wf-legend"> …四色图例… </div>
    <svg class="wf-lines" aria-hidden="true"> …标注… </svg>
  </div>
</body>
</html>
```

禁止：内联 style、内联 script、底部堆叠式说明（`.wf-notes` 已废弃）。

## 状态与边界页（强制智能分析）

每个产品方案必须分析下表状态页需求，**命中即生成为独立线框页**（菜单编号顺延），未命中的在页面总览注明「已分析，无此场景」：

| 需求信号 | 需生成 | 级别 |
|---|---|---|
| 危险操作（删除/清空/提交/支付/覆盖） | 确认弹框（遮罩 + 危险色主按钮） | 必须 |
| 表单输入 | 校验错误提示（即时、定位到字段） | 必须 |
| 列表 / 数据展示 | 空态 + 加载态（骨架屏） | 必须 |
| 网络请求 | 网络错误页 / 重试提示 | 必须 |
| 登录 / 角色体系 | 登录过期页、无权限页 | 按需 |
| 系统权限（desktop / mobile） | 权限引导页（说明用途 + 去授权入口） | 按需 |
| 首次使用 | 引导空态（带下一步动作） | 按需 |

**组织方式**：按主题合并为 1~3 个线框页（如「弹框与遮罩」「空态·加载·错误·权限」），页内用 `.wf-state-grid` 网格陈列，每个状态一个 `.wf-state-box`（顶部标签 + 状态内容）。禁止只写文字说明不画状态。

**组件**（wireframe.css 提供）：
- 遮罩与弹框：`.wf-mask` `.wf-dialog` `.wf-dialog-title` `.wf-dialog-text` `.wf-dialog-actions`（危险操作按钮加 `.wf-btn.danger`）
- 加载：`.wf-skeleton`（复用 `.wf-line` 做骨架条）
- 空态：`.wf-empty` + `.wf-empty-icon`（是否带引导按钮看设计说明）
- 轻提示：`.wf-toast`（`.warn` 为错误红色变体）

**设计说明**（页面总览必须写）：何种操作必须二次确认、错误反馈用 toast 还是弹框、空态是否带引导动作、权限回收后的降级行为。状态页标注同样用四色序号徽章规范。

## 页面总览（prototype 模块第一个页面）必须包含

1. **标注阅读说明**：四色分级表（颜色/级别/语义/典型用途）+ 读图方法（序号徽章 → 虚线 → 同序号标注框）+ 其他约定（菜单 `01 ·` 序号含义、低保真边界、每页 3~5 条标注）
2. 页面清单表（页面/入口/职责/对应需求）
3. 跳转关系 mermaid 图
4. 设计说明（如有）

二级菜单中线框页自动带 `01 ·` 序号（site 外壳按 type=prototype 自动编号，每端独立计数），序号即页面顺序，供口头引用。
