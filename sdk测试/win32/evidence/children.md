# `uiautoma.win32.Win32Element.children()` 验证证据

## 最新复测：新元素名称与自动切换表单页

本次依据测试者运行日志及明确确认更新，状态为 `VERIFIED`。

```yaml
api: "uiautoma.win32.Win32Element.children"
lifecycle: "VERIFIED"
passed: 7
total: 7
elapsed_ms: 457.4
exit_code: 0
tester_confirmed: true
persistent_script:
  path: "win32/test_win32_children.py"
  sha256: "04d72d6664ea00f96940fa95cb9991fdb817c2a5a5414d94a93ff5d95c999af9"
  command: 'uv run .\win32\test_win32_children.py'
form_tab_helper:
  path: "win32/_form_tab.py"
  sha256: "7b27bd9faf78878eff6e049aa414ba8500595cc78d50140f2bbb75d0cd593bd1"
test_environment:
  library_dir: 'D:\code\元素库\260902_win元素'
  panel_element: "win32靶场_表单控件_表单面板"
  leaf_element: "win32靶场_表单控件_按钮_保存"
  activated_tab: "win32靶场_tab_item表单控件"
observations:
  direct_children_count: 33
  expected_interactive_controls: 21
  all_expected_controls_present: true
  all_items_runtime_win32_elements: true
  relation: "children"
  leaf_children: []
cleanup:
  status: "PASS"
  borrowed_package_closed: true
  application_left_running: true
```

| 测试项 | 本次结果 | 耗时 |
| --- | --- | --- |
| API 合同 | 无公开参数，返回 list[Win32Element] | 0.1ms |
| 当前元素库 | 测试库一致；准备步骤已激活表单页 | 192.5ms |
| 面板直属子元素 | 返回 33 个直属子元素 | 192.3ms |
| 返回对象 | 所有项均为 children 关系的 Runtime Win32Element | 0.0ms |
| 已抓取控件 | 21 个预期交互控件全部包含在直属子元素中 | 0.0ms |
| 叶子元素 | 保存按钮返回空列表 | 71.8ms |
| 资源清理 | 借用 Package 已关闭；靶场保持运行 | 0.0ms |

七项均通过，总耗时 `457.4ms`，退出码 `0`。测试脚本参数为无。
脚本通过 `_form_tab.ensure_form_tab()` 点击表单 Tab 并读取原生选中索引确认切页。
33 为本轮观察值，脚本不锁死返回总数和顺序；只要求 21 个预期控件存在。
本次清理仅验证 Package 关闭和靶场保持运行，不宣称恢复原 Tab、鼠标或前台窗口。

以下保留首次验收记录。旧元素名称、源码与脚本指纹、日期和耗时属于历史版本；
最新复测以上述记录为准。本次未重新审计底层源码，也未修改产品源码。

## 首次验收记录（历史：2026-09-04）

```yaml
api: "uiautoma.win32.Win32Element.children"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  panel_children: "PASS"
  runtime_elements: "PASS"
  expected_controls: "PASS"
  leaf_children: "PASS"
  cleanup: "PASS"
  passed: 7
  total: 7
  elapsed_ms: 593.0
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.children 的 SDK→Runtime→UIA 子元素路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.children"]
      fingerprint: "8f9d9a00fdf1f5a9c7ea0160186828bbaf094b32"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.children", "WinElement._many_related"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.get_children_element", "ActionService._run_win_tree_read"]
      fingerprint: "13643d467dfd4ea60a47a1129f886253e5e06756"
    - path: "runtime/services/package_service.py"
      symbols: ["PackageService.register_runtime_win_element", "PackageService._runtime_win_item"]
      fingerprint: "6902eb720dd10ae199a4ca93197d368e54ad6633"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_get_related_element"]
      fingerprint: "af181da49de2066a1bad99d74d91bb03fac25a67"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "children(self) -> list[Win32Element]"
    public_parameters: []
    internal_timeout_seconds: 5.0
    relation: "children"
    runtime_operation: "UIA GetChildren()"
    return_annotation: "list[Win32Element]"
    empty_result: []
    returned_element_id_prefix: "rt:win:"
    returned_elements_are_chainable: true
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_children.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "cfaf64a021751c9532f9ef892fc60837654bf8b4f08aa341ec23dfb26f8c614e"
  command: 'uv run .\win32\test_win32_children.py'
test_environment:
  package_mode: "borrow current UIAutoma Package"
  library_dir: "D:\\code\\元素库\\260902_win元素"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  panel_element: "win32靶场表单面板"
  panel_name: "表单控件页"
  panel_control_type: "Pane"
  leaf_element: "win32靶场保存按钮"
  captured_direct_controls: 21
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 list[Win32Element]"
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
  panel_children:
    status: "PASS"
    returned_count: 33
    detail: "children() 返回 33 个直属 UIA 子元素"
  runtime_elements:
    status: "PASS"
    checked_count: 33
    relation: "children"
    runtime_id_valid: true
    detail: "所有返回项均为 Runtime Win32Element"
  expected_controls:
    status: "PASS"
    expected_count: 21
    missing_count: 0
    detail: "元素库记录的 21 个交互控件均在直属子元素中"
  leaf_children:
    status: "PASS"
    returned_count: 0
    detail: "保存按钮 children() 返回空列表"
cleanup:
  status: "PASS"
  package_connection: "已关闭"
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_children.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_children.py
```

脚本借用 UIAutoma 当前启用的测试元素库，不重新调用 `uiautoma.open()`。元素定位使用
`win32.find()` 作为场景准备；目标关系测试只调用无参数的
`Win32Element.children()`。

## API 参数

```python
children() -> list[Win32Element]
```

- `children()` 没有公开参数。
- 高层实现调用底层 `WinElement.children()`，内部使用固定的 `5s` 超时。
- Runtime 通过 UIA `GetChildren()` 获取当前元素的直属子元素，不递归获取后代。
- 每个结果都包装为新的 `Win32Element`，运行时元素 ID 以 `rt:win:` 开头。
- 返回对象可以继续调用 Win32 元素 API。
- 没有子元素时返回空列表，不抛出“未找到元素”异常。

## 最小实现链

```text
Win32Element.children()
  -> WinElement.children(timeout=5.0)
  -> WinElement._many_related("element.get_children", ...)
  -> ActionService.get_children_element(...)
  -> _run_win_tree_read(relation="children")
  -> UIA GetChildren()
  -> register_runtime_win_element(...)
  -> rt:win:* 元素描述列表
  -> list[Win32Element]
```

## 测试层级

```text
Pane：表单控件页（win32靶场表单面板）
├── 21 个元素库已抓取交互控件
│   ├── Edit：姓名、密码、邮箱、年龄、备注
│   ├── ComboBox：城市（单选）
│   ├── CheckBox：城市多选、兴趣多选、同意用户协议
│   ├── RadioButton：男、女、其他
│   └── Button：保存、重置
└── 12 个未抓取的静态文本等 UIA 直属元素

Button：保存（win32靶场保存按钮）
└── 无直属子元素
```

## 覆盖矩阵

| 场景 | 调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.children)` | 无公开参数，返回 `list[Win32Element]` | 符合 | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | 一致 | `PASS` |
| 面板直属子元素 | `panel.children()` | 返回非空列表 | 返回 33 项 | `PASS` |
| 返回对象 | 检查全部结果 | 均为 `children` 关系的 Runtime `Win32Element` | 33 项均符合 | `PASS` |
| 已抓取控件 | 检查 21 个名称和 ControlType | 全部包含在返回列表中 | 缺失 0 项 | `PASS` |
| 叶子元素 | `save_button.children()` | 返回空列表 | 返回 0 项 | `PASS` |
| 资源清理 | `package.close()` | 关闭借用连接，靶场保持运行 | 已完成 | `PASS` |

面板实际返回 33 个直属子元素，其中 21 个是元素库已经抓取的交互控件。测试把这 21 个
控件作为必须存在的子集，不把总数和返回顺序写成 API 合同，以允许 UIA 同时暴露静态
文本等未抓取节点。

## 首次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_children.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 面板元素：`win32靶场表单面板`
- 面板直属子元素：`33`
- 已抓取交互控件：`21/21` 均存在
- 返回对象：全部为 `children` 关系的 Runtime `Win32Element`
- 叶子元素：`win32靶场保存按钮` 返回空列表
- 总状态：`PASS`
- 通过数：`7/7`
- 总耗时：`593.0ms`
- Package：已关闭借用连接
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 递归获取后代元素；`children()` 只读取直属子元素。
- UIA 静态节点的固定数量以及所有直属子元素的固定顺序。
- 底层 `WinElement.children(timeout=...)` 的超时参数；高层 API 不暴露该参数。
- `child_at()`、`parent()`、`previous_sibling()` 和 `next_sibling()`。
- 关闭、激活或修改 Win32 靶场程序。
