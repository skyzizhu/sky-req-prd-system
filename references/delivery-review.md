# 统一交付审查与场景回归

用户要求审查交付物时读本文件；生成或修改后的语义复核也采用此口径。只审查时不重生成、不改正文、确认状态或历史版本。报告单独保存，不新增 PRD 章节或站点菜单。用户已要求修复时可继续修改明确错误；业务取舍仍保持待确认。

## 入口与结论

```bash
python3 <skill>/scripts/review_delivery.py <项目> --input <原始产品方案.md> --report <项目外>/delivery-review
```

复用现有结构、构建新鲜度和 qualitylib 检查，不维护另一套覆盖算法。支持 `--version`；多份输入重复 `--input`。JSON 保留检测证据，Markdown 提供阅读摘要。

退出码：0 已记录全部复核；1 发现问题；2 执行失败；3 尚有未复核项/待决策。`review_recorded` 只表示本次复核记录齐全，不证明业务已确认或授权开工。未执行浏览器复核必须保持 unverified，不用结构测试代替。

先得到源指纹，再由 Agent 对照原始输入和实际物料填写独立证据文件，用 `--evidence <证据.json>` 重跑：

```json
{
  "fingerprint":"首轮报告中的指纹",
  "checks":{
    "rule_closure":{
      "verdict":"fail",
      "impact":"business_question",
      "evidence":["spec.json FR-01/RULE-CANCEL：只说‘取消’，未说明提交中是否允许；原始方案第3段也未确定"],
      "recommendation":"向产品确认提交中取消的可操作性、请求结果和数据处理，明确前保持阻塞"
    }
  }
}
```

verdict 为 pass/fail/not_applicable/unverified；已复核项均需定位与观察证据，不适用也需本次理由。问题标 blocker（明确实施/验收错误）、business_question（缺业务决策）或 suggestion（不影响含义的可读性优化），附具体建议。自动错误在 quality/control findings 中保留位置、错误码及实际值；Agent 在语义记录中解释其业务影响。不能以自动脚本的错误条数衡量语义质量。

源指纹绑定项目、版本、源内容、原始输入和评测标准，改动后旧证据会拒绝复用。原始方案文件未提供时不能把 input_scope 标为通过；它与从 spec 生成的台账不是同一份证据。证据文件是复核者的记录，脚本不能证明复核者确实看过页面。

复核项：input_scope、rule_closure、consistency、flow_paths、annotation_scope、redundancy、acceptance、mobile_delivery、browser。流程路径的登记与语义核对见 [process-diagrams.md](process-diagrams.md)，逐状态精确绑定见 [prototype.md](prototype.md)。具体问题由首轮报告生成，不在此重复。逐功能/分支列出检查证据，可同一项记录多处定位；缺陷需要指出遗漏会让下游猜测什么。删除冗余前核对条件、状态、边界及恢复是否仍有唯一明确出处；上下文投影和独立边界不是重复。只为本次功能审查适用情况，不为凑完整新增功能。

同一详情有多个界面时，按prototype.md检查上下独立画板；脚本在controls.findings报告surface_*问题，包括缺标题/内容、缺触发入口、画板嵌套以及基础元素遗漏。browser证据须包含各画板完整画面、标题及灰色间隔，逐画板核对控件与标注，不以遮罩叠加或属性断言通过代替。基础画面和衍生画面同时遗漏的业务元素仍需对照原始方案复核。

## 控件一致性断言

`quality.control_checks` 是从已维护规则派生的检测断言，与输入约束台账同属核对证据，不是第二套业务规则。先确定规则，再登记断言；修改业务值时复核断言，不能为了通过检测反向修改需求。语义审查需确认 expected 与 rule_ids 真正对应。

```json
{"page":"apply","state":"default","selector":"#default-device","rule_ids":["RULE-DEVICE"],"expected":{"options":[{"value":"laptop","label":"笔记本"},{"value":"monitor","label":"显示器"}],"value":"laptop","multiple":false,"disabled":false}}
```

目标必须是该状态 snapshot 中唯一原生 input/select/textarea/button 的 ID。options 按实际顺序精确比对 value/label；value 是 select 默认值，多选时为数组。checked 用于单选/复选。required/disabled/multiple/checked/readonly 为布尔值；type/min/max/step/maxlength/minlength/pattern/placeholder 为 HTML 属性字符串，缺省为 null。textarea 检查初始文本。固定选项、默认、必填、上下限、禁用等能确定的属性逐项登记；不要为未知约束捏造值。数量上限、选择组互斥、动态数据来源、条件显隐、切换保留/清空、时间限制与权限语义仍通过规则/场景和浏览器检查，不能声称只查静态属性就已覆盖。

检查器还核对control_checks.rule_ids是否被该控件当前状态标注完整引用，包含子控件data-rule-ref指向组标注的情况；实际属性一致但标注漏掉状态依据时仍报错。它不自动判断多绑规则是否无关，需annotation_scope复核。

报告列出未登记断言的具名控件，未登记属性也不推定一致。无 ID 的业务控件须按已有逐元素标注契约修复。断言对比的是 authored HTML 初始值，不是运行时 DOM、computed CSS 或网络数据。PRD-only 不强制控件检查。

## 变更影响

沿用 `project.py impact` 的 checkpoint/base 差异入口，增加受影响规则、画面状态、标注、验收和图的保守复核范围。它只提示检查哪里，不代表这些内容都需重写。删除项看原始差异；无结构化关系的 Markdown、实体和上下游依赖仍需语义分析。纯 HTML 改动也必须核对其所在状态与规则，不能只看 changed_requirements 为空就跳过。

## 固定场景评测

`tests/scenarios/delivery.json` 固定四个中等场景：设备申领（控件/失败恢复）、会议预约取消（时间/状态/待决策）、仅指标 PRD（裁剪/口径/去重）、移动App体验课预约（跨页返回/中断重入/移动画板）。这些是独立产品输入与审查标准，不是生成模板。

1. 修改 skill 后，在临时空目录按每个 scenario.input **实际运行技能生成候选物料**；保持同一输入和交付范围。不要用演示生成器替代这些任务，也不要把已知答案灌进生成输入。
2. 逐个对照 input 和 checks 审查候选；浏览器检查适用页面。第一次无 evidence 运行收集指纹和未完成项，随后填写证据复核。
3. 候选映射 JSON 为 `{"equipment-request":{"project":"/绝对路径","evidence":"/可选的证据.json"}}`。运行：

```bash
python3 <skill>/scripts/evaluate_scenarios.py <候选映射.json> --report-dir <项目外>/scenario-reports
```

输出每场景报告和 summary.json。未提供的场景明确 not_run，未复核为 review_required；没有总分，不能把未评估当通过。脚本只评估候选，不调用模型生成候选。回归对比使用修改前后的两份报告，逐项解释新缺陷、修复和未决变化；不能用增加材料长度换取评分。新增真实失败再补场景，避免堆积同义用例。
