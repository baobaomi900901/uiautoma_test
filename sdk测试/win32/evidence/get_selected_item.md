# `uiautoma.win32.Win32Element.get_selected_item()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_selected_item"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  initial_selection: "PASS"
  all_candidate_indices: "PASS"
  native_crosscheck: "PASS"
  repeatability: "PASS"
  returned_list_isolation: "PASS"
  last_result_unchanged: "PASS"
  extra_arguments: "PASS"
  cleanup: "PASS"
  passed: 14
  total: 14
  elapsed_ms: 10518.0
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "Win32Element.get_selected_item 的公开包装、读取 RPC、原生 ComboBox 与 UIA 选中项读取路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.get_selected_item"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["RawWinElement.get_selected_items"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_get_select_items", "_handle_get_select_items", "_native_select_options_from_control", "_selected_text_from_control"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.get_selected_items_element"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "get_selected_item(self) -> list[str]"
    public_parameters: []
    return_type: "list[str]"
    single_select_return_shape: "one-item list"
    internal_timeout_seconds: 5
    updates_last_result: false
persistent_script:
  path: "win32/test_win32_get_selected_item.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "516998a33cc1901cf05c14f9fbe7f79536c5d80bca354ac15891eefa80334c40"
  command: 'uv run .\win32\test_win32_get_selected_item.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场城市下拉框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  native_combobox_handle: 2885566
  native_combobox_handle_hex: "0x2c07be"
  indexed_candidates:
    0: "北京"
    1: "上海"
    2: "广州"
    3: "深圳"
    4: "杭州"
  original_selected_index: 0
  original_selected_item: "北京"
  setup_api: "Win32Element.select_by_index"
  setup_api_previously_verified: true
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 list[str]"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致，已借用 Package"
    elapsed_ms: 7.4
  target_element:
    status: "PASS"
    detail: "已定位 SDK 元素及唯一原生 ComboBox，初始选中状态有效"
    elapsed_ms: 123.3
  initial_selection:
    status: "PASS"
    sdk_value: ["北京"]
    native_index: 0
    native_item: "北京"
    elapsed_ms: 12.9
  index_0:
    status: "PASS"
    sdk_value: ["北京"]
    native_index: 0
    setup_elapsed_ms: 1716.6
    read_elapsed_ms: 9.9
    elapsed_ms: 1726.9
  index_1:
    status: "PASS"
    sdk_value: ["上海"]
    native_index: 1
    setup_elapsed_ms: 1703.4
    read_elapsed_ms: 11.7
    elapsed_ms: 1715.7
  index_2:
    status: "PASS"
    sdk_value: ["广州"]
    native_index: 2
    setup_elapsed_ms: 1705.5
    read_elapsed_ms: 10.3
    elapsed_ms: 1716.1
  index_3:
    status: "PASS"
    sdk_value: ["深圳"]
    native_index: 3
    setup_elapsed_ms: 1713.7
    read_elapsed_ms: 10.7
    elapsed_ms: 1725.0
  index_4:
    status: "PASS"
    sdk_value: ["杭州"]
    native_index: 4
    setup_elapsed_ms: 1704.3
    read_elapsed_ms: 10.2
    elapsed_ms: 1714.8
  repeatability:
    status: "PASS"
    reads: 3
    value: ["杭州"]
    all_equal: true
    combined_elapsed_ms: 33.8
    elapsed_ms: 34.0
  returned_list_isolation:
    status: "PASS"
    local_mutation_did_not_change_runtime: true
    elapsed_ms: 23.0
  last_result_unchanged:
    status: "PASS"
    detail: "读取 API 不创建动作结果，element.last_result 保持场景准备结果"
    elapsed_ms: 11.3
  extra_arguments:
    status: "PASS"
    calls: ["get_selected_item(0)", "get_selected_item(timeout=0)"]
    expected_error: "TypeError"
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 1707.5
  original_selection_restored: "北京"
  original_index_restored: 0
  dropped_state_restored: false
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_get_selected_item.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_selected_item.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取已启动的 Win32
靶场和 `win32靶场城市下拉框`。使用已验证的 `select_by_index()` 依次准备五种选中状态，
然后通过 Windows `CB_GETCURSEL` 与 `CB_GETLBTEXT` 独立读取原生当前项，并与
`get_selected_item()` 返回结果逐项核对。结束时恢复原选项“北京”和收起状态，恢复鼠标
及前台窗口并关闭借用的 Package。

## API 合同

```python
get_selected_item() -> list[str]
```

- API 没有公开参数，返回选中项文本组成的 `list[str]`；单选 ComboBox 也返回单项列表。
- 高层接口没有公开 `timeout`；Raw SDK 内部使用固定的 5 秒动作超时。
- Runtime 优先使用原生 ComboBox/ListBox 当前索引，也支持 UIA `SelectionPattern`、
  `ValuePattern` 和控件名称等回退读取路径。
- 每次调用都会创建新的 Python 列表；修改调用方持有的旧列表不会影响 Runtime 状态。
- 该读取 API 不写入 `Win32Element.last_result`；额外位置参数或 `timeout=` 关键字由
  Python 签名抛出 `TypeError`。

## 最小实现链

```text
Win32Element.get_selected_item()
  -> RawWinElement.get_selected_items(timeout=5.0)
  -> Runtime element.get_selected_items
     -> ActionService.get_selected_items_element(selected_only=True)
     -> handle_get_select_items(...)
        -> _handle_get_select_items(selected_only=True)
           -> 原生 ComboBox: CB_GETCURSEL + CB_GETLBTEXT
           -> 或 UIA SelectionPattern / ValuePattern / Name 回退
           -> 过滤 selected=True 的 option
           -> 返回 items、selected_items、options 和 strategy
  -> 将 items 中每一项转换为 str
```

## 覆盖矩阵

| 场景 | 验收条件 | 结果 |
| --- | --- | --- |
| API 合同 | 无公开参数，返回注解为 `list[str]` | `PASS` |
| 初始选中项 | SDK 返回 `["北京"]`，与原生索引 `0` 一致 | `PASS` |
| 索引 `0` | 场景准备后返回 `["北京"]` | `PASS` |
| 索引 `1` | 场景准备后返回 `["上海"]` | `PASS` |
| 索引 `2` | 场景准备后返回 `["广州"]` | `PASS` |
| 索引 `3` | 场景准备后返回 `["深圳"]` | `PASS` |
| 索引 `4` | 场景准备后返回 `["杭州"]` | `PASS` |
| 重复读取 | 连续三次均返回 `["杭州"]` | `PASS` |
| 返回列表隔离 | 修改旧列表不影响后续读取和 Runtime 状态 | `PASS` |
| 动作结果隔离 | `element.last_result` 保持场景准备结果 | `PASS` |
| 额外参数 | 位置参数和 `timeout=` 均抛出 `TypeError` | `PASS` |
| 资源清理 | 原选项、收起状态、鼠标、焦点和 Package 均恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_get_selected_item.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场城市下拉框`
- 原生 ComboBox：`2885566 (0x2c07be)`
- 索引映射：`0=北京`、`1=上海`、`2=广州`、`3=深圳`、`4=杭州`
- 初始及恢复选项：`[0] 北京`
- 五个索引：SDK 单项列表与原生当前项全部一致
- 单次读取耗时：约 `9.9–12.9ms`
- 总状态：`PASS`
- 通过数：`14/14`
- 总耗时：`10518.0ms`
- 下拉框：原选项和收起状态已恢复
- 鼠标与原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 多选列表返回多项的真实场景；当前元素库没有适合的多选选择控件。
- 候选项完整枚举合同；该能力由 `get_all_select_items()` 单独验证。
- 文本或索引选择动作；本轮仅使用已经验证的 `select_by_index()` 准备读取场景。
- UIA `SelectionPattern`、`ValuePattern` 和名称回退路径；当前靶场可通过原生 ComboBox
  当前索引读取。
