# `uiautoma.web.WebElement.get_attribute()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_attribute"
lifecycle: "VERIFIED"
verification_summary:
  chrome_get_attribute_existing_placeholder_ok: "PASS"
  chrome_set_then_get_roundtrip_ok: "FAIL"
  cleanup: "PASS"
  verified: true
  verified_scope: "read existing attributes only; round-trip blocked by set_attribute"
  exit_code: 1
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_attribute 的最小 SDK、Runtime 与 DOM 属性读取实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_attribute"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.get_attribute"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_get_attribute"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_get_attribute_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "get_attribute(name: str) -> str"
    parameter_order: ["self", "name"]
    defaults: {}
    name_required: true
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_set_attribute_get_attribute.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "7b4aba2385b4c10f1bef28ccedac28ba4928554c"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "45299a1c5e4afa2bbfeb55cd24c424cff05dfbba"
  input_element_name: "input元素"
  expected_placeholder: "请输入文本"
source_commit_at_doc_time: "bd159d6c54ae7217fa5b58770363e57b4231e3a5"
```

## 持久化脚本

脚本与 `set_attribute` 共用：`tests/SDK/web/test_web_element_set_attribute_get_attribute.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_set_attribute_get_attribute.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_set_attribute_get_attribute.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API（本证据已验证范围）：对 `input元素` 直接调用 `get_attribute("placeholder")`。
- 往返场景中的 `set_attribute` 见 `set_attribute` 证据（当前 FAIL）。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.get_attribute
  -> RawWebElement.get_attribute
  -> AutomationDispatcher._handle_web_get_attribute
  -> ActionService.web_get_attribute_element
  -> 浏览器插件/引擎读取 DOM 属性
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `name` 必填、返回注解 `str` |
| 已有 `placeholder` | `PASS` | 值为 `请输入文本` |
| set→get 往返 | `FAIL` | 被 `set_attribute` 未实现阻塞 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- `get_attribute_existing_placeholder`：`PASS`
- 总退出码：`1`（同脚本 `set_attribute` 往返 FAIL）
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- 由 `set_attribute` 写入后再读取的往返（见 set_attribute / issue）。
- Edge、CEF、Auto。
- 空属性名负例、布尔属性序列化细节。
