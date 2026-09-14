# `uiautoma.win32.Win32Window.wait_active()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.wait_active"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  window_setup: "PASS"
  activate_target: "PASS"
  default_timeout: "PASS"
  zero_active: "PASS"
  infinite_active: "PASS"
  restore_original: "PASS"
  zero_inactive: "PASS"
  positive_wait: "PASS"
  invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 11
  total: 11
  elapsed_ms: 508.8
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.wait_active 的超时规范化、轮询和前台窗口判定路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.wait_active", "Win32Window.is_active"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["timeout_seconds"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["get_active"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["is_active"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.get_active"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols: ["NamedPipeServer._handle_window_get_active"]
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "wait_active(self, timeout: float = 20) -> None"
    public_parameters:
      - name: "timeout"
        type: "float"
        kind: "positional-or-keyword"
        default: 20
        zero: "single check"
        minus_one: "wait indefinitely"
        invalid: "less than -1 or non-numeric"
    poll_interval_seconds: 0.2
    timeout_error: "UIAError"
    invalid_timeout_error: "InvalidParamsError"
    return_annotation: "None"
persistent_script:
  path: "win32/test_win32_wait_active.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "367c337594d43b51da6d835e04252c534b239ceef66f525d96af092157dd20de"
  command: 'uv run .\win32\test_win32_wait_active.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 461558
  original_foreground_handle: 132464
  delayed_activation_seconds: 0.35
  positive_timeout_seconds: 2.0
  independent_observation: "Win32 GetForegroundWindow"
observations:
  api_contract:
    status: "PASS"
    detail: "timeout 为默认 20 的位置或关键字浮点参数，返回 None"
    elapsed_ms: 0.0
  window_setup:
    status: "PASS"
    target_handle: 461558
    original_foreground_handle: 132464
    elapsed_ms: 2.5
  activate_target:
    status: "PASS"
    detail: "靶场已成为系统前台窗口"
    elapsed_ms: 24.7
  default_timeout:
    status: "PASS"
    call: "wait_active()"
    returned_none: true
    elapsed_ms: 0.6
  zero_active:
    status: "PASS"
    call: "wait_active(0)"
    returned_none: true
    elapsed_ms: 0.4
  infinite_active:
    status: "PASS"
    call: "wait_active(timeout=-1)"
    returned_none: true
    elapsed_ms: 0.6
  restore_original:
    status: "PASS"
    elapsed_ms: 28.7
  zero_inactive:
    status: "PASS"
    call: "wait_active(timeout=0)"
    expected_error: "UIAError"
    elapsed_ms: 0.5
  positive_wait:
    status: "PASS"
    call: "wait_active(2)"
    activation_delay_ms: 350
    wait_elapsed_ms: 403.0
    returned_none: true
    native_foreground_matches_target: true
    elapsed_ms: 403.0
  invalid_timeout:
    status: "PASS"
    calls:
      - "wait_active(-2)"
      - 'wait_active("bad")'
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 46.2
  target_still_running: true
  target_initial_state_restored: true
  original_foreground_restored: true
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_wait_active.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_wait_active.py
```

脚本使用已经运行的 Win32 靶场和运行脚本时的原前台窗口。已激活场景覆盖默认值、
`0` 和 `-1`；未激活场景覆盖零超时异常，并在 `0.35s` 后自动激活靶场以验证
`wait_active(2)` 的真实等待。每个前台状态都通过 Windows `GetForegroundWindow`
独立核对。最终恢复靶场初始显示状态和原前台窗口，靶场保持运行。

## API 参数

```python
wait_active(timeout: float = 20) -> None
```

- `timeout` 是位置或关键字参数，默认值为 `20` 秒。
- `timeout=0` 只检查一次；窗口未激活时抛出 `UIAError`。
- 正数表示有限等待，内部每 `0.2s` 调用一次 `is_active()`。
- `timeout=-1` 表示无限等待。本轮在窗口已经激活时调用，确认该值被接受并立即返回。
- 小于 `-1` 或非数字值抛出 `InvalidParamsError`。
- 窗口在超时前成为前台窗口时返回 `None`。
- 调用对象必须绑定仍然有效的真实窗口句柄。

## 最小实现链

```text
Win32Window.wait_active(timeout)
  -> timeout_seconds(timeout, 20)
  -> loop:
       Win32Window.is_active()
         -> runtime_window.get_active()
         -> Automation Pipe window.get_active
         -> Win32 GetForegroundWindow()
       active: return None
       timeout: raise UIAError
       sleep(0.2s)
```

`is_active()` 的 Runtime 路径不可用时会回退到本地 Win32 `GetForegroundWindow()`。

## 覆盖矩阵

| 场景 | 调用 | 前置状态 | 预期 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.wait_active)` | — | `timeout=20`，返回 `None` | `PASS` |
| 默认超时 | `wait_active()` | 靶场已激活 | 立即返回 `None` | `PASS` |
| 零超时成功 | `wait_active(0)` | 靶场已激活 | 立即返回 `None` | `PASS` |
| 无限等待值 | `wait_active(timeout=-1)` | 靶场已激活 | 接受 `-1` 并返回 `None` | `PASS` |
| 零超时失败 | `wait_active(timeout=0)` | 靶场未激活 | 抛出 `UIAError` | `PASS` |
| 有限等待 | `wait_active(2)` | `0.35s` 后激活 | 等待后返回 `None` | `PASS` |
| 非法负值 | `wait_active(-2)` | 靶场有效 | 抛出 `InvalidParamsError` | `PASS` |
| 非数字值 | `wait_active("bad")` | 靶场有效 | 抛出 `InvalidParamsError` | `PASS` |
| 状态与焦点恢复 | 最终兜底恢复 | — | 靶场保持运行、原焦点恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_wait_active.py`
- 测试窗口：`Win32 靶场 - UIA`
- 靶场句柄：`461558`
- 原前台窗口句柄：`132464`
- 有限等待：`0.35s` 后激活，`wait_active(2)` 约 `403.0ms` 返回
- 零超时未激活：正确抛出 `UIAError`
- 非法超时：正确抛出 `InvalidParamsError`
- 总状态：`PASS`
- 通过数：`11/11`
- 总耗时：`508.8ms`
- 靶场初始显示状态：已恢复
- 原前台窗口：已恢复
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 在未激活状态永久等待 `timeout=-1`；为避免测试脚本不可退出，本轮仅验证已激活时接受该值。
- Runtime 不可用时的本地 `is_active()` 回退路径。
- 没有真实句柄或已经销毁的窗口对象。
- 用户人工抢占焦点造成的竞争场景。
