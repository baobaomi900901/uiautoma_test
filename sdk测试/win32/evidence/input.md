# `uiautoma.win32.Win32Element.input()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.input"
lifecycle: "READY_FOR_LIVE"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  default_parameters: "PASS"
  all_positional_parameters: "PASS"
  input_modes: "PASS"
  overwrite_and_append: "FAIL"
  hotkey_input: "PASS"
  send_key_delay: "PASS"
  focus_timeout: "PASS"
  click_before_input: "PASS"
  fixed_anchors: "PASS"
  random_anchor: "PASS"
  tuple_anchor: "PASS"
  mapping_anchor: "PASS"
  force_ime_eng: "PASS"
  text_conversion: "PASS"
  delay_after: "PASS"
  millisecond_boundaries: "PASS"
  invalid_anchor: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 21
  failed: 1
  total: 22
  elapsed_ms: 17339.5
  full_log_provided: true
  minimal_reproduction_confirmed: true
  verified: false
  exit_code: 1
  blocking_issue:
    number: 45
    url: "https://github.com/uiautoma/desktop/issues/45"
    title: "Win32Element.input() 自动化追加因 wintypes.DWORD_PTR 缺失而失败"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.input 的参数转换、输入模式、Runtime 文本动作和 Windows 原生追加路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.input", "Win32Element._finish"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.type_text"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.type_text_element", "ActionService._set_win_value", "ActionService._insert_win_text"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
    - path: "runtime/bridge/worker.py"
      symbols: ["_send_wm_settext", "_send_em_replacesel", "_send_message_timeout", "_insert_control_text"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
    - path: "runtime/desktop/text_actions.py"
      symbols: ["TextController.type_text", "keyboard_type_text", "_normalize_send_keys_expression"]
      fingerprint: "2f71f1d2c2447b8959d4f54cfb1fee82006d646e"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "input(self, text: str, simulative: bool = True, append: bool = False, contains_hotkey: bool = False, send_key_delay: int = 50, focus_timeout: int = 1000, delay_after: float = 1, click_before_input: bool = True, anchor: object | None = None, force_ime_ENG: bool = False) -> None"
    parameters_are_positional_or_keyword: true
    return_value: null
    action_result_property: "last_result"
    simulative_true_mode: "keyboard"
    simulative_false_mode: "automation"
    contains_hotkey_forces_keyboard_mode: true
    append_false: "clear then input"
    append_true: "append through selected input mode"
    invalid_anchor_error: "InvalidParamsError"
    invalid_integer_conversion_error: "ValueError"
open_defects:
  - issue: 45
    affected: "simulative=False and append=True"
    expected: "automation append succeeds"
    actual: "ActionError: automation_insert_failed"
    root_cause: "runtime.bridge.worker references ctypes.wintypes.DWORD_PTR, which is absent in CPython 3.13.14"
    related_unverified_paths: ["_send_wm_settext", "_send_message_timeout"]
    product_source_modified: false
persistent_script:
  path: "win32/test_win32_input.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "9eaa253de6ac09ac1357d9239f19c5f2f35f45fdbcad745d38f51c3047b99b00"
  command: 'uv run .\win32\test_win32_input.py'
minimal_reproduction:
  path: "repro_input_append.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "5f8f7d72955ddd095c003c51c14a43febcfce9ea2872766e8d1934ae0cf2254f"
  command: 'uv run .\repro_input_append.py'
  reproduced: true
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  physical_element_rect: [2841, 1185, 430, 30]
  original_value: ""
  original_mouse_position: [2764, 1806]
observations:
  api_contract:
    status: "PASS"
    detail: "十个公开参数、默认值和位置/关键字调用规则符合合同"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    elapsed_ms: 6.6
  target_element:
    status: "PASS"
    elapsed_ms: 128.3
  default_parameters:
    status: "PASS"
    value: "UIAutoma_Default_01"
    strategy: "win_type_text"
    clicked_point: [3056, 1200]
    elapsed_ms: 3694.6
  all_positional_parameters:
    status: "PASS"
    value: "UIAutoma_All_02"
    strategy: "win_type_text"
    elapsed_ms: 381.1
  input_modes:
    status: "PASS"
    keyboard_strategy: "win_type_text"
    automation_strategy: "win_value_pattern"
    elapsed_ms: 914.6
  overwrite_and_append:
    status: "FAIL"
    passed_substeps: ["automation overwrite", "keyboard append"]
    failed_substep: "automation append"
    call: 'element.input("_A", simulative=False, append=True, focus_timeout=0, delay_after=0, click_before_input=False)'
    actual_exception: "ActionError"
    trace: "automation_insert_failed"
    cause: "AttributeError: module 'ctypes.wintypes' has no attribute 'DWORD_PTR'"
    elapsed_ms: 659.7
  hotkey_input:
    status: "PASS"
    expression: "^aHotkey_Result_04"
    actual_value: "Hotkey_Result_04"
    strategy: "win_type_text"
    elapsed_ms: 856.8
  send_key_delay:
    status: "PASS"
    zero_ms_elapsed: 291.6
    thirty_ms_elapsed: 567.1
    elapsed_ms: 869.9
  focus_timeout:
    status: "PASS"
    zero_ms_elapsed: 291.7
    two_hundred_ms_elapsed: 491.2
    elapsed_ms: 794.2
  click_before_input:
    status: "PASS"
    true_clicked_point_present: true
    false_clicked_point_present: false
    elapsed_ms: 552.5
  fixed_anchors:
    status: "PASS"
    count: 9
    elapsed_ms: 3398.3
  random_anchor:
    status: "PASS"
    clicked_point: [3244, 1207]
    elapsed_ms: 355.4
  tuple_anchor:
    status: "PASS"
    clicked_point: [3066, 1204]
    elapsed_ms: 363.2
  mapping_anchor:
    status: "PASS"
    clicked_point: [3046, 1196]
    elapsed_ms: 369.6
  force_ime_eng:
    status: "PASS"
    switch_log: "已切换英文输入布局"
    restore_log: "已恢复输入布局"
    elapsed_ms: 354.6
  text_conversion:
    status: "PASS"
    input: 20260906
    actual_value: "20260906"
    elapsed_ms: 526.6
  delay_after:
    status: "PASS"
    values: [null, 0.2, "default 1"]
    elapsed_ms: 1234.8
  millisecond_boundaries:
    status: "PASS"
    negative_values_normalized_to_zero: true
    invalid_values_error: "ValueError"
    elapsed_ms: 334.1
  invalid_anchor:
    status: "PASS"
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  invalid_delay:
    status: "PASS"
    expected_error: "InvalidParamsError"
    input_completed_before_error: true
    elapsed_ms: 1028.4
cleanup:
  status: "PASS"
  elapsed_ms: 516.2
  original_value_restored: true
  restored_value: ""
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本与最小复现

完整测试：

```powershell
uv run .\win32\test_win32_input.py
```

最小复现：

```powershell
uv run .\repro_input_append.py
```

两者均借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，使用已经启动的
Win32 靶场及 `win32靶场输入框`。两份脚本都在结束时恢复输入框原值并关闭 Package。

## API 参数

```python
input(
    text: str,
    simulative: bool = True,
    append: bool = False,
    contains_hotkey: bool = False,
    send_key_delay: int = 50,
    focus_timeout: int = 1000,
    delay_after: float = 1,
    click_before_input: bool = True,
    anchor: object | None = None,
    force_ime_ENG: bool = False,
) -> None
```

- `text` 必填，当前实现通过 `str(text)` 转换后发送。
- `simulative=True` 使用键盘模式；`False` 使用自动化接口。`contains_hotkey=True`
  会强制键盘模式。
- `append=False` 覆盖原值；`True` 追加。键盘追加已通过，自动化追加受 Issue #45 阻塞。
- `send_key_delay` 和 `focus_timeout` 单位均为毫秒；负数按 0 处理，无法转换为整数的值在
  SDK 层抛出 `ValueError`。
- `delay_after` 单位为秒；非法值会在输入动作完成后抛出 `InvalidParamsError`。
- `click_before_input=False` 在键盘模式下尝试自动化聚焦，不产生输入前点击点。
- `anchor` 支持九宫格、`random`、三元组和字典偏移；非法值抛出
  `InvalidParamsError`。
- `force_ime_ENG=True` 尝试切换英文输入布局，并在输入结束后尽力恢复。

## 缺陷结论

自动化覆盖输入通过，策略为 `win_value_pattern`；自动化追加进入
`ActionService._insert_win_text()` 后调用 Bridge Worker 的原生 `EM_REPLACESEL` 路径。
该路径在构造 `SendMessageTimeoutW` 参数时访问不存在的 `wintypes.DWORD_PTR`，在真正
发送 Windows 消息前即失败：

```text
Win32Element.input(simulative=False, append=True)
  -> type_text_element(mode="automation", clear=False)
  -> _insert_win_text()
  -> _insert_control_text()
  -> _send_em_replacesel()
  -> wintypes.DWORD_PTR
  -> AttributeError
  -> ActionError: automation_insert_failed
```

当前 CPython 3.13.14 已独立确认 `hasattr(ctypes.wintypes, "DWORD_PTR") == False`。
同文件的 `_send_wm_settext()` 和 `_send_message_timeout()` 也引用该类型，属于尚未完成真实
验收的关联风险。现有 ActionService 单元测试使用 FakeFocuser，并未运行 Bridge Worker
的 Windows FFI 类型构造。

跟踪 Issue：[#45 Win32Element.input() 自动化追加因 wintypes.DWORD_PTR 缺失而失败](https://github.com/uiautoma/desktop/issues/45)

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| API 合同、当前元素库、目标准备 | `PASS` | 十个参数合同及真实元素有效 |
| 默认与全位置参数 | `PASS` | 返回 `None`，输入值及点位正确 |
| 键盘覆盖、自动化覆盖 | `PASS` | 策略分别为 `win_type_text`、`win_value_pattern` |
| 键盘追加 | `PASS` | 新文本追加到现有值 |
| 自动化追加 | `FAIL` | `wintypes.DWORD_PTR` 缺失，Issue #45 |
| 快捷键 | `PASS` | `Ctrl+A` 后输入值正确 |
| 逐键延时、聚焦等待 | `PASS` | 实测时间差符合参数 |
| 输入前点击 | `PASS` | True 有点位，False 无点位 |
| 九宫格、随机、三元组、字典锚点 | `PASS` | 输入值和物理点位正确 |
| 英文输入布局 | `PASS` | 切换与恢复诊断均存在 |
| 文本转换、延时及参数边界 | `PASS` | 与当前源码合同一致 |
| 资源清理 | `PASS` | 原值、鼠标、焦点和 Package 均恢复 |

## 最近一次真实验证

- 日期：2026-09-06
- 完整命令：`uv run .\win32\test_win32_input.py`
- 最小复现命令：`uv run .\repro_input_append.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 总状态：`FAIL`
- 通过数：`21/22`
- 失败数：`1/22`
- 总耗时：`17339.5ms`
- 最小复现：稳定得到 `automation_insert_failed` 与 `wintypes.DWORD_PTR` 错误
- 输入框：原值 `""` 已恢复
- 鼠标与原前台窗口：已恢复
- Package：已关闭
- 靶场程序：保持运行
- 退出码：`1`
- 生命周期：`READY_FOR_LIVE`
- 产品源码修改：无

## 重新验收条件

- Issue #45 修复后，最小复现输出 `BASE_APPEND` 且不抛出 `ActionError`。
- `test_win32_input.py` 的“覆盖与追加”场景通过。
- 完整测试达到 `22/22`，且输入框原值、鼠标、焦点和 Package 仍完成恢复。
- 检查 `_send_wm_settext()` 与 `_send_message_timeout()` 的相同类型引用。

## 明确排除

- `clipboard_input()`；它是独立公开 API，将单独测试。
- 对 `Alt`、Windows 键等系统级快捷键的真实输入。
- 非输入控件、密码框、多行编辑器、富文本和 ACC/Java/Helper DOM 元素。
- 自动化追加失败后的源码修复；本轮角色只记录测试和缺陷，不修改产品源码。

