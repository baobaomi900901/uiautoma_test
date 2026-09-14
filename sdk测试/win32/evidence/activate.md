# `uiautoma.win32.Win32Window.activate()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.activate"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  target_window: "PASS"
  original_foreground: "PASS"
  activate_target: "PASS"
  target_foreground: "PASS"
  restore_original: "PASS"
  cleanup: "PASS"
  passed: 7
  total: 7
  elapsed_ms: 150.5
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.activate 的 SDK→Runtime→Win32 前台激活路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.activate", "Win32Window.is_active"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["activate", "get_active"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["activate", "is_active"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.activate", "_activate_window"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols: ["NamedPipeServer._handle_window_activate"]
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "activate(self) -> None"
    public_parameters: []
    requires_native_window: true
    runtime_method: "window.activate"
    return_annotation: "None"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_activate.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "e9673a21d4af284fd35e4c3ee86654b7b35ac35d6bdc43b24198ef1f20367a21"
  command: 'uv run .\win32\test_win32_activate.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 593506
  original_foreground_handle: 1510016
  focus_timeout_seconds: 2.0
  activation_path: "Runtime window.activate"
  native_fallback_used: false
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 None"
    elapsed_ms: 0.1
  target_window:
    status: "PASS"
    detail: "已获取 Win32 靶场窗口"
    handle: 593506
    elapsed_ms: 4.8
  original_foreground:
    status: "PASS"
    handle: 1510016
    different_from_target: true
    elapsed_ms: 0.3
  activate_target:
    status: "PASS"
    returned: null
    elapsed_ms: 78.1
  target_foreground:
    status: "PASS"
    is_active: true
    elapsed_ms: 0.5
  restore_original:
    status: "PASS"
    returned: null
    is_active: true
    elapsed_ms: 64.9
cleanup:
  status: "PASS"
  elapsed_ms: 0.8
  original_foreground_restored: true
  created_resources: 0
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_activate.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_activate.py
```

脚本先记录运行命令时的前台窗口，再调用目标靶场窗口的 `activate()`，通过
`is_active()` 验证前台状态。随后对原窗口调用相同的 `activate()` 恢复焦点，最终清理
阶段再次确认原窗口处于前台。测试不关闭或修改靶场内容。

## API 参数

```python
activate() -> None
```

- `activate()` 没有公开参数。
- 调用对象必须是绑定真实顶层窗口句柄的 `Win32Window`。
- 成功返回 `None`。
- Runtime 路径通过 `window.activate` 将窗口置前并读取前台窗口句柄确认状态。
- Runtime 不支持或不可用时，高层实现回退到本地 Win32 `activate()`。
- 没有真实句柄的伪窗口调用会抛出 `UnsupportedActionError`。
- 返回值不携带前台状态；需要通过 `is_active()` 或当前前台句柄单独观察。

## 最小实现链

本次验证命中的主路径：

```text
Win32Window.activate()
  -> runtime_window.activate(NativeWindow)
  -> Automation Pipe window.activate
  -> NamedPipeServer._handle_window_activate(...)
  -> WindowService.activate(...)
  -> _activate_window(handle)
  -> Win32 ShowWindow / BringWindowToTop / SetForegroundWindow
  -> None
```

观察路径：

```text
Win32Window.is_active()
  -> runtime_window.get_active()
  -> 当前前台句柄 == 目标句柄
```

源码还包含 `runtime_window.activate()` 抛出 `UnsupportedActionError` 或
`HostUnavailableError` 时调用 `native_window.activate()` 的本地回退。本轮 Runtime
正常，未触发该路径。

## 覆盖矩阵

| 场景 | 调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.activate)` | 无参数，返回 `None` | 符合 | `PASS` |
| 靶场窗口 | `win32.get(...)` | 获取真实 Win32 靶场窗口 | 句柄 `593506` | `PASS` |
| 原前台窗口 | `win32.get_active()` | 与靶场句柄不同 | 句柄 `1510016` | `PASS` |
| 激活靶场 | `target.activate()` | 返回 `None` | 返回 `None` | `PASS` |
| 前台状态 | `target.is_active()` | `True` | `True` | `PASS` |
| 恢复原窗口 | `original.activate()` / `original.is_active()` | 返回 `None` 且恢复前台 | 符合 | `PASS` |
| 资源清理 | 最终检查与必要时再次恢复 | 原窗口处于前台，靶场保持运行 | 符合 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_activate.py`
- 测试窗口：`Win32 靶场 - UIA`
- 目标句柄：`593506`
- 原前台窗口句柄：`1510016`
- 激活调用：返回 `None`，靶场成为前台窗口
- 恢复调用：返回 `None`，原前台窗口重新成为前台窗口
- 总状态：`PASS`
- 通过数：`7/7`
- 总耗时：`150.5ms`
- 创建资源：无
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 从最小化状态激活并恢复窗口；本轮靶场窗口未预先最小化。
- Runtime 不可用时的本地 `native_window.activate()` 回退路径。
- 没有真实句柄的伪 `Win32Window` 异常路径。
- 将本次目标句柄或原前台窗口句柄固化为长期 API 合同。
- 关闭、移动、缩放或修改 Win32 靶场程序。
