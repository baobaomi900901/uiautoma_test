# `uiautoma.web.WebElement.focus()` 验证证据

```yaml
api: "uiautoma.web.WebElement.focus"
lifecycle: "VERIFIED"
verification_summary:
  chrome_focus_default_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.focus 的最小 SDK、Runtime 与 DOM 聚焦实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.focus", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.focus", "LibrarySession._run_web_action", "LibrarySession._web_target_params"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_focus"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_focus_element", "ActionService._run_web_dom_action"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "focus(*, timeout=5.0) -> None"
    parameter_order: ["self", "timeout"]
    defaults:
      timeout: 5.0
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_focus.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "d2704763f6fa28b8ac9eb0a1f192d60f02a467bc"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "a05c4292bfb6a8f1511a191ab8cee2a211a986b4"
  focus_element_name: "focus"
  copy_element_name: "复制最近的一条记录"
source_commit_at_doc_time: "1aab89445837fb9fd17530a5615597dd337dd4f6"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_focus.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_focus.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_focus.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 辅助验收 API：对“复制最近的一条记录”调用 `click()`，以及 `win32.clipboard.get_text()`
  读取剪贴板 JSON。这些调用不代替目标 `focus()` 的正确性证明。
- 目标 API：各用例只直接调用无参 `WebElement.focus()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.focus
  -> RawWebElement.focus
  -> LibrarySession._run_web_action("web.action.focus")
  -> AutomationDispatcher._handle_web_action_focus
  -> ActionService.web_focus_element
  -> ActionService._run_web_dom_action(action="focus")
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、关键字参数种类、`None` 返回注解 |
| 靶场预检 | `PASS` | `/keys-click-test` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | focus/复制元素各唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | Web 元素 `9`，两个目标名称绑定正确 |
| 无参 `focus()` | `PASS` | `eventType=focus`；`detectedKeys=-`；`JS/插件模拟`；`isTrusted=false` |
| 精确清理 | `PASS` | 本次资源 `4/4` |

## 最近一次真实验证

- 日期：2026-08-07
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场预检：约 `34.8ms`，HTTP 200
- Runtime 预检：约 `2.6ms`
- 元素库预检：约 `0.2ms`
- 临时库准备：约 `15.3ms`，清理字段 `36`
- 页面准备：约 `454.5ms`，复用已有 Chrome 会话
- 元素库连接：约 `13.0ms`，Web 元素 `9`
- 无参 `focus()`：调用约 `48.5ms`；剪贴板 `focus` / `isTrusted=false`
- 清理结果：`PASS`，本次资源 `4/4`
- 产品源码修改：无（测试侧使用临时库副本规避陈旧 `WebSessionId`）

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- 显式传入非默认 `timeout`。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
