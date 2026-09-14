# `uiautoma.win32.Win32Window.get_detail()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.get_detail"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  target_window: "PASS"
  full_detail: "PASS"
  title_text: "PASS"
  class_aliases: "PASS"
  process_aliases: "PASS"
  pid_aliases: "PASS"
  handle_aliases: "PASS"
  rect_aliases: "PASS"
  unknown_operation: "PASS"
  cleanup: "PASS"
  passed: 11
  total: 11
  elapsed_ms: 15.5
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.get_detail 的 SDK→Runtime 窗口详情路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.get_detail"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["get_info", "get_rect"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["get_rect"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
    - path: "runtime/services/window_service.py"
      symbols: ["WindowService.get_info"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/services/pipe_server.py"
      symbols: ["NamedPipeServer._handle_window_get_info"]
      fingerprint: "02bd8c42e0304863c8d135ea5034c5dccb2db6e7"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: 'get_detail(self, operation: str = "") -> Any'
    public_parameters:
      - name: "operation"
        type: "str"
        default: ""
    full_detail_keys: ["handle", "title", "text", "class_name", "process_id", "process_name", "rect"]
    operation_aliases:
      hwnd: "handle"
      class: "class_name"
      classname: "class_name"
      process: "process_name"
      pid: "process_id"
      bounding: "rect"
    operation_normalization: "strip + casefold"
    unknown_operation_result: ""
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_get_detail.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "1b1bfba9c213e97a9553d1aa6ba09be5c9d75c84fe627a587213477238ab18f0"
  command: 'uv run .\win32\test_win32_get_detail.py'
test_environment:
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  handle: 593506
  process_id: 36020
  rect_size: [1024, 720]
  detail_path: "Runtime window.get_info"
  native_fallback_used: false
observations:
  api_contract:
    status: "PASS"
    detail: '公开签名为 get_detail(operation: str = "") -> Any'
    elapsed_ms: 0.1
  target_window:
    status: "PASS"
    handle: 593506
    elapsed_ms: 5.7
  full_detail:
    status: "PASS"
    key_count: 7
    default_and_explicit_empty_equal: true
    elapsed_ms: 1.7
  title_text:
    status: "PASS"
    operation_normalization_verified: true
    elapsed_ms: 1.1
  class_aliases:
    status: "PASS"
    operations: ["class_name", "class", "classname"]
    value: "XPathWin32ShootingRange"
    elapsed_ms: 1.1
  process_aliases:
    status: "PASS"
    operations: ["process_name", "process"]
    value: "win32-shooting-range-uia.exe"
    elapsed_ms: 1.0
  pid_aliases:
    status: "PASS"
    operations: ["process_id", "pid"]
    value: 36020
    elapsed_ms: 1.2
  handle_aliases:
    status: "PASS"
    operations: ["handle", "hwnd"]
    value: 593506
    elapsed_ms: 1.0
  rect_aliases:
    status: "PASS"
    operations: ["rect", "bounding"]
    size: [1024, 720]
    elapsed_ms: 1.3
  unknown_operation:
    status: "PASS"
    returned: ""
    elapsed_ms: 0.5
cleanup:
  status: "PASS"
  elapsed_ms: 0.0
  created_resources: 0
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_get_detail.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_detail.py
```

脚本使用 `win32.get()` 获取已经运行的 Win32 靶场窗口，目标 API 测试只调用
`Win32Window.get_detail()`。所有操作均为只读，不激活、移动、关闭或修改靶场窗口。

## API 参数

```python
get_detail(operation: str = "") -> Any
```

- `operation` 是可选字符串参数，默认空字符串。
- 空字符串返回完整详情字典，包含 `handle`、`title`、`text`、`class_name`、
  `process_id`、`process_name`、`rect` 七个标准字段。
- 正式详情键为 `title`、`text`、`class_name`、`process_name`、`process_id`、
  `handle` 和 `rect`。
- 别名为 `class` / `classname`、`process`、`pid`、`hwnd`、`bounding`。
- 键名在匹配前执行 `strip()` 和 `casefold()`；例如 `" TITLE "` 等同于
  `"title"`。
- 未知键返回空字符串，不抛出异常。

## 最小实现链

本次验证命中的主路径：

```text
Win32Window.get_detail(operation)
  -> runtime_window.get_info(NativeWindow)
  -> Automation Pipe window.get_info
  -> NamedPipeServer._handle_window_get_info(...)
  -> WindowService.get_info(...)
  -> 最新窗口详情字典
  -> operation 规范化与别名映射
  -> 完整字典或指定字段值
```

源码还包含 Runtime 不可用时读取 `NativeWindow.raw`，并通过 `runtime_window.get_rect()`
或本地 `native_window.get_rect()` 补充矩形的回退路径。本轮 Runtime 正常，未触发该路径。

## 覆盖矩阵

| 场景 | 调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.get_detail)` | `operation: str = ""`，返回 `Any` | 符合 | `PASS` |
| 靶场窗口 | `win32.get(...)` | 获取真实 Win32 靶场窗口 | 句柄 `593506` | `PASS` |
| 完整详情 | `get_detail()` / `get_detail("")` | 相同的七字段字典 | 符合 | `PASS` |
| 标题与文本 | `get_detail(" TITLE ")` / `get_detail("text")` | 规范化并与完整详情一致 | 符合 | `PASS` |
| 类名及别名 | `class_name` / `class` / `classname` | 均返回靶场类名 | 符合 | `PASS` |
| 进程名及别名 | `process_name` / `process` | 均返回靶场进程名 | 符合 | `PASS` |
| 进程 ID 及别名 | `process_id` / `pid` | 相同正整数 | `36020` | `PASS` |
| 句柄及别名 | `handle` / `hwnd` | 相同正整数 | `593506` | `PASS` |
| 矩形及别名 | `rect` / `bounding` | 相同有效矩形 | `1024 × 720` | `PASS` |
| 未知详情键 | `get_detail("uiautoma_unknown_detail_key")` | 空字符串 | 空字符串 | `PASS` |
| 资源清理 | 无 | 不创建资源，靶场保持运行 | 符合 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_get_detail.py`
- 测试窗口：`Win32 靶场 - UIA`
- 窗口类名：`XPathWin32ShootingRange`
- 目标进程：`win32-shooting-range-uia.exe`
- 窗口句柄：`593506`
- 进程 ID：`36020`
- 窗口矩形：`1024 × 720`
- 完整详情：七个标准字段均存在
- 正式键及别名：全部一致
- 未知详情键：返回空字符串
- 总状态：`PASS`
- 通过数：`11/11`
- 总耗时：`15.5ms`
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- Runtime 不可用时的 `NativeWindow.raw` / 本地 Win32 矩形回退路径。
- 没有真实句柄的伪 `Win32Window` 分支。
- 窗口关闭、最小化、移动或其他状态修改。
- 将本次窗口句柄、进程 ID 和矩形固化为长期 API 合同。
