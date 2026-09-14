# `uiautoma.web.WebElement.get_all_attributes()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_all_attributes"
lifecycle: "VERIFIED"
verification_summary:
  chrome_get_all_attributes_input_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_all_attributes 的最小 SDK、Runtime 与 DOM 全量属性读取实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_all_attributes"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.get_all_attributes"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_get_all_attributes"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_get_all_attributes_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "get_all_attributes() -> dict[str, str]"
    parameter_order: ["self"]
    defaults: {}
    return_type: "dict[str, str]"
    note: "公开 Web 合同不是 List[Tuple]"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_get_all_attributes.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "cdceaec110601563bd4d92cc9d53f216e0aa7da0"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "45299a1c5e4afa2bbfeb55cd24c424cff05dfbba"
  input_element_name: "input元素"
  expected_placeholder: "请输入文本"
  expected_type: "text"
  sample_attribute_keys: ["id", "placeholder", "style", "type"]
source_commit_at_doc_time: "f079e51b6800cee0f95788d9cf1334497bdb1b71"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_all_attributes.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_all_attributes.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_all_attributes.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`；`finally` 中删除该副本。结果输出到 stderr，stdout 为 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：只对 `input元素` 直接调用无参 `WebElement.get_all_attributes()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.get_all_attributes
  -> RawWebElement.get_all_attributes
  -> AutomationDispatcher._handle_web_get_all_attributes
  -> ActionService.web_get_all_attributes_element
  -> 浏览器插件/引擎枚举 DOM 属性
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 仅 `self`、返回注解 `dict[str, str]` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 `input元素` / `重置_html` |
| 无参 `get_all_attributes()` | `PASS` | dict + placeholder/type/id |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- `get_all_attributes_input`：约 `6.0ms`，键含 `id`/`placeholder`/`style`/`type`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- 返回 `List[Tuple]`（非当前 Web 公开合同）。
- 对完整属性集合做精确相等（`style`/`id` 会变）。
- 强制要求结果包含空 `value` 键。
- Edge、CEF、Auto。
