# `uiautoma.win32.Win32Element.parent()` 验证证据

## 最新复测：新元素名称与自动切换表单页

本次依据测试者运行日志及明确确认更新，状态为 `VERIFIED`。

```yaml
api: "uiautoma.win32.Win32Element.parent"
lifecycle: "VERIFIED"
passed: 6
total: 6
elapsed_ms: 343.1
exit_code: 0
tester_confirmed: true
persistent_script:
  path: "win32/test_win32_parent.py"
  sha256: "0fec3b5fcd3c82b0fe5448388c9bd678e38cde2612625b5366a993a3577f4d77"
  command: 'uv run .\win32\test_win32_parent.py'
form_tab_helper:
  path: "win32/_form_tab.py"
  sha256: "7b27bd9faf78878eff6e049aa414ba8500595cc78d50140f2bbb75d0cd593bd1"
test_environment:
  library_dir: 'D:\code\元素库\260902_win元素'
  input_element: "win32靶场_表单控件_输入框_姓名"
  button_element: "win32靶场_表单控件_按钮_保存"
  activated_tab: "win32靶场_tab_item表单控件"
cleanup:
  status: "PASS"
  borrowed_package_closed: true
  application_left_running: true
```

| 测试项 | 本次结果 | 耗时 |
| --- | --- | --- |
| API 合同 | 无公开参数，返回 Win32Element | 0.0ms |
| 当前元素库 | 测试库一致；准备步骤已激活表单页 | 194.1ms |
| 输入框父元素 | Pane“表单控件页”，Runtime ID 有效 | 72.8ms |
| 保存按钮父元素 | Pane“表单控件页”，Runtime ID 有效 | 67.1ms |
| 链式父元素 | Pane 继续调用 parent() 得到 Tab | 8.4ms |
| 资源清理 | 借用 Package 已关闭；靶场保持运行 | 0.0ms |

六项均通过，总耗时 `343.1ms`，退出码 `0`。测试脚本参数为无。
当前脚本通过 `_form_tab.ensure_form_tab()` 点击表单 Tab，并读取原生 Tab 选中索引
确认准备完成。父级和链式父级的原有断言保持不变。
本次清理仅验证 Package 关闭和靶场保持运行，不宣称恢复原 Tab、鼠标或前台窗口。

以下保留首次验收记录用于追溯，其中旧元素名称、源码指纹、脚本指纹、日期和耗时
属于历史版本；最新复测应以上述记录为准。本次未重新审计底层源码，也未修改产品源码。

## 首次验收记录（历史：2026-09-04）

```yaml
api: "uiautoma.win32.Win32Element.parent"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  input_parent: "PASS"
  button_parent: "PASS"
  chained_parent: "PASS"
  runtime_element_identity: "PASS"
  cleanup: "PASS"
  passed: 6
  total: 6
  elapsed_ms: 279.3
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.parent 的 SDK→Runtime→UIA 父元素路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.parent"]
      fingerprint: "8f9d9a00fdf1f5a9c7ea0160186828bbaf094b32"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.parent", "WinElement._single_related"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.get_parent_element", "ActionService._run_win_tree_read"]
      fingerprint: "13643d467dfd4ea60a47a1129f886253e5e06756"
    - path: "runtime/services/package_service.py"
      symbols: ["PackageService.register_runtime_win_element", "PackageService._runtime_win_item"]
      fingerprint: "6902eb720dd10ae199a4ca93197d368e54ad6633"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_get_related_element"]
      fingerprint: "af181da49de2066a1bad99d74d91bb03fac25a67"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "parent(self) -> Win32Element"
    public_parameters: []
    internal_timeout_seconds: 5.0
    relation: "parent"
    runtime_operation: "UIA GetParentControl()"
    return_annotation: "Win32Element"
    returned_element_id_prefix: "rt:win:"
    returned_element_is_chainable: true
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_parent.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "c7bec2090b47fbdedfb4eb3779f3fe97cd4fcea0dd3e7b905c426dfb39b5daec"
  command: 'uv run .\win32\test_win32_parent.py'
test_environment:
  package_mode: "borrow current UIAutoma Package"
  library_dir: "D:\\code\\元素库\\260902_win元素"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  input_element: "win32靶场输入框"
  button_element: "win32靶场保存按钮"
  expected_direct_parent:
    name: "表单控件页"
    control_type: "Pane"
  expected_chained_parent:
    control_type: "Tab"
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名无参数并返回 Win32Element"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 8.7
  input_parent:
    status: "PASS"
    child: "win32靶场输入框"
    parent_name: "表单控件页"
    parent_control_type: "Pane"
    runtime_id_valid: true
    relation: "parent"
    elapsed_ms: 141.1
  button_parent:
    status: "PASS"
    child: "win32靶场保存按钮"
    parent_name: "表单控件页"
    parent_control_type: "Pane"
    runtime_id_valid: true
    relation: "parent"
    elapsed_ms: 121.7
  chained_parent:
    status: "PASS"
    source_control_type: "Pane"
    parent_control_type: "Tab"
    returned_element_is_chainable: true
    runtime_id_valid: true
    relation: "parent"
    elapsed_ms: 6.8
cleanup:
  status: "PASS"
  elapsed_ms: 0.1
  package_connection: "已关闭"
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_parent.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_parent.py
```

脚本借用 UIAutoma 当前启用的测试元素库，不重新调用 `uiautoma.open()`，从而避免把
Desktop 当前元素库切换成只读状态。元素定位使用 `win32.find()` 作为场景准备；实际
关系测试只调用无参数的 `Win32Element.parent()`。

## API 参数

```python
parent() -> Win32Element
```

- `parent()` 没有公开参数。
- 高层实现调用底层 `WinElement.parent()`，内部使用固定的 `5s` 超时。
- Runtime 通过 UIA `GetParentControl()` 获取直接父元素。
- 成功返回新的 `Win32Element`，运行时元素 ID以 `rt:win:` 开头。
- 返回对象可以继续调用元素 API，包括再次调用 `parent()`。
- 未找到父元素时抛出 `ElementNotFoundError`。

## 最小实现链

```text
Win32Element.parent()
  -> WinElement.parent(timeout=5.0)
  -> UIAutomaCoreClient element.get_parent
  -> ActionService.get_parent_element(...)
  -> _run_win_tree_read(relation="parent")
  -> UIA GetParentControl()
  -> register_runtime_win_element(...)
  -> rt:win:* 元素描述
  -> Win32Element
```

## 测试层级

```text
Tab
└── Pane：表单控件页
    ├── Edit：姓名（win32靶场输入框）
    └── Button：保存（win32靶场保存按钮）
```

## 覆盖矩阵

| 场景 | 调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.parent)` | 无公开参数，返回 `Win32Element` | 符合 | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | 一致 | `PASS` |
| 输入框父元素 | `input_element.parent()` | Pane“表单控件页” | Pane“表单控件页”，Runtime ID有效 | `PASS` |
| 保存按钮父元素 | `button_element.parent()` | Pane“表单控件页” | Pane“表单控件页”，Runtime ID有效 | `PASS` |
| 链式父元素 | `input_parent.parent()` | 返回 Tab | 返回 Tab，且对象可继续调用 | `PASS` |
| 资源清理 | `package.close()` | 关闭借用连接，靶场保持运行 | 已完成 | `PASS` |

## 首次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_parent.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试对象：`win32靶场输入框`、`win32靶场保存按钮`
- 两个直接父元素：均为 Pane“表单控件页”，Runtime ID有效
- 链式父元素：从 Pane 再次调用 `parent()` 得到 Tab
- 总状态：`PASS`
- 通过数：`6/6`
- 总耗时：`279.3ms`
- Package：已关闭借用连接
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 根元素无父级时的异常场景。
- 底层 `WinElement.parent(timeout=...)` 的超时参数；高层 API不暴露该参数。
- `children()`、`child_at()`、`previous_sibling()` 和 `next_sibling()`。
- 关闭、激活或修改 Win32 靶场程序。
