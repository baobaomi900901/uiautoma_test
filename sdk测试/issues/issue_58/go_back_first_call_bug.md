## 复现信息

- API：`uiautoma.web.WebBrowser.go_back()`
- 浏览器模式：Chrome（`--mode chrome`）
- 靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`（A）→ `#/element-html-test`（B）→ `#/cookie-test`（C）；另以 `https://example.com/`、`https://www.iana.org/help/example-domains` 作跨文档对照
- 测试脚本：`web/test_web_browser_go_back.py`（外部 `sdk测试` 工作区，未纳入仓库）
- 实测源码：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`
- Runtime：`python -m runtime.bootstrap --entry automation-service`（由 `build-test.py` 启动），扩展已重新加载

## 复现步骤

1. 启动 `dev`，确认 Automation Pipe 可用。
2. `cd D:\code\元素库\sdk测试` 后执行 `uv run .\web\test_web_browser_go_back.py`。
3. 脚本经 `navigate()` 建立 A→B→C 三页历史后，首次调用 `page.go_back(load_timeout=20)`。

## 实际结果

5/6 通过，`scenario` 一项失败：

```text
ActionError: 浏览器操作失败，请重试
trace=web_browser_command_failed
```

脚本只打印公开 message 与 trace，未保留底层原因。从 `ActionError.result.raw` 取出的引擎原始响应为：

```json
{"error": 5, "ok": false, "trace_info": "web_browser_command_failed",
 "failure_reason": "Cannot find a next page in history.", "command": "back"}
```

同一时刻页面自身 `history.length` 为 `3`（A、B、C 三条记录都在）。即浏览器执行层认为「无可后退项」，页面侧认为有 3 条，两侧状态不一致。

## 触发条件

导航后直接 `go_back()`，改变前置动作（每次全新开页）：

| 前置动作 | 首次 `go_back()` |
| --- | --- |
| 无（对照） | 失败，约 0.015s（10 次全部失败） |
| 先 `page.activate()` | 失败 |
| 先 `page.get_html()` | 失败 |
| 先 `page.get_title()` / `page.is_load_completed()` | 失败 |
| 先 `time.sleep(0.7)` | 失败 |
| 先 `page.execute_javascript(...)` 一次 | 成功，约 0.12s（5 次全部成功） |

导航形态不是必要条件：hash 同文档导航（1 次或 2 次）与跨文档导航（1 次或 2 次）都同样首次失败。失败后立即重试、以及等待 1.5s 后重试，仍然失败；直到该标签页执行过一次页面级脚本命令后才恢复正常。

## 预期结果

- 既有历史记录存在（`history.length` 已包含前一条）时，`go_back()` 应稳定后退并返回 `None`。
- 确实无法后退时，应返回可行动的明确 trace（例如「无可后退历史」），而不是落到 `web_browser_command_failed` 兜底文案。

## 只读源码线索

- `sdk/src/uiautoma/web/browser.py:163`：`go_back(*, load_timeout: float = 20) -> None` → `_runtime_client().web_back(...)`。
- `sdk/src/uiautoma/_core/client.py:1432`：`web_back` → `web.browser.back`。
- `runtime/services/action_service.py:2870`：`web_browser_back` → `_run_web_browser_command(command="back")`（定义在 5408）。
- `chrome/engine/plugin_packages/browser_command_package.js:1663-1671`：`back` 分支先 `chrome.tabs.goBack(tab.id)`（1667），`waitForTabReady` 在其之后（1669）。
- `chrome/engine/plugin_packages/browser_command_package.js:1843-1845`：catch-all 将该异常映射为 `web_browser_command_failed`。
- `chrome/engine/shared/web_user_messages.js:47`：该 trace 的公开文案为「浏览器操作失败，请重试」。

本次未修改产品源码；以上为只读定位，Chromium 侧 `CanGoBack()` 为 false 的确切原因尚未确认。

## 建议回归验收

- 新建页面 → 导航一次 → 直接 `go_back()`（不预先执行任何页面脚本）应成功。
- hash 同文档导航与跨文档导航两种形态都要覆盖。
- 连续两次 `go_back()`，以及 `go_back()` → `go_forward()` 往返应表现一致。
- 无历史可后退时返回明确 trace，公开文案不应是通用兜底。
- 与 `reload()`、`stop_load()` 合并回归，确认同一分支的其它命令不受同类前置状态影响。
