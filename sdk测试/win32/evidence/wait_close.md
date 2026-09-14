# `uiautoma.win32.Win32Window.wait_close()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.wait_close"
lifecycle: "VERIFIED"
verification_date: "2026-09-05"
verification_summary:
  source_contract: "PASS"
  window_setup: "PASS"
  zero_timeout: "PASS"
  finite_timeout: "PASS"
  default_wait: "PASS"
  native_closed: "PASS"
  infinite_closed: "PASS"
  invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 9
  total: 9
  elapsed_ms: 1007.2
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.wait_close 的超时规范化和 Win32 句柄轮询路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.wait_close"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["wait_close", "exists"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["timeout_seconds"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "wait_close(self, timeout: float = 20) -> bool"
    public_parameters:
      - name: "timeout"
        type: "float"
        kind: "positional-or-keyword"
        default: 20
        zero: "single check"
        minus_one: "wait indefinitely"
        invalid: "less than -1 or non-numeric"
    poll_interval_seconds: 0.2
    timeout_result: false
    closed_result: true
    invalid_timeout_error: "InvalidParamsError"
    return_annotation: "bool"
    runtime_rpc_used: false
persistent_script:
  path: "win32/test_win32_wait_close.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "75e1bb5466251628c6aa0c304da90fbe3abfe2fada14eb7d241aa0b27d8786c6"
  command: 'uv run .\win32\test_win32_wait_close.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_process_id: 109132
  target_class: "XPathWin32ShootingRange"
  target_handle_decimal: 461558
  target_handle_hex: "0x70af6"
  finite_timeout_seconds: 0.5
  delayed_close_seconds: 0.35
  close_trigger: "Win32 PostMessageW(WM_CLOSE)"
  independent_observation: "Win32 IsWindow"
observations:
  api_contract:
    status: "PASS"
    detail: "timeout 为默认 20 的位置或关键字浮点参数，返回 bool"
    elapsed_ms: 0.0
  window_setup:
    status: "PASS"
    handle: 461558
    process_id: 109132
    elapsed_ms: 3.6
  zero_timeout:
    status: "PASS"
    call: "wait_close(0)"
    returned: false
    native_window_exists: true
    elapsed_ms: 0.0
  finite_timeout:
    status: "PASS"
    call: "wait_close(timeout=0.5)"
    returned: false
    native_window_exists: true
    elapsed_ms: 600.7
  default_wait:
    status: "PASS"
    call: "wait_close()"
    delayed_close_ms: 350
    wait_elapsed_ms: 401.2
    returned: true
    native_window_exists: false
    elapsed_ms: 401.3
  native_closed:
    status: "PASS"
    observation: "IsWindow(handle)"
    returned: false
    elapsed_ms: 0.0
  infinite_closed:
    status: "PASS"
    call: "wait_close(timeout=-1)"
    returned: true
    elapsed_ms: 0.0
  invalid_timeout:
    status: "PASS"
    calls:
      - "wait_close(-2)"
      - 'wait_close("bad")'
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 0.0
  target_window_closed: true
  temporary_resources_created: false
  forced_termination: false
  target_restorable: false
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_wait_close.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_wait_close.py
```

脚本使用已经运行的 Win32 靶场。先在窗口存在时验证零超时和 `0.5s` 有限超时均返回
`False`；随后安排在 `0.35s` 后通过原生 `PostMessageW(WM_CLOSE)` 关闭靶场，让默认
`wait_close()` 真实等待并返回 `True`。关闭后使用 `IsWindow` 独立确认原句柄失效，
再验证 `timeout=-1` 和非法超时。测试会真实关闭靶场，无法恢复。

## API 参数

```python
wait_close(timeout: float = 20) -> bool
```

- `timeout` 是位置或关键字参数，默认值为 `20` 秒。
- `timeout=0` 只检查一次；窗口仍存在时返回 `False`。
- 正数表示有限等待，超时仍未关闭时返回 `False`。
- `timeout=-1` 表示无限等待。本轮对已经关闭的句柄调用，确认立即返回 `True`，避免测试挂起。
- 小于 `-1` 或非数字值抛出 `InvalidParamsError`。
- 窗口在超时前关闭，或调用时已经关闭，返回 `True`。
- 该方法只要求对象保留原生句柄；轮询直接使用本地 Win32 `IsWindow`，不发 Runtime RPC。

## 最小实现链

```text
Win32Window.wait_close(timeout)
  -> native_window.wait_close(NativeWindow, timeout)
  -> timeout_seconds(timeout, 20)
  -> loop:
       native_window.exists(NativeWindow)
         -> Win32 IsWindow(handle)
       handle invalid: return True
       timeout: return False
       sleep(0.2s)
```

## 覆盖矩阵

| 场景 | 调用 | 窗口状态 | 预期 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.wait_close)` | — | `timeout=20`，返回 `bool` | `PASS` |
| 零超时 | `wait_close(0)` | 仍存在 | `False`，立即返回 | `PASS` |
| 有限超时 | `wait_close(timeout=0.5)` | 始终存在 | 超时后返回 `False` | `PASS` |
| 默认等待 | `wait_close()` | `0.35s` 后关闭 | 等待后返回 `True` | `PASS` |
| 原生关闭确认 | `IsWindow(handle)` | 已关闭 | `False` | `PASS` |
| 无限等待值 | `wait_close(timeout=-1)` | 已关闭 | 立即返回 `True` | `PASS` |
| 非法负值 | `wait_close(-2)` | 已关闭 | 抛出 `InvalidParamsError` | `PASS` |
| 非数字值 | `wait_close("bad")` | 已关闭 | 抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 检查窗口和资源 | 已关闭 | 无临时资源、无强制终止 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-05
- 命令：`uv run .\win32\test_win32_wait_close.py`
- 测试窗口：`Win32 靶场 - UIA`
- 句柄：`461558`（`0x70af6`）
- PID：`109132`
- 有限超时：`0.5s` 后返回 `False`，窗口仍存在
- 默认等待：`0.35s` 后发送 `WM_CLOSE`，约 `401.2ms` 返回 `True`
- 关闭确认：`IsWindow` 返回 `False`
- 总状态：`PASS`
- 通过数：`9/9`
- 总耗时：`1007.2ms`
- 靶场程序：已关闭
- 临时资源：未创建
- 强制终止：未执行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 在窗口仍存在时永久等待 `timeout=-1`；为避免测试脚本不可退出，本轮只验证已关闭状态。
- 有未保存内容并出现关闭确认对话框的应用。
- 没有原生句柄的伪 `Win32Window` 异常路径。
- 验证目标进程退出；本轮只验证指定窗口句柄失效。
