# `uiautoma.web.WebElement.get_select_options()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_select_options"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_get_select_options_after_reset_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.get_select_options unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_select_options 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_select_options"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
  verified_contract:
    signature: "get_select_options() -> list[tuple[Any, ...]]"
    parameter_order: ["self"]
    defaults: {}
    note: "用户合同 List[Tuple]（选项文本，选项值，被选中状态）；当前实现直接 unsupported"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.get_select_options"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_get_select_options.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "8f7c3a13c8891508e8a3fa43ece8d816d9f4edb4"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "58086849245009d8662dddc5b6a068d019ed74a3"
  select_element_name: "select_html"
  reset_element_name: "重置_html"
  select_characteristics: "//select[@id='form-controls-native-city']"
source_commit_at_doc_time: "c1dbcac3eedd3405f4cd4ff99a3efc13fa9a1111"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_select_options.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_select_options.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_get_select_options.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：对 `select_html` 直接调用 `get_select_options()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.get_select_options
  -> raise UnsupportedActionError("web.element.get_select_options")
```

公开签名存在，但 SDK facade 尚未接到 Runtime / Page Engine 选项读取通道。同文件
`get_all_select_items` / `get_selected_item` 亦为显式 unsupported。

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| 公开签名 | `PASS` | 无参；返回注解为 `list[tuple[Any, ...]]` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html` / `重置_html` |
| 重置后读取选项 | `FAIL` | `UnsupportedActionError`（`web.element.get_select_options`） |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 靶场：`http://localhost:7199/form-controls`
- 元素：`select_html`（`//select[@id='form-controls-native-city']`）
- `get_select_options_after_reset`：`UnsupportedActionError` / `web.element.get_select_options`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- 选中后选项列表变化（接通后再验）。
- `select_html_多选` / Ant Design / 组件库下拉框。
- Edge、CEF、Auto。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/19
