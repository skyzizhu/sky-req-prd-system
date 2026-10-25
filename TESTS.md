# V2 验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/delivery.cjs
python3 scripts/create_static_demo.py /空目录
python3 scripts/validate.py /空目录
```

Python 检查项目与版本、交接快照、编辑冲突与撤销、附件、标准 PRD、规则关联及状态画布契约。Node 检查交接筛选和导出。

浏览器用真实打开页面验证：站点与独立页默认可读、状态切换与恢复、双向定位、状态对照、PRD 和验收引用、交接信息、定位链接、键盘和窄窗口。可选自动化脚本为 tests/static-reader-browser.cjs、prd-browser.cjs、delivery-browser.cjs、editor-browser.cjs、handoff-browser.cjs、maintenance-browser.cjs、outcomes-browser.cjs、standard-prd-browser.cjs；需 Playwright 和已安装浏览器。

旧演示、浮窗拖动、批注导入及旧项目迁移测试随功能删除；不作为 V2 的交付能力。

质量回归还验证：删除元素清单、精确规则关联或必要失败状态会报错；错误的验收关联、被 HTML 隐藏的必要元素、漏检维度、缺少不适用理由会报错；纯文字交付和无视觉差异的数值边界不强制新增画面；非阻塞待决策不会被当作已确认。

流程图回归验证模块全貌、功能节点映射、子流程/状态图及其上层节点；缺失图、无条件连线、错误节点、无入口可达的孤岛、层级循环及失效原型状态引用会报错。PRD 查看与完整导出使用同一套图数据，浏览器需确认渲染为图形。

按适用性回归：无流程且无状态流转时不要求图；仅有状态流转时不要求虚构父流程；持续运行状态机不强制终态。

内容去重回归：完整 PRD 每个 GWT 正文只出现一次；关联页面去重但非空控件属性保留；交接 Markdown 引用原文，JSON 保留验收全文；移除项引用旧版，只有功能物料时不生成无效标准章节链接。浏览器复核验收自动展开与定位、原型当前状态元素同步、对照模式各状态元素可展开。
