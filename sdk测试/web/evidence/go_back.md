# `WebBrowser.go_back()` 初次测试

## 用途

浏览器后退。`load_timeout` 仅限关键字传入，默认 20 秒；`0` 表示不等待加载完成，
`-1` 表示一直等待；调用成功返回 `None`。

`go_back()` **不更新** `WebBrowser.url` / `WebBrowser.title` 属性（`navigate()` 才会更新），
调用后必须用 `get_url()` 重新读取当前地址。

## 真实验收结果

**READY_FOR_LIVE：5/6 通过，退出码 1。首次调用稳定失败，缺陷未修复。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`（A）→
`#/element-html-test`（B）→ `#/cookie-test`（C）
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无公开位置参数，`load_timeout` 仅限关键字且默认 20，返回 `None` |
| 页面准备 | 通过，成功创建测试页面 |
| 初始状态 | 通过，初始 URL 可读且页面 id 非空 |
| 历史准备 | 通过，导航建立 A→B→C 三页历史 |
| 默认后退 | **失败**，`ActionError: 浏览器操作失败，请重试` |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

脚本只打印公开 message 与 `trace`，底层原因需从 `ActionError.result.raw` 取出：

```json
{"error": 5, "ok": false, "trace_info": "web_browser_command_failed",
 "failure_reason": "Cannot find a next page in history.", "command": "back"}
```

同一时刻页面侧 `history.length` 为 `3`（A、B、C 三条记录都在）。即浏览器执行层认为
「无可后退项」，页面侧认为有 3 条，两侧状态不一致。

首个目标调用抛出异常后，脚本直接终止场景，因此
`go_back_keyword`、`zero_timeout`、`invalid_timeout`、`invalid_timeout_type`、
`extra_positional`、`unknown_keyword` 六项**本次未执行到**。

## 缺陷触发条件（隔离矩阵）

每次全新开页，导航后直接 `go_back()`：

| 前置动作 | 首次 `go_back()` |
|---|---|
| 无（对照） | 失败，约 0.015s（10 次全部失败） |
| 先 `page.activate()` | 失败 |
| 先 `page.get_html()` | 失败 |
| 先 `page.get_title()` / `page.is_load_completed()` | 失败 |
| 先 `time.sleep(0.7)` | 失败 |
| 先 `page.execute_javascript(...)` 一次 | 成功，约 0.12s（5 次全部成功） |

导航形态不是必要条件：hash 同文档导航（1、2 次）与跨文档导航（`https://example.com/`、
`https://www.iana.org/help/example-domains`，1、2 次）均同样首次失败。失败后立即重试、
以及等待 1.5s 后重试仍然失败，直到该标签页执行过一次页面级脚本命令。

## 只读源码线索

- `sdk/src/uiautoma/web/browser.py:163`：`go_back(*, load_timeout: float = 20) -> None`。
- `sdk/src/uiautoma/_core/client.py:1432`：`web_back` → `web.browser.back`。
- `runtime/services/action_service.py:2870`：`web_browser_back` →
  `_run_web_browser_command(command="back")`（定义在 5408）。
- `chrome/engine/plugin_packages/browser_command_package.js:1667`：
  `chrome.tabs.goBack(tab.id)`；`waitForTabReady` 在其后（1669）。
- `chrome/engine/plugin_packages/browser_command_package.js:1843-1845`：catch-all 映射为
  `web_browser_command_failed`。

以上为只读定位，未修改产品源码；Chromium 侧 `CanGoBack()` 为 false 的确切原因尚未确认。

## 复现

脚本：[test_web_browser_go_back.py](../test_web_browser_go_back.py)（复现本次失败）
最小复现：[../../issues/issue_58/test_issue_58_go_back.py](../../issues/issue_58/test_issue_58_go_back.py)
原始产物：[../../issues/issue_58/artifacts/repro_20260915.json](../../issues/issue_58/artifacts/repro_20260915.json)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_go_back.py
uv run .\issues\issue_58\test_issue_58_go_back.py
```

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/58

## 明确排除

- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `load_timeout=-1`（无限等待）路径：因首次调用失败未进入。
- 失败后的关键字/零等待/非法参数用例：本次未执行到。
- 页面关闭后 `go_back()` 的 `stale_page_reference` 行为。
- `go_forward()` 往返一致性。
