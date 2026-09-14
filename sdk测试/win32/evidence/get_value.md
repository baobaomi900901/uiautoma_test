# `uiautoma.win32.Win32Element.get_value()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_value"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  initial_value: "PASS"
  empty_value: "PASS"
  ascii_value: "PASS"
  unicode_value: "PASS"
  symbols_and_spaces: "PASS"
  repeatability: "PASS"
  no_value_control: "PASS"
  last_result_unchanged: "PASS"
  extra_arguments: "PASS"
  mixed_dpi_displays: "PASS"
  cleanup: "PASS"
  passed: 13
  total: 13
  elapsed_ms: 346.3
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "Win32Element.get_value 的公开包装、读取 RPC 和 Runtime Value 读取路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.get_value"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["RawWinElement.get_value"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.get_value_element", "ActionService._read_win_value"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_read_element", "_control_value_text"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "get_value(self) -> str"
    public_parameters: []
    public_timeout_parameter: false
    internal_timeout_seconds: 5
    return_type: "str"
    empty_value_fallback: "empty string"
    updates_last_result: false
persistent_script:
  path: "win32/test_win32_get_value.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "63ca1749923e9e8bbe78f838b70c2f06b90c86afddeb5cb1a28b5ccd08cb6e62"
  command: 'uv run .\win32\test_win32_get_value.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  value_element: "win32靶场输入框"
  no_value_element: "win32靶场保存按钮"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  dpi_awareness: "Per-Monitor v2 (process)"
  verified_display_scales: ["100%", "250%"]
  native_value_reference: "WM_SETTEXT / WM_GETTEXT"
live_runs:
  - display_scale: "100%"
    sdk_rect: [1400, 447, 430, 30]
    native_rect: [1400, 447, 430, 30]
    passed: 13
    total: 13
    elapsed_ms: 434.0
    exit_code: 0
  - display_scale: "250%"
    sdk_rect: [3938, 278, 1075, 75]
    native_rect: [3938, 278, 1075, 75]
    passed: 13
    total: 13
    elapsed_ms: 346.3
    exit_code: 0
cleanup:
  status: "PASS"
  input_value_restored: true
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_get_value.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_value.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，从已经启动的 Win32
靶场获取 `win32靶场输入框` 和 `win32靶场保存按钮`。它根据 SDK 元素的物理边界定位
原生 Edit 控件，通过 Windows `WM_SETTEXT` 准备测试值、通过 `WM_GETTEXT` 独立读取
实际值，再与 `get_value()` 的返回结果核对。脚本在导入 SDK 前启用 Per-Monitor DPI
Awareness v2，使 SDK 与 User32 均使用物理像素坐标。结束时恢复输入框原值、鼠标和
前台窗口，关闭借用的 Package，并保持靶场运行。

## API 合同

```python
get_value() -> str
```

- `get_value()` 没有公开参数；多余位置参数和 `timeout` 关键字均由 Python 抛出
  `TypeError`。
- 公开返回值固定为 `str`；控件没有可读 Value 或底层返回空值时归一化为空字符串。
- 高层 API 没有公开 `timeout` 参数；Raw SDK 内部使用固定的 5 秒读取超时。
- Runtime 优先读取 UIA `ValuePattern.Value`，再回退到控件的 `Value` 属性。
- 该读取 API 不写入 `Win32Element.last_result`。

## 最小实现链

```text
Win32Element.get_value()
  -> RawWinElement.get_value(timeout=5s)
  -> Session._run_win_value("element.get_value", ...)
  -> ActionService.get_value_element(...)
  -> ActionService._read_win_value(..., op="get_value")
  -> Runtime Worker handle_read_element(...)
  -> UIA ValuePattern.Value，失败时回退到控件 Value
  -> SDK 将 value/text 归一化为 str
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.get_value)` | 无公开参数，返回注解为 `str` | `PASS` |
| 当前元素库 | `uiautoma.current()` | 当前 Package 是指定测试库 | `PASS` |
| 测试目标 | 输入框及保存按钮 | SDK 元素可定位；输入框与唯一原生 Edit 的物理边界一致 | `PASS` |
| 初始值 | 输入框运行前的值 | SDK 返回 `str`，并与原生当前值一致 | `PASS` |
| 空字符串 | `""` | SDK 与 `WM_GETTEXT` 均返回空字符串 | `PASS` |
| 英文数字 | `"UIAutoma_Value_123"` | SDK 与原生读取精确一致 | `PASS` |
| 中文文本 | `"中文值_自动化测试"` | Unicode 文本读取精确一致 | `PASS` |
| 符号与空格 | `"  {}[]!@#_+-=()  "` | 首尾空格和符号均被保留 | `PASS` |
| 重复读取 | 连续调用三次 | 三次返回相同字符串 | `PASS` |
| 无 Value 控件 | 保存按钮 | 返回空字符串 | `PASS` |
| 动作结果隔离 | 读取前后 `last_result` | 保持原对象，不创建动作结果 | `PASS` |
| 额外参数 | `get_value(0)`、`get_value(timeout=0)` | 均抛出 `TypeError` | `PASS` |
| 100% 与 250% 缩放 | 两个不同缩放倍率的显示器 | SDK 与 User32 物理边界完全一致，两次均 13/13 通过 | `PASS` |
| 资源清理 | 输入值、鼠标、焦点和 Package | 全部恢复，靶场保持运行 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_get_value.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 值元素：`win32靶场输入框`
- 无 Value 元素：`win32靶场保存按钮`
- DPI 模式：`Per-Monitor v2（进程）`
- 100% 显示器：SDK 与原生边界均为 `(1400, 447, 430, 30)`，`13/13` 通过，
  总耗时 `434.0ms`
- 250% 显示器：SDK 与原生边界均为 `(3938, 278, 1075, 75)`，`13/13` 通过，
  总耗时 `346.3ms`
- 250% 显示器原生 Edit：`22486628 (0x1571e64)`
- 验证值：空字符串、`UIAutoma_Value_123`、`中文值_自动化测试`、
  `  {}[]!@#_+-=()  ` 均与原生读取一致
- 总状态：`PASS`
- 通过数：`13/13`
- 总耗时：`346.3ms`（最近一次 250% 显示器运行）
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者提供的 100% 与 250% 显示器完整运行日志
- 数据恢复：输入框原值、鼠标和原前台窗口已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行
- 产品源码修改：无

## 明确排除

- 密码框、富文本编辑器、自定义控件及 Java 控件的 Value 读取路径。
- `get_text()` 的 UIA Name 读取语义；本轮只验证 Value。
- `set_value()`、`input()` 和 `clipboard_input()` 的动作合同；`WM_SETTEXT` 仅用于独立准备
  测试数据，不作为 SDK 被测 API。
