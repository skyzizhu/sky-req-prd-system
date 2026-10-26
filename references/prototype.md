# 静态原型阅读器（V2）

开发打开页面即默认选中有效标注，同时阅读状态画面与该控件规则；点击其他标注切换说明。页面状态预设，控件仅提供简单局部交互；不接真实业务或新增批注模式。

## 布局与线框密度

轻量美化以阅读清晰为目标：统一灰阶、细边框、小圆角、字段对齐、标签字重和适度分组；少量强调色用于选中定位。保留控件密度、错误/禁用辨识，不增加装饰插画、宽松空卡片或高保真品牌视觉。规则面板用稳定的标签/内容列区分默认、约束和结果，编号不与业务文字争夺视觉。

- 阅读器顶部只保留页面身份、显示编号、状态对照、页面信息与定位链接；桌面工具区约 44px、状态栏约 34px。页面身份不重复大标题或常驻说明，补充信息默认收起；普通桌面高度下为画面优先保留空间，不能靠缩小文字达到这一点。
- 业务画面默认是线框原型：中性黑白灰、细边框、少量用于阅读定位的强调色。字号通常 12–14px、普通桌面控件约 28–32px、组内间距 8–12px；这些是默认密度，不覆盖用户指定端、可访问性需求或确有业务意义的尺寸。
- 字段、列表、弹窗和反馈按内容占用空间；去掉装饰阴影、大圆角、渐变、巨幅标题、成功插画、无业务意义的空卡片和固定最小高度。列表以合理样例行呈现列、操作与滚动关系，不用大量占位撑高页面。移动端保持适当触控尺寸，不强套桌面小控件。
- 页面 CSS 只负责业务画面，不给阅读器 header/main/button 等裸标签设置全局大间距或高度；使用 `.sr-snapshot` 内的页面类。参考 `examples/static-reader/page.css`，优先表现信息层次、元素和状态差异。

## 控件形态

优先使用原生 input、select、textarea、button；复合控件按真实结构绘制。控件使用原生元素，不能用字符“○ / ● / □ / ☑”或普通文本 div 冒充。原生下拉在画面内直接展开；确有自定义组件时只做必要的展开与选择，不额外模拟业务。

文本框只用于可输入文本；单选/复选组、开关、按钮、纯展示数值不套 `.field` 文本框边框。组容器无常驻输入框边框，可使用 `.sr-control-group`；选中标注时由 `.sr-highlight` 显示强调色外框，不改变布局。只读输入框仅在实际产品采用该形态时使用。

```html
<div id="default-method" data-rule-ref="INT-METHOD" class="sr-control-group" role="group" aria-label="领取方式">
  <label><input type="radio" name="default-method" checked>前台自取</label>
  <label><input type="radio" name="default-method">园区配送</label>
</div>
<div id="default-accessories" data-rule-ref="INT-ACCESSORIES" class="sr-control-group" role="group" aria-label="配件">
  <label><input type="checkbox" checked>转接线</label>
  <label><input type="checkbox">便携包</label>
</div>
```

实际业务选中值使用 checked/selected，禁用用 disabled；标注强调框仅表示正在查看哪个控件的说明，不更改其业务值。开关用 checkbox role="switch" 配合滑轨样式，滑块、日期、文件等控件按实际类型展示，不能统一画成文本框。

## 页面与状态

一个真实页面一个 HTML。`spec.pages[]` 增加 `states: [{id,title,summary,next,elements}]`；id 是稳定短标识，summary 解释该状态的触发条件，next 说明接下来如何处理或恢复。状态由业务决定，不强制枚举不适用状态。

HTML 的 `main` 包含多个 `section data-ps-state="状态ID"`。每段含状态标题与 `.sr-snapshot`，里面是完整的静态画面；运行时仅放行 data-ps-local 声明的局部控件，阻止提交、业务按钮及导航；不将整张画面设为 inert。不同状态内元素 ID 全页唯一。

```html
<body data-page-id="create-order" data-prototype-mode="static">
  <main>
    <section data-ps-state="default">
      <h2>默认</h2>
      <div class="sr-snapshot"><!-- 静态业务画面，元素有稳定 ID --></div>
    </section>
    <section data-ps-state="failed">
      <h2>提交失败</h2>
      <div class="sr-snapshot"><!-- 保留输入与错误反馈 --></div>
    </section>
  </main>
  <script src="assets/spec-data.js"></script>
  <script src="assets/prototype-runtime.js"></script>
</body>
```

head 引用页面 CSS 与 `assets/prototype-runtime.css`。共用运行时从 Skill assets 复制；spec-data 由 build 编译，并声明 schema_version=2。独立打开和固定入口 iframe 采用相同阅读器，不写内联脚本/样式/事件。

## 页面状态与局部交互分层

Tab 来自 states[]，画面内的轻量操作由声明属性控制；状态选择、state_review 格式、事件分离及重置只在 [local-controls.md](local-controls.md) 维护。绘图前先按该文档核对适用状态，不能以局部交互替代页面级异常画面。

## 规则关联

requirements 继续包含稳定 id、title、description、module、source、status、blocking、rule_details、acceptance。规则仍是唯一来源，不在 HTML 硬写第二份。

每个有业务含义的区域声明一条 interaction：

```json
{"id":"INT-ORDER-FAILURE","page":"create-order","selector":"#failed-feedback","title":"失败反馈","description":"失败后保留输入并允许重试","action":"inspect","requirement_ids":["FR-ORDER-001"],"rule_ids":["RULE-ORDER-FAILURE"],"state_ids":["failed"]}
```

- `title` 是短业务名称；description 是后备简述，不重复显示规则正文。
- 同一控件在不同状态适用不同规则时，分别登记状态专属interaction（可指向各状态内对应元素），不能复用同一个interaction ID却悄悄改变rule_ids。
- `state_ids` 缺省或空数组表示共用说明，填写表示只在这些状态显示。元素目标须在这些状态的画布中。共用规则只列一份，目标可指向 main 内包围各状态的稳定区域；差异规则绑定状态内具体区域。
- 共用区域在各状态内可用 `data-rule-ref="INT-ORDER-NAME"` 关联同一 interaction；编号和定位优先选择当前状态对应区域，避免为相同规则维护多份记录。selector 保留指向页面内稳定容器的 #id。
- `rule_ids` 指向本 interaction 关联需求内的精确细目。每个 rule_details 包含 id/category/statement/source/status/acceptance_ids，必要时附 examples。不与其他正文重复。
- 新版 interaction 仍只使用 inspect，表示标注关联；局部交互由HTML的声明属性控制，不能把标注action改为submit或业务操作。实际产品按钮的可用/禁用样式按画面状态呈现，不因原型不可操作而写成“产品不支持”。
- 所有业务控件、只读关键数据均有关联；纯装饰不需要编号。编号由 interaction 顺序生成，稳定 ID 用于维护。

## 标注粒度与内容

逐控件编写及复核时读取 [control-annotations.md](control-annotations.md)，包含下拉、多选、单选及其他控件的数据、默认值与交互要求。标注只解释实际使用的控件，不扩充页面能力。

一个独立业务控件或数据项使用精确 interaction，通过 selector 或元素自身的 data-rule-ref 关联；不能以整个表单的一条说明代替逐元素规则。重复行可标列/操作代表项，说明统一适用范围。控件语义及复核表只在 [control-annotations.md](control-annotations.md) 维护。

规则表达复用 [functional-detail.md](functional-detail.md) 的 title/statement/clauses/table/examples；原型由 interaction.rule_ids 精确引用，不另写正文或猜测拆句。

## 阅读行为

- 首次打开选第一个状态作为基准画面；有有效深链接时按链接选中。否则按 interaction 顺序选中当前状态内第一个可见且有关联规则的标注。状态切换重新选择本状态首个有效标注；失效链接同样回落，不展示空白或跨状态规则。没有有效标注时明确提示。默认选择不移动滚动位置或抢键盘焦点。
- 右侧只渲染选中标注在当前状态下精确关联的全部规则，按规则ID去重；不渲染其他规则、不提供“全页全部规则”或“其他规则”折叠区。完整业务规则通过 PRD 查看。多个控件共享规则时仍保留关联编号定位按钮。
- 标注按“规则/控件主题 → 关联控件编号 → 简短说明 → 适用的取值/默认/限制/结果分项或表格 → 依据与验收”阅读。直接读取rule_details的title/statement/clauses/table，不根据长段落自动推断或拆改业务含义。
- 编号常驻可见，非选中编号使用中性弱强调；选中编号、对应控件和关联说明同步高亮，键盘焦点/悬停始终清晰。
- 点击画面编号切换选中控件，原选中框清除，当前控件及编号用统一强调色边框高亮。右侧保留必要取值、约束与恢复，多条关联规则集中展示；“本状态说明”按需展开说明相对基准的元素变化和后续，不复制规则正文。
- 若当前状态改变控件显隐、编辑性、禁用或恢复行为，相应状态规则也要精确关联到该控件；不能只在其他按钮或全页说明中写过，就认为该控件的标注已完整。
- 控件规则仍含必要取值、默认、限制、结果及恢复，不能为简短删掉条件。精确关联由源数据负责，不因同属一个功能便塞入该功能全部规则；过宽的规则应在源数据按业务含义拆分，而非展示层猜测删句。
- 点击关联控件编号高亮画面区域，支持键盘；定位链接保留控件聚焦。共用规则可关联多个控件，但只展示一份正文。
- 状态切换同步画面与说明；hash 使用 `state=<状态ID>&rule=<交互ID>` 定位，项目入口使用同名查询参数传入 iframe。展开状态对照后展示全部画面，右侧仍只显示选中标注的关联规则；点击任一画面标注时同步其状态。
- 主工具区提供状态切换、状态对照、编号、页面信息与定位链接；不用悬浮卡片、连线、四色优先级或标注模式。
- 来源、规则 ID 和验收在“依据与验收”中展开；待确认规则旁保持轻量提示。
- 桌面双栏各自滚动；窄屏画面在前、规则在后。不遮挡画面，文字不依赖悬停。

## 验收

逐状态核对必要元素、业务数据、禁用/提示、失败后保留输入等可见差异。设计可重新设计布局与视觉，但不能遗漏业务状态和必要元素。实际检查两种入口、默认规则可读、切换同步、双向定位、对照、隐藏编号、窄屏与键盘。静态画面不验证网络、提交、动画或真实产品执行结果。

## 下游交付信息

page.handoff 为当前页面交接信息：role（角色名称）、preconditions、scope、out_of_scope、design_notes、dependencies、decisions（其余均为短文本数组）。只填写本页独有的补充；全局角色、范围、排除项、通用前提及通用设计说明引用 PRD，不在每页复写。缺失且影响开发的信息明确待确认，不伪造角色、设计稿或接口契约。

顶部“页面信息”按钮展开页面补充与必要元素：单状态只展示当前元素，对照模式按状态折叠展开。状态清单由状态切换栏提供，不再在交接面板重复。CTO 的整体方案阅读在 PRD，原型不单独增加技术负责人汇报区。

规则的“依据与验收”列出规则 ID、来源、确认状态及验收链接。完整 GWT 只在 PRD 功能详情维护，点击验收链接自动展开；原型不复制全文。定位链接保留项目/版本/页面/状态/规则；localhost 不代表可供其他电脑访问，不自动发布。

窄窗口默认收起站点侧栏，菜单以覆盖层打开，避免把 iframe 挤成窄条。实际校对规则后不以截图声称真实产品功能已通过。

## 状态与必要元素完整性

每个状态用 `elements: [{selector: "#default-name", title: "订单名称"}]` 声明必须出现的业务元素，如字段、操作、结果、错误提示。selector 是对应状态内真实元素 ID；不同状态 ID 不重复。纯装饰不必登记。

按原始方案及规则核对哪些元素在哪些状态出现、隐藏或禁用。清单与画面一致是结构检查，不能证明方案中所有元素都已发现。设计人员可重新设计布局、样式及组件，但需保留这些状态和业务内容。共用规则保持一份，元素清单只记录名称与定位，不复制规则。

## 边界与状态覆盖

交付前按 [quality-contract.md](quality-contract.md) 核对规则所需状态及必要元素。规则需声明 prototype 或 text 表达及理由；画面规则精确关联页面、状态、元素。数值边界不单独扩画面，结构、可操作性或反馈类型变化才增加静态状态。
