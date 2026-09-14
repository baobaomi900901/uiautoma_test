# `uiautoma.win32.Win32Element.get_all_select_items()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_all_select_items"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_element: "PASS"
  return_type: "PASS"
  native_crosscheck: "PASS"
  candidate_quality: "PASS"
  repeatability: "PASS"
  state_unchanged: "PASS"
  last_result_unchanged: "PASS"
  non_select_control: "PASS"
  extra_arguments: "PASS"
  cleanup: "PASS"
  passed: 12
  total: 12
  elapsed_ms: 8727.5
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "Win32Element.get_all_select_items 的公开包装、读取 RPC、原生 ComboBox 与 UIA 枚举路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.get_all_select_items"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["RawWinElement.get_select_items"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_get_select_items", "_handle_get_select_items", "_native_select_options_from_control", "_selectable_candidates"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.get_select_items_element"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "get_all_select_items(self) -> list[str]"
    public_parameters: []
    return_type: "list[str]"
    internal_timeout_seconds: 5
    updates_last_result: false
persistent_script:
  path: "win32/test_win32_get_all_select_items.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "8fe9e3e784fa04c65fab0314cb2a8fd90e3c869706b6b547b4e440e027344374"
  command: 'uv run .\win32\test_win32_get_all_select_items.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场城市下拉框"
  non_select_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  native_combobox_handle: 2885566
  native_combobox_handle_hex: "0x2c07be"
  native_candidates: ["北京", "上海", "广州", "深圳", "杭州"]
  original_selected_index: 0
  original_selected_item: "北京"
  original_dropped_state: false
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 list[str]"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致，已借用 Package"
    elapsed_ms: 8.2
  target_element:
    status: "PASS"
    detail: "已定位 SDK 元素及唯一原生 ComboBox，初始状态有效"
    elapsed_ms: 189.6
  return_type:
    status: "PASS"
    type: "list[str]"
    value: ["北京", "上海", "广州", "深圳", "杭州"]
    elapsed_ms: 1217.2
  native_crosscheck:
    status: "PASS"
    sdk_value: ["北京", "上海", "广州", "深圳", "杭州"]
    native_value: ["北京", "上海", "广州", "深圳", "杭州"]
    count: 5
    text_equal: true
    order_equal: true
    elapsed_ms: 1214.3
  candidate_quality:
    status: "PASS"
    non_empty: true
    all_strings: true
    unique: true
    elapsed_ms: 0.0
  repeatability:
    status: "PASS"
    reads: 3
    all_equal: true
    combined_elapsed_ms: 3655.4
    elapsed_ms: 3655.5
  state_unchanged:
    status: "PASS"
    selected_index_before: 0
    selected_index_after: 0
    selected_item_after: "北京"
    dropped_after: false
    elapsed_ms: 1213.7
  last_result_unchanged:
    status: "PASS"
    detail: "读取 API 不创建动作结果，element.last_result 保持原值"
    elapsed_ms: 1220.9
  non_select_control:
    status: "PASS"
    element: "win32靶场输入框"
    value: []
    elapsed_ms: 7.0
  extra_arguments:
    status: "PASS"
    calls: ["get_all_select_items(0)", "get_all_select_items(timeout=0)"]
    expected_error: "TypeError"
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 1.1
  selected_index_restored: 0
  selected_item_restored: "北京"
  dropped_state_restored: false
  mouse_position_restored: true
  foreground_window_restored: true
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_get_all_select_items.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_all_select_items.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取已启动的 Win32
靶场、`win32靶场城市下拉框` 和作为非选择控件参照的 `win32靶场输入框`。测试脚本通过
Windows `CB_GETCOUNT`、`CB_GETLBTEXT`、`CB_GETCURSEL` 和 `CB_GETDROPPEDSTATE` 消息
独立读取原生 ComboBox 状态，再与 SDK 返回值交叉校验。测试只读；清理阶段仍会检查并
恢复原生选中索引和收起状态，恢复鼠标及前台窗口并关闭借用的 Package。

## API 合同

```python
get_all_select_items() -> list[str]
```

- API 没有公开参数，返回候选项文本组成的 `list[str]`。
- 返回顺序与 Runtime 枚举到的选择候选项顺序一致。
- 高层接口没有公开 `timeout`；Raw SDK 内部使用固定的 5 秒动作超时。
- Runtime 优先尝试通过原生 ComboBox/ListBox 消息读取；不可用时读取当前 UIA 树，必要
  时展开控件、枚举候选项并在结束后收起。
- 普通非选择控件没有候选项，当前实现返回空列表。
- 该读取 API 不写入 `Win32Element.last_result`；额外位置参数或 `timeout=` 关键字由
  Python 签名抛出 `TypeError`。

## 最小实现链

```text
Win32Element.get_all_select_items()
  -> RawWinElement.get_select_items(timeout=5.0)
  -> Runtime element.get_select_items
     -> ActionService.get_select_items_element(...)
     -> handle_get_select_items(...)
        -> 优先 _native_select_options_from_control(...)
           ComboBox: CB_GETCOUNT / CB_GETCURSEL / CB_GETLBTEXT
           ListBox: LB_GETCOUNT / LB_GETCURSEL / LB_GETTEXT
        -> 原生消息不可用时枚举 UIA SelectionItem 候选项
        -> 必要时展开读取并收起控件
        -> 返回 items、selected_items、options 和 strategy
  -> 将 items 中每一项转换为 str
```

## 覆盖矩阵

| 场景 | 验收条件 | 结果 |
| --- | --- | --- |
| API 合同 | 无公开参数，返回注解为 `list[str]` | `PASS` |
| 返回类型 | 实际返回列表且所有成员均为字符串 | `PASS` |
| 原生交叉校验 | SDK 与 ComboBox 的数量、文本、顺序完全一致 | `PASS` |
| 候选项质量 | 非空、无空白文本且无重复项 | `PASS` |
| 重复读取 | 连续三次结果完全一致 | `PASS` |
| 状态不变 | 选中索引仍为 `0`，下拉框保持收起 | `PASS` |
| 动作结果隔离 | `element.last_result` 保持原值 | `PASS` |
| 非选择控件 | 普通输入框返回 `[]` | `PASS` |
| 额外参数 | 位置参数和 `timeout=` 均抛出 `TypeError` | `PASS` |
| 资源清理 | 原选项、收起状态、鼠标、焦点和 Package 均恢复 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_get_all_select_items.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场城市下拉框`
- 原生 ComboBox：`2885566 (0x2c07be)`
- SDK 与原生候选项：`北京`、`上海`、`广州`、`深圳`、`杭州`
- 原选项及索引：`北京`，索引 `0`
- 重复读取：三次结果一致，合计 `3655.4ms`
- 总状态：`PASS`
- 通过数：`12/12`
- 总耗时：`8727.5ms`
- 下拉选项：未改变
- 展开状态：已收起
- 鼠标与原前台窗口：已恢复
- Package：借用连接已关闭
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 当前选中项的完整读取合同；该能力属于独立公开 API `get_selected_item()`。
- 文本或索引选择动作；分别由 `select()` 与 `select_by_index()` 验证。
- 多选列表、树控件及无原生窗口句柄的 UIA 控件；本轮使用单选原生 ComboBox。
- UIA 展开读取回退路径；当前靶场可通过原生 ComboBox 消息读取。
