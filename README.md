# sky-req-prd-system · 1.1

把产品需求维护成一个长期使用的项目方案站点。开发在同一入口查看版本差异、需求、可操作原型、验收与上线范围；原型内直接打开对应页面的需求。

## 1.1 的变化

- 验收与上线复盘台账：原型/真实产品分开记录，保存环境、构建、执行人和证据；指标记录口径、基线、目标、实际及观察窗口。更正留历史、物料变动提示复核，跟进事项关联已有规划版本。浏览器支持 JSON 草稿导出，正式入库使用 `scripts/record_outcome.py`；不改冻结物料、不自动放行上线。

- 角色与状态复现链接：spec 声明合成场景，固定入口及独立原型链接还原指定版本、角色与初始数据；跨页演示隔离、重置不影响普通演示，失效场景明确拒绝。接入与权限行为验收见 references/replay.md。

- 批注处理闭环：待处理/采纳/驳回/完成、处理说明、需求及正式修改记录关联、验证说明与处理历史；修改批注内容会重新待处理。支持筛选和新版 JSON 导出，`scripts/review_notes.py` 只读核对本地需求与保存记录。

- 开发交接视图：按变化、待确认/阻塞及关注方向筛选需求，查看规则、控件和验收，导出当前筛选的 Markdown/JSON 任务包。分工与依赖按实际资料填写，不自动创建外部工单。

- 同版本多次交接：`python3 scripts/project.py handoff <项目> --version v1.1 --revision r1`，冻结独立交接快照，保留可编辑草稿；左侧按产品版本归组，标明当前开发依据，历史深链接不跳转。

- 本机 PRD 编辑器：`python3 scripts/edit_project.py <项目目录> --version <规划版本>`。支持既有需求/规则/实例/验收及 Markdown 正文的正式编辑、变更预览、冲突检查、保存与撤销。详见 references/editing.md；原型业务脚本仍按影响报告复核。
- 同一编辑器支持点选布局预览修改原型文案、原生输入约束、选项、默认值、跳转目标与有限宽度；保存到 spec，runtime 应用。静态预览不运行页面脚本，实际交互需另行验证。

- 一个项目一个固定入口，左侧按版本组织全部物料。
- 新版本继承已有物料，只修改本次变化；冻结历史文档、原型和资源。
- PRD 和可拖拽、缩放、停靠的“本页需求”面板共用 spec.json。
- 控件有稳定编号与行为说明；支持演示/标注模式、页面跳转、弹框、场景切换与重置。
- 可手动新增/编辑/删除/恢复原型标记：选中控件或位置后就地填写优先级和说明，确认即增加；再次点击默认查看。支持撤销及 JSON 导出/导入。修改保存在当前浏览器，不自动修改 PRD 或共享至其他设备。
- 页面业务脚本实现输入、筛选、提交、异常和模拟数据；共享运行时不包含真实后端。
- 检查需求变化影响、控件覆盖、验收关联、资源路径、历史哈希和构建新鲜度。
- 可备份迁移原 1.0 项目；未建立 spec 的历史物料继续可浏览。

Skill 版本 1.1 与用户项目版本独立。`v1.0` Git 标签保留原 Skill，`v1.1` 分支开发新能力。

## 使用场景

“为订单管理创建首版方案，Web，企业内部使用，范围是创建和查阅订单。”

“在这个项目的下一版增加批量完成，沿用当前入口，保留历史版本。”

“把当前版订单名称上限调整为 60 字，同步原型、校验和验收。”

“打开订单列表原型，同时查看当前页面的需求规则。”

调用时先定位已有项目，再确定版本和范围。更新一个功能不会默认建立另一个独立项目；项目识别存在歧义时需提供项目目录。

## 结构

```text
project/
├── project.json
├── build.py / projectlib.py
├── versions/
│   ├── v1.0/content/        # manifest、spec、文档、原型、测试与上线
│   └── v1.1/content/
└── site/index.html          # 项目固定入口
```

规划版可以修订；冻结、开发中、已发布版本保护内容快照，后续改动进入下一版。冻结是产品交付动作，需依据用户实际确认状态执行。

## 本地体验

仅需 Python 3.9+；浏览器使用现代 Chrome、Edge 或 Safari。核心页面与原型使用本地脚本，可 file:// 打开；Mermaid 图表仍使用 CDN，断网降级为源码。跨页面本地模拟存储依赖浏览器支持，也可用本机 HTTP 服务演示。

```bash
python3 scripts/create_demo.py /绝对路径/空的示例目录
```

双击示例目录的 `site/index.html`。示例含已发布 V1.0 与规划 V1.1：
创建订单 → 查阅详情 → 返回列表 → 批量完成；也可切换空态、加载、失败、权限，打开本页需求并拖拽停靠。示例需求是合成数据，confirmed 仅为测试冻结能力。

项目工具：

```bash
python3 scripts/project.py discover /项目所在工作区
python3 scripts/project.py init /空目录 --name "订单管理" --form web --version v1.0
python3 scripts/project.py new-version /项目目录 --version v1.1 --name "批量完成"
python3 /项目目录/build.py
python3 scripts/validate.py /项目目录
python3 scripts/project.py impact /项目目录
python3 scripts/project.py checkpoint /项目目录
```

迁移原项目：`python3 scripts/project.py migrate /项目目录 --version v1.0`。旧内容保留，并创建 migration-backup。固定入口不变。

长期团队链接需要固定服务或托管位置。临时分享：`python3 scripts/serve.py 8000 /项目目录`，服务会暴露指定项目目录给可达的局域网用户。请按实际分享范围启动。

## 配置与安装

`config.md` 为全局偏好；项目自己的 config.md 优先，用户当场要求优先于两者。默认配置注释不生效。

```bash
git clone https://github.com/skyzizhu/sky-req-prd-system.git ~/.agents/skills/sky-req-prd-system
bash ~/.agents/skills/sky-req-prd-system/scripts/install.sh
```

开发分支使用 `git switch v1.1`；默认 main 仍是原稳定基线。install.sh 支持链接或 --copy，详情运行时见脚本说明。

## 开发与验证

开发 Skill 时只修改本仓库的 SKILL.md、references、assets、template、scripts 与 tests。回归测试在临时目录生成一次性项目；不得为了展示或验收而更新用户已有的方案目录。模板升级也不会自动覆盖已冻结版本。

```bash
python3 -m unittest discover -s tests -v
node --test tests/annotations.cjs
NODE_PATH=/包含playwright的node_modules node tests/browser.cjs /示例目录 /截图目录
```

Python 测试覆盖冻结保护、构建过期、关联断裂、验收缺失、内联样式和越界路径、迁移备份。浏览器测试操作实际交互与面板。静态验证不证明任意生成项目的业务逻辑正确，生成后的关键路径仍需实际验收。

- SKILL.md：Agent 入口与交付流程。
- references/workflow.md：项目 schema、版本命令、修改保护。
- references/prototype.md：spec 与原型运行时接入。
- references/nodes.md：按业务范围裁剪物料。
- assets/：共享线框和原型运行时。
- template/：固定入口与项目构建库。
- examples/order-demo/：可操作的参考原型。
- tests/：结构与浏览器回归。

MIT License。
