# sky-req-prd-system

> req / PRD in → **Product System** out
> 把散落的需求，变成一个能看、能改、能追溯的产品系统。

[![skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-blue)](https://agentskills.io) ![agents](https://img.shields.io/badge/%E5%85%BC%E5%AE%B9-ZCode%20%7C%20Claude%20Code%20%7C%20Codex%20%7C%20Gemini%20%7C%20OpenClaw-green)

**一句话**：这是给产品经理的 AI 工作流 skill。你把 PRD 文档、半成品需求、甚至几句话的零散想法交给它，它还你一个**双击即开的「产品系统」网站**——需求文档、流程图、低保真原型、测试与上线目标，在一个站点里浏览、评审、持续演进。

## 它解决产品经理的什么痛点

| PM 的日常困境 | sky-req-prd-system 的答案 |
|---|---|
| 需求散落在聊天记录、会议纪要、脑子里，永远凑不成一份完整文档 | 扔进来就行：AI 按标准 PRD 骨架（11 个固定节点 + 15 个条件节点）整理成结构化站点 |
| PRD 模板太重，写完即过时，没人愿意维护 | 产物是**活文档**：说一句“把回收站改成 3 天”，只增量更新对应页面，永不整站重生成 |
| AI 生成的内容不敢直接用——分不清哪些是真需求哪些是编的 | **全面溯源**：每个页面带徽标（PRD 原文 / AI 推断 × 已确认 / 待确认），“待确认清单”自动聚合，评审时逐条勾 |
| 原型图和需求文档两张皮，交互说明堆成一团 | 低保真线框 + **连线式四色标注**（红=核心、黄=待确认、蓝=说明、绿=参考），序号徽章指哪说哪，连线永不交叉 |
| 评审会上翻几十个文档找上下文 | 一个站点：左菜单右详情；投屏「待确认清单」页，从上往下过 |
| 换个 AI 工具就得重来一套 | SKILL.md 遵循开放规范，一条命令装到 ZCode / Claude Code / Codex / Gemini / OpenClaw |

## 它能生成什么

一个纯本地、零依赖、**双击 index.html 就能打开**的静态站点：

```
product-system/
├── content/                   # 内容层（AI 生成/维护的唯一部分）
│   ├── manifest.json          # 结构唯一事实源
│   ├── overview/              # 产品概览：定位、商业/用户目标、北极星、竞品、版本记录
│   ├── requirements/          # 需求文档：功能清单、FR 详述、用户故事、非功能、
│   │                          #   风险依赖、名词解释 + 流程/泳道/状态图（Mermaid）
│   ├── info-structure/        # 信息结构图（HTML/CSS 卡片树）
│   ├── prototype/             # 低保真线框原型：按产品形态选画布，序号徽章四色标注
│   ├── testing/               # 验收标准（Given/When/Then）、测试用例
│   └── launch/                # 上线目标、里程碑、Checklist、数据埋点
└── site/                      # 展示外壳（一次安装，基本不动）
    └── index.html             # ← 双击这里
```

站点自带：模块折叠菜单（页面自动带 01· 序号）、溯源徽标、待确认聚合页、Mermaid 渲染（断网降级源码）、原型 iframe 预览。

## 怎么用（就是对话）

```
你：帮我建一个产品系统：健身打卡应用，用户每天记录运动、分享给朋友。
AI：（贫瘠输入 → 批量问 3~4 个骨架问题：形态？范围？阶段？目标？）
你：mobile App，全量，0→1 新品，目标是次月留存 35%
AI：（归纳清单确认 → 生成全部页面 → 构建+校验）
AI：✅ 产品系统已更新
    入口文件：/Users/xx/ps-test/product-system/site/index.html（双击打开）
    本次变更：新增 23 个页面…  待确认：12 项

你：把打卡积分上限改成每天 50 分，再加一个排行榜页面
AI：（增量更新：只动相关文件 → 变更清单 → 交付报告）

你：快速粘贴这块需求确认了
AI：（状态翻转 → 徽标与待确认清单同步更新）
```

## 五阶段工作流

```
定位（初始化 or 增量）→ 输入解析（形态必判·分级追问·拒绝时类比自补全）
→ 归纳确认（冲突六查·变更清单）→ 生成/更新（manifest 先行·人工修改保护）
→ 构建验证（build.py + validate.py 退出码驱动）→ 交付报告（入口路径·变更·待确认数）
```

核心机制：内容与站点分离 · manifest 唯一事实源 · 增量更新 · 全面溯源 · file:// 直开 · validate.py 不带病交付。

## 安装

SKILL.md 格式遵循开放规范（[agentskills.io](https://agentskills.io)），各主流 agent 均可直接使用，差异仅在发现路径：

```bash
git clone https://github.com/skyzizhu/sky-req-prd-system.git \
  ~/.agents/skills/sky-req-prd-system
```

多 agent 共存时一键安装（symlink 到各家目录，未安装的自动跳过）：

```bash
bash ~/.agents/skills/sky-req-prd-system/scripts/install.sh          # 链接（推荐）
bash ~/.agents/skills/sky-req-prd-system/scripts/install.sh --copy   # 或复制
```

| Agent | 用户级 skills 目录 |
|---|---|
| ZCode | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex CLI | `~/.codex/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| OpenClaw | `~/.openclaw/skills/`（工作区 `skills/` 优先级更高） |

## Skill 仓库结构

```
sky-req-prd-system/
├── SKILL.md            # 五阶段流程 + 核心规则（agent 读取的主文件）
├── references/
│   ├── nodes.md        # 固定/条件节点清单与判定依据
│   ├── prototype.md    # 画布/线框组件/序号徽章四色标注规范
│   └── workflow.md     # manifest schema、增量更新、验证、FAQ
├── scripts/
│   ├── validate.py     # 一致性校验（manifest/引用/零内联/data.js 新鲜度）
│   └── install.sh      # 多 agent 一键安装（symlink/复制）
├── template/
│   ├── build.py        # content/ → site/js/data.js 编译脚本
│   └── site/           # 站点外壳（index + css/ + js/，零内联）
└── assets/
    ├── wireframe.css   # 低保真线框组件库
    └── info.css        # 信息结构图样式
```

## 设计原则

1. 内容与站点分离：只生成 `content/`，外壳一次安装基本不动
2. manifest 唯一事实源：结构变更先改 manifest
3. 增量更新 + 人工修改保护：产物是活文档，不是一次性输出
4. 全面溯源：AI 补全永远可见、可评审，杜绝“AI 编的需求混进真需求”
5. 多端支持：C 端 App + 管理后台等组合，原型按端分组
6. 确定性验证：validate.py 一键校验，不带病交付
7. 零依赖：纯静态 + Python 标准库构建，file:// 双击直开

## License

MIT
