# `uiautoma.web.WebElement.drag_to()` 验证证据

```yaml
api: "uiautoma.web.WebElement.drag_to"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_delay_after_ok: "PASS"
  chrome_drag_delta_ok: "FAIL"
  chrome_drag_log_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  note: "同步 drag 事件仅产生 phase=start，位移仍为 0"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.drag_to 的最小 SDK→web.action.drag→Page Engine dragElement 路径"
source_review:
  status: "reviewed_with_known_defect"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.drag_to", "WebElement.drag"]
      fingerprint: "4b6e99fdafe1c3a18c71761df0b6fe4cc3356f4b"
    - path: "chrome/engine/engine_packages/page_engine_runtime.js"
      symbols: ["dragElement", "webDomCommand"]
      fingerprint: "6e14f6d659abf956ae0f29d4a68d60e0fa2adeac"
      note: "同步 mousedown/mousemove/mouseup；靶场 React 后挂 window 监听"
  verified_contract:
    signature: "drag_to(*, simulative=True, behavior='smooth', top=0, left=0, delay_after=1, anchor=None, move_speed='middle') -> None"
    parameter_order:
      - "self"
      - "simulative"
      - "behavior"
      - "top"
      - "left"
      - "delay_after"
      - "anchor"
      - "move_speed"
    defaults:
      simulative: true
      behavior: "smooth"
      top: 0
      left: 0
      delay_after: 1
      anchor: null
      move_speed: "middle"
    return_annotation: "None"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_drag_to.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "154c1def59ac10aba7ef8dc30f3d714985ff0106"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "a77c5aaeeee8781799d06fb12237ec84ca2755e7"
  drag_element_name: "拖拽元素"
  copy_log_element_name: "获取拖拽日志"
  expected_left: 100
  expected_top: 50
source_commit_at_doc_time: "dbd5e189d80f90f8f86b4989e7ba9a4c74eac97a"
known_issue: "https://github.com/uiautoma/desktop/issues/26"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_drag_to.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_drag_to.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_drag_to.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：对 `拖拽元素` 直接调用 `drag_to(left=100, top=50, delay_after=1)`。
- 副作用验收：点击 `获取拖拽日志`，读取剪贴板 JSON；并读取
  `data-delta-left` / `data-delta-top`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.drag_to
  -> ensure_supported(simulative/behavior/move_speed)
  -> RawWebElement.drag(left, top)
  -> web.action.drag
  -> page_engine dragElement
       mousedown(start) → mousemove(end) → mouseup(end)  # 同步
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | keyword-only、默认值、`None` |
| 预检 / 页面 / 库 | `PASS` | drag-to-test 与两库项 |
| `delay_after=1` | `PASS` | ~1068ms |
| 位移 ≈ 100/50 | `FAIL` | attr 仍为 0/0 |
| 拖拽日志 | `FAIL` | `phase=start`，Δ=0 |
| 精确清理 | `PASS` | `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`
- 产品源码修改：无

## 明确排除

- Edge、CEF、Auto
- `simulative=False` / `behavior=instant` 完整矩阵
- `anchor` / `move_speed` 轨迹差异
- `drag_to_by_cdp`

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/26
