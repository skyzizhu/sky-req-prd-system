# V2 开发约定

本仓库将已确定产品方案转为标准九章 PRD 与静态多状态原型。产品目标与规范见 SKILL.md。

- 只支持 V2 项目数据，不保留旧项目迁移、旧运行入口或旧标注模式。当前系统仍有项目版本、冻结和交接快照，它们用于 V2 的持续维护。
- 标准章节完整，做与不做明确；模块 → 功能 → 规则分类，简明且保留关键条件与结果。
- 规则和验收单一来源，原型引用。静态快照不接业务脚本；状态、定位和对照工具可交互。
- 涉及数据工具执行 Python 单测；涉及交接执行 node --test tests/delivery.cjs；阅读器改动实际检查独立页、站点 iframe、键盘及窄窗口。
- 本地修改不自动提交或推送。用户明确要求时再按仓库实际分支处理。

常用命令：

```bash
python3 scripts/project.py init /空目录 --name 项目名 --form web --version v0.1
python3 /项目/build.py
python3 scripts/validate.py /项目
python3 scripts/project.py impact /项目
python3 scripts/project.py checkpoint /项目
```
