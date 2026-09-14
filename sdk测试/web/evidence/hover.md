# `uiautoma.web.WebElement.hover()` 验证证据

```yaml
api: "uiautoma.web.WebElement.hover"
lifecycle: "VERIFIED"
verification_summary:
  chrome_background_ok: "PASS"
  chrome_delay_after_ok: "PASS"
  chrome_simulative_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.hover 的最小 SDK、Runtime 与鼠标悬停实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.hover", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["anchor_to_pt", "_anchor_parts"]
      fingerprint: "09ff7f1d81bf850bfc94ae8cbd2c122b3d6f7041"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.hover", "LibrarySession._run_web_action", "LibrarySession._web_target_params"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_hover"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_hover_element", "ActionService._run_web_dom_action"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
    - path: "runtime/desktop/mouse_actions.py"
      symbols: ["point_in_rect_xywh", "_point_code_and_offset"]
      fingerprint: "d5804f849b14016faf47f77acb09491ccdb38adc"
  verified_contract:
    signature: "hover(simulative=True, delay_after=1, anchor=None) -> None"
    parameter_order: ["self", "simulative", "delay_after", "anchor"]
    defaults:
      simulative: true
      delay_after: 1
      anchor: null
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_hover.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "dbe888324971470ff68408add1dee18791a10c56"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "a05c4292bfb6a8f1511a191ab8cee2a211a986b4"
  hover_element_name: "hover"
  copy_element_name: "复制最近的一条记录"
source_commit_at_doc_time: "1aab89445837fb9fd17530a5615597dd337dd4f6"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_hover.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_hover.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_hover.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活与 Chrome
  窗口焦点准备。
- 辅助验收 API：对“复制最近的一条记录”调用 `click()`，以及 `win32.clipboard.get_text()`
  读取剪贴板 JSON。这些调用不代替目标 `hover()` 的正确性证明。
- 目标 API：各用例只直接调用被测元素上的 `WebElement.hover(...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、恢复 Chrome 窗口状态、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.hover
  -> anchor_to_pt
  -> RawWebElement.hover
  -> LibrarySession._run_web_action("web.action.hover")
  -> AutomationDispatcher._handle_web_action_hover
  -> ActionService.web_hover_element
  -> ActionService._run_web_dom_action(action="hover")
  -> runtime.desktop.mouse_actions.point_in_rect_xywh  # 真实鼠标路径
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、参数种类、`None` 返回注解 |
| 靶场预检 | `PASS` | `/keys-click-test` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | hover/复制元素各唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | Web 元素 `9`，两个目标名称绑定正确 |
| 后台悬停 | `PASS` | `eventType=hover`；`detectedKeys=-`；`JS/插件模拟`；`isTrusted=false` |
| 后台 `delay_after=1` | `PASS` | 调用耗时约 `1040ms`（`>=900ms`） |
| 窗口与焦点准备 | `PASS` | Chrome 窗口为 normal 并取得焦点 |
| 模拟人工悬停 | `PASS` | `eventType=hover`；`真实鼠标`；`isTrusted=true` |
| 精确清理 | `PASS` | 本次资源 `4/4` |

## 最近一次真实验证

- 日期：2026-08-07
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场预检：约 `41.8ms`，HTTP 200
- Runtime 预检：约 `2.8ms`
- 元素库预检：约 `0.4ms`
- 临时库准备：约 `15.8ms`，清理字段 `36`
- 页面准备：约 `484.2ms`，复用已有 Chrome 会话
- 元素库连接：约 `23.7ms`，Web 元素 `9`
- 后台悬停：调用约 `239.6ms`；剪贴板 `hover` / `isTrusted=false`
- 后台 `delay_after=1`：调用约 `1040.5ms`
- 窗口与焦点准备：约 `2050.8ms`，`unique_visible_chrome_window`
- 模拟人工悬停：调用约 `1062.6ms`；剪贴板 `hover` / `真实鼠标` / `isTrusted=true`
- 清理结果：`PASS`，本次资源 `4/4`
- 产品源码修改：无（测试侧使用临时库副本规避陈旧 `WebSessionId`）

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `anchor` 九宫格与偏移、`anchor='random'`。
- 模拟人工路径下的 `delay_after=1` 默认耗时。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
