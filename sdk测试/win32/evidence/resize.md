# `uiautoma.win32.Win32Window.resize()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.resize"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  initial_rect: "PASS"
  default_size: "PASS"
  width_only: "PASS"
  height_only: "PASS"
  full_size: "PASS"
  invalid_sizes: "PASS"
  cleanup: "PASS"
  passed: 8
  total: 8
  elapsed_ms: 4116.7
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.resize 的 SDK→Runtime→Win32 窗口缩放路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.resize"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["resize", "get_rect", "set_rect"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["resize", "get_rect", "_set_window_pos"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.get_rect", "WindowService.set_rect"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols: ["NamedPipeServer._handle_window_get_rect", "NamedPipeServer._handle_window_set_rect"]
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "resize(self, *, width: int = 1, height: int = 1) -> None"
    public_parameters:
      - name: "width"
        type: "int"
        kind: "keyword-only"
        default: 1
        rule: "> 0"
      - name: "height"
        type: "int"
        kind: "keyword-only"
        default: 1
        rule: "> 0"
    preserves_top_left: true
    requires_native_window: true
    invalid_size_error: "InvalidParamsError"
    return_annotation: "None"
persistent_script:
  path: "win32/test_win32_resize.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "e7c7d594882bbb8991e3292ce6b5914bd285b259ad24ba3d5fa83c6bf899fcd3"
  command: 'uv run .\win32\test_win32_resize.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  initial_rect: [2052, 243, 900, 680]
  target_minimum_outer_size: [900, 680]
  explicit_test_size: [1000, 800]
  observation_delay_seconds: 1.0
  size_observation: "Win32 GetWindowRect"
  native_fallback_used: false
observations:
  api_contract:
    status: "PASS"
    detail: "width、height 均为默认 1 的仅限关键字整数参数，返回 None"
    elapsed_ms: 0.0
  initial_rect:
    status: "PASS"
    value: [2052, 243, 900, 680]
    elapsed_ms: 4.9
  default_size:
    status: "PASS"
    call: "resize()"
    effective_size: [900, 680]
    top_left_preserved: true
    returned_none: true
    returned_to_initial_size: true
    elapsed_ms: 1002.1
  width_only:
    status: "PASS"
    call: "resize(width=1000)"
    effective_size: [1000, 680]
    top_left_preserved: true
    returned_none: true
    returned_to_initial_size: true
    elapsed_ms: 1032.7
  height_only:
    status: "PASS"
    call: "resize(height=800)"
    effective_size: [900, 800]
    top_left_preserved: true
    returned_none: true
    returned_to_initial_size: true
    elapsed_ms: 1036.0
  full_size:
    status: "PASS"
    call: "resize(width=1000, height=800)"
    effective_size: [1000, 800]
    top_left_preserved: true
    returned_none: true
    returned_to_initial_size: true
    elapsed_ms: 1035.2
  invalid_sizes:
    status: "PASS"
    calls:
      - "resize(width=0, height=800)"
      - "resize(width=-1, height=800)"
      - "resize(width=1000, height=0)"
      - "resize(width=1000, height=-1)"
    expected_error: "InvalidParamsError"
    elapsed_ms: 2.0
cleanup:
  status: "PASS"
  elapsed_ms: 2.7
  target_initial_rect_restored: true
  target_initial_state_restored: true
  original_foreground_restored: true
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_resize.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_resize.py
```

脚本动态记录 Win32 靶场的初始矩形。每个合法用例调用 `resize()` 后，通过 Windows
`GetWindowRect` 独立校验尺寸与左上角位置，停留 `1` 秒供人工观察，再恢复初始尺寸。
最终清理兜底恢复靶场初始矩形、显示状态和运行脚本前的前台窗口。

## API 参数

```python
resize(*, width: int = 1, height: int = 1) -> None
```

- `width` 和 `height` 都是仅限关键字参数，默认值均为 `1`。
- 两个参数都必须大于 `0`，否则抛出 `InvalidParamsError`。
- 尺寸表示窗口外框的目标宽度和高度。
- 调用保持窗口外框左上角位置不变。
- 成功返回 `None`。
- Windows 和目标应用可以把请求尺寸限制到窗口允许的最小值。本轮靶场通过
  `WM_GETMINMAXINFO` 将最小外框限制为 `900 × 680`，因此默认 `1 × 1` 实际生效为
  `900 × 680`。
- Runtime 不支持或不可用时，高层实现回退到本地 Win32 `resize()`。

## 最小实现链

```text
Win32Window.resize(width=..., height=...)
  -> runtime_window.resize(NativeWindow, width, height)
  -> runtime_window.get_rect(...)
  -> Automation Pipe window.get_rect
  -> runtime_window.set_rect(current_x, current_y, width, height)
  -> Automation Pipe window.set_rect
  -> NamedPipeServer._handle_window_set_rect(...)
  -> WindowService.set_rect(...)
  -> Win32 SetWindowPos(SWP_NOZORDER | SWP_NOACTIVATE)
  -> None
```

源码还包含 Runtime 不可用时通过 `native_window.get_rect()` 和本地 `SetWindowPos()`
缩放的回退路径。本轮 Runtime 正常，未触发该路径。

## 覆盖矩阵

| 场景 | 调用 | 实际尺寸 | 额外断言 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.resize)` | — | 参数仅限关键字、默认 1，返回 `None` | `PASS` |
| 靶场初始矩形 | `GetWindowRect` | `900 × 680` | 动态记录位置和尺寸 | `PASS` |
| 全部默认参数 | `resize()` | `900 × 680` | 应用最小尺寸生效，左上角不变，停留后恢复 | `PASS` |
| 仅指定宽度 | `resize(width=1000)` | `1000 × 680` | 高度使用默认值并受最小值限制 | `PASS` |
| 仅指定高度 | `resize(height=800)` | `900 × 800` | 宽度使用默认值并受最小值限制 | `PASS` |
| 完整尺寸 | `resize(width=1000, height=800)` | `1000 × 800` | 左上角不变，停留后恢复 | `PASS` |
| 非法尺寸 | 宽高分别传入 `0`、`-1` | — | 均抛出 `InvalidParamsError` | `PASS` |
| 尺寸与焦点恢复 | 最终兜底恢复 | 初始矩形 | 显示状态及原前台窗口恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_resize.py`
- 测试窗口：`Win32 靶场 - UIA`
- 初始矩形：`(2052, 243, 900, 680)`
- 四种合法调用：默认、仅宽度、仅高度和完整尺寸均通过
- 非法尺寸：宽高的零值和负值均正确抛出 `InvalidParamsError`
- 观察延迟：每次目标缩放后 `1s`
- 用例级恢复：每次停留后均恢复动态记录的初始尺寸
- 总状态：`PASS`
- 通过数：`8/8`
- 总耗时：`4116.7ms`
- 靶场初始矩形及状态：已恢复
- 原前台窗口：已恢复
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- Runtime 不可用时的本地 `native_window.resize()` 回退路径。
- 没有真实句柄的伪 `Win32Window` 异常路径。
- 最大化、最小化或隐藏状态下直接缩放的行为。
- 非整数但可被 `int()` 转换的输入；公开合同只承诺整数。
