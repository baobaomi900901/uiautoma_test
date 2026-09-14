# `uiautoma.web.WebElement.select_by_index()` 验证证据

```yaml
api: "uiautoma.web.WebElement.select_by_index"
lifecycle: "VERIFIED"
verification_summary:
  chrome_select_by_index_beijing_ok: "PASS"
  chrome_select_by_index_shanghai_ok: "PASS"
  chrome_select_by_index_placeholder_ok: "PASS"
  chrome_select_by_index_delay_after_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.select_by_index 的最小 SDK、Runtime 与 DOM select 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.select_by_index", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.select_by_index"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_select"]
      fingerprint: "23a56351fce260eaccdfa8a4465519e0ffd85a73"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_select_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "select_by_index(index: int, delay_after: float = 1) -> None"
    parameter_order: ["self", "index", "delay_after"]
    defaults:
      delay_after: 1
    index_required: true
    note: "index/delay_after 均为位置或关键字参数；index 从 0 开始"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_select_by_index.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "1147f0a45fce2b95c45b44429b288d0a0b6b0af8"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "ca318ee0b1f358e39b7b061de278aa9200a562ec"
  select_element_name: "select_html"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
source_commit_at_doc_time: "39dfab9ce9b6b18ccefdcfdf3e632584d21919ef"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_select_by_index.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select_by_index.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_select_by_index.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`；`finally` 中删除该副本。选择步骤日志输出到 stderr。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` / `提交_html` 的 `click()`。
- 目标 API：只对 `select_html` 直接调用 `WebElement.select_by_index(...)`。
- 验收 API：`get_value()` 与剪贴板表单 JSON 的 `city`（非目标合同）。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.select_by_index
  -> RawWebElement.select_by_index
  -> AutomationDispatcher._handle_web_action_select
  -> ActionService.web_select_element (index=...)
  -> page_engine selectOptionByIndex
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `index` 必填；`delay_after` 默认 `1` |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与三库项可用 |
| 页面与库连接 | `PASS` | 绑定成功 |
| index `1` | `PASS` | `value`/`city`=`beijing` |
| index `2` | `PASS` | `value`/`city`=`shanghai` |
| index `0` | `PASS` | `value`/`city`=`""` |
| `delay_after=1` | `PASS` | 耗时 ≥900ms 且选中正确 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- `select_by_index_beijing`：约 `282.5ms`
- `select_by_index_shanghai`：约 `283.5ms`
- `select_by_index_placeholder`：约 `288.0ms`
- `select_by_index_delay_after`：约 `1026.3ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- 越界 index（`option_not_found`）负例矩阵。
- Ant Design / 组件库下拉框。
- Edge、CEF、Auto。
