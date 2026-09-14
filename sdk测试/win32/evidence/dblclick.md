# `uiautoma.win32.Win32Element.dblclick()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.dblclick"
alias: "uiautoma.win32.Win32Element.double_click"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  default_parameters: "PASS"
  all_positional_parameters: "PASS"
  simulative_modes: "PASS"
  move_mouse_modes: "PASS"
  fixed_anchors: "PASS"
  random_anchor: "PASS"
  tuple_anchor: "PASS"
  mapping_anchor: "PASS"
  delay_after: "PASS"
  public_alias: "PASS"
  invalid_anchor: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 16
  total: 16
  elapsed_ms: 5831.6
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.dblclick 的参数规范化、别名、锚点和 Runtime 双击路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.dblclick", "Win32Element.double_click", "Win32Element._finish"]
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
      symbols: ["point_in_rect_xywh", "MouseController.double_click"]
      fingerprint: "d5804f849b14016faf47f77acb09491ccdb38adc"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "dblclick(self, simulative: bool = True, delay_after: float = 1, move_mouse: bool | None = None, anchor: object | None = None) -> None"
    alias_signature: "double_click(self, simulative: bool = True, delay_after: float = 1, move_mouse: bool | None = None, anchor: object | None = None) -> None"
    parameters_are_positional_or_keyword: true
    return_value: null
    action_result_property: "last_result"
    button: "left"
    default_anchor: "middleCenter"
    fixed_anchor_count: 9
    other_anchor_forms: ["random", "tuple/list", "mapping"]
    invalid_parameter_error: "InvalidParamsError"
persistent_script:
  path: "win32/test_win32_dblclick.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "56dd71b3a575b6b876105ad588c9a24bde041be51c25368f303ec26da44c608f"
  command: 'uv run .\win32\test_win32_dblclick.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  physical_element_rect: [2841, 1185, 430, 30]
  original_mouse_position: [2531, 1801]
  manual_motion_disabled_during_test: true
observations:
  api_contract:
    status: "PASS"
    detail: "四个公开参数与 double_click 别名的签名、默认值均符合合同"
    elapsed_ms: 0.1
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致，已借用 Package"
    elapsed_ms: 7.0
  target_element:
    status: "PASS"
    detail: "已定位靶场输入框并关闭人工轨迹，物理边界有效"
    elapsed_ms: 117.7
  default_parameters:
    status: "PASS"
    call: "element.dblclick()"
    returned: null
    strategy: "win"
    clicked_point: [3056, 1200]
    elapsed_ms: 1519.3
  all_positional_parameters:
    status: "PASS"
    call: 'element.dblclick(False, 0, False, "middleCenter")'
    returned: null
    strategy: "win"
    actual_path: "mouse fallback"
    fallback_diagnostic_present: true
    elapsed_ms: 181.6
  simulative_modes:
    status: "PASS"
    values: [true, false]
    simulated_strategy: "win"
    false_strategy: "win"
    false_fell_back_to_mouse: true
    elapsed_ms: 342.7
  move_mouse_modes:
    status: "PASS"
    values: [false, true]
    clicked_points_inside_element: true
    elapsed_ms: 421.3
  fixed_anchors:
    status: "PASS"
    values: ["topLeft", "topCenter", "topRight", "middleLeft", "middleCenter", "middleRight", "bottomLeft", "bottomCenter", "bottomRight"]
    clicked_points_matched_physical_bounds: true
    elapsed_ms: 1520.0
  random_anchor:
    status: "PASS"
    clicked_point: [2931, 1188]
    point_inside_element: true
    elapsed_ms: 170.2
  tuple_anchor:
    status: "PASS"
    value: ["middleCenter", 10, 4]
    clicked_point: [3066, 1204]
    elapsed_ms: 168.8
  mapping_anchor:
    status: "PASS"
    value: {anchor: "middleCenter", offset_x: -10, offset_y: -4}
    clicked_point: [3046, 1196]
    elapsed_ms: 169.0
  delay_after:
    status: "PASS"
    values: [null, 0, 0.2, "default 1"]
    elapsed_ms: 707.3
  public_alias:
    status: "PASS"
    call: 'element.double_click(True, 0, False, "middleCenter")'
    returned: null
    strategy: "win"
    clicked_point: [3056, 1200]
    elapsed_ms: 169.5
  invalid_anchor:
    status: "PASS"
    values: ["center", 123]
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  invalid_delay:
    status: "PASS"
    values: [-1, "bad"]
    expected_error: "InvalidParamsError"
    note: "double-click action completes and last_result is saved before delay_after validation"
    elapsed_ms: 336.7
cleanup:
  status: "PASS"
  elapsed_ms: 0.3
  manual_motion_disabled: true
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
  target_form_content_modified: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_dblclick.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_dblclick.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取已经启动的
Win32 靶场窗口，并使用 `win32靶场输入框` 执行真实左键双击。脚本不输入或删除内容；
结束时关闭人工轨迹、恢复鼠标和原前台窗口、关闭借用的 Package，并保持靶场运行。

## API 参数

```python
dblclick(
    simulative: bool = True,
    delay_after: float = 1,
    move_mouse: bool | None = None,
    anchor: object | None = None,
) -> None
```

- 四个参数都是位置或关键字参数，调用成功返回 `None`；动作详情保存在 `last_result`。
- `double_click()` 是公开别名，签名、默认值和返回行为与 `dblclick()` 一致。
- `simulative=True` 使用鼠标双击。虽然参数说明把 `False` 表述为优先控件动作，但当前
  Runtime 的控件 Invoke 只适用于单击；双击会留下诊断并回退到坐标鼠标动作。
- `delay_after` 默认等待 1 秒；`None` 或 `0` 不等待。当前实现先完成双击并保存
  `last_result`，再校验及执行动作后延时，因此非法延时也会先触发真实双击。
- `move_mouse=None` 读取人工轨迹配置，默认等效为 `True`；显式布尔值可控制可见移动或
  瞬移。
- `anchor=None` 默认使用 `middleCenter`；另支持九宫格固定位置、`random`、三元组及
  包含锚点和偏移量的字典。
- API 固定执行左键双击，不提供 `button` 或 `keys` 参数。

## 最小实现链

```text
Win32Element.dblclick(...)
  -> _motion.click_anchor(anchor)
  -> anchor_to_pt(...)
  -> RawWinElement.double_click(pt, move_mouse, simulative)
  -> Runtime action.double_click_element
     -> ActionService._run_pointer_action(..., action="double_click")
        simulative=False：记录坐标动作回退原因
        -> 解析实时元素矩形
        -> point_in_rect_xywh(rect, pt)
        -> _perform_mouse(...)
        -> MouseController.double_click(...)
        -> ActionResult(clicked_point, strategy, diagnostics)
  -> Win32Element._finish(result, delay_after)
     -> 保存 last_result
     -> 抛出动作错误（如有）
     -> 执行动作后延时

Win32Element.double_click(...)
  -> Win32Element.dblclick(...)
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `dblclick` 与 `double_click` 签名 | 四个参数、默认值和调用种类一致 | `PASS` |
| 默认调用 | `element.dblclick()` | 返回 `None`，中心双击，默认约 1 秒延时 | `PASS` |
| 全位置参数 | `dblclick(False, 0, False, "middleCenter")` | 四项位置参数生效，回退可诊断 | `PASS` |
| 动作模式 | `simulative=True/False` | 两种模式均完成双击，False 为鼠标回退 | `PASS` |
| 鼠标移动 | `move_mouse=False/True` | 两种模式均成功且点位在元素内 | `PASS` |
| 固定锚点 | 九宫格九项 | `clicked_point` 与对应物理边界一致 | `PASS` |
| 随机锚点 | `random` | 随机点位于元素内 | `PASS` |
| 三元组锚点 | `("middleCenter", 10, 4)` | 点击点包含指定偏移 | `PASS` |
| 字典锚点 | 中心点和 `-10/-4` 偏移 | 点击点包含指定偏移 | `PASS` |
| 动作后延时 | `None/0/0.2/default 1` | 不等待与有限等待均符合合同 | `PASS` |
| 公开别名 | `element.double_click(...)` | 委托成功并更新 `last_result` | `PASS` |
| 非法锚点 | `center`、整数 | 抛出 `InvalidParamsError` | `PASS` |
| 非法延时 | `-1`、`"bad"` | 双击后保存结果并抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 恢复本次测试状态 | 鼠标和焦点恢复，Package 关闭，靶场保持运行 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_dblclick.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 物理边界：`(2841, 1185, 430, 30)`
- 默认双击点：`(3056, 1200)`
- `simulative=False`：以 `win` 鼠标动作成功回退，诊断信息存在
- `double_click()`：公开别名调用通过
- 总状态：`PASS`
- 通过数：`16/16`
- 总耗时：`5831.6ms`
- 人工轨迹：已关闭
- 鼠标与原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行，表单内容未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 右键或中键双击；此公开 API 固定使用左键且没有 `button` 参数。
- 修饰键双击；此公开 API 没有 `keys` 参数。
- `simulative=False` 的纯控件 Invoke 分支；当前 Runtime 的双击只提供可诊断鼠标回退。
- 开启人工轨迹后的随机默认锚点；脚本在真实双击前显式关闭人工轨迹。
- 双击后选择文本的业务语义；本轮只验证动作成功、诊断和物理点位，不修改文本内容。

