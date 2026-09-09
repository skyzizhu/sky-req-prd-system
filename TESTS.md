# 测试与本地验证

测试分三层，按改动范围选择；提交前建议至少让相关层全绿。

## 环境要求

| 层 | 依赖 | 说明 |
|---|---|---|
| Python 单测 | Python ≥ 3.9，仅标准库 | 无需 pip 安装任何包 |
| Node 逻辑测试 | Node ≥ 18 | 使用内置 node:test / node:assert |
| 浏览器测试 | Node ≥ 18 + playwright | `npm i -D playwright && npx playwright install chromium`；未安装时该层直接报模块缺失（不是跳过） |

## 第一层：Python 单元测试（50 例）

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

覆盖项目/版本/交接/台账/编辑器/质量审计的纯逻辑（projectlib、outcomelib、prdlib、editlib、audit_quality 等），不需要浏览器。

## 第二层：Node 逻辑测试（16 例）

```bash
node --test tests/annotations.cjs tests/delivery.cjs
```

覆盖标注存储（annotation-store.js）与开发交接导出（delivery.js）的纯逻辑，零外部依赖。

## 第三层：浏览器行为测试

先用 create_demo 生成一个演示项目，再逐个运行（参数：项目根 + 截图目录）：

```bash
python3 scripts/create_demo.py /tmp/psdemo-test
mkdir -p /tmp/psdemo-shots
for t in browser prd-browser delivery-browser replay-browser handoff-browser \
         editor-browser maintenance-browser outcomes-browser standard-prd-browser; do
  node tests/$t.cjs /tmp/psdemo-test /tmp/psdemo-shots || break
done
```

- `browser.cjs / prd-browser.cjs / delivery-browser.cjs / replay-browser.cjs`：外壳导航、结构化 PRD、交接导出、复现链接的实际行为；
- `handoff-browser.cjs`：交接修订（只收项目根参数）；
- `editor-browser.cjs / maintenance-browser.cjs / outcomes-browser.cjs / standard-prd-browser.cjs`：本机编辑服务、轻量维护、台账与九章 PRD（内部自建临时项目）；
- 全部脚本离线运行（外网请求被拦截），断言失败即非零退出。
- 提示：`browser.cjs` 断言「需求差异」等文案，改外壳文案时同步更新测试。

## 按改动范围选择

| 改动 | 至少跑 |
|---|---|
| `scripts/*.py`、`template/*.py` | 第一层 |
| `assets/prototype-runtime.*`、`assets/annotation-store.js` | 第一层 + 第二层 + 浏览器层（至少 browser / replay） |
| `template/site/`（外壳） | 第一层 + 浏览器层（至少 browser / prd-browser / delivery-browser） |
| `references/`、`SKILL.md`、`config.md` | 无需测试，人工评审 |

## 相关质量门禁

```bash
# 需求规则完整性审计（--strict 时有缺口则 exit 1，可作门禁）
python3 scripts/audit_quality.py <项目目录> --version v1.1 --strict

# 项目结构与关联校验（build 后必须通过）
python3 scripts/validate.py <项目目录>
```

两者都只检查已记录数据：没有缺口不等于业务正确或开发已认可，关键路径仍需按 SKILL.md 在浏览器实际操作验证。
