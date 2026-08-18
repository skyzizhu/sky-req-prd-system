#!/usr/bin/env python3
"""validate.py —— 产品系统一致性校验

用法：
    python3 <skill>/scripts/validate.py [产品系统目录]    # 缺省为当前目录

检查项：
    1. manifest.json 结构与字段合法性（枚举值、id 规范、唯一性）
    2. 每个页面 file 引用的文件真实存在
    3. content/ 下 HTML 无内联 style / <style> / <script>
    4. data.js 新鲜度：不早于参与编译的文件（manifest + markdown/mermaid）

退出码：0 = 通过（可有警告）；1 = 有错误
"""

import json
import pathlib
import re
import sys
import time

ERRORS = []
WARNINGS = []

FORMS = {"web", "desktop", "mobile", "h5", "miniapp", "tv"}
PAGE_TYPES = {"markdown", "mermaid", "prototype", "html-embed"}
SOURCES = {"origin", "ai-inferred"}
STATUS = {"confirmed", "pending"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    manifest_path = root / "content" / "manifest.json"

    if not manifest_path.exists():
        err(f"缺少 manifest：{manifest_path}")
        report(root, 0, 0)
        return 1

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        err(f"manifest 不是合法 JSON：{e}")
        report(root, 0, 0)
        return 1

    # ---- product 字段 ----
    product = manifest.get("product")
    if not isinstance(product, dict):
        err("缺少 product 对象")
        product = {}
    for field in ("name", "form", "version", "tagline", "updated"):
        if not product.get(field):
            err(f"product.{field} 缺失")
    if product.get("form") and product["form"] not in FORMS:
        err(f"product.form 非法：{product['form']}（允许：{sorted(FORMS)}）")
    ends = product.get("ends")
    if ends is not None:
        if not isinstance(ends, list) or not ends:
            err("product.ends 应为非空数组（多端标识），单端产品请省略")
        else:
            for e in ends:
                if e not in FORMS:
                    err(f"product.ends 含非法形态：{e}")

    # ---- modules 与 pages ----
    modules = manifest.get("modules")
    if not isinstance(modules, list) or not modules:
        err("modules 缺失或为空")
        modules = []

    module_ids = set()
    page_total = 0
    pending_total = 0
    for mi, mod in enumerate(modules):
        mid = mod.get("id", f"<#{mi}>")
        if not ID_RE.match(str(mod.get("id", ""))):
            err(f"模块 id 不合规（需 kebab-case）：{mid}")
        if mod.get("id") in module_ids:
            err(f"模块 id 重复：{mid}")
        module_ids.add(mod.get("id"))

        if mod.get("special") == "pending-report":
            if mi != 0:
                warn("pending-report 模块不在第一位（菜单顺序建议置顶）")
            continue

        pages = mod.get("pages")
        if not isinstance(pages, list) or not pages:
            err(f"模块 {mid} 没有任何页面")
            continue

        page_ids = set()
        for page in pages:
            pid = page.get("id", "?")
            page_total += 1
            if not ID_RE.match(str(page.get("id", ""))):
                err(f"{mid}/{pid}: 页面 id 不合规（需 kebab-case）")
            if page.get("id") in page_ids:
                err(f"{mid}/{pid}: 页面 id 在模块内重复")
            page_ids.add(page.get("id"))

            for field in ("title", "type", "file"):
                if not page.get(field):
                    err(f"{mid}/{pid}: 缺少 {field}")
            if page.get("type") and page["type"] not in PAGE_TYPES:
                err(f"{mid}/{pid}: type 非法：{page['type']}")
            if page.get("source") and page["source"] not in SOURCES:
                err(f"{mid}/{pid}: source 非法：{page['source']}")
            if page.get("status") and page["status"] not in STATUS:
                err(f"{mid}/{pid}: status 非法：{page['status']}")
            if page.get("status") == "pending":
                pending_total += 1

            f = page.get("file")
            if f:
                if str(f).startswith("content/"):
                    warn(f"{mid}/{pid}: file 不应带 content/ 前缀：{f}")
                target = root / "content" / str(f)
                if not target.exists():
                    err(f"{mid}/{pid}: 文件不存在：content/{f}")

    # ---- HTML 零内联 ----
    for html_file in sorted((root / "content").rglob("*.html")):
        text = html_file.read_text(encoding="utf-8", errors="replace")
        rel = html_file.relative_to(root)
        if re.search(r'style="', text):
            err(f"{rel}: 存在内联 style 属性")
        if "<style" in text:
            err(f"{rel}: 存在 <style> 块")
        if "<script" in text:
            err(f"{rel}: 存在 <script>（内容产物不允许脚本）")

    # ---- data.js 新鲜度 ----
    data_js = root / "site" / "js" / "data.js"
    if not data_js.exists():
        warn("site/js/data.js 不存在（首次生成请运行 build.py）")
    else:
        data_mtime = data_js.stat().st_mtime
        # 只有 markdown / mermaid / manifest 参与编译；原型与信息图 HTML 由浏览器直接加载，改动无需重编译
        compiled = [manifest_path]
        for mod in manifest.get("modules", []):
            for page in mod.get("pages", []):
                if page.get("type") in ("markdown", "mermaid") and page.get("file"):
                    f = root / "content" / str(page["file"])
                    if f.exists():
                        compiled.append(f)
        stale = [str(f.relative_to(root)) for f in compiled if f.stat().st_mtime > data_mtime]
        if stale:
            err("data.js 已过期（以下参与编译的文件比它新，请重跑 build.py）：\n      " + "\n      ".join(stale[:10]))

    return report(root, page_total, pending_total)


def report(root, page_total, pending_total):
    print(f"目录：{root}")
    print(f"页面：{page_total} ｜ 待确认：{pending_total}")
    for w in WARNINGS:
        print(f"  ⚠️  {w}")
    if ERRORS:
        for e in ERRORS:
            print(f"  ❌ {e}")
        print(f"结果：未通过（{len(ERRORS)} 个错误，{len(WARNINGS)} 个警告）")
        return 1
    print(f"结果：通过（{len(WARNINGS)} 个警告）✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
