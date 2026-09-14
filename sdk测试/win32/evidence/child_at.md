# `uiautoma.win32.Win32Element.child_at()` 验证证据

## 最新复测：负数和越界索引仍未通过

依据测试者提供的运行日志及明确确认更新；生命周期维持 `READY_FOR_LIVE`。

```yaml
api: "uiautoma.win32.Win32Element.child_at"
lifecycle: "READY_FOR_LIVE"
passed: 7
failed: 2
total: 9
elapsed_ms: 596.3
exit_code: 1
tester_confirmed: true
verified: false
persistent_script:
  path: "win32/test_win32_child_at.py"
  sha256: "b75d77fd2514e130ade62f7fa23df3a919b5a32c7d71ffcc533f10b98d0b18ba"
  command: 'uv run .\win32\test_win32_child_at.py'
form_tab_helper:
  path: "win32/_form_tab.py"
  sha256: "7b27bd9faf78878eff6e049aa414ba8500595cc78d50140f2bbb75d0cd593bd1"
test_environment:
  library_dir: 'D:\code\元素库\260902_win元素'
  panel_element: "win32靶场_表单控件_表单面板"
  activated_tab: "win32靶场_tab_item表单控件"
  reference_children_count: 33
failures:
  - index: -1
    expected_exception: "ElementNotFoundError"
    actual_message: "child_not_found"
    actual_exception_class_in_printed_log: "not displayed"
  - index: 33
    expected_exception: "ElementNotFoundError"
    actual_message: "child_not_found"
    actual_exception_class_in_printed_log: "not displayed"
cleanup:
  status: "PASS"
  borrowed_package_closed: true
  application_left_running: true
tracking_issue: "https://github.com/uiautoma/desktop/issues/44"
```

| 测试项 | 结果 | 本次观察 | 耗时 |
| --- | --- | --- | --- |
| API 合同 | PASS | 必填 index: int，返回 Win32Element | 0.0ms |
| 当前元素库 | PASS | 元素库一致；准备步骤已激活表单页 | 207.4ms |
| 参照子元素 | PASS | 读取 33 个直属子元素作为索引参照 | 197.4ms |
| 首个索引 | PASS | child_at(0) 返回 TextControl“用户信息表单” | 41.1ms |
| 中间索引 | PASS | child_at(16) 返回 CheckBoxControl“深圳” | 38.3ms |
| 最后索引 | PASS | child_at(32) 返回 ButtonControl“重置” | 41.0ms |
| 负数索引 | FAIL | child_at(-1) 抛出非预期异常，消息 child_not_found | 35.2ms |
| 越界索引 | FAIL | child_at(33) 抛出非预期异常，消息 child_not_found | 35.1ms |
| 资源清理 | PASS | 借用 Package 已关闭；靶场保持运行 | 0.0ms |

本轮 `7/9` 通过、`2` 项失败，总耗时 `596.3ms`，退出码 `1`。
有效索引行为通过，负数与越界索引仍未满足 `ElementNotFoundError` 的验收条件。
本轮打印日志未显示具体异常类，不能仅凭消息将其重新断言为 `RpcProtocolError`；
该异常类型属于下方首次诊断的证据。继续关联已有 Issue #44，未重复提单或变更其状态。

以下保留首次诊断记录，其中旧元素名称、指纹、日期和耗时属于历史版本。
最新复测以上述记录为准；本次未修改产品源码或放宽测试断言。

## 首次诊断记录（历史：2026-09-04）

```yaml
api: "uiautoma.win32.Win32Element.child_at"
lifecycle: "READY_FOR_LIVE"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  reference_children: "PASS"
  first_index: "PASS"
  middle_index: "PASS"
  last_index: "PASS"
  negative_index: "FAIL"
  out_of_range_index: "FAIL"
  cleanup: "PASS"
  passed: 7
  failed: 2
  total: 9
  elapsed_ms: 453.3
  verified: false
  exit_code: 1
  blocking_issue:
    number: 44
    url: "https://github.com/uiautoma/desktop/issues/44"
    title: "Win32Element.child_at() 越界索引未映射为 ElementNotFoundError"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.child_at 的 SDK→Runtime→UIA 索引子元素路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.child_at"]
      fingerprint: "8f9d9a00fdf1f5a9c7ea0160186828bbaf094b32"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.child_at", "WinElement._single_related", "UIAutomaCoreClient._raise_business_error"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.get_child_at_element", "ActionService._run_win_tree_read"]
      fingerprint: "13643d467dfd4ea60a47a1129f886253e5e06756"
    - path: "runtime/services/package_service.py"
      symbols: ["PackageService.register_runtime_win_element", "PackageService._runtime_win_item"]
      fingerprint: "6902eb720dd10ae199a4ca93197d368e54ad6633"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_get_related_element"]
      fingerprint: "af181da49de2066a1bad99d74d91bb03fac25a67"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: "child_at(self, index: int) -> Win32Element"
    public_parameters:
      - name: "index"
        type: "int"
        required: true
        base: 0
    internal_timeout_seconds: 5.0
    relation: "child_at"
    runtime_operation: "UIA GetChildren()[index]"
    return_annotation: "Win32Element"
    returned_element_id_prefix: "rt:win:"
    returned_element_is_chainable: true
    status_model: ["PASS", "FAIL", "BLOCKED"]
  observed_error_mapping:
    runtime_trace: "child_not_found"
    actual_exception: "RpcProtocolError"
    expected_exception: "ElementNotFoundError"
    status: "FAIL"
open_defects:
  - issue: 44
    affected: "index < 0 或 index >= 直属子元素数量"
    root_cause: "UIAutomaCoreClient._raise_business_error 未映射 child_not_found"
    product_source_modified: false
persistent_script:
  path: "win32/test_win32_child_at.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "d8f6ffbbed53d57fbebe4ebde574c43d0bd66739150b2e67d317d846e13cd06b"
  command: 'uv run .\win32\test_win32_child_at.py'
test_environment:
  package_mode: "borrow current UIAutoma Package"
  library_dir: "D:\\code\\元素库\\260902_win元素"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  panel_element: "win32靶场表单面板"
  panel_direct_child_count: 33
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名包含必填 index: int，并返回 Win32Element"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 7.6
  reference_children:
    status: "PASS"
    count: 33
    elapsed_ms: 248.2
  first_index:
    status: "PASS"
    index: 0
    returned: "TextControl 用户信息表单"
    elapsed_ms: 42.8
  middle_index:
    status: "PASS"
    index: 16
    returned: "CheckBoxControl 深圳"
    elapsed_ms: 39.2
  last_index:
    status: "PASS"
    index: 32
    returned: "ButtonControl 重置"
    elapsed_ms: 40.6
  negative_index:
    status: "FAIL"
    index: -1
    actual_exception: "RpcProtocolError"
    trace_info: "child_not_found"
    elapsed_ms: 34.6
  out_of_range_index:
    status: "FAIL"
    index: 33
    actual_exception: "RpcProtocolError"
    trace_info: "child_not_found"
    elapsed_ms: 38.8
cleanup:
  status: "PASS"
  elapsed_ms: 0.1
  package_connection: "已关闭"
  target_application: "保持运行"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_child_at.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_child_at.py
```

脚本借用 UIAutoma 当前启用的测试元素库，以 `children()` 返回列表作为索引顺序参照，
再对相同面板调用 `child_at()`。测试不锁死 UIA 子元素的名称顺序，只校验指定索引返回
的元素与当次参照列表一致。

## API 参数

```python
child_at(index: int) -> Win32Element
```

- `index` 是唯一必填参数，公开类型为 `int`，从 `0` 开始计数。
- 高层实现调用 `int(index)` 后转给底层 `WinElement.child_at()`；可转换的非整数值属于
  当前实现细节，不作为公开合同验证。
- 底层查询使用固定的 `5s` 超时，高层 API 不暴露 `timeout` 参数。
- 有效索引返回新的 `Win32Element`，Runtime 关系为 `child_at`。
- Runtime 对负数或越界索引返回 `child_not_found`。当前 SDK 未将该 trace 映射为
  `ElementNotFoundError`，而是暴露 `RpcProtocolError`，详见 Issue
  [#44](https://github.com/uiautoma/desktop/issues/44)。

## 最小实现链

```text
Win32Element.child_at(index)
  -> WinElement.child_at(int(index), timeout=5.0)
  -> WinElement._single_related("element.get_child_at", index=index)
  -> ActionService.get_child_at_element(...)
  -> _run_win_tree_read(relation="child_at", index=index)
  -> UIA GetChildren()[index]
  -> register_runtime_win_element(...)
  -> rt:win:* 元素描述
  -> Win32Element
```

越界错误路径：

```text
index < 0 或 index >= len(GetChildren())
  -> child_not_found
  -> UIAutomaCoreClient._raise_business_error(...)
  -> 未命中 ElementNotFoundError 映射
  -> RpcProtocolError
```

## 覆盖矩阵

| 场景 | 调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.child_at)` | 必填 `index: int`，返回 `Win32Element` | 符合 | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | 一致 | `PASS` |
| 索引参照 | `panel.children()` | 至少 3 个直属子元素 | 返回 33 项 | `PASS` |
| 首个索引 | `panel.child_at(0)` | 与参照列表第 0 项一致 | TextControl“用户信息表单” | `PASS` |
| 中间索引 | `panel.child_at(16)` | 与参照列表第 16 项一致 | CheckBoxControl“深圳” | `PASS` |
| 最后索引 | `panel.child_at(32)` | 与参照列表第 32 项一致 | ButtonControl“重置” | `PASS` |
| 负数索引 | `panel.child_at(-1)` | `ElementNotFoundError` | `RpcProtocolError: child_not_found` | `FAIL` |
| 越界索引 | `panel.child_at(33)` | `ElementNotFoundError` | `RpcProtocolError: child_not_found` | `FAIL` |
| 资源清理 | `package.close()` | 关闭借用连接，靶场保持运行 | 已完成 | `PASS` |

## 缺陷结论

有效索引功能已经验证通过。阻塞项是 SDK 的错误映射：Runtime 已准确区分
`child_not_found`，但 `_raise_business_error()` 只将 `item_not_found`、
`element_not_found` 和 `image_not_found` 映射为 `ElementNotFoundError`。
`child_not_found` 因未被覆盖而落入通用 `RpcProtocolError`。

跟踪 Issue：[#44 Win32Element.child_at() 越界索引未映射为 ElementNotFoundError](https://github.com/uiautoma/desktop/issues/44)

## 首次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_child_at.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 面板元素：`win32靶场表单面板`
- 直属子元素：`33`
- 有效索引：`0`、`16`、`32` 均通过
- 越界索引：`-1`、`33` 均返回 `RpcProtocolError: child_not_found`
- 总状态：`FAIL`
- 通过数：`7/9`
- 失败数：`2/9`
- 总耗时：`453.3ms`
- Package：已关闭借用连接
- 靶场程序：保持运行
- 退出码：`1`
- 生命周期：`READY_FOR_LIVE`
- 产品源码修改：无

## 重新验收条件

- Issue #44 修复后，`child_at(-1)` 和 `child_at(直属子元素数量)` 均抛出
  `ElementNotFoundError`。
- 首项、中间项和末项索引仍返回正确的 Runtime `Win32Element`。
- 重新运行本脚本达到 `9/9` 通过后，生命周期升级为 `VERIFIED`。

## 明确排除

- 将数字字符串或小数传给 `index`；公开合同只承诺 `int`。
- 将当前 33 个 UIA 直属子元素的数量、名称和顺序固化为长期 API 合同。
- 底层 `WinElement.child_at(timeout=...)` 的超时参数；高层 API 不暴露该参数。
- `children()` 本身的完整功能；本脚本只用它建立当次索引参照。
- 关闭、激活或修改 Win32 靶场程序。
