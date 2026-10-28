---
name: sky-req-prd-system
description: 将产品经理已经分析、确定的产品方案（可零散）整理为有明确范围、层次清晰的 PRD 与多状态线框原型，支持已有项目增量维护。用于明确要求生成、更新或审查产品方案、PRD、原型的任务；不用于从原始用户痛点挖掘需求，也不因讨论或代码修改自动生成方案。
metadata:
  version: "2.0.0-preview.32"
---

# 产品方案 → PRD 与多状态原型

将产品经理已确定的方案补全为可实现、可验收的交付物，减少与开发、测试、设计的反复沟通。保留影响本次实现、结果和设计的信息，完整但不冗余；不重新挖掘痛点或擅自增加功能。

## 定位任务与依据

- 已有项目先读 `project.json` 和 `.skill-lock.json`；已锁定时改读锁内 runtime 的 SKILL.md，并使用该副本的说明和工具，不因本机安装更新而升级项目。缺锁的 V2 项目先检查，不猜测来源版本；用户明确采用候选版本后走下述升级流程。
- 无路径用 `scripts/project.py discover <工作区>`，候选不唯一再询问。不为局部修改另建项目。
- 读取全局及项目 `config.md` 的实际偏好，当场指令优先。首次生成读 [workflow.md](references/workflow.md)；既有物料小改先读 [maintenance.md](references/maintenance.md)，需要规则/控件定位时再读 [incremental.md](references/incremental.md)。
- 明确交付物、本次做/不做、已有能力影响及待确认项。未提及不等于不做；仅追问会改变范围、平台或关键业务结果的问题。只有用户原话/痛点时，请补充拟采用的产品方案。
- 可补齐必要执行细节，无依据的补充标 `ai-inferred/pending`，不编造权限、阈值或业务取舍。`source: origin/ai-inferred` 与 `status: confirmed/pending` 独立；生成、测试和交付都不替代业务确认。
- 只生成用户指定的交付物，裁剪方式见 [nodes.md](references/nodes.md)；仅原型也保留规则依赖的最小 spec。

## 已有物料修改：先分流

用户要求改已有规则、控件或整页时，进入 [maintenance.md](references/maintenance.md)，跳过首次生成及下方全量编写流程。先定位原项目/版本及目标，只读取目标叶字段、页面片段和必要关联；规则改动同步受影响画面/验收，页面改动保留未涉及规则及其他页面。整页改版允许只重做该页，不扩成重生成整个项目。构建更新展示数据是程序编译，不让模型重写全部物料。

## 审查与回归

审查交付物、核对跨物料一致性或评测技能时，读取 [delivery-review.md](references/delivery-review.md)。统一使用 `scripts/review_delivery.py` 复用现有质量检查，独立保存有位置、证据和建议的报告；语义与浏览器检查未执行时明确未复核，不能用脚本通过代替。仅审查不自动修改物料。技能改动的固定场景输入与评测入口也见该文件；评测候选在临时目录生成，不覆盖既有案例。

## 编写 PRD

读取 [standard-prd.md](references/standard-prd.md)、[functional-detail.md](references/functional-detail.md) 和 [delivery-quality.md](references/delivery-quality.md)。菜单、正文归属和跨物料引用见 [information-architecture.md](references/information-architecture.md)。

- 使用标准九章；第一章先背景与目标，再本版功能清单，明确范围及既有能力影响。章节按适用性填写，未知项待确认，不以边界清单代替完整 PRD。
- 按业务模块 → 功能 → 规则分类组织。规则简短但保留对象、条件、行为、结果及必要异常；复杂约束用分项，多结果分支按需用决策表替代长段；共用与关联规则只引用唯一正文，按完整操作查阅及复核。PRD 本身足以说明业务要求，不能依赖原型补全遗漏。
- `spec.json` 的 `rule_details` 是规则唯一来源；GWT 在功能详情维护，边界索引引用同一场景。共用规则只写一处，状态只写差异，原型、交接与导出读取或引用它，不再手写第二套正文。
- 有流程才画流程图，有状态流转才画状态图，覆盖适用的正常、异常和恢复路径；无流程不虚构。涉及图时读 [process-diagrams.md](references/process-diagrams.md)，涉及业务抽象时读 [business-modeling.md](references/business-modeling.md)。实体与规则按需说明，状态机直接引用已有状态图。

## 生成原型

读取 [prototype.md](references/prototype.md)、[control-annotations.md](references/control-annotations.md) 和 [local-controls.md](references/local-controls.md)，分别负责布局/阅读、控件语义、局部交互契约。

- 按功能任务组织原型详情，使用紧凑线框及真实控件形态。设计可重做视觉，但不能遗漏必要元素、数据和适用状态。
- 受众（B/C端）与平台分别判断；面向消费者或涉及移动端时，读取 [consumer-prototype.md](references/consumer-prototype.md)，按实际端补齐布局、触控和适用状态，不能把阅读器窄屏适配当作移动产品支持。
- 同一原型详情涉及多个页面、弹窗或抽屉时，上下排列独立画板，各有标题栏、边框和白色内容容器，画板之间留灰色间隔；标明触发关系，完整保留各界面控件。生成与检查契约见 [prototype.md](references/prototype.md)。
- Tab 展示页面级状态；下拉展开、选择、开关等只做画面内必要交互，不模拟业务提交或网络。逐项登记状态覆盖及局部核对路径，不能为减少 Tab 删除异常状态。
- 默认选中有效标注，右侧仅显示它在当前状态下精确关联的全部规则。点击控件只操作，点击独立编号只看规则，点击区域不重叠。不恢复浮窗、连线或标注模式。
- 标注覆盖有业务含义的字段、小操作和只读数据，尤其明确选择项及数量、默认值、约束和结果。重复列表按列或同类操作标注一次，保留状态/权限/行为差异；覆盖全部元素不等于为每个重复实例放一个编号。细则见 control-annotations.md，不能用整表单泛化说明代替字段规则。

## 维护与交付

项目锁定、显式升级和交付打包读取 [production-delivery.md](references/production-delivery.md)。新建项目自动保存技能副本；普通修订和新产品版本沿用项目锁，升级先预览差异并在副本验证。最终用 prepare_delivery.py 汇总检查、地址和静态/源项目包；缺失的语义或浏览器复核由 Agent 补做，只有业务决策交给用户。

- 固定项目入口、稳定版本及页面 ID，只接受 V2 契约。修改前 impact 并检查手改，完成后 build、validate、checkpoint；不整体重生成已有物料，不覆盖冻结版本。
- 正式编辑读 [editing.md](references/editing.md)，交接读 [developer-delivery.md](references/developer-delivery.md)，记录实际测试/上线结果读 [outcomes.md](references/outcomes.md)。原型校对与真实产品结果分开记录。
- 按 [quality-contract.md](references/quality-contract.md) 登记输入 → 功能 → 规则 → 画面/文字 → 验收，执行输入独立约束、规则与验收分支的语义复核；关键实施问题未决时明确阻塞，不因能出稿而标为可开工。构建后运行 `scripts/validate.py <项目> --report <项目>/quality-report`，修复缺项；非阻塞待决策单列，评审稿不冒充开工就绪。
- 含原型的生成/修改在validate后使用统一审查入口，检查控件属性及当前状态的规则绑定；命令、原始输入证据与未复核项处理见 [delivery-review.md](references/delivery-review.md)。不把引用存在或属性一致当作标注语义完整。
- 实际检查独立页和站点 iframe 的默认规则、状态同步、编号定位、状态对照、控件操作、键盘和窄屏；结构检查不能证明内容完整或图意准确。未执行项如实说明。
- 生成或修改物料后，启动/复用本机服务并确认入口200；执行delivery_info.py（见workflow.md），最终回复必须列出①localhost打开地址②本地PRD Web入口的绝对文件路径，并给出可打包的项目目录。不能只把地址留在报告或工具输出中。说明改动、实际验证与关键待决策；不自动发布或发送物料。
