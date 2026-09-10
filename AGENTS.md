# sky-req-prd-system

> 把产品经理手里零散的产品需求，变成开发直接能用的完整交付物——结构化需求文档、可交互原型、测试用例、上线计划。

## 你的任务（Agent 必读）

1. 读取 [SKILL.md](SKILL.md) 了解完整交付流程与规范。
2. 按用户需求的粒度与范围，调用 `scripts/` 下的工具生成或修改项目物料。
3. 遵循 `config.md` 中的用户标准（硬约束）。
4. 交付物写进 `versions/<版本>/content/`，禁止整体重生成已有项目。

## 关键文件

| 文件 | 用途 |
|---|---|
| SKILL.md | Agent 完整交付流程与规范 |
| references/workflow.md | 项目结构、命令、修改方式矩阵 |
| references/prototype.md | 原型运行时与状态覆盖标准 |
| references/delivery-quality.md | 细目完整性十维度、测试格式、上线四类、埋点骨架 |
| config.md | 用户标准（硬约束，优先于默认） |
| scripts/ | 项目管理与构建工具 |
| assets/ | 共享原型运行时与 CSS |

## 兼容性

本技能的 SKILL.md 格式兼容 Claude Code / ZCode / Codex / Cursor / Windsurf 等支持文件读取的 Agent。核心交付物为标准 Web 技术（HTML/CSS/JS + Python 工具链），无专有依赖。

MIT License。
