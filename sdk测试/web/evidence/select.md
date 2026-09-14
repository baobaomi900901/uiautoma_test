# `uiautoma.web.WebElement.select()` 验证证据

```yaml
api: "uiautoma.web.WebElement.select"
lifecycle: "VERIFIED"
verification_summary:
  chrome_select_fuzzy_shanghai_ok: "PASS"
  chrome_select_exact_beijing_ok: "PASS"
  chrome_select_value_shanghai_ok: "PASS"
  chrome_select_fuzzy_delay_after_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.select 的最小 SDK、Runtime 与 DOM select 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.select", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.select"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_select"]
      fingerprint: "23a56351fce260eaccdfa8a4465519e0ffd85a73"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_select_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "select(item: str, *, mode: str = 'fuzzy', delay_after: float = 1) -> None"
    parameter_order: ["self", "item", "mode", "delay_after"]
    defaults:
      mode: "fuzzy"
      delay_after: 1
    item_required: true
    mode_values: ["fuzzy", "exact", "value"]
    note: "mode/delay_after 为仅关键字参数；不支持 regex"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_select.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "ec5ed92375e34da735d77229c5d2398bd5d7c3fa"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "ca318ee0b1f358e39b7b061de278aa9200a562ec"
  select_element_name: "select_html"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
source_commit_at_doc_time: "39dfab9ce9b6b18ccefdcfdf3e632584d21919ef"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_select.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`；`finally` 中删除该副本。选择步骤日志输出到 stderr。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` / `提交_html` 的 `click()`。
- 目标 API：只对 `select_html` 直接调用 `WebElement.select(...)`。
- 验收 API：`get_value()` 与剪贴板表单 JSON 的 `city`（非目标合同）。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.select
  -> RawWebElement.select
  -> AutomationDispatcher._handle_web_action_select
  -> ActionService.web_select_element
  -> page_engine selectOption
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `item` 必填；`mode`/`delay_after` 仅关键字与默认值 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与三库项可用 |
| 页面与库连接 | `PASS` | 绑定成功 |
| fuzzy `上海` | `PASS` | `value`/`city`=`shanghai` |
| exact `北京` | `PASS` | `value`/`city`=`beijing` |
| value `shanghai` | `PASS` | `value`/`city`=`shanghai` |
| fuzzy `delay_after=1` | `PASS` | 耗时 ≥900ms 且选中正确 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- `select_fuzzy_shanghai`：约 `278.2ms`
- `select_exact_beijing`：约 `282.3ms`
- `select_value_shanghai`：约 `291.2ms`
- `select_fuzzy_delay_after`：约 `1026.7ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- `mode="regex"`（公开合同抛 `InvalidParamsError`）。
- Ant Design / 组件库下拉框。
- Edge、CEF、Auto。
