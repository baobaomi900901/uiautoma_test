# `uiautoma.win32.Win32Window.set_state()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.set_state"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  initial_state: "PASS"
  display_states: "PASS"
  maximize_aliases: "PASS"
  minimize_aliases: "PASS"
  hide_state: "PASS"
  invalid_state: "PASS"
  cleanup: "PASS"
  passed: 8
  total: 8
  elapsed_ms: 517.1
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.set_state 的 SDK→Runtime→Win32 窗口状态路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.set_state"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["set_state"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["set_state"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.set_state"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols:
        - "NamedPipeServer._handle_window_minimize"
        - "NamedPipeServer._handle_window_maximize"
        - "NamedPipeServer._handle_window_restore"
        - "NamedPipeServer._handle_window_hide"
        - "NamedPipeServer._handle_window_show"
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "set_state(self, flag: str) -> None"
    public_parameters:
      - name: "flag"
        type: "str"
        required: true
    accepted_values:
      - "normal"
      - "show"
      - "restore"
      - "max"
      - "maximize"
      - "maximized"
      - "min"
      - "minimize"
      - "minimized"
      - "hide"
    flag_normalization: "strip + casefold"
    invalid_flag_exception: "InvalidParamsError"
    requires_native_window: true
    return_annotation: "None"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_set_state.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "7f9ab641fc0b6203b2b1f288d38abaecc1b17aa57494bbfb584549fda91174bd"
  command: 'uv run .\win32\test_win32_set_state.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 1247902
  initial_state: "normal"
  state_observation:
    - "Win32 IsWindowVisible"
    - "Win32 IsIconic"
    - "Win32 IsZoomed"
  state_timeout_seconds: 2.0
  state_path: "Runtime window.show/minimize/maximize/restore/hide"
  native_fallback_used: false
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名包含必填 flag: str，并返回 None"
    elapsed_ms: 0.0
  initial_state:
    status: "PASS"
    handle: 1247902
    state: "normal"
    elapsed_ms: 3.3
  display_states:
    status: "PASS"
    flags: ["normal", "show", "restore"]
    returned_none: true
    observed_visible_and_restored: true
    elapsed_ms: 135.7
  maximize_aliases:
    status: "PASS"
    flags: ["max", "maximize", "maximized"]
    returned_none: true
    observed_zoomed: true
    elapsed_ms: 199.1
  minimize_aliases:
    status: "PASS"
    flags: ["min", "minimize", "minimized"]
    returned_none: true
    observed_iconic: true
    elapsed_ms: 102.8
  hide_state:
    status: "PASS"
    flag: "hide"
    returned_none: true
    observed_visible: false
    elapsed_ms: 20.8
  invalid_state:
    status: "PASS"
    flag: "unsupported-state"
    exception: "InvalidParamsError"
    elapsed_ms: 11.3
cleanup:
  status: "PASS"
  elapsed_ms: 43.5
  target_initial_state_restored: true
  original_foreground_restored: true
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_set_state.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_set_state.py
```

脚本对已运行的 Win32 靶场逐一调用所有公开状态值，并使用 Windows 原生
`IsWindowVisible`、`IsIconic` 和 `IsZoomed` 独立观察状态。每个别名前先把窗口设为
正常显示，避免把上一次调用残留的状态误判为当前别名生效。

## API 参数

```python
set_state(flag: str) -> None
```

- `flag` 是唯一必填参数，类型为字符串。
- 正常显示：`normal`、`show`。
- 恢复：`restore`。
- 最大化：`max`、`maximize`、`maximized`。
- 最小化：`min`、`minimize`、`minimized`。
- 隐藏：`hide`。
- 参数匹配前执行 `strip()` 和 `casefold()`。
- 成功返回 `None`；非法枚举值抛出 `InvalidParamsError`。
- 调用对象必须绑定真实顶层窗口句柄。
- Runtime 不支持或不可用时，高层实现回退到本地 Win32 `set_state()`。

## 最小实现链

```text
Win32Window.set_state(flag)
  -> runtime_window.set_state(NativeWindow, flag)
  -> flag 规范化与状态方法映射
  -> Automation Pipe window.show / minimize / maximize / restore / hide
  -> NamedPipeServer 对应 window handler
  -> WindowService.set_state(...)
  -> Win32 ShowWindow(handle, state_flag)
  -> None
```

别名映射：

```text
normal, show                  -> window.show
restore                       -> window.restore
max, maximize, maximized      -> window.maximize
min, minimize, minimized      -> window.minimize
hide                          -> window.hide
```

## 覆盖矩阵

| 场景 | 调用 | 独立观察 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.set_state)` | 必填 `flag: str`，返回 `None` | `PASS` |
| 初始状态 | 获取靶场窗口 | 句柄 `1247902`，正常显示 | `PASS` |
| 显示与恢复 | `normal`、`show`、`restore` | 可见且非最小化 | `PASS` |
| 最大化及别名 | `max`、`maximize`、`maximized` | `IsZoomed=True` | `PASS` |
| 最小化及别名 | `min`、`minimize`、`minimized` | `IsIconic=True` | `PASS` |
| 隐藏状态 | `hide` | `IsWindowVisible=False` | `PASS` |
| 非法状态 | `unsupported-state` | 抛出 `InvalidParamsError` | `PASS` |
| 状态与焦点恢复 | 恢复记录的初始状态及原窗口 | 两项均恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_set_state.py`
- 测试窗口：`Win32 靶场 - UIA`
- 靶场句柄：`1247902`
- 初始状态：正常显示
- 合法枚举：`10/10` 均已调用并通过原生状态观察
- 非法枚举：正确抛出 `InvalidParamsError`
- 总状态：`PASS`
- 通过数：`8/8`
- 总耗时：`517.1ms`
- 靶场初始状态：已恢复
- 原前台窗口：已恢复
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 带首尾空白或不同大小写的状态值；源码已支持规范化，本轮只实测精确小写值。
- Runtime 不可用时的本地 `native_window.set_state()` 回退路径。
- 没有真实句柄的伪 `Win32Window` 异常路径。
- 窗口状态切换后的具体位置和尺寸；本轮只验证显示、最小化、最大化状态。
- 将本次窗口句柄固化为长期 API 合同。

