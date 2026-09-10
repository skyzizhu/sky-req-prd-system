# AGENTS.md — sky-req-prd-system

> 把产品经理手里零散的产品需求，变成开发直接能用的完整交付物——结构化需求文档、可交互原型、测试用例、上线计划。

## Commands

```bash
# 定位已有项目
python3 scripts/project.py discover /工作区

# 新建项目（空目录）
python3 scripts/project.py init /空目录 --name "项目名" --form web --version v0.1

# 下一版本（继承基线，只改变化）
python3 scripts/project.py new-version /项目 --version v0.2 --name "主题" --from-version v0.1

# 构建
python3 /项目/build.py

# 结构校验（每次修改后必须通过）
python3 scripts/validate.py /项目

# 规则完整性审计
python3 scripts/audit_quality.py /项目 --version vX

# 修改影响面
python3 scripts/project.py impact /项目 --version vX

# 记录工作基线
python3 scripts/project.py checkpoint /项目 --version vX

# 冻结版本
python3 scripts/project.py freeze /项目 --version vX

# 交接快照
python3 scripts/project.py handoff /项目 --version vX --revision r1

# 外壳升级（不动版本内容）
python3 scripts/project.py upgrade-shell /项目 --apply

# 局域网共享
python3 scripts/serve.py 8000 /项目

# 本机 PRD 编辑器
python3 scripts/edit_project.py /项目 --version vX

# 单字段精准修改
python3 scripts/revise_item.py /项目 --version vX --query '关键词'

# 轻量检索
python3 scripts/maintain.py '/项目/site/index.html#/路径' --version vX --query '关键词'
```

## Testing

```bash
python3 -m unittest discover -s tests -p 'test_*.py'   # 50 例，零依赖
node --test tests/annotations.cjs tests/delivery.cjs    # 16 例，零依赖
node tests/browser.cjs /示例项目 /截图目录               # 需 playwright
```

分层说明与覆盖矩阵见 [TESTS.md](TESTS.md)。

## Project Structure

```
skills/sky-req-prd-system/
├── SKILL.md                # Agent 完整交付流程与规范（入口）
├── AGENTS.md               # 本文件（跨 Agent 通用入口）
├── config.md               # 用户标准（硬约束，优先于默认）
├── references/             # 12 份规范文档（按需读取）
│   ├── workflow.md         # 项目结构、版本命令、修改方式矩阵
│   ├── nodes.md            # 按业务范围裁剪物料
│   ├── prototype.md        # 原型运行时与状态覆盖标准
│   ├── delivery-quality.md # 需求深化、测试格式、上线四类、埋点骨架
│   ├── editing.md          # 本机 PRD 编辑器与原型属性
│   └── …                   # 按需读取，不默认加载全部
├── scripts/                # 项目管理、构建、校验、审计工具
├── assets/                 # 共享原型运行时（JS/CSS）
├── template/               # 项目固定入口与构建库模板
├── tests/                  # Python 单测 + Node 逻辑 + 浏览器测试
├── TESTS.md                # 测试运行说明
└── examples/               # 示例项目生成脚本
```

生成的项目结构：

```
project/
├── project.json            # 版本注册表
├── build.py                # 项目构建脚本
├── versions/
│   ├── v0.1/content/       # manifest、spec、文档、原型、测试、上线
│   └── v0.2/content/
└── site/index.html         # 固定入口（单入口，多版本共用）
```

## Code Style

- 需求颗粒度：细目可独立开发、可独立验收；边界与异常为 boundary 细目
- 描述一句话；细节进细目与实例；禁止冗余（单一来源+指针）
- 每条需求附带 GWT 验收；有 rule_details 时 rules 省略
- 原型默认浅色主题；不做深色背景（除非用户明确要求）
- 禁用词汇：赋能、抓手

## Git Workflow

- 分支：v1.1（开发）；main（稳定基线）
- 提交后推送到 GitHub（`git push origin v1.1`）
- 版本追加到列表末尾（时间正序），左侧菜单旧版在上、新版在下
- 冻结版本内容不可修改，后续改动进下一版

## Boundaries

- 禁止整体重生成已落地项目的物料（只用增量入口修改）
- 禁止在冻结版本中修改内容（后续改动进下一版）
- 用户点名可裁剪交付物，但须在概览列明未出项
- 输入过于简洁时可适当挖掘补细颗粒度（标 AI 推断+待确认），业务决策不代拍板
- 不编造公司标准、不自动放行上线、不操作外部系统

## Agent Compatibility

SKILL.md（YAML frontmatter + Markdown）兼容 Claude Code / ZCode / Codex / Cursor / Windsurf 等所有支持文件读取的 Agent。本文件（AGENTS.md）遵循 [agents.md](https://agents.md/) 开放标准，提供跨 Agent 通用入口。
