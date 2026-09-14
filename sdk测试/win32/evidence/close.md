# `uiautoma.win32.Win32Window.close()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.close"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  handle_validation: "PASS"
  window_binding: "PASS"
  close_request: "PASS"
  window_closed: "PASS"
  cleanup: "PASS"
  passed: 6
  total: 6
  elapsed_ms: 53.5
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.close 的 SDK→Runtime→Win32 窗口关闭路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.close"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["close"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["close"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.close"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols: ["NamedPipeServer._handle_window_close"]
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "close(self) -> None"
    public_parameters: []
    requires_native_window: true
    sends_close_request: true
    asynchronous_close: true
    return_annotation: "None"
persistent_script:
  path: "win32/test_win32_close.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "e979c2e818cc061e8171efd71ebcd1fdd3b813951b43825e5d2a05dfe1a62a30"
  command: 'uv run .\win32\test_win32_close.py --handle 0x130a9e'
  script_parameters:
    - name: "--handle"
      required: true
      formats: ["decimal", "0x hexadecimal"]
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process_id: 33528
  target_class: "XPathWin32ShootingRange"
  target_handle_decimal: 1247902
  target_handle_hex: "0x130a9e"
  close_observation: "Win32 IsWindow"
  close_timeout_seconds: 5.0
  native_fallback_used: false
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 None"
    elapsed_ms: 0.0
  handle_validation:
    status: "PASS"
    detail: "传入句柄有效，标题、类名和 PID 已读取"
    elapsed_ms: 0.1
  window_binding:
    status: "PASS"
    call: "win32.get_by_handle(1247902, timeout=5)"
    detail: "返回 Win32Window 已绑定传入句柄"
    elapsed_ms: 1.6
  close_request:
    status: "PASS"
    call: "window.close()"
    returned_none: true
    elapsed_ms: 0.6
  window_closed:
    status: "PASS"
    handle_valid_after_close: false
    detail: "原窗口句柄已失效，窗口关闭完成"
    elapsed_ms: 50.3
cleanup:
  status: "PASS"
  elapsed_ms: 0.0
  temporary_resources_created: false
  forced_termination: false
  target_window_closed: true
  target_restorable: false
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_close.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_close.py --handle 0x130a9e
```

`--handle` 是测试脚本参数，不是 `close()` 的 API 参数。它是必填项，支持十进制和
`0x` 十六进制。脚本先用 Windows `IsWindow` 校验句柄并读取标题、类名和 PID，再用
`get_by_handle()` 建立 SDK 对象。调用 `close()` 后，脚本轮询 `IsWindow`，最多等待
`5` 秒确认原句柄失效。测试会真实关闭窗口，无法恢复。

## API 参数

```python
close() -> None
```

- `close()` 没有 API 参数。
- 调用对象必须绑定真实顶层窗口句柄。
- 成功返回 `None`。
- 关闭请求是异步的；返回 `None` 不等价于窗口已经退出。
- 如果目标应用需要保存确认，发送关闭请求后窗口可能继续存在。
- Runtime 不支持或不可用时，高层实现回退到本地 Win32 `close()`。

## 最小实现链

```text
Win32Window.close()
  -> runtime_window.close(NativeWindow)
  -> Automation Pipe window.close
  -> NamedPipeServer._handle_window_close(...)
  -> WindowService.close(...)
  -> Win32 PostMessageW(WM_CLOSE)
  -> None
```

源码还包含 Runtime 不可用时直接调用本地 `PostMessageW(WM_CLOSE)` 的回退路径。本轮
Runtime 正常，未触发该路径。

## 覆盖矩阵

| 场景 | 调用或观察 | 断言 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.close)` | 无参数，返回 `None` | `PASS` |
| 句柄校验 | `IsWindow(0x130a9e)` | 句柄有效并读取窗口信息 | `PASS` |
| 窗口对象绑定 | `get_by_handle(0x130a9e)` | 返回对象绑定同一句柄 | `PASS` |
| 关闭请求 | `window.close()` | 调用完成并返回 `None` | `PASS` |
| 窗口关闭确认 | 轮询 `IsWindow` | 原句柄在超时前失效 | `PASS` |
| 资源清理 | 检查测试资源 | 未创建临时资源，未强制终止进程 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_close.py --handle 0x130a9e`
- 测试窗口：`Win32 靶场 - UIA`
- 窗口类名：`XPathWin32ShootingRange`
- 句柄：`0x130a9e`（十进制 `1247902`）
- PID：`33528`
- `close()` 返回值：`None`
- 关闭结果：原窗口句柄已失效
- 总状态：`PASS`
- 通过数：`6/6`
- 总耗时：`53.5ms`
- 强制终止：未执行
- 临时资源：未创建
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 有未保存内容并出现确认对话框的窗口。
- Runtime 不可用时的本地 `native_window.close()` 回退路径。
- 无效、已失效或非顶层窗口句柄的真实调用。
- 验证目标进程退出；本轮只验证指定窗口句柄失效。
