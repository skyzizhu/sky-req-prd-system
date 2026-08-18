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

结构：SVG 覆盖层（`.wf-lines`）画引导线与目标点，标注框与图例放在右侧标注栏。

**铁律：标注栏从上到下的顺序 = 目标元素在线框中从上到下的顺序。** 先排序目标再排标注框，确保连线互不交叉。

四色分级（重要程度从高到低）：

| 级别 | class | 颜色 | 语义 | 典型用途 |
|---|---|---|---|---|
| crit | `.wf-ann.crit` | 红 | 核心 / 必须 | 核心交互路径、P0 功能行为 |
| warn | `.wf-ann.warn` | 黄 | 待确认 / 注意 | 策略待评审、边界场景、风险点 |
| info | `.wf-ann.info` | 蓝 | 一般说明 | 常规功能说明、交互细节 |
| ok | `.wf-ann.ok` | 绿 | 参考信息 | 状态栏、辅助信息、布局说明 |

每个标注是一个 `<g class="wf-ann 级别">`：

```html
<g class="wf-ann crit">
  <line class="wf-ann-line" x1="783" y1="238" x2="37" y2="161"/>   <!-- 从标注框左缘到目标点附近 -->
  <circle class="wf-ann-dot" cx="33" cy="164" r="4"/>              <!-- 精确落在目标元素上 -->
  <rect class="wf-ann-box" x="785" y="215" width="205" height="46" rx="6"/>
  <text class="wf-ann-label" x="795" y="233">第一行</text>
  <text class="wf-ann-label" x="795" y="251">第二行（可选）</text>
</g>
```

坐标约定（以 desktop 1000 宽画布为例）：

- 标注栏图例固定在 `left:785px; top:36px`（HTML div `.wf-legend`，四色圆点 + 文字，每个线框页都要有）
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
