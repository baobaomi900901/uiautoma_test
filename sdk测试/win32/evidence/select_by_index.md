# `uiautoma.win32.Win32Element.select_by_index()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.select_by_index"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  default_parameters: "PASS"
  all_positional_parameters: "PASS"
  first_index: "PASS"
  middle_index: "PASS"
  last_index: "PASS"
  index_conversion: "PASS"
  delay_after: "PASS"
  negative_index: "PASS"
  out_of_range_index: "PASS"
  invalid_index_type: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 15
  total: 15
  elapsed_ms: 27898.8
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "Win32Element.select_by_index 的参数转换、UIA 候选项索引、选择动作和结果确认路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.select_by_index", "Win32Element._finish"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["sleep_after"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["RawWinElement.select_by_index", "RawWinElement.get_select_items", "RawWinElement.get_selected_items"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_select_element", "_handle_select_element", "_selectable_candidates"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.select_element_by_index"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "select_by_index(self, index: int, delay_after: float = 1) -> None"
    parameters_are_positional_or_keyword: true
    index_origin: 0
    index_conversion: "int(index)"
    return_value: null
    action_result_property: "last_result"
    invalid_delay_error: "InvalidParamsError"
    failed_selection_error: "ActionError"
persistent_script:
  path: "win32/test_win32_select_by_index.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "1231b294b332cb5b9e225684b1f095fa80b531f91b7a1f277c40fb8af592c8f7"
  command: 'uv run .\win32\test_win32_select_by_index.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场城市下拉框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  indexed_candidates:
    0: "北京"
    1: "上海"
    2: "广州"
    3: "深圳"
    4: "杭州"
  original_selection: "北京"
  original_index: 0
  original_mouse_position: [4377, 1406]
  manual_motion_disabled_during_test: true
observations:
  api_contract:
    status: "PASS"
    detail: "两个公开参数、默认值和位置/关键字调用规则符合合同"
    elapsed_ms: 0.1
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致，已借用 Package"
    elapsed_ms: 7.4
  target_element:
    status: "PASS"
    detail: "已定位城市下拉框，候选项顺序和原选项均可读取"
    elapsed_ms: 1370.0
  default_parameters:
    status: "PASS"
    call: "element.select_by_index(1)"
    selected_item: "上海"
    strategy: "GetSelectionItemPattern.Select"
    elapsed_ms: 2730.5
  all_positional_parameters:
    status: "PASS"
    call: "element.select_by_index(2, 0)"
    selected_item: "广州"
    elapsed_ms: 1720.5
  first_index:
    status: "PASS"
    index: 0
    selected_item: "北京"
    elapsed_ms: 1721.2
  middle_index:
    status: "PASS"
    index: 2
    selected_item: "广州"
    elapsed_ms: 1724.2
  last_index:
    status: "PASS"
    index: 4
    selected_item: "杭州"
    elapsed_ms: 1714.2
  index_conversion:
    status: "PASS"
    conversions:
      - {input: "1", output_index: 1}
      - {input: 2.9, output_index: 2}
      - {input: true, output_index: 1}
      - {input: false, output_index: 0}
    elapsed_ms: 6895.7
  delay_after:
    status: "PASS"
    values: [null, 0.2, "default 1"]
    observed_none_ms: 1728.5
    observed_0_2_ms: 1919.3
    observed_default_1_ms: 2717.9
    note: "单次 UIA 索引选择动作本身约需 1.72 秒，delay_after 在此基础上追加等待"
    elapsed_ms: 3673.8
  negative_index:
    status: "PASS"
    index: -1
    expected_error: "ActionError"
    trace_info: "select_item_not_found"
    selection_unchanged: true
    elapsed_ms: 717.2
  out_of_range_index:
    status: "PASS"
    index: 5
    candidate_count: 5
    expected_error: "ActionError"
    trace_info: "select_item_not_found"
    selection_unchanged: true
    elapsed_ms: 552.3
  invalid_index_type:
    status: "PASS"
    inputs: ["bad", null, "object()"]
    errors: ["ValueError", "TypeError", "TypeError"]
    selection_unchanged: true
    elapsed_ms: 36.7
  invalid_delay:
    status: "PASS"
    values: [-1, "bad"]
    expected_error: "InvalidParamsError"
    selection_completed_before_error: true
    negative_delay_selected: {index: 1, item: "上海"}
    text_delay_selected: {index: 2, item: "广州"}
    elapsed_ms: 3312.4
cleanup:
  status: "PASS"
  elapsed_ms: 1722.6
  original_selection_restored: "北京"
  original_index_restored: 0
  manual_motion_disabled: true
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_select_by_index.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_select_by_index.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取已启动的 Win32
靶场窗口和 `win32靶场城市下拉框`。候选项及其顺序由脚本运行时读取，不硬编码城市名称；
开始选择前必须读到唯一原选项。脚本使用 `get_all_select_items()` 和
`get_selected_item()` 作为状态观察器，只把 `select_by_index()` 作为被测动作。结束时
按原索引恢复原选项，恢复鼠标和原前台窗口，关闭借用的 Package，并保持靶场运行。

## API 参数

```python
select_by_index(
    index: int,
    delay_after: float = 1,
) -> None
```

- 两个参数都是位置或关键字参数，调用成功返回 `None`；动作详情保存在 `last_result`。
- `index` 从 `0` 开始，顺序与 UIA 候选项枚举一致。SDK 在调用 Runtime 前执行
  `int(index)`；因此整数文本、浮点数和布尔值会分别转换为整数，浮点数向零截断。
- 负数或大于等于候选项数量的索引由 Runtime 返回 `select_item_not_found`，高层接口表现
  为 `ActionError`，并且原选中状态不变。
- 无法执行 `int(index)` 的输入在 SDK 边界分别抛出 `ValueError` 或 `TypeError`，不会发送
  选择请求，也不会改变状态。
- `delay_after` 默认等待 1 秒；`None` 或 `0` 不等待。当前实现先完成选择并保存
  `last_result`，再校验及执行动作后延时，因此非法延时也会先改变选中项。

## 最小实现链

```text
Win32Element.select_by_index(index, delay_after)
  -> int(index)
  -> RawWinElement.select_by_index(index)
     -> Runtime action.select_element_by_index
        -> handle_select_element(...)
           -> 展开选择控件
           -> 按 UIA 顺序枚举带 SelectionItemPattern 的候选项
           -> 校验 0 <= index < len(candidates)
           -> SelectionItemPattern.Select()
           -> 收起选择控件并返回 option.index、selected_item、strategy
     -> ActionResult
  -> Win32Element._finish(result, delay_after)
     -> 保存 last_result
     -> 抛出动作错误（如有）
     -> 执行动作后延时
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | 公开签名 | 两个参数、默认值及调用种类一致 | `PASS` |
| 默认调用 | `select_by_index(1)` | 选中“上海”，默认 1 秒延时生效 | `PASS` |
| 全位置参数 | `select_by_index(2, 0)` | 两项位置参数生效并返回 `None` | `PASS` |
| 首个索引 | `0` | 选中“北京” | `PASS` |
| 中间索引 | `2` | 选中“广州” | `PASS` |
| 最后索引 | `4` | 选中“杭州” | `PASS` |
| 索引转换 | `"1"`、`2.9`、`True`、`False` | 按 `int(index)` 规则选择 | `PASS` |
| 动作后延时 | `None/0.2/default 1` | 等待差异符合合同 | `PASS` |
| 负数索引 | `-1` | `select_item_not_found`，状态不变 | `PASS` |
| 越界索引 | `5` | `select_item_not_found`，状态不变 | `PASS` |
| 非法类型 | `"bad"`、`None`、普通对象 | SDK 转换阶段抛错，状态不变 | `PASS` |
| 非法延时 | `-1`、`"bad"` | 选择后抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 恢复运行前状态 | 原索引、原选项、鼠标、焦点及 Package 均恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_select_by_index.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场城市下拉框`
- 索引映射：`0=北京`、`1=上海`、`2=广州`、`3=深圳`、`4=杭州`
- 原选项及索引：`北京`，索引 `0`
- 成功动作策略：`GetSelectionItemPattern.Select`
- 总状态：`PASS`
- 通过数：`15/15`
- 总耗时：`27898.8ms`
- 原选项：已恢复为 `北京`
- 鼠标与原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 按文本选择及四种文本匹配模式；这些能力属于独立公开 API `select()`。
- 多选列表的追加或移除语义；`select_by_index()` 每次只接受一个索引。
- 候选项枚举和已选项读取本身的完整合同；本轮只把两个读取 API 作为状态观察器。
- 非 UIA SelectionItem 控件的 Invoke 或鼠标点击回退；本轮靶场通过
  `GetSelectionItemPattern.Select` 完成选择。
