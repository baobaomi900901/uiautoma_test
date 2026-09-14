# `uiautoma.win32.get_by_handle()` 验证证据

```yaml
api: "uiautoma.win32.get_by_handle"
lifecycle: "VERIFIED"
verification_date: "2026-09-03"
verification_summary:
  api_contract: "PASS"
  runtime_preflight: "PASS"
  get_handle_int_default_timeout: "PASS"
  get_handle_decimal_string: "PASS"
  get_handle_hex_string: "PASS"
  get_timeout_zero: "PASS"
  get_invalid_handle_none: "PASS"
  get_invalid_handle_empty: "PASS"
  get_invalid_handle_non_numeric: "PASS"
  get_invalid_handle_zero: "PASS"
  get_invalid_handle_negative: "PASS"
  get_stale_positive_handle: "PASS"
  get_invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 14
  total: 14
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.get_by_handle 的最小 SDK→runtime/native 句柄解析路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["get_by_handle"]
      fingerprint: "74d663274e634604e87b96ece9d6c90d274db35d"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["get_by_handle"]
      fingerprint: "413554db0b49f571dc0672f50a6e04f74be4a8da"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["get_by_handle"]
      fingerprint: "c425101cb7ca55df3f5b54f319f693a5f6cdd3e1"
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window", "Win32Window.get_detail"]
      fingerprint: "88c1f4821db340c4fc00268bc4a89e88524b9a6c"
  verified_contract:
    signature: "get_by_handle(handle=None, *, timeout=5) -> Win32Window"
    parameter_order:
      - "handle"
      - "timeout"
    defaults:
      handle: null
      timeout: 5
    return_annotation: "Win32Window"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_get_by_handle.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "6e32d0e866d74bf8216c4ef4ee227bd6eb9869e0"
  command: 'uv run .\win32\test_win32_get_by_handle.py --handle 0x1106c'
test_asset:
  input_handle: "0x1106c"
  decimal_handle: 69740
  hexadecimal_handle: "0x1106c"
  actual_title: "微信"
  class_name: "Qt51514QWindowIcon"
  process_name: "Weixin.exe"
  stale_positive_handle: 2147483647
source_commit_at_doc_time: "8a974056fdad67d73adb6dea7863a43ff048001e"
```

## 持久化脚本

脚本：`win32/test_win32_get_by_handle.py`

运行前必须显式传入当前有效窗口句柄。从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_by_handle.py --handle 0x1106c
uv run .\win32\test_win32_get_by_handle.py --handle 69740 --contract-only
uv run .\win32\test_win32_get_by_handle.py --handle 69740 --no-color
uv run .\win32\test_win32_get_by_handle.py --handle 69740 --json
```

默认模式输出带状态颜色的中文对齐表格。`--no-color` 保留友好摘要但关闭颜色；
`--json` 只输出机器可读 JSON，不包含 ANSI 控制字符。缺少 `--handle` 时脚本在测试前
直接报错并以退出码 `2` 结束。

## API 角色划分

- 场景准备：调用者提供当前有效窗口句柄；Runtime 与 Automation Pipe 可响应。
- 目标 API：`win32.get_by_handle(handle, *, timeout=5)`。
- 验收：整数、十进制字符串和十六进制字符串均返回 `Win32Window`，且返回句柄与
  输入句柄完全一致。
- 负例：空值、非数字、零、负数、失效正数句柄及非法超时均返回约定异常。
- 清理：只读获取，不创建、激活、关闭或修改目标窗口。

## 最小实现链

```text
uiautoma.win32.get_by_handle
  -> retry_until
  -> runtime_window.get_by_handle / native_window.get_by_handle
  -> handle 解析与 IsWindow 校验
  -> Win32Window(_native=...)
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `handle`、keyword-only `timeout`、默认值和 `Win32Window` 返回注解 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 整数句柄与默认超时 | `PASS` | `69740`，省略 `timeout`，返回原窗口 |
| 十进制字符串 | `PASS` | `"69740"` 返回原窗口 |
| 十六进制字符串 | `PASS` | `"0x1106c"` 返回原窗口 |
| 零超时 | `PASS` | `timeout=0` 单次查询返回已存在窗口 |
| `None` 句柄 | `PASS` | 抛出 `InvalidParamsError` |
| 空字符串句柄 | `PASS` | 抛出 `InvalidParamsError` |
| 非数字字符串 | `PASS` | 抛出 `InvalidParamsError` |
| 零句柄 | `PASS` | 抛出 `InvalidParamsError` |
| 负数句柄 | `PASS` | 抛出 `InvalidParamsError` |
| 失效正数句柄 | `PASS` | `2147483647` 配合 `timeout=0` 抛出 `ElementNotFoundError` |
| 非法超时 | `PASS` | 有效句柄配合 `timeout=-2` 抛出 `InvalidParamsError` |
| 资源清理 | `PASS` | 未创建或关闭任何窗口 |

## 最近一次真实验证

- 日期：2026-09-03
- 命令：`uv run .\win32\test_win32_get_by_handle.py --handle 0x1106c`
- 测试对象：`微信` / `Qt51514QWindowIcon` / `Weixin.exe`
- 输入句柄：`0x1106c`（十进制 `69740`）
- 总状态：`PASS`
- 通过数：`14/14`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- `timeout=-1` 无限等待：避免目标窗口失效时测试脚本永久挂起。
- 元素库绑定：窗口级 API 不要求 Package。
- 关闭、激活或修改目标窗口。
