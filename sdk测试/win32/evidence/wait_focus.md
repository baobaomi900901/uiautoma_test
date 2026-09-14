# `uiautoma.win32.Win32Window.wait_focus()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.wait_focus"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  window_setup: "PASS"
  zero_inactive: "PASS"
  finite_inactive: "PASS"
  positive_wait: "PASS"
  default_active: "PASS"
  zero_active: "PASS"
  infinite_active: "PASS"
  invalid_timeout: "PASS"
  pseudo_window: "PASS"
  restore_original: "PASS"
  cleanup: "PASS"
  passed: 12
  total: 12
  elapsed_ms: 1044.6
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.wait_focus 的句柄校验、前台状态和超时轮询路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.wait_focus", "Win32Window.is_active", "Win32Window._require_live_native"]
      fingerprint: "d7cf81028692e9f891770481ed7888c26e022397"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["exists", "is_active"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["get_active"]
      fingerprint: "ad9106067c78707de7673da34353d14c13bfbe52"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["timeout_seconds"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "wait_focus(self, timeout: float = 20) -> bool"
    public_parameters:
      - name: "timeout"
        type: "float"
        kind: "positional-or-keyword"
        default: 20
        zero: "single foreground check"
        positive: "poll until focused or deadline"
        minus_one: "wait indefinitely"
        invalid: "less than -1 or non-numeric"
    focused_result: true
    timeout_result: false
    poll_interval_seconds: 0.2
    invalid_timeout_error: "InvalidParamsError"
    missing_window_error: "ElementNotFoundError"
    no_native_handle_error: "UnsupportedActionError"
    return_annotation: "bool"
persistent_script:
  path: "win32/test_win32_wait_focus.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "4aa7a5362673d262a3ed1bf258d490b6e43508eafb3a93b17acababa196bb45e"
  command: 'uv run .\win32\test_win32_wait_focus.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 1509880
  original_foreground_handle: 68196
  finite_inactive_timeout_seconds: 0.5
  delayed_activation_seconds: 0.35
  positive_wait_timeout_seconds: 2.0
  independent_observation: "Win32 GetForegroundWindow and IsWindow"
observations:
  api_contract:
    status: "PASS"
    detail: "timeout 为默认 20 的位置或关键字浮点参数，返回 bool"
    elapsed_ms: 0.0
  window_setup:
    status: "PASS"
    target_handle: 1509880
    original_foreground_handle: 68196
    elapsed_ms: 2.8
  zero_inactive:
    status: "PASS"
    call: "target.wait_focus(timeout=0)"
    returned: false
    elapsed_ms: 0.3
  finite_inactive:
    status: "PASS"
    call: "target.wait_focus(0.5)"
    returned: false
    elapsed_ms: 604.9
  positive_wait:
    status: "PASS"
    call: "target.wait_focus(2)"
    delayed_activation_ms: 350
    wait_elapsed_ms: 402.6
    returned: true
    native_foreground_confirmed: true
    elapsed_ms: 402.6
  default_active:
    status: "PASS"
    call: "target.wait_focus()"
    returned: true
    elapsed_ms: 0.3
  zero_active:
    status: "PASS"
    call: "target.wait_focus(timeout=0)"
    returned: true
    elapsed_ms: 0.2
  infinite_active:
    status: "PASS"
    call: "target.wait_focus(timeout=-1)"
    returned: true
    elapsed_ms: 0.2
  invalid_timeout:
    status: "PASS"
    values: [-2, "bad"]
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  pseudo_window:
    status: "PASS"
    call: "Win32Window(title='...').wait_focus(0)"
    expected_error: "UnsupportedActionError"
    elapsed_ms: 0.0
  restore_original:
    status: "PASS"
    restored_handle: 68196
    elapsed_ms: 31.4
cleanup:
  status: "PASS"
  elapsed_ms: 0.0
  target_application_left_running: true
  original_foreground_restored: true
  temporary_resources_created: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_wait_focus.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_wait_focus.py
```

脚本使用用户已经启动的 Win32 靶场和运行脚本时的原前台窗口，不依赖元素库。测试先
保持终端为前台，验证靶场未聚焦时的返回值；随后定时激活靶场，验证真实等待；结束时
恢复原前台窗口并保持靶场运行。

## API 参数

```python
wait_focus(timeout: float = 20) -> bool
```

- `timeout` 是位置或关键字参数，默认值为 `20` 秒。
- `timeout=0` 只检查一次；正数每隔约 `0.2s` 检查；`timeout=-1` 一直等待。
- 窗口在期限内获得系统前台焦点返回 `True`；超时仍未聚焦返回 `False`。
- 小于 `-1` 或非数字超时抛出 `InvalidParamsError`。
- 窗口句柄已失效时抛出 `ElementNotFoundError`。
- 对没有真实句柄的伪 `Win32Window` 调用时抛出 `UnsupportedActionError`。
- 与 `wait_active()` 不同，`wait_focus()` 用布尔值表示成功或超时；`wait_active()`
  成功返回 `None`，超时抛出 `UIAError`。

## 最小实现链

```text
Win32Window.wait_focus(timeout)
  -> _require_live_native("win32.window.wait_focus")
     -> 没有真实句柄：UnsupportedActionError
     -> 句柄已失效：ElementNotFoundError
  -> timeout_seconds(timeout, 20)
  -> loop:
       is_active()
         -> Runtime get_active().handle
         -> Runtime 不可用时回退 Win32 GetForegroundWindow
       已聚焦：return True
       timeout=0 或到达期限：return False
       sleep(0.2s)
```

测试使用 Win32 `GetForegroundWindow` 独立确认靶场和原窗口的实际前台状态。

## 覆盖矩阵

| 场景 | 调用 | 前台状态 | 预期 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.wait_focus)` | — | `timeout=20`，返回 `bool` | `PASS` |
| 窗口准备 | 获取靶场和原前台窗口 | 终端在前台 | 两个句柄有效且不同 | `PASS` |
| 零超时未聚焦 | `wait_focus(timeout=0)` | 靶场未聚焦 | `False` | `PASS` |
| 有限等待未聚焦 | `wait_focus(0.5)` | 始终未聚焦 | 超时后 `False` | `PASS` |
| 延迟获得焦点 | `wait_focus(2)` | `0.35s` 后激活靶场 | 等待后 `True` | `PASS` |
| 默认超时已聚焦 | `wait_focus()` | 靶场已聚焦 | 立即 `True` | `PASS` |
| 零超时已聚焦 | `wait_focus(timeout=0)` | 靶场已聚焦 | `True` | `PASS` |
| 无限等待值 | `wait_focus(timeout=-1)` | 靶场已聚焦 | 立即 `True` | `PASS` |
| 非法超时 | `-2`、`"bad"` | 靶场有效 | 抛出 `InvalidParamsError` | `PASS` |
| 伪窗口 | `Win32Window(...).wait_focus(0)` | 无真实句柄 | 抛出 `UnsupportedActionError` | `PASS` |
| 恢复原窗口 | `original.activate()` | 靶场在前台 | 原句柄恢复为前台 | `PASS` |
| 资源清理 | `IsWindow`、`GetForegroundWindow` | — | 靶场存活且原焦点已恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_wait_focus.py`
- 测试窗口：`Win32 靶场 - UIA`
- 靶场句柄：`1509880`
- 原前台句柄：`68196`
- 有限未聚焦等待：`0.5s` 后约 `604.9ms` 返回 `False`
- 延迟聚焦：`0.35s` 后激活，约 `402.6ms` 返回 `True`
- 总状态：`PASS`
- 通过数：`12/12`
- 总耗时：`1044.6ms`
- 原前台窗口：已恢复
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 真实关闭靶场后验证 `ElementNotFoundError`；本轮保持靶场运行。
- 对仍未聚焦窗口执行 `timeout=-1`；这会按合同永久等待。
- 验证 Runtime 前台查询失败后的原生回退分支；本次只独立核对最终 Win32 前台句柄。

