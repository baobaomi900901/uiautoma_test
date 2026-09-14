# `uiautoma.web.WebElement.click()` 验证证据

```yaml
api: "uiautoma.web.WebElement.click"
lifecycle: "VERIFIED"
verification_summary:
  chrome_background_keys_ok: "PASS"
  chrome_simulative_keys_ok: "PASS"
  chrome_simulative_right_ok: "PASS"
  chrome_grid_nine_anchors_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.click 的最小 SDK、Runtime 与鼠标点击实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.click", "_normalize_web_button", "_normalize_keys", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["anchor_to_pt", "_anchor_parts"]
      fingerprint: "09ff7f1d81bf850bfc94ae8cbd2c122b3d6f7041"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.click", "LibrarySession._run_web_action", "LibrarySession._web_target_params"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_click"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_click_element", "ActionService._run_web_dom_action", "ActionService._run_web_click_with_mouse_if_needed"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
    - path: "runtime/desktop/mouse_actions.py"
      symbols: ["point_in_rect_xywh", "_point_code_and_offset"]
      fingerprint: "d5804f849b14016faf47f77acb09491ccdb38adc"
  verified_contract:
    signature: "click(*, button='left', simulative=True, keys='none', delay_after=1, move_mouse=None, anchor=None, allow_coord_fallback=False) -> None"
    parameter_order: ["self", "button", "simulative", "keys", "delay_after", "move_mouse", "anchor", "allow_coord_fallback"]
    defaults:
      button: "left"
      simulative: true
      keys: "none"
      delay_after: 1
      move_mouse: null
      anchor: null
      allow_coord_fallback: false
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_click.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "b93ca90ae1c6f8ec26f29c760e0364a2938ba8cb"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "a05c4292bfb6a8f1511a191ab8cee2a211a986b4"
  click_element_name: "单击触发"
  right_element_name: "右键触发"
  grid_element_name: "按钮_九宫格"
  copy_element_name: "复制最近的一条记录"
source_commit_at_doc_time: "cc72002ce10f5732a6fd78995e4e3d6e8eebc235"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_click.py`

```powershell
uv run python tests\SDK\web\test_web_element_click.py --mode chrome
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活与 Chrome
  窗口焦点准备。
- 辅助验收 API：对“复制最近的一条记录”调用 `click()`，以及 `win32.clipboard.get_text()`
  读取剪贴板 JSON。这些调用不代替目标 `click()` 的正确性证明。
- 目标 API：各用例只直接调用被测元素上的 `WebElement.click(...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、恢复 Chrome 窗口状态、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.click
  -> anchor_to_pt / _normalize_web_button / _normalize_keys
  -> RawWebElement.click
  -> LibrarySession._run_web_action("web.action.click")
  -> AutomationDispatcher._handle_web_action_click
  -> ActionService.web_click_element
  -> ActionService._run_web_dom_action
       -> _run_web_click_with_mouse_if_needed   # simulative=True
       -> web_bridge.action("click", ...)       # simulative=False
  -> runtime.desktop.mouse_actions.point_in_rect_xywh  # 真实鼠标点位与偏移
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、关键字参数种类、`None` 返回注解 |
| 靶场预检 | `PASS` | `/keys-click-test` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | 单击/右键/九宫格/复制元素各唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | Web 元素 `9`，四个目标名称绑定正确 |
| 后台左键辅助键 | `PASS` | `none/ctrl/alt/shift/win`；`JS/插件模拟`，`isTrusted=false` |
| 后台 `delay_after=1` | `PASS` | 调用耗时约 `1044ms`（`>=900ms`） |
| 窗口与焦点准备 | `PASS` | 标题匹配 Chrome 窗口为 normal 并取得焦点 |
| 模拟人工左键辅助键 | `PASS` | 同上辅助键；`真实鼠标`，`isTrusted=true` |
| 模拟人工右键 | `PASS` | `contextmenu`，`btn-rightclick-target` |
| 九宫格九方位 | `PASS` | 向中心偏移 `20`；页面方位文案与非空 offset |
| 精确清理 | `PASS` | 本次资源 `4/4` |

## 最近一次真实验证

- 日期：2026-08-07
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场预检：约 `32.0ms`，HTTP 200
- Runtime 预检：约 `2.3ms`
- 元素库预检：约 `0.2ms`
- 临时库准备：约 `15.1ms`，清理字段 `36`
- 页面准备：约 `573.6ms`，复用已有 Chrome 会话
- 元素库连接：约 `13.0ms`，Web 元素 `9`
- 窗口与焦点准备：约 `2047.4ms`，`title_matched_chrome_window`
- 九宫格样例：`topLeft` → `topLeft-(左上)`，`offsetX/Y=17/17`；
  `topCenter` → `top-(上)`；`middleCenter` → `center-(中)`
- 清理结果：`PASS`，本次资源 `4/4`
- 产品源码修改：无（测试侧使用临时库副本规避陈旧 `WebSessionId`）

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `button=right` 且 `simulative=False`。
- 右键辅助键矩阵。
- `move_mouse` 鼠标轨迹可见性。
- `anchor=None` 默认中心点的独立用例（中心点已由九宫格 `middleCenter` 覆盖方位，
  但未单独断言“省略 anchor”语义）。
- `anchor='random'`。
- 页面 `offsetX/offsetY` 与传入 offset 像素值一一对应。
- `allow_coord_fallback=True`。
- 组合辅助键。
- 模拟人工路径下的 `delay_after=1` 默认耗时。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
