# `uiautoma.web.WebElement.get_selected_item()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_selected_item"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_get_selected_item_after_reset_ok: "FAIL"
  chrome_get_selected_item_after_select_shanghai_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.get_selected_item unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_selected_item 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_selected_item"]
      fingerprint: "4b6e99fdafe1c3a18c71761df0b6fe4cc3356f4b"
  verified_contract:
    signature: "get_selected_item() -> list[str]"
    parameter_order: ["self"]
    defaults: {}
    return_annotation: "list[str]"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.get_selected_item"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_get_selected_item.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "470ba96eaea9f2e5661a0b36bb82fafc61cfac28"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "a77c5aaeeee8781799d06fb12237ec84ca2755e7"
  select_element_name: "select_html"
  reset_element_name: "重置_html"
  select_characteristics: "//select[@id='form-controls-native-city']"
  expected_selected_after_reset: ["请选择城市"]
  expected_selected_after_select_shanghai: ["上海"]
source_commit_at_doc_time: "16f2e338b123cbac891ecf5ff7fc9867efe8cac1"
known_issue: "https://github.com/uiautoma/desktop/issues/28"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_selected_item.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_selected_item.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_get_selected_item.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，
  `重置_html.click()`，以及非目标 API `select("上海", mode="fuzzy")`。
- 目标 API：对 `select_html` 直接调用 `get_selected_item()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.get_selected_item
  -> raise UnsupportedActionError("web.element.get_selected_item")
```

公开签名存在，但 SDK facade 尚未接到 Runtime / Page Engine 选中项读取通道。同批
`get_select_options`（#19）/ `get_all_select_items` 亦为显式 unsupported。

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| 公开签名 | `PASS` | 无参；`list[str]` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html` / `重置_html` |
| 重置后读取选中项 | `FAIL` | `UnsupportedActionError` |
| `select("上海")` 后读取 | `FAIL` | `UnsupportedActionError` |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`
- 产品源码修改：无

## 明确排除

- `select_html_多选` 多选选中列表
- Ant / 组件库下拉
- Edge、CEF、Auto

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/28
