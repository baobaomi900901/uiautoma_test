# `uiautoma.win32.Win32Window.move()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.move"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  initial_rect: "PASS"
  default_position: "PASS"
  x_only: "PASS"
  y_only: "PASS"
  xy_position: "PASS"
  cleanup: "PASS"
  passed: 7
  total: 7
  elapsed_ms: 4021.5
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.move 的 SDK→Runtime→Win32 窗口移动路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.move"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["move", "get_rect", "set_rect"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["move", "get_rect", "_set_window_pos"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.get_rect", "WindowService.set_rect"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols: ["NamedPipeServer._handle_window_get_rect", "NamedPipeServer._handle_window_set_rect"]
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "move(self, *, x: int = 0, y: int = 0) -> None"
    public_parameters:
      - name: "x"
        type: "int"
        kind: "keyword-only"
        default: 0
      - name: "y"
        type: "int"
        kind: "keyword-only"
        default: 0
    preserves_window_size: true
    requires_native_window: true
    return_annotation: "None"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_move.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "8899a48817ba3a277bb75d29aa60ac75a2774a6ed0435dc3cdb43a847fe4f1d3"
  command: 'uv run .\win32\test_win32_move.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  initial_rect: [2052, 243, 1024, 720]
  target_coordinates:
    default: [0, 0]
    x_only: [160, 0]
    y_only: [0, 120]
    xy: [160, 120]
  observation_delay_seconds: 1.0
  position_observation: "Win32 GetWindowRect"
  move_path: "Runtime window.get_rect + window.set_rect"
  native_fallback_used: false
observations:
  api_contract:
    status: "PASS"
    detail: "x、y 均为默认 0 的仅限关键字整数参数，返回 None"
    elapsed_ms: 0.1
  initial_rect:
    status: "PASS"
    value: [2052, 243, 1024, 720]
    elapsed_ms: 5.2
  default_position:
    status: "PASS"
    call: "move()"
    expected_position: [0, 0]
    returned_none: true
    size_preserved: true
    returned_to_initial_position: true
    elapsed_ms: 1003.5
  x_only:
    status: "PASS"
    call: "move(x=160)"
    expected_position: [160, 0]
    returned_none: true
    size_preserved: true
    returned_to_initial_position: true
    elapsed_ms: 1003.3
  y_only:
    status: "PASS"
    call: "move(y=120)"
    expected_position: [0, 120]
    returned_none: true
    size_preserved: true
    returned_to_initial_position: true
    elapsed_ms: 1003.5
  xy_position:
    status: "PASS"
    call: "move(x=160, y=120)"
    expected_position: [160, 120]
    returned_none: true
    size_preserved: true
    returned_to_initial_position: true
    elapsed_ms: 1003.3
cleanup:
  status: "PASS"
  elapsed_ms: 1.9
  target_initial_position_restored: true
  target_initial_state_restored: true
  original_foreground_restored: true
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_move.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_move.py
```

脚本动态记录 Win32 靶场的初始位置和尺寸。每个用例先调用 `move()` 到目标位置，通过
Windows `GetWindowRect` 独立校验坐标和尺寸，停留 `1` 秒供人工观察，再移回初始位置
并再次校验。最终清理继续兜底恢复初始位置、显示状态和原前台窗口。

## API 参数

```python
move(*, x: int = 0, y: int = 0) -> None
```

- `x` 和 `y` 都是仅限关键字参数，默认值均为 `0`。
- 坐标表示窗口外框左上角的屏幕位置。
- `move()` 等价于移动到 `(0, 0)`。
- 只提供 `x` 时，`y` 使用默认值 `0`；只提供 `y` 时，`x` 使用默认值 `0`。
- 移动时保留当前窗口宽度和高度。
- 成功返回 `None`。
- 调用对象必须绑定真实顶层窗口句柄。
- Runtime 不支持或不可用时，高层实现回退到本地 Win32 `move()`。

## 最小实现链

```text
Win32Window.move(x=..., y=...)
  -> runtime_window.move(NativeWindow, x, y)
  -> runtime_window.get_rect(...)
  -> Automation Pipe window.get_rect
  -> runtime_window.set_rect(x, y, current_width, current_height)
  -> Automation Pipe window.set_rect
  -> NamedPipeServer._handle_window_set_rect(...)
  -> WindowService.set_rect(...)
  -> Win32 SetWindowPos(SWP_NOZORDER | SWP_NOACTIVATE)
  -> None
```

源码还包含 Runtime 不可用时通过 `native_window.get_rect()` 和本地 `SetWindowPos()`
移动的回退路径。本轮 Runtime 正常，未触发该路径。

## 覆盖矩阵

| 场景 | 调用 | 目标位置 | 额外断言 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.move)` | — | `x/y` 仅限关键字、默认 0，返回 `None` | `PASS` |
| 靶场初始矩形 | `GetWindowRect` | 动态记录 | 记录位置和尺寸 | `PASS` |
| 全部默认参数 | `move()` | `(0, 0)` | 尺寸不变，停留 1 秒后移回 | `PASS` |
| 仅指定 X | `move(x=160)` | `(160, 0)` | `y` 默认 0，尺寸不变，停留后移回 | `PASS` |
| 仅指定 Y | `move(y=120)` | `(0, 120)` | `x` 默认 0，尺寸不变，停留后移回 | `PASS` |
| 完整坐标 | `move(x=160, y=120)` | `(160, 120)` | 尺寸不变，停留 1 秒后移回 | `PASS` |
| 位置与焦点恢复 | 最终兜底恢复 | 初始位置 | 显示状态及原前台窗口恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_move.py`
- 测试窗口：`Win32 靶场 - UIA`
- 初始矩形：`(2052, 243, 1024, 720)`
- 四种调用：默认、仅 X、仅 Y、完整坐标均通过
- 观察延迟：每次目标移动后 `1s`
- 用例级恢复：每次停留后均移回动态记录的初始位置
- 尺寸：每次移动及返回后均保持不变
- 总状态：`PASS`
- 通过数：`7/7`
- 总耗时：`4021.5ms`
- 靶场初始位置及状态：已恢复
- 原前台窗口：已恢复
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及人工确认
- 产品源码修改：无

## 明确排除

- 负坐标和跨显示器坐标。
- 非整数或可被 `int()` 转换的坐标输入；公开合同只承诺整数。
- Runtime 不可用时的本地 `native_window.move()` 回退路径。
- 没有真实句柄的伪 `Win32Window` 异常路径。
- 改变窗口尺寸、最大化或最小化状态的行为。
