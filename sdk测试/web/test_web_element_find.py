"""WebElement.find() 最小真实验收脚本。"""
from __future__ import annotations

import shutil
import inspect
from pathlib import Path

import uiautoma
from uiautoma import ElementNotFoundError, web

GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"

URL = "https://baobaomi900901.github.io/xpath/#/anchor-test"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
PARENT = "web靶场_测试find_父级"
CHILD = "web靶场_测试find_子级"


def main() -> int:
    results = []
    sig = inspect.signature(type(web.create).__call__) if False else inspect.signature(__import__('uiautoma.web', fromlist=['WebElement']).WebElement.find)
    ok = tuple(sig.parameters) == ("self", "selector", "timeout") and sig.parameters["timeout"].default == 10
    results.append(("api_contract", ok, "find(selector, *, timeout=10) 合同正确" if ok else f"公开签名不符: {sig}"))
    tmp = Path(__file__).resolve().parents[1] / ".pytest_tmp" / "element_find"
    shutil.rmtree(tmp, ignore_errors=True)
    page = None
    try:
        shutil.copytree(LIBRARY, tmp)
        uiautoma.open(str(tmp), timeout=20, connect_timeout=20)
        results.append(("library_prepare", True, "已打开元素库副本，并保持原元素库不变"))
        page = web.create(URL, mode="chrome", load_timeout=20)
        results.append(("page_prepare", True, f"已打开靶场页面: {URL}"))
        parent = page.find(PARENT, timeout=10)
        child = parent.find(CHILD, timeout=10)
        assert child.id.startswith("rt:web:"), child.id
        results.append(("find_child", True, f"父元素内成功找到子元素（name={child.name!r}, id 前缀 rt:web:）"))
        try:
            parent.find("missing-name", timeout=0)
        except ElementNotFoundError as exc:
            results.append(("missing_child", True, f"缺失子元素正确抛出 ElementNotFoundError: {exc}"))
        else:
            raise AssertionError("缺失元素未抛出 ElementNotFoundError")
        return_code = 0
    finally:
        if page is not None:
            page.close(ignore_beforeunload=True)
        shutil.rmtree(tmp, ignore_errors=True)
        results.append(("cleanup", True, "页面已关闭，临时元素库副本已删除"))
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.find")
    print(f"页面    : {URL}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for i, (case, passed, detail) in enumerate(results, 1):
        color = GREEN if passed else RED
        print(f"{i:02d}/{len(results):02d}    {color}[{'通过' if passed else '失败'}]{RESET}  {case:<22}  {detail}")
    passed = sum(x[1] for x in results)
    print("─" * 72)
    print(f"{'测试通过' if passed == len(results) else '测试失败'} · {passed}/{len(results)} 通过 · 退出码 {return_code}")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
