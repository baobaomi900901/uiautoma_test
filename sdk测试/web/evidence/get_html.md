# `uiautoma.web.WebElement.get_html()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_html"
lifecycle: "VERIFIED"
verification_summary:
  chrome_baidu_get_html_default_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_html 的最小 SDK、Runtime 与 DOM HTML 读取实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_html"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.get_html"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_get_html"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_get_html_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "get_html() -> str"
    parameter_order: ["self"]
    defaults: {}
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_get_html.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "42808f2d396f5cc895db6f0369c8e226b48fa284"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "8281c519e8dc529f039a3b58c17219eb57189f47"
  seed_element_name: "百度一下"
  target_url: "https://www.baidu.com/"
  expected_html_substrs: ["百度一下", "id=\"su\""]
source_commit_at_doc_time: "b3bcb48dd9840884b356936a8d5571c49034aa84"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_html.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_html.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_html.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

`get_html()` 结果的 `print(...)` 输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：只对种子元素直接调用无参 `WebElement.get_html()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.get_html
  -> RawWebElement.get_html
  -> AutomationDispatcher._handle_web_get_html
  -> ActionService.web_get_html_element
  -> 浏览器插件/引擎在当前页面 DOM 上读取 outerHTML
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 仅 `self`、返回注解 `str` |
| 靶场预检 | `PASS` | `https://www.baidu.com/` 可访问 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | `百度一下` 唯一命中且 URL 匹配 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | Chrome 打开百度首页 |
| 元素库连接 | `PASS` | 种子元素名称绑定正确 |
| 无参 `get_html()` | `PASS` | HTML 含 `百度一下` 与 `id="su"` |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`https://www.baidu.com/`
- 种子元素：`百度一下`（`//input[@id="su"]`）
- 返回 HTML：`<input type="submit" value="百度一下" id="su" class="btn self-btn bg s_btn">`
- `get_html()` 调用耗时：约 `39.1ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- 完整 outerHTML 精确匹配（class 可能随百度改版变化）。
- 空 HTML 负例。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
