# `uiautoma.win32.Win32Element.click()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.click"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  default_parameters: "PASS"
  all_positional_parameters: "PASS"
  canonical_buttons: "PASS"
  button_aliases: "PASS"
  modifier_keys: "PASS"
  simulative_modes: "PASS"
  move_mouse_modes: "PASS"
  fixed_anchors: "PASS"
  random_anchor: "PASS"
  tuple_anchor: "PASS"
  mapping_anchor: "PASS"
  delay_after: "PASS"
  invalid_button: "PASS"
  invalid_keys: "PASS"
  invalid_anchor: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 20
  total: 20
  elapsed_ms: 2823.5
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.click 的参数规范化、动作模式、锚点和 Runtime 鼠标路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.click", "Win32Element._finish", "_normalize_button", "_normalize_keys"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["anchor_to_pt", "_anchor_parts"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/win32/_motion.py"
      symbols: ["click_anchor", "default_bool", "disable"]
      fingerprint: "5131d0d264945b297636be763183436a02d893ac"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService._run_pointer_action", "ActionService._perform_mouse"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
    - path: "runtime/desktop/mouse_actions.py"
      symbols: ["point_in_rect_xywh"]
      fingerprint: "d5804f849b14016faf47f77acb09491ccdb38adc"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: 'click(self, button: str = "left", simulative: bool = True, keys: str = "none", delay_after: float = 1, move_mouse: bool | None = None, anchor: object | None = None) -> None'
    parameters_are_positional_or_keyword: true
    return_value: null
    action_result_property: "last_result"
    canonical_buttons: ["left", "right", "middle"]
    button_aliases:
      primary: "left"
      secondary: "right"
      mid: "middle"
    modifier_keys: ["ctrl", "shift", "alt", "win"]
    default_anchor: "middleCenter"
    fixed_anchor_count: 9
    other_anchor_forms: ["random", "tuple/list", "mapping"]
    invalid_parameter_error: "InvalidParamsError"
persistent_script:
  path: "win32/test_win32_click.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "23d70f88adf7bcb955b8fc87ab6e70bf3f4d70de5c8704796055b00e5c6cba0f"
  command: 'uv run .\win32\test_win32_click.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  physical_element_rect: [2841, 1185, 430, 30]
  original_mouse_position: [2708, 1710]
  manual_motion_disabled_during_test: true
observations:
  api_contract:
    status: "PASS"
    detail: "六个公开参数、默认值和位置/关键字调用规则符合合同"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致，已借用 Package"
    elapsed_ms: 6.5
  target_element:
    status: "PASS"
    detail: "已定位靶场输入框，物理屏幕边界有效"
    elapsed_ms: 276.4
  default_parameters:
    status: "PASS"
    call: "element.click()"
    returned: null
    strategy: "win"
    clicked_point: [3056, 1200]
    elapsed_ms: 1324.9
  all_positional_parameters:
    status: "PASS"
    call: 'element.click("left", False, "none", 0, False, "middleCenter")'
    returned: null
    strategy: "win"
    actual_path: "control action unavailable; mouse fallback succeeded"
    elapsed_ms: 30.0
  canonical_buttons:
    status: "PASS"
    values: ["left", "right", "middle"]
    elapsed_ms: 137.5
  button_aliases:
    status: "PASS"
    values: ["primary", "secondary", "mid"]
    elapsed_ms: 87.8
  modifier_keys:
    status: "PASS"
    values: [null, "", "none", "ctrl", "control+shift"]
    excluded_live_values: ["alt", "win"]
    elapsed_ms: 141.7
  simulative_modes:
    status: "PASS"
    values: [true, false]
    simulated_strategy: "win"
    control_preferred_strategy: "win"
    control_preferred_fell_back_to_mouse: true
    elapsed_ms: 55.2
  move_mouse_modes:
    status: "PASS"
    values: [false, true]
    elapsed_ms: 134.7
  fixed_anchors:
    status: "PASS"
    values: ["topLeft", "topCenter", "topRight", "middleLeft", "middleCenter", "middleRight", "bottomLeft", "bottomCenter", "bottomRight"]
    clicked_points_matched_element_bounds: true
    elapsed_ms: 242.1
  random_anchor:
    status: "PASS"
    clicked_point: [3189, 1203]
    point_inside_element: true
    elapsed_ms: 25.9
  tuple_anchor:
    status: "PASS"
    value: ["middleCenter", 10, 4]
    clicked_point: [3066, 1204]
    elapsed_ms: 26.8
  mapping_anchor:
    status: "PASS"
    value: {anchor: "middleCenter", offset_x: -10, offset_y: -4}
    clicked_point: [3046, 1196]
    elapsed_ms: 25.6
  delay_after:
    status: "PASS"
    values: [null, 0, 0.2, "default 1"]
    elapsed_ms: 254.7
  invalid_button:
    status: "PASS"
    value: "back"
    expected_error: "InvalidParamsError"
  invalid_keys:
    status: "PASS"
    value: "ctrl+meta"
    expected_error: "InvalidParamsError"
  invalid_anchor:
    status: "PASS"
    values: ["center", 123]
    expected_error: "InvalidParamsError"
  invalid_delay:
    status: "PASS"
    values: [-1, "bad"]
    expected_error: "InvalidParamsError"
    note: "click action completes before delay_after validation"
    elapsed_ms: 53.2
cleanup:
  status: "PASS"
  elapsed_ms: 0.2
  manual_motion_disabled: true
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
  target_form_content_modified: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_click.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_click.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取已经启动的
Win32 靶场窗口，并使用 `win32靶场输入框` 执行真实点击。脚本不输入或删除表单内容；
结束时关闭人工轨迹、恢复鼠标和原前台窗口、关闭借用的 Package，并保持靶场运行。

## API 参数

```python
click(
    button: str = "left",
    simulative: bool = True,
    keys: str = "none",
    delay_after: float = 1,
    move_mouse: bool | None = None,
    anchor: object | None = None,
) -> None
```

- 六个参数都是位置或关键字参数，调用成功返回 `None`；动作详情保存在元素对象的
  `last_result` 中。
- `button` 的正式值为 `left`、`right`、`middle`；`primary`、`secondary`、`mid`
  分别是对应别名。
- `simulative=True` 直接使用鼠标动作；`False` 优先尝试控件动作，控件动作不可用时
  允许回退到可诊断的鼠标动作。本次输入框实际走了 `win` 鼠标回退。
- `keys` 支持 `none`、`ctrl`、`shift`、`alt`、`win` 及组合；`None` 和空字符串也表示
  无修饰键。
- `delay_after` 默认等待 1 秒；`None` 或 `0` 不等待，负数和非数字值抛出
  `InvalidParamsError`。当前实现先执行点击，再校验并执行动作后延时。
- `move_mouse=None` 读取人工轨迹配置，默认等效为 `True`；显式 `True` 或 `False` 分别
  表示可见移动或瞬移到点击点。
- `anchor=None` 默认使用 `middleCenter`。固定锚点包括九宫格的九个位置，另支持
  `random`、`(anchor, offset_x, offset_y)` 以及包含 `anchor`、`offset_x`、
  `offset_y` 的字典。

## 最小实现链

```text
Win32Element.click(...)
  -> _motion.click_anchor(anchor)
  -> anchor_to_pt(...)
  -> _normalize_button(button)
  -> _normalize_keys(keys)
  -> RawWinElement.click(...)
  -> Runtime action.click_element
     -> ActionService._run_pointer_action(..., action="click")
        simulative=False 且参数适用：优先尝试控件 Invoke
        否则或 Invoke 不可用：
          -> 解析实时元素矩形
          -> point_in_rect_xywh(rect, pt)
          -> _perform_mouse(...)
          -> ActionResult(clicked_point, strategy, diagnostics)
  -> Win32Element._finish(result, delay_after)
     -> 保存 last_result
     -> 抛出动作错误（如有）
     -> 执行动作后延时
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.click)` | 六个参数、默认值、调用种类和返回合同一致 | `PASS` |
| 默认调用 | `element.click()` | 返回 `None`，中心点击，默认约 1 秒延时 | `PASS` |
| 全位置参数 | 六项参数全部按位置传入 | `simulative=False` 成功，允许鼠标回退 | `PASS` |
| 鼠标键 | `left/right/middle` | 三种真实点击均成功 | `PASS` |
| 鼠标键别名 | `primary/secondary/mid` | 全部规范化并成功 | `PASS` |
| 修饰键 | 无键、`ctrl`、`control+shift` | 组合键点击成功，按键最终释放 | `PASS` |
| 动作模式 | `simulative=True/False` | 模拟点击和控件优先路径均成功 | `PASS` |
| 鼠标移动 | `move_mouse=False/True` | 两种模式均成功且点位在元素内 | `PASS` |
| 固定锚点 | 九宫格全部九项 | `clicked_point` 与对应物理边界位置一致 | `PASS` |
| 随机锚点 | `random` | 随机点位于元素内 | `PASS` |
| 三元组锚点 | `("middleCenter", 10, 4)` | 点击点包含指定偏移 | `PASS` |
| 字典锚点 | 中心点和 `-10/-4` 偏移 | 点击点包含指定偏移 | `PASS` |
| 动作后延时 | `None/0/0.2/default 1` | 不等待与有限等待均符合合同 | `PASS` |
| 非法鼠标键 | `back` | 抛出 `InvalidParamsError` | `PASS` |
| 非法修饰键 | `ctrl+meta` | 抛出 `InvalidParamsError` | `PASS` |
| 非法锚点 | `center`、整数 | 抛出 `InvalidParamsError` | `PASS` |
| 非法延时 | `-1`、`"bad"` | 点击后抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 恢复本次测试状态 | 鼠标和焦点恢复，Package 关闭，靶场保持运行 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_click.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 物理边界：`(2841, 1185, 430, 30)`
- 默认点击点：`(3056, 1200)`
- `simulative=False`：控件动作不可用后以 `win` 鼠标动作成功回退
- 总状态：`PASS`
- 通过数：`20/20`
- 总耗时：`2823.5ms`
- 人工轨迹：已关闭
- 鼠标与原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行，表单内容未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- `Alt` 和 Windows 键的真实组合点击；为避免触发系统级快捷键，本轮未执行。
- `simulative=False` 的纯控件 Invoke 成功分支；当前输入框不支持该动作，本轮验证的是
  合同允许的可诊断鼠标回退。
- 开启人工轨迹后的随机默认锚点；本脚本在真实点击前显式关闭人工轨迹。
- 点击导致的业务内容变化；测试目标是无预置内容的输入框，脚本不输入或删除文本。

