# 交付完整性检查

生成/修改交付物时读取。质量数据与规则同存 `content/spec.json`，报告由其生成，不另维护业务口径。完整合成示例由 `scripts/create_static_demo.py` 生成；其 `example_spec()` 同时供图测试使用，不作为通用业务模板。

## 交付检查流程

1. 登记用户确定方案的原始条目，逐项归入功能、排除或待决策；不把未提及的能力自动登记为“不做”。合理补充的执行细节保留来源；功能扩展需有明确依据。
2. 每个功能选择适用类型，核对各维度。结论为已说明、不适用或待确认；“已说明”不代表已确认。按需组合类型，不适用写本次范围内的理由，不能批量填“不适用”绕过核对。
3. 每条规则关联验收与表达方式。需要画面时关联页面、状态、必要元素及精确规则编号；不需要画面时说明文字足够的理由。
4. 从规则选择关键边界及异常用例；PRD 展示与导出共用这些用例。不要在验收章节复制另一套规则。
5. 按 [process-diagrams.md](process-diagrams.md) 先核对流程/状态图是否适用，再检查所需图的正常和异常路径、条件分支及状态连线；图、规则和原型状态一致。
6. 对照 [functional-detail.md](functional-detail.md) 做内容复核：covered 规则是否真的回答该维度，引用验收是否覆盖关键分支，原输入的独立约束是否逐项承接；不能把存在一条引用当作整项完整。
7. 涉及原型时按 [control-annotations.md](control-annotations.md) 逐控件语义复核，尤其检查选择项/数量、默认值、多选限制、单选互斥及小操作结果；存在标注关联不等于内容已完整。
8. 用page.state_review核对页面状态与局部变化：适用的校验、取消、加载、失败、未知、空数据及权限状态不能遗漏；下拉展开等不占Tab，局部选项/联动有可操作核对路径。实际检查控件与标注互不触发、编号不遮挡控件。
9. build 后运行 validate 并保存质量报告；修复缺项，再进行语义与浏览器复核。

```bash
python3 <项目>/build.py
python3 <skill>/scripts/validate.py <项目> --report <项目>/quality-report
```

`validate.py` 默认检查全部版本结构、编译一致性及当前版交付覆盖。检查其他版本或单独输出覆盖报告时用 `audit_quality.py --version <版本> --strict --report <前缀>`；它不替代结构与构建一致性检查。空脚手架或阶段草稿可用 `validate.py --structure-only`，该结果不能当交付通过。基础构建与 `projectlib.validate` 仍只管结构，允许逐步完善草稿。

报告状态：`incomplete` 有缺项或明确阻塞事项，严格检查返回非零；`review_required` 登记覆盖通过但仍有待决策项，可交评审稿；`checks_passed` 仅表示登记证据检查通过。任何状态都不自动授权开工或上线。业务评审后，阻塞实现/验收的问题标 `blocking:true`，不能为通过检查任意改为 false。

## 输入与范围

```json
"quality": {
  "schema_version": 1,
  "scope": {"prd": true, "prototype": true, "acceptance": true},
  "input_items": [
    {"id":"INPUT-01", "summary":"用户已确定的方案摘要", "disposition":"included", "requirement_ids":["FR-01"], "constraints":[{"id":"INPUT-NAME", "quote":"名称最多40字", "rule_ids":["RULE-01"], "literals":["40字"]}]},
    {"id":"INPUT-02", "summary":"明确排除的方案", "disposition":"excluded", "reason":"本次排除的依据"},
    {"id":"INPUT-03", "summary":"有范围歧义的方案", "disposition":"pending", "question":"需确定的问题", "blocking":true}
  ]
}
```

登记必须对照原始输入逐项复核。报告不能发现从输入登记和规则中同时漏掉的事实。仅 PRD 或仅原型按实际交付范围标记，不强制产出全部材料。

## 功能类型

在 `requirements[].review` 中写 `types` 与 `checks`。所有适用维度需要结论；每个检查项可引用多条规则。

| types | 核对维度 |
| --- | --- |
| form | fields 字段、validation 校验、submission 提交、result 结果、recovery 恢复、permissions 权限 |
| list | data_scope 数据范围、sorting 排序、filtering 筛选、pagination 加载范围、empty 空结果、failure 加载失败、permissions 权限 |
| workflow | roles 角色、transitions 转换、conditions 条件、recovery 恢复、concurrency 重复与冲突 |
| batch | selection 选择、limits 数量、partial_success 部分成功、recovery 重试、permissions 权限 |
| metric | definition 定义、unit 单位、time 时间、aggregation 聚合、empty 空值 |
| action | preconditions 前置、result 结果、recovery 恢复 |
| display | data_scope 数据范围、format 展示口径、empty 空值 |

检查项写法：

```json
"review": {"types":["form"], "checks":[
  {"dimension":"validation", "status":"covered", "rule_ids":["RULE-01"], "case_ids":["BC-01"]},
  {"dimension":"permissions", "status":"pending", "question":"哪些角色可使用？", "impact":"implementation", "blocking":true},
  {"dimension":"recovery", "status":"not_applicable", "reason":"仅本地格式预览，不涉及请求或数据写入"}
]}
```

上例仅展示写法，实际需核对选定类型的全部维度。表单校验、列表空结果、批量数量、指标空值、展示空值需边界用例；失败恢复、加载失败、流程恢复、部分成功需异常用例（不适用/待确认时不虚构用例）。

## 规则、画面与验收

每条 `rule_details[]` 增加 `presentation`。两种方式：

```json
{"mode":"prototype", "targets":[{"page":"create-order", "state":"failed", "selector":"#failed-focus"}]}
```

```json
{"mode":"text", "reason":"同布局的数值边界，用例表足以说明，不增加新画面。"}
```

画面目标必须出现在 `pages[].states[].elements`，且位于该状态 HTML 的 `.sr-snapshot` 内。`interactions[]` 必须有精确的 `rule_ids`；画面规则须由同一页面、状态、元素关联。HTML hidden/aria-hidden 会报错，CSS 遮挡及实际可见性由浏览器复核。

每个状态的必要业务元素还需有适用于该状态的精确标注；共用标注可由元素自身的 data-rule-ref 关联。只有外层区域的标注不能替代子字段、小操作或只读数据的说明。结构检查只验证关联存在，细节是否足够仍需按 prototype.md 做语义复核。

规则的 `acceptance_ids` 指向本功能验收；验收写 given/when/then，场景可带 kind（normal/boundary/exception）。未关联的验收、关联不存在的状态/元素、无规则的标注均报错。后台口径等纯文字规则无需强造原型。

## 边界与异常用例

`requirements[].boundary_cases`：

```json
[{"id":"BC-01", "kind":"boundary", "rule_ids":["RULE-01"], "acceptance_ids":["AC-01"], "presentation":{"mode":"text", "reason":"同布局的数值边界，验收场景足够表达"}}]
```

kind 可为 boundary、exception、normal。引用型用例省略 input/expected，关联唯一完整 GWT，且该验收明确相同 kind；GWT 的前提/操作/预期是唯一场景正文。网页和导出展示引用，质量报告展开证据。确有独立条件/数据/断言的补充用例才同时提供 input/expected；未交付验收时用独立用例，不引用不存在的 GWT。覆盖检查项引用的用例必须关联该检查项的规则。

同类型也不代表同场景：空结果不能关联失败重试。自动检查类型和关系，语义复核仍需核对具体前提、触发和预期。不要通过更改类型掩盖错误关联。

- 数量/金额/长度的上下界、超过边界、空值、精度、时间跨界等，优先用具体输入与预期描述；只选本功能适用的情况。
- 页面结构、必要元素、可操作性、提示位置、权限可见性或恢复路径变化时，补对应静态状态并声明必要元素。
- 同类错误仅文案不同，可复用一个画面并在规则/用例说明差异；未知文案或处理方式写待确认，不用画面替团队决策。
- 不机械扩展状态，也不把所有规则都标成文字以回避有意义的画面。

自动检查证明的是登记关系存在。规则与用例的业务一致性、输入是否完整、标记为“不适用”是否合理，以及画面是否正确表达业务，仍需人工/Agent 逐项语义复核。

规则可带字段/内容/决策表 `rule_details[].table`（columns 为非空列名数组，rows 为等宽文本数组），格式见 functional-detail.md。表格与正文为同一规则来源，网页和 Markdown 导出均显示。待明确的实现问题沿用 review.checks，不藏在报告中；正文同步展示问题及是否影响实现。

## 输入约束与未决事项的检查

included 输入条目必须有 constraints：每项 id、quote（本次输入原文片段）、rule_ids；可选 literals 是原文中不能遗漏的关键字面值，如“254字符”“1～40字”。片段保持输入原意，不能从生成规则反抄以假装覆盖。固定枚举、默认、上限等有独立约束时分别追溯；不把内部台账再展示成一份 PRD。

检查器校验约束指向本条输入所属功能的有效规则；去空白后，关键字面值必须同时存在于输入片段及对应规则正文/分项/表格中。它只能发现显式值的遗漏，不能证明关系、否定、单位及完整语义正确，也无法发现根本未登记的原始要求。最终仍需对照原输入复核。

含原型的交付必须提供各页面 state_review，全部已声明状态均纳入 covered 核对；局部控件路径照 local-controls.md 登记。清单完整仍不代表已穷尽业务状态。

pending 检查项声明 impact 为 implementation、acceptance 或 editorial。前两者必须 blocking:true；只有不改变含义、约束和预期的文案校对可用 editorial/false。未声明影响默认按实施问题处理；关键问题未决时报告 incomplete，不能降级让报告通过。结构有效的评审草稿仍可生成，但不能作为就绪交付。

## 统一审查与跨物料检测

含原型的生成/修改完成后，按 [delivery-review.md](delivery-review.md) 执行统一审查入口；它复用本检查器，不替代语义与浏览器复核。含原型时，将规则中可确定的原生控件属性派生为 quality.control_checks（schema 见该文件），由统一入口比对实际 HTML；未知或动态属性保持待复核。该台账不进入 PRD 正文，不作为第二套业务决策来源。
