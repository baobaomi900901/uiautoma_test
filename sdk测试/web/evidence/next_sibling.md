# `uiautoma.web.WebElement.next_sibling()` 验证证据

```yaml
api: "uiautoma.web.WebElement.next_sibling"
lifecycle: "VERIFIED"
verification_summary:
  chrome_next_sibling_default_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.next_sibling 的最小 SDK、Runtime 与 DOM 兄弟节点实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.next_sibling"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.next_sibling", "WebElement._single_related", "LibrarySession._run_web_related"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_element_get_next_sibling"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_get_next_sibling_element", "ActionService._run_web_related"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "next_sibling(*, timeout=5.0) -> WebElement"
    parameter_order: ["self", "timeout"]
    defaults:
      timeout: 5.0
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_next_sibling.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "86b9fea7b599c7b8430e883df5dca39c66aa4eae"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "cbcaba3f4b319cb9845a254ed0fd2ca06efc6370"
  seed_element_name: "九宫格_中"
source_commit_at_doc_time: "8d381f945cf062b8e76d06b67e5241d8badff858"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_next_sibling.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_next_sibling.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_next_sibling.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

兄弟元素 `print(...)` 输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：只对种子元素直接调用无参 `WebElement.next_sibling()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.next_sibling
  -> RawWebElement.next_sibling
  -> LibrarySession._run_web_related("web.element.get_next_sibling")
  -> AutomationDispatcher._handle_web_element_get_next_sibling
  -> ActionService.web_get_next_sibling_element
  -> ActionService._run_web_related(relation="next_sibling")
  -> 浏览器插件/引擎在当前页面 DOM 上取下一个兄弟节点
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、关键字参数种类、`WebElement` 返回注解 |
| 靶场预检 | `PASS` | `/keys-click-test` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | `九宫格_中` 唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | 种子元素名称绑定正确 |
| 无参 `next_sibling()` | `PASS` | 返回 `div:右 right`，类型为 `WebElement` |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 种子元素：`九宫格_中`
- 兄弟元素：`div:右 right`
- 关系来源：当前页面 DOM 实时读取
- `next_sibling()` 调用耗时：约 `15.7ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- 显式传入非默认 `timeout`。
- 首尾格无下一个兄弟时的 `ElementNotFoundError` 负例。
- 兄弟元素与库项名称一一对应。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
