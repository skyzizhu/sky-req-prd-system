# sky-req-prd-system

> req / PRD in → **Product System** out：把 PRD 文档或零散产品需求，整理为一个可浏览、可增量维护的「产品系统」Web 站点。

[![skill](https://img.shields.io/badge/ZCode-skill-blue)](https://github.com/skyzizhu/sky-req-prd-system) ![forms](https://img.shields.io/badge/%E4%BA%A7%E5%93%81%E5%BD%A2%E6%80%81-web%7Cdesktop%7Cmobile%7Ch5%7Cminiapp%7Ctv-green)

## 它做什么

输入 PRD 文档 / 半成品需求 / 零散产品需求，输出一个双击即开的静态站点：

- **左侧菜单 + 右侧详情**：待确认清单 → 产品概览 → 需求文档 → 原型图 → 测试 → 上线目标
- **标准 PRD 骨架**：固定节点（产品目标/功能清单/功能需求/用户故事/非功能/风险/名词解释…）+ 条件节点（数据埋点/泳道图/状态图/权限/接口…按需生成）
- **低保真线框原型**：按产品形态选画布，连线式四色标注（红=核心、黄=待确认、蓝=说明、绿=参考），标注线永不交叉
- **Mermaid 图**：整体流程 / 泳道 / 状态图，CDN 失败自动降级源码展示
- **全面溯源**：每个页面标注「PRD 原文 / AI 推断」+「已确认 / 待确认」，待确认清单自动聚合供评审
- **增量更新**：manifest 是唯一事实源，需求变更只改受影响文件；覆盖前人工修改保护
- **file:// 双击直开**：无 fetch、无 ES modules，内容经 `build.py` 编译进 `site/js/data.js`

## 安装

```bash
git clone https://github.com/skyzizhu/sky-req-prd-system.git \
  ~/.agents/skills/sky-req-prd-system
```

## 目录结构

```
sky-req-prd-system/
├── SKILL.md            # 五阶段流程 + 核心规则
├── references/
│   ├── nodes.md        # 固定/条件节点清单与判定依据
│   ├── prototype.md    # 画布/线框组件/连线式四色标注规范
│   └── workflow.md     # manifest schema、增量更新、验证清单
├── template/
│   ├── build.py        # content/ → site/js/data.js 编译脚本
│   └── site/           # 站点外壳（index + css/ + js/，零内联）
└── assets/
    ├── wireframe.css   # 低保真线框组件库
    └── info.css        # 信息结构图样式
```

## 使用

在 ZCode 中直接说：

- 「帮我建一个产品系统，需求是 …」
- 「把这份 PRD 整理成产品系统」（附文档）
- 「把回收站保留期从 7 天改成 3 天」（增量更新）

生成完毕会报告**入口文件绝对路径**，双击 `site/index.html` 即可浏览。

## 设计原则

1. 内容与站点分离：只生成 `content/`，外壳一次安装基本不动
2. manifest 唯一事实源：结构变更先改 manifest
3. 增量更新 + 人工修改保护：产物是活文档，不是一次性输出
4. 全面溯源：AI 补全永远可见、可评审
5. 零依赖：纯静态 + Python 标准库构建脚本

## License

MIT
