# `uiautoma.win32.Win32Element.hover()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.hover"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  target_element: "PASS"
  default_parameters: "PASS"
  simulative_modes: "PASS"
  delay_after: "PASS"
  fixed_anchors: "PASS"
  random_anchor: "PASS"
  tuple_anchor: "PASS"
  list_anchor: "PASS"
  mapping_anchor: "PASS"
  mapping_aliases: "PASS"
  anchor_casefold: "PASS"
  invalid_anchor: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 25
  total: 25
  elapsed_ms: 3880.5
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.hover 的参数规范化、锚点、动作结果和 Runtime 鼠标移动路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.hover", "Win32Element._finish", "Win32Element.get_bounding"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["anchor_to_pt", "_anchor_parts", "sleep_after"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/win32/_motion.py"
      symbols: ["default_bool"]
      fingerprint: "5131d0d264945b297636be763183436a02d893ac"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.hover", "Session._run_win_action"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "sdk/src/uiautoma/_core/models.py"
      symbols: ["ActionResult"]
      fingerprint: "d0d5b2c074943a825f1a9514ff333a62666acf10"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.hover_element", "ActionService._run_pointer_action", "ActionService._perform_mouse"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
    - path: "runtime/desktop/mouse_actions.py"
      symbols: ["point_in_rect_xywh", "MouseBackend.move", "move_to"]
      fingerprint: "d5804f849b14016faf47f77acb09491ccdb38adc"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "hover(self, simulative: bool | None = None, delay_after: float = 1, anchor: object | None = None) -> None"
    parameters_are_positional_or_keyword: true
    return_value: null
    action_result_property: "last_result"
    simulative_values: [null, true, false]
    default_delay_after_seconds: 1
    no_delay_values: [null, 0]
    default_anchor: "middleCenter"
    fixed_anchor_count: 9
    other_anchor_forms: ["random", "tuple", "list", "mapping"]
    mapping_aliases: ["name", "x", "y"]
    anchor_names_case_insensitive: true
    invalid_parameter_error: "InvalidParamsError"
    action_error: "ActionError"
persistent_script:
  path: "win32/test_win32_hover.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "16db5fa5c8f4d15da12dc15e79b41899e09cedf1e2134059c42b1065734d91b4"
  command: 'uv run .\win32\test_win32_hover.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  physical_element_rect: [2841, 1185, 430, 30]
  safe_element_rect: [2843, 1187, 3269, 1213]
  center_point: [3056, 1200]
  independent_observation:
    - "Win32 GetCursorPos"
    - "ActionResult.clicked_point"
observations:
  api_contract:
    status: "PASS"
    detail: "三个参数均为位置或关键字参数，默认值和返回 None 符合合同"
    elapsed_ms: 0.0
  element_setup:
    status: "PASS"
    physical_rect: [2841, 1185, 430, 30]
    elapsed_ms: 137.4
  all_defaults:
    status: "PASS"
    call: "element.hover()"
    effective_simulative: true
    effective_delay_after_seconds: 1
    effective_anchor: "middleCenter"
    elapsed_ms: 1469.6
  simulative_false:
    status: "PASS"
    call: 'element.hover(False, 0, "middleCenter")'
    effective_move_mouse: false
    elapsed_ms: 6.4
  simulative_true:
    status: "PASS"
    call: 'element.hover(True, 0, "middleCenter")'
    effective_move_mouse: true
    elapsed_ms: 466.8
  delay_none:
    status: "PASS"
    call: 'element.hover(False, None, "middleCenter")'
    elapsed_ms: 5.0
  delay_positive:
    status: "PASS"
    call: 'element.hover(False, 0.2, "middleCenter")'
    elapsed_ms: 204.9
  fixed_anchors:
    status: "PASS"
    values: ["topLeft", "topCenter", "topRight", "middleLeft", "middleCenter", "middleRight", "bottomLeft", "bottomCenter", "bottomRight"]
    all_cursor_positions_matched: true
    all_action_points_matched: true
    elapsed_ms_by_anchor:
      topLeft: 5.0
      topCenter: 4.1
      topRight: 5.0
      middleLeft: 4.2
      middleCenter: 6.6
      middleRight: 4.3
      bottomLeft: 5.2
      bottomCenter: 5.0
      bottomRight: 3.5
  random_anchor:
    status: "PASS"
    point_inside_safe_rect: true
    elapsed_ms: 4.2
  tuple_anchor:
    status: "PASS"
    value: ["middleCenter", 12, -6]
    elapsed_ms: 6.7
  list_anchor:
    status: "PASS"
    value: ["topLeft", 10, 8]
    elapsed_ms: 3.9
  mapping_anchor:
    status: "PASS"
    value: {anchor: "bottomRight", offset_x: -10, offset_y: -8}
    elapsed_ms: 4.3
  mapping_aliases:
    status: "PASS"
    value: {name: "topCenter", x: 5, y: 7}
    elapsed_ms: 4.4
  anchor_casefold:
    status: "PASS"
    value: "MiDdLeRiGhT"
    elapsed_ms: 4.7
  invalid_anchor:
    status: "PASS"
    values: ["not-an-anchor", 42]
    expected_error: "InvalidParamsError"
    mouse_moved_before_error: false
    elapsed_ms: 300.5
  invalid_delay:
    status: "PASS"
    values: [-0.1, "bad"]
    expected_error: "InvalidParamsError"
    note: "hover action completes and last_result is saved before delay_after validation"
    elapsed_ms: 314.6
cleanup:
  status: "PASS"
  elapsed_ms: 150.3
  mouse_position_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
  target_form_content_modified: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_hover.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_hover.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，使用
`win32靶场输入框` 执行真实悬停。每次调用同时检查 Win32 当前鼠标位置和
`ActionResult.clicked_point`；结束时恢复鼠标、关闭借用的 Package，并保持靶场运行。

## API 参数

```python
hover(
    simulative: bool | None = None,
    delay_after: float = 1,
    anchor: object | None = None,
) -> None
```

- 三个参数都是位置或关键字参数；成功返回 `None`，动作详情保存在 `last_result`。
- `simulative=None` 读取人工轨迹偏好，并以 `True` 作为当前默认；`True` 显示移动轨迹，
  `False` 瞬间移动。
- `delay_after` 默认等待 1 秒；`None` 或 `0` 不等待，非负数字按秒等待。
- 当前实现先执行悬停并保存 `last_result`，再校验及执行动作后延时。因此负数或非数字
  延时会先完成真实悬停，再抛出 `InvalidParamsError`。
- `anchor=None` 表示 `middleCenter`；另支持九宫格固定锚点和 `random`。
- 锚点名称不区分大小写；还支持元组、列表、字典形式的 X/Y 像素偏移。
- 字典正式字段为 `anchor`、`offset_x`、`offset_y`，并兼容 `name`、`x`、`y`。
- 非法锚点名称或类型在鼠标移动前抛出 `InvalidParamsError`。

## 最小实现链

```text
Win32Element.hover(simulative, delay_after, anchor)
  -> _motion.default_bool(simulative, key="motion_move", default=True)
  -> anchor_to_pt(anchor)
  -> RawWinElement.hover(pt, move_mouse, simulative)
  -> Runtime action.hover_element
     -> ActionService._run_pointer_action(..., action="hover")
        -> 解析实时元素矩形
        -> point_in_rect_xywh(rect, pt)
        -> MouseBackend.move(..., motion=move_mouse)
        -> ActionResult(clicked_point, mouse_diagnostics)
  -> Win32Element._finish(result, delay_after)
     -> 保存 last_result
     -> 抛出动作错误（如有）
     -> 校验并执行动作后延时
```

固定锚点在元素边缘内缩 2 个物理像素；测试以 `(2843, 1187, 3269, 1213)` 为安全边界。

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.hover)` | 三个参数、默认值和返回标注一致 | `PASS` |
| 元素准备 | 当前 Package 与 `win32靶场输入框` | 元素库一致且物理边界有效 | `PASS` |
| 默认调用 | `element.hover()` | 默认轨迹、中心锚点和约 1 秒延时生效 | `PASS` |
| 人工轨迹关闭 | `simulative=False` | 瞬时移动且最终落点正确 | `PASS` |
| 人工轨迹开启 | `simulative=True` | 显示轨迹且最终落点正确 | `PASS` |
| 无动作后延时 | `delay_after=None/0` | 不额外等待 | `PASS` |
| 正数动作后延时 | `delay_after=0.2` | 悬停后等待约 0.2 秒 | `PASS` |
| 固定锚点 | 九宫格九项 | 鼠标与动作报告均匹配安全锚点 | `PASS` |
| 随机锚点 | `random` | 落点位于安全边界内 | `PASS` |
| 元组锚点 | `("middleCenter", 12, -6)` | X/Y 偏移生效 | `PASS` |
| 列表锚点 | `["topLeft", 10, 8]` | X/Y 偏移生效 | `PASS` |
| 字典锚点 | `anchor/offset_x/offset_y` | X/Y 偏移生效 | `PASS` |
| 字典别名 | `name/x/y` | 字段别名与偏移生效 | `PASS` |
| 大小写兼容 | `MiDdLeRiGhT` | 归一化为 `middleRight` | `PASS` |
| 非法锚点 | 非法名称和整数 | 移动前抛出 `InvalidParamsError` | `PASS` |
| 非法延时 | `-0.1`、`"bad"` | 悬停后抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 恢复本次测试状态 | 鼠标恢复、Package 关闭、靶场保持运行 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_hover.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 物理边界：`(2841, 1185, 430, 30)`
- 安全边界：`(2843, 1187, 3269, 1213)`
- 默认调用：`1469.6ms`，默认轨迹、1 秒延时和中心锚点生效
- `simulative=False`：`6.4ms`，瞬时移动并到达中心
- `simulative=True`：`466.8ms`，人工轨迹移动并到达中心
- `delay_after=0.2`：`204.9ms`
- 固定锚点：九项全部匹配
- 其他锚点：`random`、元组、列表、字典、字段别名和大小写兼容全部通过
- 总状态：`PASS`
- 通过数：`25/25`
- 总耗时：`3880.5ms`
- 鼠标位置：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行，表单内容未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 悬停触发业务 ToolTip 或视觉样式的语义校验；本轮验证公开调用、轨迹、延时和物理落点。
- 在全局 `manual_motion_on()` 的不同配置下重复默认调用；本轮直接覆盖单次
  `simulative=True/False/None`。
- Runtime 返回失败时的 `ActionError`；当前真实目标的全部动作均成功。
- 无效数字偏移的静默回退行为；公开说明仅承诺像素偏移，不把兼容回退固化为合同。

