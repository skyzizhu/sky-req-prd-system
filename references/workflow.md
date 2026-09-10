# 项目与版本工作流

## 目录

```text
project/
├── project.json
├── config.md                         # 可选的项目偏好
├── build.py
├── projectlib.py
├── versions/
│   ├── v1.0/
│   │   ├── .snapshot.json           # 冻结时所有版本文件的 SHA-256
│   │   ├── .baseline.json           # 上次确认维护完成的源文件哈希
│   │   └── content/
│   │       ├── manifest.json
│   │       ├── spec.json
│   │       ├── overview/
│   │       ├── requirements/
│   │       ├── prototype/
│   │       │   ├── list.html
│   │       │   └── assets/          # 本版独立的 CSS/JS/spec-data.js
│   │       ├── testing/
│   │       └── launch/
│   └── v1.1/...
└── site/
    ├── index.html                    # 永久项目入口
    └── js/data.js                    # 全版本编译数据
```

版本采用完整物料副本，让历史原型自包含。新版本只重写变化文件。避免无版本约束的远程原型素材；需保存历史外观的资源应复制到版本内。外壳不属于历史内容快照，升级外壳前做兼容验证。

## 项目 schema

```json
{
  "schema_version": 2,
  "id": "稳定项目标识",
  "name": "订单管理",
  "summary": "项目定位与长期范围",
  "current_version": "v1.1",
  "versions": [
    {"id":"v1.1","title":"批量完成","status":"planning","base":"v1.0","goal":"减少重复处理"},
    {"id":"v1.0","title":"基础订单","status":"released","base":null}
  ]
}
```

版本顺序即导航顺序，通常最新在前。版本 ID 只允许小写字母、数字、连字符与点。状态与需求 confirmed/pending 不共用字段。

各版 manifest 保留 1.0 的 product/modules/pages 结构。页面 ID 在**同一版本全局唯一**，跨版本保持相同 ID 便于比较；模块 id 不随标题改动。页面 type 增加 `spec`，无需 file，由 spec.json 自动生成正文。

```json
{
  "product":{"name":"订单管理","form":"web","audience":"b","version":"v1.1","tagline":"管理订单","updated":"2026-09-08"},
  "modules":[
    {"id":"requirements","title":"需求文档","layout":"continuous","pages":[
      {"id":"spec","title":"页面需求与验收","type":"spec","source":"ai-inferred","status":"pending"}
    ]},
    {"id":"prototype","title":"交互原型","pages":[
      {"id":"order-list","title":"订单列表","type":"prototype","file":"prototype/list.html","source":"ai-inferred","status":"pending"}
    ]}
  ]
}
```

其他 type：markdown、mermaid、prototype、html-embed。file 相对本版 content，禁止越界。多端沿用 product.ends，各端原型按模块分组，ID 带端前缀避免碰撞。

## 命令

以下 `project.py` 位于 Skill 的 scripts/。不会操作 Git 或调用网络。

```bash
python3 <skill>/scripts/project.py discover <工作区>
python3 <skill>/scripts/project.py init <空项目目录> --name "订单管理" --form web --version v1.0
python3 <skill>/scripts/project.py new-version <项目目录> --version v1.1 --name "批量完成"
python3 <项目目录>/build.py
python3 <skill>/scripts/validate.py <项目目录>
python3 <skill>/scripts/project.py impact <项目目录> --version v1.1
python3 <skill>/scripts/project.py checkpoint <项目目录> --version v1.1
python3 <skill>/scripts/project.py freeze <项目目录> --version v1.1
python3 <skill>/scripts/project.py status <项目目录> --version v1.1 --state developing
python3 <skill>/scripts/project.py status <项目目录> --version v1.1 --state released
python3 <skill>/scripts/project.py upgrade-shell <项目目录>            # 预览：外壳/构建工具/规划版共享资源与模板的差异
python3 <skill>/scripts/project.py upgrade-shell <项目目录> --apply   # 应用升级
```

new-version 可加 `--from-version v1.0`，默认继承 current_version；若来源仍是 planning 必须明确 --from-version，避免无意继承未完成草稿。版本追加到列表末尾（时间正序），左侧菜单旧版在上、新版在下。同版本修订直接编辑，不调用 new-version。新增版本复用项目 ID、原 site/index.html 和旧深链接，只追加菜单及变化物料；命令检查冻结历史哈希未变，并回报原固定入口。首次 init 创建概览与九章登记，缺失内容标待补；接下来按用户范围补充物料。

**继承版本的九章补齐义务**：new-version 继承的九章（用户/埋点/非功能/验收/里程碑/风险/附录）可能仍是「待补充」占位——新版本交付前，Agent 必须按本版业务逐章补写或显式标注不适用及原因，不得原样留白交付；补写内容标「AI 推断 + 待确认」走评审转正。

upgrade-shell 用于 skill 模板升级后刷新既有项目：默认预览差异，`--apply` 才执行。只覆盖 `site/` 外壳、根目录构建工具与**规划工作版**的共享原型资源（prototype-runtime / annotation-store），被覆盖文件先备份到项目 `.upgrade-backup/<时间戳>/`；冻结与交接快照绝不触碰（只报告漂移）。应用后自动重建并校验；规划版构建戳会显示新模板版本，需重新在浏览器验证关键路径。

freeze：先构建验证，再记录本版全部文件哈希，状态改 frozen。阻塞开发的 pending 需求不得冻结。frozen/developing/released 均不可修改内容；check/build 会检测快照改变。版本状态存在 project.json，状态流转不会修改冻结内容。

## 修改方式矩阵（禁止整体重生成）

项目落地后的一切修改都走增量路径，禁止重生成全部物料（浪费 token 与等待时间，且会覆盖手改）。按修改类型选择入口：

| 修改类型 | 入口 |
|---|---|
| 单字段（需求/规则/实例/验收/控件属性） | `revise_item.py` 单字段补丁，预览后保存 |
| 多字段打包 / Markdown 正文 / 测试与上线物料 | `maintain.py` 物料锚点补丁 或 `edit_project.py` 编辑器 |
| 原型 HTML 文本、业务脚本、样式 | Agent 局部修订源文件（保持稳定 ID 与结构） |
| 新功能 → 下一版 | `new-version` 继承基线，只生成本版变化物料 |
| 外壳与运行时升级 | `upgrade-shell --apply`（不动版本内容） |
| 全部物料重新生成 | 仅 init 后首次生成允许；落地后禁止 |

## 修改保护与影响检查

### 同版本交接修订

用户要求交接当前工作成果时执行：

```bash
python3 <skill>/scripts/project.py handoff <项目目录> --version v1.1 --revision r1 --name "第一轮开发交接"
```

工作版 v1.1 保持 planning，可继续修订；命令复制完整 content 到内部版本 `v1.1.r1`，在副本编译原型数据后冻结快照。产品仍属于 v1.1，project.json 中 handoff_parent/revision 记录归属；左侧把交接归入 v1.1 下的“交接修订”，不是新产品版本。每次编号唯一，不能覆盖。r2 的比较基线为 r1，父版本 current_handoff 指向最新一次交接；项目 current_version 仍是工作版。

固定入口的 `#/v/v1.1.r1/_changes/report` 展示该次差异及全套物料链接；页面深链接仍采用该内部版本 ID，原型资源和模拟状态独立。旧链接不自动跳到最新修订，顶部标明历史交接或当前开发依据。普通保存不创建交接，不自动 checkpoint，不把待确认事项改为已确认；阻塞需求或子规则尚待确认则拒绝交接。

交接副本可使用现有 status 命令进入 developing/released，文件仍不可修改。原有已冻结版本继续只读，不能借此解冻；需要修改时先按已有工作流建立规划工作版。新流程的 freeze（锁定整个工作版）与 handoff（冻结一次交接，继续保留工作草稿）按用户意图选择。

命令先在临时副本验证，并在落盘前检查项目指纹。目录复制、元数据及构建写入仍不是完整事务；中断时保留目标目录，检查 project.json、快照和构建结果，不能删掉快照后复用编号重试。避免和编辑/构建命令同时运行。

开始更新时先 validate，再 impact、读取目标文件：
- since_checkpoint 标出上次工作完成后新增/修改/删除的源文件，**可能来自人工修改**，需读取并保留；无法判断时展示具体差异再问。
- since_base_version 比较当前版与来源版本的文件变更。
- changed_requirements、review_pages、review_interactions、review_acceptance 给出结构化需求变化的关联复核范围。

哈希能发现变化，不能确定作者，也不能自动证明所有相关文案已同步。对受影响的编号、旧数值和规则关键词执行文本搜索，检查 PRD 外的文案、原型脚本和测试说明。交付时明确仍需人工判断的关联。

完成本次修改、构建、检查及业务验证后才 checkpoint。它只更新源文件基线，不清除任何快照保护。命令不会自动推断用户确认了需求。

## 迁移 1.0 方案

```bash
python3 <skill>/scripts/project.py migrate <已有方案目录> --version v1.0
```

迁移先把原 content、site、build.py 复制到 migration-backup，再把 content 复制到 versions/v1.0/content，安装新外壳，固定 site/index.html 不变。旧 content 保留；不要主动删除备份。旧 `#/模块/页面` 链接映射至当前工作版本。

迁移不编造需求关联。缺 spec 的旧版可展示、会发出关联未建立警告；需要交互能力时，在新版本补建 spec、外部 JS 和需求面板。迁移不代表已经冻结或发布，请依据用户对该产品历史状态的说明执行。

## 导航与详情空间

项目壳的导航按三级区分：版本使用有底色的粗体组标题，模块使用次级标题与树状引导线，页面使用进一步缩进的常规字重及选中条。当前路由自动展开所属模块，并用 aria-current 标记页面。

顶部导航保持单行紧凑（桌面默认 40px），历史状态作为同行短标签保留。原型页不在 iframe 上方重复输出页面大标题、说明条和历史横幅；“新窗口打开”和“专注查看”集中在顶部。专注查看收起左栏，可通过按钮退出。

原型内的共享工具栏保持单行（默认 40px）；窄窗口横向滚动控件，不能压缩为不可操作的极小按钮。新的样式在规划版本使用；已经冻结的原型资源不随外壳更新覆盖。

## 构建与恢复

项目根 outcomes/ 保存交付后的验收/指标记录，按 outcomes.md 追加，与冻结版本内容分离。构建指纹包含台账；记录后重建固定入口才能展示最新结果。复制或备份项目需包含台账；它不是防篡改审计日志。

每次构建写完整项目数据并保存内容哈希，validate 检查构建是否过期或被修改。规划版本编译本地 spec-data.js；冻结版本资源不会重写。构建错误不应交付。

新版本追加或物料保存后，已经打开的静态站点需要刷新才能载入最新编译数据；仅切换 hash 不会重新加载 data.js。入口路径/部署地址不变，不能把当前浏览器未刷新的旧菜单误当成新项目。托管时继续更新同一部署位置，按实际服务配置验证缓存，不自动创建新的临时链接。

PRD 正式编辑可使用 editing.md 的本机服务或共享命令；原型脚本及结构调整仍由 Agent 完成。建议版本内容纳入用户自己的 Git。完整多文件工作流不是事务；中断后检查 project.json、版本目录、`.editing/` 保存记录和 validate 报错，保留已有内容，补齐缺失项后重新构建。不要反复运行 init 覆盖现有项目。
