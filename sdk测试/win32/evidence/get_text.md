# `uiautoma.win32.Win32Element.get_text()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_text"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  element_prepare: "PASS"
  exact_text: "PASS"
  return_type: "PASS"
  repeat_read: "PASS"
  argument_rejection: "PASS"
  cleanup: "PASS"
  passed: 8
  total: 8
  elapsed_ms: 228.9
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.get_text 的公开合同和 Runtime 文本读取路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.get_text"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.get_text"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.get_text_element", "ActionService._read_win_value"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_read_element", "_control_value_text"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "get_text(self) -> str"
    public_parameters: []
    public_timeout_parameter: false
    internal_timeout_seconds: 5
    primary_text_source: "UIA Name"
    empty_name_fallback: "control value"
    return_type: "str"
persistent_script:
  path: "win32/test_win32_get_text.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "1012a8912fb1d7e0599ec3883287427b5ee2af3025326cf94e1d581ee68376f8"
  command: 'uv run .\win32\test_win32_get_text.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场标题"
  expected_live_text: "用户信息表单"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  test_nature: "read-only"
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 str"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 8.5
  element_prepare:
    status: "PASS"
    detail: "已由元素库名称获取标题 Runtime 元素"
    elapsed_ms: 178.3
  exact_text:
    status: "PASS"
    call: "element.get_text()"
    expected: "用户信息表单"
    actual: "用户信息表单"
    detail: "get_text() 返回实时 UIA 文本，而不是元素库名称"
    elapsed_ms: 5.9
  return_type:
    status: "PASS"
    expected: "str"
    actual: "str"
    elapsed_ms: 0.0
  repeat_read:
    status: "PASS"
    expected: ["用户信息表单", "用户信息表单"]
    actual: ["用户信息表单", "用户信息表单"]
    detail: "连续两次读取结果稳定"
    elapsed_ms: 13.4
  argument_rejection:
    status: "PASS"
    cases: ["多余位置参数", "timeout 关键字"]
    expected_error: "TypeError"
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 21.0
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
  target_control_modified: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_get_text.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_text.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，通过元素库名称
`win32靶场标题` 获取靶场标题元素，并读取其实时 UIA 文本。测试只读；结束时恢复原前台
窗口、关闭借用的 Package，并保持 Win32 靶场运行。

## API 参数

```python
get_text() -> str
```

- `get_text()` 没有公开参数；多余位置参数和 `timeout` 关键字均由 Python 抛出
  `TypeError`。
- 公开返回值固定为 `str`，底层返回空值时会归一化为空字符串。
- 高层 API 没有公开 `timeout` 参数，底层读取超时固定为 5 秒。
- Runtime 对真实 Win32 UIA 元素优先读取 UIA `Name`；`Name` 为空时回退到控件值。
- 元素库名称用于选择元素，不是 `get_text()` 的返回内容。本次元素库名称为
  `win32靶场标题`，实时 UIA 文本为 `用户信息表单`。

## 最小实现链

```text
Win32Element.get_text()
  -> WinElement.get_text(timeout=5s)
  -> Session._run_win_value("element.get_text", ...)
  -> ActionService.get_text_element(...)
  -> ActionService._read_win_value(..., op="get_text")
  -> Runtime Worker handle_read_element(...)
  -> UIA Name，空时回退到控件值
  -> SDK 将结果归一化为 str
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.get_text)` | 无公开参数，返回标注为 `str` | `PASS` |
| 当前元素库 | `uiautoma.current()` | 当前 Package 是指定测试库 | `PASS` |
| 元素准备 | `win32靶场标题` | 返回与元素库记录绑定的 Runtime `Win32Element` | `PASS` |
| 实时文本 | `element.get_text()` | 精确返回 `用户信息表单` | `PASS` |
| 返回类型 | 首次读取结果 | 类型为 `str` | `PASS` |
| 重复读取 | 连续调用两次 | 两次都返回 `用户信息表单` | `PASS` |
| 参数数量 | 位置参数、`timeout=1` | 均抛出 `TypeError` | `PASS` |
| 资源清理 | 焦点和 Package | 焦点恢复、连接关闭、靶场保持运行且未修改 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_get_text.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 元素库名称：`win32靶场标题`
- 预期及实际实时文本：`用户信息表单`
- API 合同、精确文本、返回类型、重复读取和参数限制：全部通过
- 总状态：`PASS`
- 通过数：`8/8`
- 总耗时：`228.9ms`
- 原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行且未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- UIA `Name` 为空时的控件值回退路径；指定标题元素的 `Name` 非空，本轮未制造额外夹具。
- 动态修改标题后的刷新行为；本轮只验证稳定的实时标题读取。
- 用户自定义读取超时；公开 `get_text()` 不提供该参数。

