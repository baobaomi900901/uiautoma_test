# `uiautoma.win32.Win32Element.set_value()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.set_value"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  element_prepare: "PASS"
  plain_string: "PASS"
  unicode_symbols: "PASS"
  keyword_value: "PASS"
  integer_conversion: "PASS"
  empty_string: "PASS"
  unsupported_control: "PASS"
  argument_count: "PASS"
  cleanup: "PASS"
  passed: 11
  total: 11
  elapsed_ms: 3397.6
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.set_value 的公开合同、动作结果和 Runtime 设置值路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.set_value", "Win32Element._finish"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.type_text", "Session._run_win_action"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "sdk/src/uiautoma/_core/models.py"
      symbols: ["ActionResult"]
      fingerprint: "d0d5b2c074943a825f1a9514ff333a62666acf10"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.type_text_element", "ActionService._set_win_value"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_set_element_value", "_set_control_value_text"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "set_value(self, value: str) -> None"
    value_required: true
    value_positional_or_keyword: true
    value_string_conversion: "str(value)"
    behavior: "replace complete value"
    internal_mode: "automation"
    internal_clear: true
    internal_click_before_input: false
    internal_timeout_seconds: 10
    public_timeout_parameter: false
    public_delay_after_parameter: false
    return_value: null
    action_result_property: "last_result"
    action_error: "ActionError"
persistent_script:
  path: "win32/test_win32_set_value.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "3d506559b65354dedb0f3678a8245b5c36e5c905dfac265d5850a6c01e6e7564"
  command: 'uv run .\win32\test_win32_set_value.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  unsupported_element: "win32靶场保存按钮"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  initial_value: "123123"
  value_observation: "Win32Element.get_value()"
  action_observation: "Win32Element.last_result"
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名为 set_value(value: str) -> None"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 7.1
  element_prepare:
    status: "PASS"
    detail: "已获取输入框、保存按钮并记录输入框原值"
    elapsed_ms: 245.8
  plain_string:
    status: "PASS"
    call: 'element.set_value("UIAutoma_SetValue_Alpha_123")'
    expected_value: "UIAutoma_SetValue_Alpha_123"
    detail: "位置参数已覆盖写入普通字符串"
    elapsed_ms: 529.9
  unicode_symbols:
    status: "PASS"
    call: 'element.set_value("中文_SetValue_Ω_!@#")'
    expected_value: "中文_SetValue_Ω_!@#"
    detail: "中文、希腊字母和符号均被完整写入"
    elapsed_ms: 516.1
  keyword_value:
    status: "PASS"
    call: 'element.set_value(value="keyword_value_260907")'
    expected_value: "keyword_value_260907"
    detail: "value 关键字参数已覆盖写入目标值"
    elapsed_ms: 517.9
  integer_conversion:
    status: "PASS"
    call: "element.set_value(20260907)"
    expected_value: "20260907"
    detail: "整数 value 已通过 str() 转换后写入"
    elapsed_ms: 517.0
  empty_string:
    status: "PASS"
    call: 'element.set_value("")'
    expected_value: ""
    detail: "空字符串已清空输入框完整值"
    elapsed_ms: 517.1
  successful_action_result:
    status: "PASS"
    strategy: "win_value_pattern"
    clicked_point: null
    result_ok: true
  unsupported_control:
    status: "PASS"
    target: "win32靶场保存按钮"
    expected_error: "ActionError"
    detail: "保存按钮不支持设置值，正确抛出 ActionError"
    elapsed_ms: 7.4
  argument_count:
    status: "PASS"
    cases: ["缺少 value", "多余位置参数"]
    expected_error: "TypeError"
    action_result_unchanged: true
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 537.4
  initial_value_restored: "123123"
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_set_value.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_set_value.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，在
`win32靶场输入框` 上执行真实值覆盖，并以 `get_value()` 校验界面实际值。每次成功调用
还会验证 `last_result.ok`、动作策略以及没有输入前点击坐标。结束时恢复输入框原值
`123123` 和原前台窗口、关闭借用的 Package，并保持靶场运行。

## API 参数

```python
set_value(value: str) -> None
```

- `value` 是必填的位置或关键字参数；缺少参数或传入多余参数会由 Python 抛出
  `TypeError`。
- 公开注解为 `str`，当前实现会执行 `str(value)`，因此本次也验证了整数
  `20260907` 被写为字符串 `"20260907"`。
- `set_value()` 覆盖元素完整值，不追加内容；空字符串会清空当前值。
- 成功返回 `None`，动作结果保存在 `last_result`。
- 公开 API 不提供 `timeout` 或 `delay_after`。底层固定使用 automation 模式、
  `clear=True`、`click_before_input=False` 和 10 秒动作超时。
- Runtime 优先使用 UIA ValuePattern；如果控件提供原生窗口句柄，也可使用
  `WM_SETTEXT` 兜底。本次输入框的公开动作结果策略为 `win_value_pattern`。
- Runtime 动作失败会在 `_finish()` 中通过 `last_result.raise_for_error()` 抛出
  `ActionError`。

## 最小实现链

```text
Win32Element.set_value(value)
  -> str(value)
  -> RawWinElement.type_text(
       mode="automation",
       clear=True,
       click_before_input=False,
       timeout=10s,
     )
  -> Runtime action.type_text_element
  -> ActionService.type_text_element(..., mode="automation")
  -> ActionService._set_win_value(...)
  -> Runtime Worker handle_set_element_value(...)
  -> UIA ValuePattern.SetValue / WM_SETTEXT fallback
  -> ActionResult
  -> Win32Element._finish(result, 0)
     -> 保存 last_result
     -> 动作失败时抛出 ActionError
     -> 不增加动作后等待
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.set_value)` | 必填 `value: str` 和返回标注一致 | `PASS` |
| 当前元素库 | `uiautoma.current()` | 当前 Package 是指定测试库 | `PASS` |
| 元素准备 | 输入框与保存按钮 | 两个元素均可定位并记录输入框原值 | `PASS` |
| 普通字符串 | `"UIAutoma_SetValue_Alpha_123"` | 实际值完全一致，动作结果成功 | `PASS` |
| 中文与符号 | `"中文_SetValue_Ω_!@#"` | Unicode 与符号完整保留 | `PASS` |
| 关键字调用 | `value="keyword_value_260907"` | 关键字参数写入成功 | `PASS` |
| 整数转换 | `20260907` | 通过 `str()` 转为 `"20260907"` | `PASS` |
| 空字符串 | `""` | 输入框完整值被清空 | `PASS` |
| 不支持控件 | 保存按钮 | 抛出 `ActionError`，失败结果保留在 `last_result` | `PASS` |
| 参数数量 | 缺少参数、两个位置参数 | 动作前抛出 `TypeError` | `PASS` |
| 状态与资源恢复 | 原值、焦点和 Package | 原值与焦点恢复，连接关闭，靶场保持运行 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_set_value.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 不支持控件：`win32靶场保存按钮`
- 输入框原始值：`123123`
- 字符串覆盖、Unicode、关键字调用、整数转换和空字符串清空：全部通过
- 不支持设置值的保存按钮：正确抛出 `ActionError`
- 参数数量限制：正确抛出 `TypeError`
- 总状态：`PASS`
- 通过数：`11/11`
- 总耗时：`3397.6ms`
- 输入框状态：已恢复为 `123123`
- 原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- `win32靶场备注文本域` 等其他可编辑控件；本轮只验证单行输入框。
- 密码输入框的值读取限制；本轮目标允许通过 `get_value()` 核对实际值。
- 主动制造只读 ValuePattern 控件；使用保存按钮覆盖了不支持设置值的失败路径。
- 强制验证底层 `WM_SETTEXT` 兜底；本次真实目标使用 `win_value_pattern`。
- 用户自定义动作超时或动作后等待；公开 `set_value()` 没有这些参数。

