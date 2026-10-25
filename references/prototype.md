# 静态原型阅读器（V2）

开发打开页面就能同时阅读状态画面与规则；点击仅帮助定位。V2 只有静态阅读器，不提供演示、批注或旧运行入口。

## 页面与状态

一个真实页面一个 HTML。`spec.pages[]` 增加 `states: [{id,title,summary,next,elements}]`；id 是稳定短标识，summary 解释该状态的触发条件，next 说明接下来如何处理或恢复。状态由业务决定，不强制枚举不适用状态。

HTML 的 `main` 包含多个 `section data-ps-state="状态ID"`。每段含状态标题与 `.sr-snapshot`，里面是完整的静态画面；运行时将快照设为 inert，业务控件不接受输入或执行操作。不同状态内元素 ID 全页唯一。

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

## 规则关联

requirements 继续包含稳定 id、title、description、module、source、status、blocking、rule_details、acceptance。规则仍是唯一来源，不在 HTML 硬写第二份。

每个有业务含义的区域声明一条 interaction：

```json
{"id":"INT-ORDER-FAILURE","page":"create-order","selector":"#failed-feedback","title":"失败反馈","description":"失败后保留输入并允许重试","action":"inspect","requirement_ids":["FR-ORDER-001"],"rule_ids":["RULE-ORDER-FAILURE"],"state_ids":["failed"]}
```

- `title` 是短业务名称；description 是后备简述，不重复显示规则正文。
- `state_ids` 缺省或空数组表示共用说明，填写表示只在这些状态显示。元素目标须在这些状态的画布中。共用规则只列一份，目标可指向 main 内包围各状态的稳定区域；差异规则绑定状态内具体区域。
- 共用区域在各状态内可用 `data-rule-ref="INT-ORDER-NAME"` 关联同一 interaction；编号和定位优先选择当前状态对应区域，避免为相同规则维护多份记录。selector 保留指向页面内稳定容器的 #id。
- `rule_ids` 指向本 interaction 关联需求内的精确细目。每个 rule_details 包含 id/category/statement/source/status/acceptance_ids，必要时附 examples。不与其他正文重复。
- 新版 interaction 仅使用 inspect，表示静态画面说明，不模拟业务点击。实际产品按钮的可用/禁用样式按画面状态呈现，不因原型不可操作而写成“产品不支持”。
- 所有业务控件、只读关键数据均有关联；纯装饰不需要编号。编号由 interaction 顺序生成，稳定 ID 用于维护。

## 阅读行为

- 首次打开选第一个状态，右侧直接列出共用规则和当前状态差异。
- 点击画面编号滚动并高亮说明；点击说明标题滚动并高亮画面区域。键盘可操作。
- 状态切换同步画面与说明；hash 使用 `state=<状态ID>&rule=<交互ID>` 定位，项目入口使用同名查询参数传入 iframe。展开状态对照后展示全部画面和规则。
- 只保留「状态」「展开状态对照」「显示编号」工具；不用悬浮卡片、连线、四色优先级或标注模式。
- 来源、规则 ID 和验收在“依据与验收”中展开；待确认规则旁保持轻量提示。
- 桌面双栏各自滚动；窄屏画面在前、规则在后。不遮挡画面，文字不依赖悬停。

## 验收

逐状态核对必要元素、业务数据、禁用/提示、失败后保留输入等可见差异。设计可重新设计布局与视觉，但不能遗漏业务状态和必要元素。实际检查两种入口、默认规则可读、切换同步、双向定位、对照、隐藏编号、窄屏与键盘。静态画面不验证网络、提交、动画或真实产品执行结果。

## 下游交付信息

page.handoff 为当前页面交接信息：role（角色名称）、preconditions、scope、out_of_scope、design_notes、dependencies、decisions（其余均为短文本数组）。只填写本页独有的补充；全局角色、范围、排除项、通用前提及通用设计说明引用 PRD，不在每页复写。缺失且影响开发的信息明确待确认，不伪造角色、设计稿或接口契约。

本页交接折叠展示页面补充与必要元素：单状态只展示当前元素，对照模式按状态折叠展开。状态清单由状态切换栏提供，不再在交接面板重复。CTO 的整体方案阅读在 PRD，原型不单独增加技术负责人汇报区。

规则的“依据与验收”列出规则 ID、来源、确认状态及验收链接。完整 GWT 只在 PRD 功能详情维护，点击验收链接自动展开；原型不复制全文。定位链接保留项目/版本/页面/状态/规则；localhost 不代表可供其他电脑访问，不自动发布。

窄窗口默认收起站点侧栏，菜单以覆盖层打开，避免把 iframe 挤成窄条。实际校对规则后不以截图声称真实产品功能已通过。

## 状态与必要元素完整性

每个状态用 `elements: [{selector: "#default-name", title: "订单名称"}]` 声明必须出现的业务元素，如字段、操作、结果、错误提示。selector 是对应状态内真实元素 ID；不同状态 ID 不重复。纯装饰不必登记。

按原始方案及规则核对哪些元素在哪些状态出现、隐藏或禁用。清单与画面一致是结构检查，不能证明方案中所有元素都已发现。设计人员可重新设计布局、样式及组件，但需保留这些状态和业务内容。共用规则保持一份，元素清单只记录名称与定位，不复制规则。

## 边界与状态覆盖

交付前按 [quality-contract.md](quality-contract.md) 核对规则所需状态及必要元素。规则需声明 prototype 或 text 表达及理由；画面规则精确关联页面、状态、元素。数值边界不单独扩画面，结构、可操作性或反馈类型变化才增加静态状态。
