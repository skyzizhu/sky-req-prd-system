# 可交互原型与本页需求

低保真表达真实布局与行为。开发应能操作关键流程，并在原型旁读到相应规则。参考 examples/order-demo 与 scripts/create_demo.py 了解可运行接入。

## 一份结构化需求

每版 content/spec.json：

```json
{
  "requirements": [{
    "id":"FR-ORDER-001",
    "title":"创建订单",
    "description":"用户从订单列表创建订单。",
    "source":"ai-inferred",
    "status":"pending",
    "blocking":true,
    "rules":{
      "显示规则":"有创建权限才可操作。",
      "输入与校验":"名称必填，去除首尾空格后 1～40 字；提交时定位错误。",
      "提交反馈":"处理中禁重复提交；成功关闭弹框并刷新列表。",
      "异常与边界":"失败保留输入并允许重试。"
    },
    "acceptance":[{"id":"AC-ORDER-001","given":"名称有效且有权限","when":"提交","then":"创建成功并显示在列表"}]
  }],
  "pages":[{"id":"order-list","title":"订单列表","purpose":"查阅和创建订单","requirement_ids":["FR-ORDER-001"]}],
  "interactions":[{
    "id":"INT-CREATE",
    "page":"order-list",
    "selector":"#create",
    "requirement_ids":["FR-ORDER-001"],
    "action":"dialog",
    "target":"create-dialog",
    "description":"点击打开创建弹框；无权限禁用。",
    "level":"crit"
  }]
}
```

requirements 为 PRD 的唯一规则来源，pages 将需求关联到 manifest 页面，interactions 将具体控件关联到需求。稳定 ID 不随文案或页面标题改变。同一需求可以关联多个页面。

每个 requirements 条目包含来源、确认状态、阻塞属性、行为规则和 Given/When/Then 验收。rules 按业务填写：显示、可操作条件、输入校验、动作、跳转、处理中、成功、失败、数据格式与边界。不要用空泛“按设计实现”代替规则。纯装饰元素无需编造需求。

action：
- inspect：只读业务数据，无业务点击动作；金额、状态、统计数等用 data-business-value 标记并提供稳定 ID，validate 检查是否关联说明。
- navigate：target 为同版本原型页面 ID，runtime 处理跳转。
- dialog / close：target 为本页 dialog 的元素 ID，runtime 打开/关闭。
- toggle：target 为本页可显隐区块 ID。
- input / submit / custom：行为由本页独立 JS 实现，包括校验、筛选、批量、Tab、模拟请求等。列出声明不代表行为已经完成。

selector 使用稳定的 #元素ID，不能依赖 DOM 顺序。所有业务 button/input/select/textarea/a 要有对应交互；范围外控件用 data-out-of-scope 写明原因，并禁用。脚本动态创建的交互控件也必须实际测试，静态校验无法穷尽动态 DOM。

## 接入

原型 HTML 放在 content/prototype/ 一级，样式和脚本放 assets/。复制 Skill 的 assets/prototype-runtime.css、prototype-runtime.js、annotation-store.js 到本版本 assets；可复用 wireframe.css。页面自己的布局与业务行为分离为独立 CSS/JS。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>订单列表</title>
  <link rel="stylesheet" href="assets/wireframe.css">
  <link rel="stylesheet" href="assets/prototype-runtime.css">
  <link rel="stylesheet" href="assets/page.css">
</head>
<body data-page-id="order-list">
  <main><!-- 带稳定元素 ID 的业务内容 --></main>
  <script src="assets/spec-data.js"></script>
  <script src="assets/annotation-store.js"></script>
  <script src="assets/prototype-runtime.js"></script>
  <script src="assets/page.js"></script>
</body>
</html>
```

spec-data.js 由 build 生成，包含本版需求与页面索引（含模板版本与构建时间，用于识别模板漂移），独立打开原型也可读取。禁止手工修改生成数据。所有真实规则进入 spec，页面 JS 实现相同规则。

## 原型运行时能力

需要角色、状态与模拟数据的可分享复现链接时，按 replay.md 在 spec 声明 replay_cases；共享运行时提供场景选择与链接窗口，业务 JS 实现角色权限。链接还原预设起点，不导出用户当前输入；跨页演示数据与普通演示隔离。

interactions 可带 properties（控件文案 text、placeholder、defaultValue、maxLength、required、select 的 options[{value,label}]、width:auto/compact/full，以及数值约束 min/max/step、单位 unit、格式 pattern、文件类型 accept），由共享 runtime 在业务脚本之前应用；min/max/step 仅支持数值/日期类 input，accept 仅支持 file input，unit 为展示性标注。编辑器表单暂覆盖原有键，新增键由 Agent 直接修订 spec.json。字段合法性和元素类型由 validate 检查；不允许任意 HTML、脚本或 CSS 属性。正式编辑与保存见 editing.md。自定义 JS 需读取元素原生约束，不能硬编码另一份长度等规则；动态生成控件仍须独立实现并测试。属性会同时显示在 PRD 和控件规则区，其他规则正文的冲突不能因配置生效而忽略。

本页需求顶部提供“控件与数据规则”检查区。标注模式点击元素即显示其规则；也可从下拉列表选择隐藏、禁用或弹框内元素。仅看待确认筛选依据规则自身状态，不能用需求已确认掩盖尚待确认的子规则。旧数据没有控件级关联时，明确提示展示关联需求范围，不能声称已经精确匹配。

新建/深改控件在 interactions 添加 `rule_ids: ["RULE-NAME-INPUT"]`，只能引用该控件 requirement_ids 内的 rule_details。字段、显示、操作、反馈等使用规则 category 分组，statement 记录具体语义、类型、单位、默认值、空值、条件等适用信息；例子和验收从规则引用读取，不维护第二份正文。只读数据也遵循此结构，纯装饰不标为业务数据。静态检查只能覆盖声明的业务数据，仍需实际审阅遗漏。

- 演示/标注切换；标注模式点击业务控件定位需求，不执行提交等业务动作。
- 可见编号徽章、四色简述、详细需求面板与元素双向定位；不限制标注数量。
- 本页需求面板支持拖动、调整大小、收起、右侧停靠；独立原型与 iframe 中均可用。
- 原生 dialog 内提供“查看弹框需求”，面板可进入弹框顶层供查阅。
- 场景选择器：normal/empty/loading/error/forbidden；页面 JS 必须监听 ps:scenario 并实际呈现状态。普通演示支持 `?scenario=` 深链直达（复现模式保持自身预设，不生效）。
- 脚本错误以页面底部错误条显式展示（含未处理的 Promise 拒绝），不静默失败；需求面板或场景切换失灵时先看错误条。
- PSPrototype.readState()/writeState()：按项目+版本隔离浏览器模拟数据。
- PSPrototype.notify(text)：操作反馈；重置只清除本项目本版本的演示状态。

运行时不提供真实后端。不同页面共享模拟数据，独立版本互不污染。file:// 的本地存储支持受浏览器策略影响，测试目标浏览器；不支持时界面仍需可打开，可使用固定本机服务演示跨页状态。

## 布局与标注

### 手动编辑标记

已保存标记可通过查看卡片的“处理批注”进入评审状态表单；状态、说明、需求关联、修改记录和验证说明见 review-loop.md。批注管理面板支持处理状态筛选。新批注导出 schema_version=2，旧 v1 导入兼容。

“编辑标记”打开管理面板。点击“新增标记”后，管理面板收起，用户直接点击原型中的控件或任意位置；系统优先选择点击处所属的按钮、输入框、链接等可操作控件，并在落点附近立刻弹出表单。表单只要求填写“标注优先级”和“说明内容”，确认后直接增加。新增过程拦截业务点击，Esc 或页面底部“取消放置”结束。

优先级选项为：P0 核心（红）、P1 重要/待确认（黄）、P2 一般说明（蓝）、参考信息（绿）。说明最多 2000 字。保存后的标记点击行为固定为“查看”：就地弹出只读卡片，展示优先级、说明、标注来源及关联 FR；用户从卡片明确点击“编辑”后才进入表单，也可在卡片中删除。禁止点击标记后直接进入编辑态。

手动评审批注可删除、撤销和恢复；正式规则标记只能查看，编辑模式下可复制上下文交给 Agent 修改正式 PRD，不能用批注覆盖/隐藏正式规则。旧导出中的覆盖保留以便恢复，但保存到项目时拒绝此类覆盖，需先核对迁移。手动标记使用 M1、M2 等，删除不导致其他编号变化。

手动标记优先绑定元素 ID；没有 ID 时绑定结构选择器及元素内相对位置。滚动与尺寸变化时重算坐标；页面结构或动态内容变化后需检查落点，找不到目标时编辑列表会提示。优先为会被评审的业务元素提供稳定 ID。

默认演示模式；“查看说明”显示正式规则及项目已保存批注，不展示增删改按钮。“编辑标记”显式进入产品编辑模式，“管理批注”重开管理面板，“退出编辑”回到已保存视图。手动草稿保存在浏览器 localStorage，键按项目、版本、页面隔离；演示重置不清除。选择落点有悬停高亮；保存后退出新增；单击只查看，显式编辑/重新定位，Esc 取消，未保存正文离开前确认。模式不是身份鉴权。

“保存到项目…”先导出文件，明确提示尚未写入；用户在本机编辑器的“原型批注 · 保存到项目”选择文件并确认，或让 Agent 使用 save_notes.py。成功后批注进入 spec.review_notes 并编译，刷新后的新浏览器可见；没有服务时不假装直接写磁盘。规划版可保存，冻结版不得改原快照。记录含导出基线指纹，旧草稿覆盖新保存结果会被拒绝；先导出保留本地草稿，由 Agent 对照正式批注合并，不能强行更新指纹绕过比较。

需要以项目已保存内容继续编辑时，刷新页面后选择“载入项目已保存批注”。确认后先导出旧草稿备份，再替换草稿并清空撤销历史；导出的旧文件仍可供 Agent 对照合并。跨基线文件不直接导入覆盖。浏览器存储失败时仍可导出当前内存草稿。

导出为本页 JSON 批注文件，导入校验项目/版本/页面、字段、数量、类型、字数与落点；不匹配时拒绝且保留现状。导入替换本页批注，可撤销。原始规则和交互逻辑保持不变：删除标记不删除 FR，编辑标记说明不自动更新 PRD。需要把评审意见正式纳入需求时，用户提供导出文件并明确修改意图，再走需求变更和验证流程。

已冻结的历史资源不自动升级；如需新编辑功能，放入规划版本。原型内原生弹框提供“编辑弹框标记”。

按 form 使用合适画布：移动端常用 375～430 内容宽，桌面/Web 按任务需要设置，电视关注遥控焦点。面板是独立可拖拽层，不强迫画布为标注预留固定 220px。

四色：crit 红=核心；warn 黄=待确认/风险；info 蓝=一般说明；ok 绿=参考。来源和确认状态另用文字表达。关键流程可加短连线，避免穿过文字；复杂规则放面板。编号对应 interactions 顺序，同一页面稳定排序。标注数量以覆盖为准。

## 业务交互验收

至少操作：
1. 核心正常路径到结果页；返回后应保留的状态仍存在。
2. 必填/格式/长度校验、处理中、重复点击、失败保留输入与重试。
3. 显示/禁用条件、无权限、空数据、加载、错误等真实场景。
4. 原型 → 需求 → 元素定位、面板拖拽/缩放/停靠/收起。
5. 同入口切历史版本；历史内容、旧原型资源不变化。
6. 对业务控件逐项核对，不出现无反馈假按钮。

validate 校验静态引用、需求和验收关联、控件覆盖、脚本接入、历史哈希。仍需浏览器操作证明行为；校验通过不能作为已完成所有业务实现的证据。
