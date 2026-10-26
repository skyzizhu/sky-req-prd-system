# V2 验证

## 数据与模型回归

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/delivery.cjs tests/annotation-model.cjs
python3 scripts/create_static_demo.py /空的预览目录
python3 scripts/validate.py /预览目录 --report /预览目录/quality-report
```

Python 覆盖版本/冻结/交接、编辑冲突与撤销、附件、标准 PRD、规则/验收关联、图结构及交付完整性。Node 覆盖交接筛选/导出、当前标注的精确规则关联和共享规则去重。报告状态及语义复核标准见 [quality-contract.md](references/quality-contract.md)；自动通过不能替代业务确认或实际产品测试。

## 浏览器回归

需 Node.js、可解析的 Playwright 包及已安装浏览器。统一入口自动创建独立临时项目，不修改既有交付物；失败保留临时物料及截图，全部通过后清理。

```bash
node tests/run-browser.cjs
```

默认使用 Playwright 已安装的 Chromium；使用本机 Chrome 可设置 `PW_CHANNEL=chrome`，指定其他可执行文件用 `PW_EXECUTABLE`。依赖位于独立目录时，将其 node_modules 加入 NODE_PATH，无需将依赖打包进技能。

| 用例 | 覆盖 |
| --- | --- |
| static-reader-browser.cjs | 独立页与站点 iframe、默认标注、状态切换/对照、精确规则、PRD 导出、窄屏 |
| diagrams-browser.cjs | 本地图形库延迟冷启动、离线真实SVG、缩放/窄屏/键盘、缺资源与错误语法的明确诊断 |
| local-controls-browser.cjs | 原生选择与联动、状态重置、键盘、窄屏、编号不遮挡控件、控件/标注互不触发、提交受阻 |
| editor-browser.cjs | 属性/正文预览保存、实际属性生效、撤销与冲突；不模拟业务提交 |
| prd-browser.cjs | 业务层次、定位信息、关联页面去重、非空控件属性保留与完整导出 |
| delivery-browser.cjs | 交接筛选、待确认子规则、JSON/Markdown 导出及原型入口 |
| handoff-browser.cjs | 交接版本深链接、历史静态原型及独立快照 |
| outcomes-browser.cjs | 验收记录与复盘、旧基线提示及证据展示 |
| standard-prd-browser.cjs | 标准章节、附录真实上传/下载及完整导出 |

对外合成演示仅由 `scripts/create_static_demo.py` 生成，其 `example_spec()` 与图测试共用数据。`tests/fixtures/versioned_project.py` 是测试生命周期和编辑操作的最小夹具，只保证结构有效，不作为完整交付样例。旧浮窗、批注导入和业务演示能力不再回归。

内容闭合回归：输入关键值从规则中删除会报错；缺少状态核对或漏掉已声明状态会报错；引用型边界场景指向错误类型/缺失 GWT 会报错；实现/验收问题不能标为非阻塞。标准合成演示故意保留真实阻塞信息，默认 validate 返回非零；单测中的非阻塞场景使用独立测试夹具，不修改公开演示的阻塞结论。

网页/导出复核：引用型边界索引不复制 GWT 正文，点击定位具体验收并展开；当前标注按作者顺序列完整必要规则，关联控件只列一次；文字表达理由不进入业务表格，空附录不显示上传操作帮助；背景在功能清单之前。

## 技能行为评测

固定输入与逐场景标准见 `tests/scenarios/delivery.json`。按 [delivery-review.md](references/delivery-review.md) 在临时目录实际使用技能生成候选，再用 `scripts/evaluate_scenarios.py` 汇总审查；单元测试不能替代这些生成评测。未提供候选标 not_run，缺语义/浏览器证据标 review_required。

`test_delivery_review.py` 核对实际 HTML 的枚举/默认/多选/必填/长度/禁用/初始保留值，拒绝错状态和无效引用；同时验证只读、过期证据拒绝、原输入缺失不可通过、明确问题需建议，以及变更状态/图依赖范围。

分支回归：删掉已登记的失败重试连线即使图仍连通也报错；错误场景、断开的路径、重复连线ID均拒绝。控件属性虽匹配但当前标注缺少依据规则会报错；同组子控件精确引用仍可通过。
