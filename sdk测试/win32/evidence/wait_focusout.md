# `uiautoma.win32.Win32Window.wait_focusout()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.wait_focusout"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  window_setup: "PASS"
  activate_target: "PASS"
  zero_active: "PASS"
  finite_active: "PASS"
  positive_wait: "PASS"
  default_inactive: "PASS"
  zero_inactive: "PASS"
  infinite_inactive: "PASS"
  none_timeout: "PASS"
  invalid_timeout: "PASS"
  pseudo_window: "PASS"
  cleanup: "PASS"
  passed: 13
  total: 13
  elapsed_ms: 1031.1
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.wait_focusout 的句柄校验、前台状态和超时轮询路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.wait_focusout", "Win32Window.is_active", "Win32Window._require_live_native", "Win32Window._is_native_gone"]
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
    signature: "wait_focusout(self, timeout: float = 20) -> bool"
    public_parameters:
      - name: "timeout"
        type: "float"
        kind: "positional-or-keyword"
        default: 20
        zero: "single foreground check"
        positive: "poll until focus is lost or deadline"
        minus_one: "wait indefinitely"
        none_runtime_behavior: "use default timeout"
        invalid: "less than -1 or non-numeric"
    focus_lost_result: true
    window_disappeared_during_wait_result: true
    timeout_while_focused_result: false
    poll_interval_seconds: 0.2
    invalid_timeout_error: "InvalidParamsError"
    initially_missing_window_error: "ElementNotFoundError"
    no_native_handle_error: "UnsupportedActionError"
    return_annotation: "bool"
persistent_script:
  path: "win32/test_win32_wait_focusout.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "09a257fdd5865252ecef0e4e85f5957d7b974ac2a15f8a2ec62f44128ce050fd"
  command: 'uv run .\win32\test_win32_wait_focusout.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 1509880
  original_foreground_handle: 68196
  finite_active_timeout_seconds: 0.5
  delayed_focusout_seconds: 0.35
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
    elapsed_ms: 2.6
  activate_target:
    status: "PASS"
    detail: "靶场已成为系统前台窗口"
    elapsed_ms: 20.0
  zero_active:
    status: "PASS"
    call: "target.wait_focusout(timeout=0)"
    returned: false
    elapsed_ms: 0.5
  finite_active:
    status: "PASS"
    call: "target.wait_focusout(0.5)"
    returned: false
    elapsed_ms: 603.0
  positive_wait:
    status: "PASS"
    call: "target.wait_focusout(2)"
    delayed_focusout_ms: 350
    wait_elapsed_ms: 402.5
    returned: true
    original_foreground_confirmed: true
    elapsed_ms: 402.5
  default_inactive:
    status: "PASS"
    call: "target.wait_focusout()"
    returned: true
    elapsed_ms: 0.3
  zero_inactive:
    status: "PASS"
    call: "target.wait_focusout(timeout=0)"
    returned: true
    elapsed_ms: 0.3
  infinite_inactive:
    status: "PASS"
    call: "target.wait_focusout(timeout=-1)"
    returned: true
    elapsed_ms: 0.1
  none_timeout:
    status: "PASS"
    call: "target.wait_focusout(timeout=None)"
    returned: true
    elapsed_ms: 0.2
  invalid_timeout:
    status: "PASS"
    values: [-2, "bad"]
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  pseudo_window:
    status: "PASS"
    call: "Win32Window(title='...').wait_focusout(0)"
    expected_error: "UnsupportedActionError"
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 0.0
  target_application_left_running: true
  original_foreground_restored: true
  temporary_resources_created: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_wait_focusout.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_wait_focusout.py
```

脚本使用用户已经启动的 Win32 靶场和运行脚本时的原前台窗口，不依赖元素库。测试先
激活靶场并验证聚焦状态下的超时结果，再定时激活原窗口以制造真实失焦；结束时确认
靶场保持运行，并恢复原前台窗口。

## API 参数

```python
wait_focusout(timeout: float = 20) -> bool
```

- `timeout` 是位置或关键字参数，默认值为 `20` 秒。
- `timeout=0` 只检查一次；正数每隔约 `0.2s` 检查；`timeout=-1` 一直等待。
- 当前实现还接受 `timeout=None`，并按默认超时处理；公开类型标注仍为 `float`。
- 窗口在期限内失去系统前台焦点返回 `True`；超时仍聚焦返回 `False`。
- 等待过程中窗口消失也返回 `True`。
- 小于 `-1` 或非数字超时抛出 `InvalidParamsError`。
- 调用开始前窗口句柄已失效时抛出 `ElementNotFoundError`。
- 对没有真实句柄的伪 `Win32Window` 调用时抛出 `UnsupportedActionError`。

## 最小实现链

```text
Win32Window.wait_focusout(timeout)
  -> _require_live_native("win32.window.wait_focusout")
     -> 没有真实句柄：UnsupportedActionError
     -> 调用前句柄已失效：ElementNotFoundError
  -> timeout_seconds(timeout, 20)
  -> loop:
       原生窗口已消失：return True
       is_active()
         -> Runtime get_active().handle
         -> Runtime 不可用时回退 Win32 GetForegroundWindow
       已失焦：return True
       timeout=0 或到达期限：return False
       sleep(0.2s)
```

测试使用 Win32 `GetForegroundWindow` 独立确认靶场和原窗口的实际前台状态。

## 覆盖矩阵

| 场景 | 调用 | 前台状态 | 预期 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.wait_focusout)` | — | `timeout=20`，返回 `bool` | `PASS` |
| 窗口准备 | 获取靶场和原前台窗口 | 终端在前台 | 两个句柄有效且不同 | `PASS` |
| 激活靶场 | `target.activate()` | 终端在前台 | 靶场成为前台 | `PASS` |
| 零超时仍聚焦 | `wait_focusout(timeout=0)` | 靶场聚焦 | `False` | `PASS` |
| 有限等待仍聚焦 | `wait_focusout(0.5)` | 始终聚焦 | 超时后 `False` | `PASS` |
| 延迟失去焦点 | `wait_focusout(2)` | `0.35s` 后激活原窗口 | 等待后 `True` | `PASS` |
| 默认超时已失焦 | `wait_focusout()` | 靶场已失焦 | 立即 `True` | `PASS` |
| 零超时已失焦 | `wait_focusout(timeout=0)` | 靶场已失焦 | `True` | `PASS` |
| 无限等待值 | `wait_focusout(timeout=-1)` | 靶场已失焦 | 立即 `True` | `PASS` |
| `None` 超时值 | `wait_focusout(timeout=None)` | 靶场已失焦 | 按默认值并立即 `True` | `PASS` |
| 非法超时 | `-2`、`"bad"` | 靶场有效 | 抛出 `InvalidParamsError` | `PASS` |
| 伪窗口 | `Win32Window(...).wait_focusout(0)` | 无真实句柄 | 抛出 `UnsupportedActionError` | `PASS` |
| 资源清理 | `IsWindow`、`GetForegroundWindow` | — | 靶场存活且原焦点已恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_wait_focusout.py`
- 测试窗口：`Win32 靶场 - UIA`
- 靶场句柄：`1509880`
- 原前台句柄：`68196`
- 有限聚焦等待：`0.5s` 后约 `603.0ms` 返回 `False`
- 延迟失焦：`0.35s` 后激活原窗口，约 `402.5ms` 返回 `True`
- 总状态：`PASS`
- 通过数：`13/13`
- 总耗时：`1031.1ms`
- 原前台窗口：已恢复
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 等待过程中关闭靶场并验证“窗口消失返回 `True`”；本轮采用非破坏性方案。
- 对调用前已经失效的真实窗口验证 `ElementNotFoundError`；这需要先关闭测试窗口。
- 对仍聚焦窗口执行 `timeout=-1`；这会按合同永久等待。
- 强制制造 Runtime 前台查询失败以验证原生回退分支；本次只独立核对最终 Win32 前台句柄。

