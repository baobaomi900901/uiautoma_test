"""页面标识与「标签是否泄漏」判定（适配 main 移除 `WebBrowser.id` 之后的基线）。

背景：`main` 的 `44c8e91f 🦄 refactor: 收敛 SDK 独有公开接口与内部状态` 移除了
`WebBrowser.id`（以及 `WebElement.element_id`、`WebElement.raw`），验收脚本不能再按 id
判定页面归属。这里改用公开面上仍然存在的 `(url, title)` 组合键，并把「是否泄漏」定义成
**收尾时该键的匹配数是否超过进入时的匹配数**——比按 id 匹配更强：任何新增的同键标签都会被算作泄漏。

用法（在各验收脚本里）：

```python
page_id = page_key(page)                     # 进入时：页面组合键（同时用于报告与临时标题）
baseline_matches = count_key(page_id, args.mode)   # 进入时：该键已存在的标签数
...
leftover = leaked(page_id, baseline_matches, args.mode)   # 收尾：比进入时多出来的标签
cleaned = not leftover and ...
```

组合键里包含 url 与 title，便于在报告里直接读懂；若同一路由被用户同时打开多个标签，
计数法仍然成立（比较的是「多出来的数量」而非存在性）。

## 关于「同一个页面对象」的断言

移除 `id` 后，原先 `page.id == page_id`（断言「导航/刷新后仍是同一个标签页」）没有公开替代物：
公开面上不存在任何标签身份访问器。替换策略分两种，均如实记录在脚本与证据里：

- **键不变型**（刷新、原地重载）：url 与 title 都不变，`page_key(page) == page_id` 是等价断言。
- **键变化型**（导航、前进/后退）：url 必然变化，改用 `page_alive()`（对象仍可驱动该标签：
  url/title 可读、`execute_javascript` 可往返）**加上** `tab_count()` 前后一致（没有新开标签）。
  这不能证明「同一个标签」，只能证明「对象仍可用且未泄漏标签」——证据文档必须写明这一点。
"""
from __future__ import annotations

from uiautoma import web

__all__ = ["page_key", "count_key", "leaked", "tab_keys", "tab_count", "page_alive"]


def page_key(page) -> str:
    """页面的组合标识：`url|title`（两者都是公开面 API）。"""
    return f"{page.get_url()}|{page.get_title()}"


def count_key(key: str, mode: str = "chrome") -> int:
    """当前浏览器中组合键等于 `key` 的标签数。"""
    return sum(1 for item in web.get_all(mode=mode) if page_key(item) == key)


def leaked(key: str, baseline_matches: int, mode: str = "chrome") -> list:
    """收尾时返回比进入时多出来的同键标签（长度即本次泄漏数）。"""
    matches = [item for item in web.get_all(mode=mode) if page_key(item) == key]
    return matches[max(0, len(matches) - baseline_matches):]


def tab_keys(mode: str = "chrome") -> list[str]:
    """当前所有标签的组合键列表（可排序后比较标签集合是否变化）。"""
    return sorted(page_key(item) for item in web.get_all(mode=mode))


def tab_count(mode: str = "chrome") -> int:
    """当前标签数量。

    「导航没有新开标签」必须用**数量**判断而不能用组合键列表：同标签导航后，该标签自身的
    组合键（url|title）必然改变，键列表恒不相等。数量不变才是可验证的判据。
    """
    return len(web.get_all(mode=mode))


def page_alive(page, probe_js: str = "function () { return 40 + 2; }") -> tuple[bool, str]:
    """`WebBrowser.id` 被移除后的替代断言：该对象是否仍能驱动它的标签。

    通过公开面做三次真实调用（`get_url` / `get_title` / `execute_javascript`），
    任一失败即视为不可用。返回 `(是否可用, 说明)`；说明可直接写进用例 detail。
    """
    try:
        url = page.get_url()
        title = page.get_title()
        value = page.execute_javascript(probe_js)
    except Exception as exc:  # noqa: BLE001 - 任何异常都说明对象不可用
        return False, f"对象不可用: {type(exc).__name__}: {exc}"
    if value != 42:
        return False, f"对象不可用: execute_javascript 返回 {value!r}（期望 42）"
    return True, f"对象仍可用（url={url!r}, title={title!r}, 脚本往返 42）"
