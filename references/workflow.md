# 工作流细则：manifest schema、初始化、更新、验证、FAQ

## manifest.json schema

```jsonc
{
  "product": {
    "name": "产品名",
    "form": "desktop",          // 主形态：web|desktop|mobile|h5|miniapp|tv，必填
    "ends": ["mobile", "web"],  // 可选：多端组合（如 C 端 App + web 管理后台）；单端省略
    "version": "0.1.0",
    "tagline": "一句话定位",
    "updated": "YYYY-MM-DD"
  },
  "modules": [
    {
      "id": "pending",           // 固定第一个：待确认清单聚合页
      "title": "待确认清单",
      "special": "pending-report",
      "pages": []
    },
    {
      "id": "requirements",      // kebab-case，路由用
      "title": "需求文档",
      "pages": [
        {
          "id": "capture",                  // kebab-case
          "title": "剪贴板捕获",
          "type": "markdown",              // markdown|mermaid|prototype|html-embed
          "file": "requirements/capture.md",  // 相对 content/，不含 content/ 前缀
          "source": "origin",              // origin|ai-inferred
          "status": "confirmed",           // confirmed|pending
          "summary": "侧栏/页头一句话摘要"
        }
      ]
    }
  ]
}
```

规则：

- 模块顺序即菜单顺序：pending → 产品概览 → 需求文档 → 原型图 → 测试 → 上线目标
- `special: "pending-report"` 模块无 pages，站点自动聚合所有 pending 页面
- file 路径与目录一致：requirements/、prototype/、info-structure/、testing/、launch/
- 用户评审通过某页后：把 status 改为 confirmed → 重跑 build.py

## 初始化（首次生成）

1. 建目录结构，复制模板：
   - `<skill>/template/build.py` → `<系统>/build.py`
   - `<skill>/template/site/` → `<系统>/site/`（整个目录）
   - `<skill>/assets/wireframe.css` → `<系统>/content/prototype/assets/wireframe.css`
   - `<skill>/assets/info.css` → `<系统>/content/info-structure/info.css`
2. 判定产品形态（缺失必问，见 SKILL.md 阶段 1）
3. 归纳清单 → 用户确认
4. 写 manifest → 按固定节点 + 纳入的条件节点生成内容文件
5. `python3 build.py` → 自检 → 交付报告

## 更新（增量，默认模式）

1. 读现有 manifest，对照用户的新需求，产出**变更清单**（涉及增删页面/模块时，先备份 `cp content/manifest.json content/manifest.backup.json`）：
   - 新增页（写明 source 判定）
   - 修改页（写明改什么）
   - 删除/下架页（需用户确认）
   - 状态翻转页（pending → confirmed 等）
2. **人工修改保护**：对要覆盖的每个已存在文件，先读当前内容；若当前内容包含上次生成时没有的段落/修改（与 manifest 的 summary 及本次要写的内容对不上），暂停并向用户展示差异确认，而不是直接覆盖。用户手改是常态，产物是活文档。
3. 执行变更：只写受影响文件；同步 manifest（页面、updated、状态）。
4. `python3 build.py` → 自检 → 交付报告（含变更清单）。

典型更新指令与动作：

| 用户说 | 动作 |
|---|---|
| "把回收站保留期从 7 天改成 3 天" | 改对应需求 md + 相关标注/用例中的数字 → build |
| "新增一个深色模式设置项" | FR 表加行 → 功能清单同步 → settings.html 线框加开关 → build |
| "快速粘贴这块确认了" | manifest 中相关页 status → confirmed → build（徽标与待确认清单更新） |
| "把风险与依赖、名词解释也都确认了" | 批量 status 翻转 → build → 报告剩余待确认数 |
| "再加一个页面：关于我们" | manifest 加页（判断归入哪个模块）→ 生成文件 → build |

## 验证（每次 build 后）

```bash
cd <系统目录> && python3 build.py                                # 必须成功
python3 <skill 目录>/scripts/validate.py <系统目录>               # 退出码必须为 0
```

validate.py 覆盖：manifest JSON 与枚举合法性、id 唯一性与 kebab-case、file 引用存在性、HTML 零内联（style=/`<style>`/`<script>`）、data.js 新鲜度（不早于任何 content 文件）。脚本报错必须修复重跑。

脚本之外肉眼确认：Mermaid 语法、原型标注无交叉且四色语义正确。

有浏览器环境时可进一步：起 `python3 -m http.server`，截图检查菜单/徽标/原型标注。

## 交付报告

固定格式见 SKILL.md 阶段 5。要点：入口文件**绝对路径** + 双击打开说明 + 变更清单 + 待确认统计。这是用户找产物的唯一线索，不能省略。

## 内容深度基准（防止过深或过浅）

- FR 表：每模块 5~15 行，超过时考虑拆模块
- 用户故事：3~6 个；关键场景：2~4 个
- 原型页：每页标注 3~5 条；线框组件够用即可，不做视觉细节
- Mermaid 图：单图节点 ≤ 15，超过用 subgraph 拆分或拆多张图
- 验收标准：8~12 条；测试用例按模块 3~5 条
- 所有「AI 补全的深度」以够评审用为准，宁可待确认也不要编造细节

## FAQ / 边界情况

- **用户想改 site/ 外壳样式**：可以改，但改完把 index.html 中资源 `?v=N` +1，并提醒此后 skill 不再维护外壳的一致性。
- **模板升级**：skill 的 template/ 更新后，已存在的系统**不自动覆盖** site/；只提示用户有新模板，由用户决定。
- **data.js 与 content/ 不同步**：以 content/ 为准重跑 build.py 即可；data.js 是纯生成物，可随时删除重建。
- **多产品**：`product-systems/<产品名>/`，每个产品独立一套完整结构。
- **git**：建议用户纳管；skill 不主动执行 git 命令，仅在报告尾部提示一次（首次）。
- **大产品防上下文溢出**：>20 页时分批生成（manifest + 概览 + 功能清单先行），每批 build 一次保持可用。
- **多端产品**：`product.ends` 记录端组合（如 ["mobile","web"]）；原型图模块按端分组（id 如 `prototype-app` / `prototype-admin`，标题「原型图 · App」「原型图 · 管理后台」），每端有自己的页面总览与页面；功能清单加「端」列；各端画布按各自形态选择。
- **版本演进**：仅当用户明确说「开始 X 版本 / 新版本规划」时 bump `product.version` 并在概览页版本记录表追加一行；普通需求修改不 bump。每次变更刷新 `product.updated`。
- **回滚**：结构变更前已备份 manifest.backup.json；内容回滚建议走 git（无 git 时报告里提醒）。
- **中断恢复**：若上次生成中断（manifest 引用的文件缺失），先报告缺失清单并补齐，再继续新需求。
