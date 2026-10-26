# sky-req-prd-system · V2

将产品经理已分析的确定方案（可以零散）整理为标准 PRD、静态多状态原型及按需的测试/上线材料。输入不是未经分析的用户痛点。

## 本次重构

- 标准九章 PRD：背景目标与边界、角色流程、功能规则、数据埋点、非功能、验收上线、计划、风险、附录。
- 功能详情按适用性展开入口前提、字段/内容表、操作结果、分类规则、异常恢复、边界与验收。网页与导出共用正文；待明确的实现口径直接显示，不以结构齐全代替内容完整。
- PRD 维护完整正文；交付清单只列变更、分工依赖和原文入口。原型保留当前适用规则，完整验收链接回 PRD。菜单区分需求文档、页面原型、补充资料与交付管理。
- 静态原型左画面右规则，默认可读；状态切换、编号双向定位和对照。原型不模拟业务提交。
- 原型主要服务开发与测试：角色前置、状态与规则、验收引用和定位链接；设计侧核对各状态必要元素，布局可重新设计。CTO 主要看 PRD 大纲、范围与自动生成的本版功能清单。
- 仅 V2 数据契约（project schema_version=3，spec schema_version=2）。无旧项目迁移、旧路由回退、动态演示或浮窗标注运行时。

## 使用

输入已确定方案并说明平台和交付要求，例如：“Web 订单管理增加创建订单，字段为名称和金额；失败保留输入。请完善 PRD 并生成静态原型。”没有给出的业务取舍明确待确认，必要细节以 AI 推断标记。

示例均为合成方案，不代表真实公司规范、正式设计稿或已认可的接口契约。

```bash
python3 scripts/create_static_demo.py /空的预览目录
python3 -m http.server 8766 --bind 127.0.0.1 --directory /预览目录
```

默认合成示例保留字段/权限实施缺口，质量报告为 incomplete，须明确阻塞问题后才能作为实施依据；生成成功只代表评审草稿和结构可读。

打开 `http://localhost:8766/site/index.html#/v/v0.1/prototype/create-order`。本机链接不能直接供其他电脑访问；团队共享需另行部署，不自动发布。

技能入口：[SKILL.md](SKILL.md)。内容规范：[standard-prd.md](references/standard-prd.md)。原型契约：[prototype.md](references/prototype.md)。检查方式：[TESTS.md](TESTS.md)。

交付审查统一入口：`python3 scripts/review_delivery.py /项目 --input /原始方案.md --report /报告目录/review`。自动检查、语义结论和实际界面证据分开记录；未复核不冒充通过。控件一致性断言、变更影响及固定场景评测见 [delivery-review.md](references/delivery-review.md)。

图形库随站点本地打包并固定版本，支持离线及file直开；来源、版本、SHA-256和许可保存在 `template/site/js/vendor/mermaid.json`。场景路径检查与精确标注复核见对应参考文档；未登记的分支及规则语义仍需Agent审查。
