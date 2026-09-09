# 从已有 HTML 精确增量修改

用户说“把这条需求改一下”“订单列表按钮改成…”“FR-…/RULE-… 中的规则改为…”时，这是修改已有项目，不是生成请求。复用目录、版本、稳定 ID、页面和未改内容。重新 build 更新展示数据是编译，不等于重新生成 PRD/原型。

## 定位优先

每个原型页的稳定编号就是 manifest.pages[].id、spec.pages[].id 与 HTML body 的 data-page-id，三者必须一致。左侧菜单及原型工具栏显示同一编号，例如“订单列表 / 页面：order-list”。改名、重排、创建后续版本时沿用原页面 ID；不另造按序号变化的映射，不重新编号历史。不同版本同一页面共用 ID，因此修改时提供“项目 + 版本 + 页面编号”。

按页精确检索：`python3 <skill>/scripts/revise_item.py <项目> --version v1.1 --page order-list`，返回对应 HTML 路径、资源引用、本页需求与控件；可组合 --query 缩小范围，或与 --id/--field 组合限制保存范围。页面不存在或目标不属于该页时拒绝，不跳到其他页。资源引用仍需按 HTML 所在目录解析并复核。

1. 从 HTML 的本地路径或带版本路由定位 project.json、版本、manifest、spec 和页面源码。`revise_item.py` 支持项目目录（需 --version）、本地 HTML 路径和 file:// 深链接。
2. 优先使用用户给出的 FR、RULE、AC、INT、页面 ID 或 #元素ID。只给名称时搜索候选；“保存”必须精确选择 ID，同名多候选才询问，不默认取第一项。可读取原型 DOM、标题、控件文字辅助定位，不要求用户先学会编号。
3. 只有远端网页、截图或孤立 HTML 时，先寻找用户提供工作区中的原项目。找不到 spec/源目录时明确缺失，询问来源；不能自动从展示页重建整套项目。若用户明确只修改孤立 HTML，则保留原文件并局部修订，但说明无法同步缺失 PRD 数据。
4. 定位结果包含所属版本及 editable。冻结页不能直接编辑；映射到对应工作版并确认用户想改的版本。不得为一次小修改自动新建项目或新版本。

```bash
python3 <skill>/scripts/revise_item.py '<原型HTML路径或固定入口深链接>' --query 'FR-ORDER-001'
python3 <skill>/scripts/revise_item.py <项目> --version v1.1 --query 'RULE-NAME-INPUT'
```

读取返回的 revision 与实际条目，以及 project.py impact。自然语言由 Agent 理解，脚本不调用模型。PRD 页面“交给 Agent 修改此需求/控件”只生成可复制的版本/需求/控件定位信息，不会偷偷发送请求或写文件。

## 只改一个字段

以 apply_patch 写 JSON 值文件，例如文件内容为 `"订单名称最多 60 字，去除首尾空格后校验。"`。路径使用 `/` 分隔；列表用稳定 ID，不用数组下标。

```bash
python3 <skill>/scripts/revise_item.py <项目> --version v1.1 --id FR-ORDER-001 --field rule_details/RULE-NAME-INPUT/statement --value <值.json> --revision <刚读取的指纹>
python3 <skill>/scripts/revise_item.py <项目> --version v1.1 --id FR-ORDER-001 --field rule_details/RULE-NAME-INPUT/statement --value <值.json> --revision <相同指纹> --save
```

默认只预览，--save 才正式保存。保持未修改条目、未知字段、ID、关联、文档与历史；冲突拒绝覆盖。保存复用 editing.md 的校验、备份及撤销记录。需求支持 title/description、rules/既有键、rule_details/规则ID/statement 等既有子字段和 acceptance/验收ID/given|when|then；不通过此入口改 ID、来源、状态、关联或替换整组规则。控件支持 properties/text、properties/placeholder、properties/maxLength 等已有白名单及 target。

多个相关字段（规则、控件约束、提示）应在一个 editing.md 修改包中共同修改，避免将逐项保存的中间状态交付。单项工具是定位和局部维护捷径，不取消关联复核。

## 原型布局、控件和业务显示

- 简单文案/输入约束：优先修改 interactions.properties，同时核对关联规则、提示和测试。
- 元素层次、布局、样式：读取当前 HTML/CSS，按稳定 selector 局部 apply_patch；保留其他元素、资源路径和已有手工调整，不重新套模板或重写全页。
- 显示/隐藏、权限、弹框、跳转、校验、数据：修改对应 spec 规则及页面独立 JS 分支；“文字改了”不等于逻辑已改。读取现有持久化状态，避免演示旧数据掩盖修改。
- 布局/JS 修改不在单项保存器支持范围内；按 workflow.md 的 impact、源码局部修改、build、validate、浏览器验证、checkpoint 执行。修改前保留原始差异/可恢复备份，不以重生成绕过冲突。

交付列出“页面名称 + 需求名称（编号）/控件说明（编号）→ 修改点 → 关联复核结果”。运行正常/边界路径，核对无关需求和冻结哈希未变。新增/删除结构只有用户真的要求时才做，不因为找不到目标就创建替代项。PRD 更新、原型更新、实际行为验证分开报告，不能用 build 通过代替全部验证。
