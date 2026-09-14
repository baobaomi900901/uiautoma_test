# `uiautoma.win32.Win32Window.is_active()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.is_active"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  window_setup: "PASS"
  activate_target: "PASS"
  active_true: "PASS"
  restore_original: "PASS"
  active_false: "PASS"
  cleanup: "PASS"
  passed: 7
  total: 7
  elapsed_ms: 67.4
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.is_active 的 SDK→Runtime→Win32 前台窗口判定路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.is_active"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["get_active"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["is_active", "get_active"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.get_active"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols: ["NamedPipeServer._handle_window_get_active"]
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "is_active(self) -> bool"
    public_parameters: []
    requires_native_window: true
    true_when_foreground: true
    false_when_not_foreground: true
    return_annotation: "bool"
persistent_script:
  path: "win32/test_win32_is_active.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "bbe05ecb9f9122644d8bd6e891cb41aa9a42360f5ecbf1123c1a7ef5717dc941"
  command: 'uv run .\win32\test_win32_is_active.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 461558
  original_foreground_handle: 132464
  independent_observation: "Win32 GetForegroundWindow"
  native_fallback_used: false
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 bool"
    elapsed_ms: 0.0
  window_setup:
    status: "PASS"
    target_handle: 461558
    original_foreground_handle: 132464
    elapsed_ms: 2.9
  activate_target:
    status: "PASS"
    detail: "靶场已成为系统前台窗口"
    elapsed_ms: 27.3
  active_true:
    status: "PASS"
    call: "target.is_active()"
    returned: true
    native_foreground_matches_target: true
    elapsed_ms: 0.6
  restore_original:
    status: "PASS"
    detail: "运行脚本前的前台窗口已恢复"
    elapsed_ms: 32.9
  active_false:
    status: "PASS"
    call: "target.is_active()"
    returned: false
    native_foreground_matches_target: false
    elapsed_ms: 0.6
cleanup:
  status: "PASS"
  elapsed_ms: 2.3
  target_still_running: true
  target_initial_state_restored: true
  original_foreground_restored: true
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_is_active.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_is_active.py
```

脚本获取已经运行的 Win32 靶场和运行脚本时的原前台窗口。先用 `activate()` 将靶场
置前，再调用 `is_active()` 验证 `True`；恢复原前台窗口后，再验证靶场返回 `False`。
每次 SDK 结果都与 Windows `GetForegroundWindow` 直接读取的句柄比较。最终清理恢复
靶场初始显示状态和原前台窗口，靶场保持运行。

## API 参数

```python
is_active() -> bool
```

- `is_active()` 没有 API 参数。
- 调用对象必须绑定真实窗口句柄。
- 目标句柄等于系统前台窗口句柄时返回 `True`，否则返回 `False`。
- Runtime 路径读取当前活动窗口并比较句柄。
- Runtime 不支持或不可用时，回退到本地 Win32 `GetForegroundWindow()`。

## 最小实现链

```text
Win32Window.is_active()
  -> runtime_window.get_active()
  -> Automation Pipe window.get_active
  -> NamedPipeServer._handle_window_get_active(...)
  -> WindowService.get_active(...)
  -> Win32 GetForegroundWindow()
  -> active_handle == target_handle
  -> bool
```

源码还包含 Runtime 不可用时直接调用本地 `GetForegroundWindow()` 比较句柄的回退路径。
本轮 Runtime 正常，未触发该路径。

## 覆盖矩阵

| 场景 | 操作 | SDK 预期 | 原生观测 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.is_active)` | 无参数，返回 `bool` | — | `PASS` |
| 窗口准备 | 获取靶场和原前台窗口 | 两个不同的有效句柄 | `461558 != 132464` | `PASS` |
| 激活靶场 | `target.activate()` | 返回 `None` | 前台句柄为靶场 | `PASS` |
| 前台状态 | `target.is_active()` | `True` | 前台句柄等于靶场 | `PASS` |
| 恢复原窗口 | `original.activate()` | 返回 `None` | 前台句柄为原窗口 | `PASS` |
| 非前台状态 | `target.is_active()` | `False` | 前台句柄不等于靶场 | `PASS` |
| 状态与焦点恢复 | 最终兜底恢复 | 靶场保持运行 | 初始状态与原焦点恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_is_active.py`
- 测试窗口：`Win32 靶场 - UIA`
- 靶场句柄：`461558`
- 原前台窗口句柄：`132464`
- 前台调用：返回 `True`，与 `GetForegroundWindow` 一致
- 非前台调用：返回 `False`，与 `GetForegroundWindow` 一致
- 总状态：`PASS`
- 通过数：`7/7`
- 总耗时：`67.4ms`
- 靶场初始显示状态：已恢复
- 原前台窗口：已恢复
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- Runtime 不可用时的本地 `native_window.is_active()` 回退路径。
- 没有真实句柄的伪 `Win32Window` 异常路径。
- 前台窗口句柄暂时为 `0` 时 Runtime 的最近激活窗口回退语义。
- 已销毁窗口对象调用 `is_active()` 的行为。
