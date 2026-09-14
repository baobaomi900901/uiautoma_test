# `uiautoma.web.WebElement.select_multiple_by_index()` 验证证据

```yaml
api: "uiautoma.web.WebElement.select_multiple_by_index"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_select_multiple_by_index_items_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.select_multiple_by_index unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.select_multiple_by_index 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.select_multiple_by_index"]
  verified_contract:
    signature: "select_multiple_by_index(indexes: list[int], *, append: bool = False, delay_after: float = 1) -> None"
    parameter_order: ["self", "indexes", "append", "delay_after"]
    defaults:
      append: false
      delay_after: 1
    indexes_required: true
    note: "append/delay_after 为仅关键字参数；当前实现直接 unsupported"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.select_multiple_by_index"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_select_multiple_by_index.py"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  select_element_name: "select_html_多选"
  reset_element_name: "重置_html"
  select_characteristics: "//input[@id='form-controls-native-cities']"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_select_multiple_by_index.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select_multiple_by_index.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_select_multiple_by_index.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：对 `select_html_多选` 直接调用
  `select_multiple_by_index(indexes, append=..., delay_after=...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.select_multiple_by_index
  -> raise UnsupportedActionError("web.element.select_multiple_by_index")
```

## 覆盖矩阵

| 场景 | 结果 | 说明 |
| --- | --- | --- |
| 公开签名 | `PASS` | `indexes` 必填；`append`/`delay_after` 仅关键字 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `select_html_多选` / `重置_html` |
| 索引多选探测 | `FAIL` | `UnsupportedActionError`（`web.element.select_multiple_by_index`） |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 靶场：`http://localhost:7199/form-controls`
- 元素：`select_html_多选`（`//input[@id='form-controls-native-cities']`）
- `select_multiple_by_index([1, 0], append=False)`：`UnsupportedActionError` /
  `web.element.select_multiple_by_index`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- `append=True` / `delay_after` 计时（实现接通后再验）。
- 原生 `<select multiple>`（当前控件为带 input 的多选 UI）。
- Ant Design / 组件库下拉框。
- Edge、CEF、Auto。

## 跟踪 Issue

- https://github.com/uiautoma/desktop/issues/18（`select_multiple_by_index`）
- https://github.com/uiautoma/desktop/issues/17（`select_multiple`，同批 stub）
