# `uiautoma.win32.Win32Element.select()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.select"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  default_parameters: "PASS"
  all_positional_parameters: "PASS"
  fuzzy_match: "PASS"
  exact_match: "PASS"
  contains_match: "PASS"
  regex_match: "PASS"
  mode_normalization: "PASS"
  item_normalization: "PASS"
  text_conversion: "PASS"
  delay_after: "PASS"
  empty_item: "PASS"
  invalid_mode: "PASS"
  invalid_regex: "PASS"
  item_not_found: "PASS"
  ambiguous_item: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 18
  total: 18
  elapsed_ms: 24825.0
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "Win32Element.select 的参数规范化、候选项匹配、UIA SelectionItem 动作和结果确认路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.select", "Win32Element._finish"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["sleep_after"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["RawWinElement.select", "RawWinElement.get_select_items", "RawWinElement.get_selected_items"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_select_element", "_handle_select_element", "_selectable_candidates"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.select_element"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "select(self, item: str, mode: str = 'fuzzy', delay_after: float = 1) -> None"
    parameters_are_positional_or_keyword: true
    match_modes: ["exact", "contains", "fuzzy", "regex"]
    default_match_mode: "fuzzy"
    return_value: null
    action_result_property: "last_result"
    invalid_parameter_error: "InvalidParamsError"
    failed_selection_error: "ActionError"
persistent_script:
  path: "win32/test_win32_select.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "513c04bbb16bd3c6baea165ac1235ea1bd3119487076d1f26f4575e4995a65d1"
  command: 'uv run .\win32\test_win32_select.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场城市下拉框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  candidates: ["北京", "上海", "广州", "深圳", "杭州"]
  original_selection: "北京"
  original_mouse_position: [4320, 1435]
  manual_motion_disabled_during_test: true
observations:
  api_contract:
    status: "PASS"
    detail: "三个公开参数、默认值和位置/关键字调用规则符合合同"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致，已借用 Package"
    elapsed_ms: 7.7
  target_element:
    status: "PASS"
    detail: "已定位城市下拉框，候选项和原选项均可读取"
    elapsed_ms: 1383.5
  default_parameters:
    status: "PASS"
    call: 'element.select("上")'
    mode: "fuzzy"
    selected_item: "上海"
    strategy: "GetSelectionItemPattern.Select"
    elapsed_ms: 2751.1
  all_positional_and_exact:
    status: "PASS"
    call: 'element.select("广州", "exact", 0)'
    selected_item: "广州"
    strategy: "GetSelectionItemPattern.Select"
    elapsed_ms: 1742.7
  contains_match:
    status: "PASS"
    call: 'element.select("深", mode="contains", delay_after=0)'
    selected_item: "深圳"
    strategy: "GetSelectionItemPattern.Select"
    elapsed_ms: 1758.4
  regex_match:
    status: "PASS"
    call: 'element.select("^杭州$", mode="regex", delay_after=0)'
    selected_item: "杭州"
    strategy: "GetSelectionItemPattern.Select"
    elapsed_ms: 1753.4
  mode_normalization:
    status: "PASS"
    value: " ExAcT "
    normalized: "exact"
    elapsed_ms: 1751.7
  item_normalization:
    status: "PASS"
    leading_and_trailing_whitespace_removed: true
    elapsed_ms: 1764.6
  text_conversion:
    status: "PASS"
    converted_item: "广州"
    elapsed_ms: 1752.6
  delay_after:
    status: "PASS"
    values: [null, 0.2, "default 1"]
    observed_none_ms: 1750.7
    observed_0_2_ms: 1922.9
    note: "单次 UIA 选择动作本身约需 1.75 秒，delay_after 在此基础上追加等待"
    elapsed_ms: 3699.0
  empty_item:
    status: "PASS"
    values: ["", "   "]
    expected_error: "InvalidParamsError"
    selection_unchanged: true
    elapsed_ms: 27.2
  invalid_mode:
    status: "PASS"
    values: ["prefix", null]
    expected_error: "InvalidParamsError"
    selection_unchanged: true
    elapsed_ms: 22.7
  invalid_regex:
    status: "PASS"
    value: "["
    expected_error: "ActionError"
    trace_info: "invalid_match_regex:unterminated character set at position 0"
    selection_unchanged: true
    elapsed_ms: 29.0
  item_not_found:
    status: "PASS"
    expected_error: "ActionError"
    trace_info: "select_item_not_found"
    selection_unchanged: true
    elapsed_ms: 749.6
  ambiguous_item:
    status: "PASS"
    call: 'element.select(".*", mode="regex", delay_after=0)'
    expected_error: "ActionError"
    trace_info: "ambiguous_select_item"
    matched_candidate_count: 5
    selection_unchanged: true
    elapsed_ms: 578.6
  invalid_delay:
    status: "PASS"
    values: [-1, "bad"]
    expected_error: "InvalidParamsError"
    selection_completed_before_error: true
    negative_delay_selected: "北京"
    text_delay_selected: "上海"
    elapsed_ms: 3311.5
cleanup:
  status: "PASS"
  elapsed_ms: 1741.5
  original_selection_restored: "北京"
  manual_motion_disabled: true
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_select.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_select.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取已启动的 Win32
靶场窗口和 `win32靶场城市下拉框`。候选项由脚本运行时读取，不硬编码城市名称；开始
选择前必须读到唯一原选项。脚本使用 `get_all_select_items()` 和
`get_selected_item()` 作为状态观察器，只把 `select()` 作为被测动作。结束时恢复原选项、
鼠标和原前台窗口，关闭借用的 Package，并保持靶场运行。

## API 参数

```python
select(
    item: str,
    mode: str = "fuzzy",
    delay_after: float = 1,
) -> None
```

- 三个参数都是位置或关键字参数，调用成功返回 `None`；动作详情保存在 `last_result`。
- `item` 在 SDK 边界调用 `str()`，随后去除首尾空白；空字符串或纯空白被
  `InvalidParamsError` 拒绝。
- `mode` 支持 `exact`、`contains`、`fuzzy`、`regex`，会去除首尾空白并忽略模式名称
  的大小写。
- `exact` 对候选项进行不区分大小写的完整匹配；当前实现中 `contains` 与 `fuzzy` 均为
  不区分大小写的子串匹配；`regex` 使用 Python 正则搜索并保留表达式本身的大小写语义。
- 目标必须唯一命中。未命中返回 `select_item_not_found`，多项命中返回
  `ambiguous_select_item`，高层接口均表现为 `ActionError`。
- `delay_after` 默认等待 1 秒；`None` 或 `0` 不等待。当前实现先完成选择并保存
  `last_result`，再校验及执行动作后延时，因此非法延时也会先改变选中项。

## 最小实现链

```text
Win32Element.select(item, mode, delay_after)
  -> RawWinElement.select(str(item), match=mode)
     -> 规范化 item 和 match
     -> Runtime action.select_element
        -> handle_select_element(...)
           -> 展开选择控件
           -> 枚举带 SelectionItemPattern 的候选项
           -> exact / contains / fuzzy / regex 唯一匹配
           -> SelectionItemPattern.Select()
           -> 收起选择控件并返回 selected_item、strategy
     -> ActionResult
  -> Win32Element._finish(result, delay_after)
     -> 保存 last_result
     -> 抛出动作错误（如有）
     -> 执行动作后延时
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | 公开签名 | 三个参数、默认值及调用种类一致 | `PASS` |
| 默认调用 | `select("上")` | 默认 fuzzy 唯一选中“上海”，约 1 秒动作后延时 | `PASS` |
| 全位置参数 | `select("广州", "exact", 0)` | 三项位置参数生效并返回 `None` | `PASS` |
| 包含匹配 | `contains` 和唯一真子串 | 选中“深圳” | `PASS` |
| 正则匹配 | `^杭州$` | 唯一选中“杭州” | `PASS` |
| 模式规范化 | ` ExAcT ` | 去空白及大小写规范化生效 | `PASS` |
| 文本规范化 | item 首尾空白 | 去空白后精确选择 | `PASS` |
| 文本转换 | 可字符串化对象 | `str(item)` 后选择成功 | `PASS` |
| 动作后延时 | `None/0.2/default 1` | 等待差异符合合同 | `PASS` |
| 空选项 | 空字符串、纯空白 | 抛出 `InvalidParamsError`，状态不变 | `PASS` |
| 非法模式 | `prefix`、`None` | 抛出 `InvalidParamsError`，状态不变 | `PASS` |
| 非法正则 | `[` | 抛出 `ActionError`，trace 可诊断 | `PASS` |
| 未命中 | 不存在文本 | `select_item_not_found`，状态不变 | `PASS` |
| 多项命中 | 正则 `.*` | `ambiguous_select_item`，状态不变 | `PASS` |
| 非法延时 | `-1`、`"bad"` | 选择后抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 恢复运行前状态 | 原选项、鼠标、焦点及 Package 均恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_select.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场城市下拉框`
- 候选项：`北京`、`上海`、`广州`、`深圳`、`杭州`
- 原选项：`北京`
- 成功动作策略：`GetSelectionItemPattern.Select`
- 总状态：`PASS`
- 通过数：`18/18`
- 总耗时：`24825.0ms`
- 原选项：已恢复为 `北京`
- 鼠标与原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 多选列表的追加/移除语义；`select()` 只接受单个 `item`，不提供多选控制参数。
- 按索引选择；该能力属于独立公开 API `select_by_index()`。
- 候选项枚举和已选项读取本身的完整合同；本轮只把两个读取 API 作为状态观察器。
- 非 UIA SelectionItem 控件的 Invoke 或鼠标点击回退；本轮靶场通过
  `GetSelectionItemPattern.Select` 完成选择。
