# `uiautoma.web.WebElement.set_attribute()` 验证证据

```yaml
api: "uiautoma.web.WebElement.set_attribute"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_set_then_get_roundtrip_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defect: "web.element.set_attribute unsupported"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.set_attribute 的公开签名与当前 SDK 未实现行为"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.set_attribute"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
  verified_contract:
    signature: "set_attribute(name: str, value: str) -> None"
    parameter_order: ["self", "name", "value"]
    defaults: {}
    name_required: true
    value_required: true
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web.element.set_attribute"
      message: "当前版本暂不支持"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_set_attribute_get_attribute.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "7b4aba2385b4c10f1bef28ccedac28ba4928554c"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "45299a1c5e4afa2bbfeb55cd24c424cff05dfbba"
  input_element_name: "input元素"
  sample_attr_name: "data-uiautoma-sdk"
source_commit_at_doc_time: "bd159d6c54ae7217fa5b58770363e57b4231e3a5"
```

## 持久化脚本

脚本与 `get_attribute` 共用：`tests/SDK/web/test_web_element_set_attribute_get_attribute.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_set_attribute_get_attribute.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_set_attribute_get_attribute.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：对 `input元素` 直接调用 `set_attribute(name, value)`。
- 验收 API：`get_attribute(name)`（往返核对）。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链（当前缺口）

```text
uiautoma.web.WebElement.set_attribute
  -> raise UnsupportedActionError("web.element.set_attribute")
```

公开签名存在，但 SDK facade 尚未接到 Runtime / Page Engine 属性写入通道。架构文档亦将
`set_attribute` 列为显式 unsupported。

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `name`/`value` 必填、返回注解 `None` |
| set→get 往返 | `FAIL` | `UnsupportedActionError` |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`（阻塞 `VERIFIED`）
- `set_attribute_then_get_attribute`：`FAIL`，`UnsupportedActionError`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- 任意真实属性写入语义（实现前无法验收）。
- Edge、CEF、Auto。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/14
