# `uiautoma.win32.Win32Element.clipboard_input()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.clipboard_input"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  default_parameters: "PASS"
  all_positional_parameters: "PASS"
  overwrite_and_append: "PASS"
  unicode_text: "PASS"
  focus_timeout: "PASS"
  send_key_delay: "PASS"
  click_before_input: "PASS"
  fixed_anchors: "PASS"
  random_anchor: "PASS"
  tuple_anchor: "PASS"
  mapping_anchor: "PASS"
  text_conversion: "PASS"
  delay_after: "PASS"
  millisecond_boundaries: "PASS"
  invalid_anchor: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 20
  total: 20
  elapsed_ms: 10973.6
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "Win32Element.clipboard_input 的参数规范化、输入动作、剪贴板保存与恢复路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.clipboard_input", "Win32Element._finish"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["anchor_to_pt", "_anchor_parts"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["RawWinElement.type_text"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/desktop/text_actions.py"
      symbols: ["TextBackend.type_text", "clipboard_type_text", "_send_key_wait_time"]
      fingerprint: "2f71f1d2c2447b8959d4f54cfb1fee82006d646e"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.type_text_element"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "clipboard_input(self, text: str, append: bool = False, focus_timeout: int = 1000, delay_after: float = 1, send_key_delay: int = 50, click_before_input: bool = True, anchor: object | None = None) -> None"
    parameters_are_positional_or_keyword: true
    return_value: null
    action_result_property: "last_result"
    input_mode: "clipboard"
    restore_clipboard: true
    default_anchor: "middleCenter"
    fixed_anchor_count: 9
    other_anchor_forms: ["random", "tuple/list", "mapping"]
    invalid_parameter_error: "InvalidParamsError"
persistent_script:
  path: "win32/test_win32_clipboard_input.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "7565cc5dcd95826f254ab5c2623e02a001badf83dca826bf678f56c0b9dbc7bc"
  command: 'uv run .\win32\test_win32_clipboard_input.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  physical_element_rect: [6352, 692, 645, 45]
  original_element_value: "123123"
  original_mouse_position: [4403, 1615]
  original_clipboard_format: "CF_UNICODETEXT"
  original_clipboard_text_recorded: false
  manual_motion_disabled_during_test: true
observations:
  api_contract:
    status: "PASS"
    detail: "七个公开参数、默认值和位置/关键字调用规则符合合同"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致，已借用 Package"
    elapsed_ms: 7.4
  target_element:
    status: "PASS"
    detail: "已定位输入框并保存可恢复的 Unicode 剪贴板文本"
    elapsed_ms: 130.2
  default_parameters:
    status: "PASS"
    call: 'element.clipboard_input("Clipboard_Default_01")'
    returned: null
    actual_value: "Clipboard_Default_01"
    strategy: "win_type_text"
    clicked_point: [6674, 714]
    clipboard_restored: true
    elapsed_ms: 2645.3
  all_positional_parameters:
    status: "PASS"
    call: 'element.clipboard_input("Clipboard_All_02", False, 0, 0, 0, True, "middleCenter")'
    actual_value: "Clipboard_All_02"
    strategy: "win_type_text"
    clipboard_restored: true
    elapsed_ms: 245.1
  overwrite_and_append:
    status: "PASS"
    values: [false, true]
    final_value: "Clipboard_Base_APPEND"
    clipboard_restored_after_each_call: true
    elapsed_ms: 252.3
  unicode_text:
    status: "PASS"
    value: "中文_Clipboard_{}[]_✓"
    clipboard_restored: true
    elapsed_ms: 141.7
  focus_timeout:
    status: "PASS"
    values_ms: [0, 200]
    observed_ms: [232.8, 434.9]
    clipboard_restored_after_each_call: true
    elapsed_ms: 688.1
  send_key_delay:
    status: "PASS"
    values_ms: [0, 150]
    observed_ms: [131.5, 321.2]
    clipboard_restored_after_each_call: true
    elapsed_ms: 470.8
  click_before_input:
    status: "PASS"
    values: [true, false]
    enabled_clicked_point_present: true
    disabled_clicked_point_absent: true
  fixed_anchors:
    status: "PASS"
    values: ["topLeft", "topCenter", "topRight", "middleLeft", "middleCenter", "middleRight", "bottomLeft", "bottomCenter", "bottomRight"]
    clicked_points_matched_physical_bounds: true
    clipboard_restored_after_each_call: true
    elapsed_ms: 3487.0
  random_anchor:
    status: "PASS"
    clicked_point: [6752, 716]
    point_inside_element: true
    elapsed_ms: 308.1
  tuple_anchor:
    status: "PASS"
    value: ["middleCenter", 10, 4]
    clicked_point: [6684, 718]
    elapsed_ms: 250.9
  mapping_anchor:
    status: "PASS"
    value: {anchor: "middleCenter", offset_x: -10, offset_y: -4}
    clicked_point: [6664, 710]
    elapsed_ms: 251.4
  text_conversion:
    status: "PASS"
    input: 20260906
    actual_value: "20260906"
    elapsed_ms: 149.0
  delay_after:
    status: "PASS"
    values: [null, 0.2, "default 1"]
    observed_none_ms: 136.2
    observed_0_2_ms: 336.7
    elapsed_ms: 490.4
  millisecond_boundaries:
    status: "PASS"
    negative_values_normalized_to_zero: true
    non_integer_error: "ValueError"
    clipboard_restored: true
    elapsed_ms: 248.6
  invalid_anchor:
    status: "PASS"
    values: ["center", 123]
    expected_error: "InvalidParamsError"
    clipboard_unchanged: true
    elapsed_ms: 0.1
  invalid_delay:
    status: "PASS"
    values: [-1, "bad"]
    expected_error: "InvalidParamsError"
    input_completed_before_error: true
    clipboard_restored_after_each_call: true
    elapsed_ms: 295.4
cleanup:
  status: "PASS"
  elapsed_ms: 523.6
  element_value_restored: true
  clipboard_text_restored: true
  manual_motion_disabled: true
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_clipboard_input.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_clipboard_input.py
```

运行前需要在剪贴板中放入普通 Unicode 文本。脚本借用 UIAutoma 当前启用的
`D:\code\元素库\260902_win元素`，获取已启动的 Win32 靶场窗口，并对
`win32靶场输入框` 执行真实剪贴板输入。每次 API 调用后均验证运行前的 Unicode
剪贴板文本已经恢复；结束时恢复输入框原值、剪贴板、鼠标和原前台窗口，关闭借用的
Package，并保持靶场运行。

## API 参数

```python
clipboard_input(
    text: str,
    append: bool = False,
    focus_timeout: int = 1000,
    delay_after: float = 1,
    send_key_delay: int = 50,
    click_before_input: bool = True,
    anchor: object | None = None,
) -> None
```

- 七个参数都是位置或关键字参数，调用成功返回 `None`；动作详情保存在 `last_result`。
- `text` 在 SDK 边界调用 `str()`；实测整数和 Unicode 文本均正确输入。
- `append=False` 先发送 `Ctrl+A` 再粘贴；`append=True` 直接在当前插入点粘贴。
- `focus_timeout` 是输入前等待毫秒数，负数被 SDK 归一化为 `0`。
- `send_key_delay` 控制清空及粘贴快捷键后的节奏；Runtime 对等待设置最小值。
- `delay_after` 是输入完成后的等待秒数；`None` 或 `0` 不等待。当前实现先完成输入并
  保存 `last_result`，再校验及执行动作后延时，因此非法延时会在输入完成后抛错。
- `click_before_input=True` 会先按锚点点击，`False` 仅通过自动化接口聚焦。
- `anchor=None` 默认使用 `middleCenter`；另支持九宫格固定位置、`random`、三元组及
  包含锚点和偏移量的字典。
- SDK 固定使用 `mode="clipboard"` 和 `restore_clipboard=True`。当前 Runtime 保存和
  恢复的是 `CF_UNICODETEXT`，本轮不验证非文本剪贴板格式的完整保留。

## 最小实现链

```text
Win32Element.clipboard_input(...)
  -> anchor_to_pt(anchor)
  -> RawWinElement.type_text(
       mode="clipboard",
       restore_clipboard=True,
       clear=not append,
       click_before_input=...,
       focus_delay_ms=...,
       send_key_delay_ms=...)
  -> Runtime action.type_text_element
     -> 定位并按需点击或聚焦元素
     -> TextBackend.type_text(mode="clipboard")
        -> clipboard_type_text(...)
           -> 保存 CF_UNICODETEXT
           -> 将输入文本写入剪贴板
           -> append=False 时发送 Ctrl+A
           -> 发送 Ctrl+V
           -> 恢复保存的 CF_UNICODETEXT
     -> ActionResult(strategy="win_type_text", clicked_point=...)
  -> Win32Element._finish(result, delay_after)
     -> 保存 last_result
     -> 抛出动作错误（如有）
     -> 执行动作后延时
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | 公开签名 | 七个参数、默认值及调用种类一致 | `PASS` |
| 默认调用 | 仅传 `text` | 覆盖输入、中心点击、等待生效、剪贴板恢复 | `PASS` |
| 全位置参数 | 七项位置参数 | 全部参数生效并返回 `None` | `PASS` |
| 覆盖与追加 | `append=False/True` | 先覆盖，再得到 `Clipboard_Base_APPEND` | `PASS` |
| Unicode | 中文及符号 | 输入值保持一致 | `PASS` |
| 聚焦等待 | `focus_timeout=0/200` | 产生可测等待差异 | `PASS` |
| 快捷键等待 | `send_key_delay=0/150` | 产生可测等待差异 | `PASS` |
| 输入前点击 | `True/False` | 点击点存在/不存在与参数一致 | `PASS` |
| 固定锚点 | 九宫格九项 | 点位与物理边界一致 | `PASS` |
| 随机锚点 | `random` | 点位位于元素内 | `PASS` |
| 偏移锚点 | 三元组、字典 | X/Y 偏移生效 | `PASS` |
| 文本转换 | 整数 | 按字符串输入 | `PASS` |
| 动作后延时 | `None/0.2/default 1` | 不等待与有限等待符合合同 | `PASS` |
| 毫秒参数边界 | 负数、非整数 | 负数按零处理，非整数抛 `ValueError` | `PASS` |
| 非法锚点 | `center`、整数 | 抛出 `InvalidParamsError` | `PASS` |
| 非法延时 | `-1`、`"bad"` | 输入后抛错且剪贴板恢复 | `PASS` |
| 剪贴板保护 | 每次 API 调用 | 原 Unicode 文本均已恢复 | `PASS` |
| 资源清理 | 恢复测试前状态 | 输入框、剪贴板、鼠标、焦点及 Package 均恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_clipboard_input.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 物理边界：`(6352, 692, 645, 45)`
- 默认策略：`win_type_text`
- 默认点击点：`(6674, 714)`
- 剪贴板：运行前存在 `CF_UNICODETEXT`；20 项测试期间逐次校验并在结束时恢复
- 总状态：`PASS`
- 通过数：`20/20`
- 总耗时：`10973.6ms`
- 输入框原值：已恢复为 `123123`
- 鼠标与原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 非文本剪贴板格式的完整保存与恢复；当前 Runtime 只显式读写 `CF_UNICODETEXT`。
- 剪贴板被其他进程并发占用或测试期间被外部程序改写的竞争场景。
- 密码框、富文本控件及其他控件类型；本轮使用 Win32 靶场普通输入框。
- 人工轨迹开启状态；脚本在真实输入前显式关闭人工轨迹。
