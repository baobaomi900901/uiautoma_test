# `uiautoma.web.WebElement.get_text()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_text"
lifecycle: "VERIFIED"
verification_summary:
  chrome_get_text_default_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_text 的最小 SDK、Runtime 与 DOM 文本读取实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_text"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.get_text"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_get_text"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_get_text_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "get_text() -> str"
    parameter_order: ["self"]
    defaults: {}
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_get_text.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "2b6e1c340eb92b0698604f01d37c0b7d71122aa4"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "3ee077f87318ea7d9a8310aeadf7500f2e89f237"
  seed_element_name: "get_text元素"
  expected_text: "每次刷新页面, 所有控件的 id 都会随机变化; label 文字固定, 可作为锚点定位"
source_commit_at_doc_time: "867001b0b2d050d60b85d392fc7ab11dca08297a"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_text.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_text.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_text.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

`get_text()` 结果的 `print(...)` 输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：只对种子元素直接调用无参 `WebElement.get_text()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.get_text
  -> RawWebElement.get_text
  -> AutomationDispatcher._handle_web_get_text
  -> ActionService.web_get_text_element
  -> 浏览器插件/引擎在当前页面 DOM 上读取文本
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 仅 `self`、返回注解 `str` |
| 靶场预检 | `PASS` | `/form-controls` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | `get_text元素` 唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | 种子元素名称绑定正确 |
| 无参 `get_text()` | `PASS` | 全文精确匹配提示条文案 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 种子元素：`get_text元素`
- 返回文本：`每次刷新页面, 所有控件的 id 都会随机变化; label 文字固定, 可作为锚点定位`
- `get_text()` 调用耗时：约 `18.7ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 2026-09-15：元素 HTML 靶场复测

脚本：`web/test_web_element_get_text_html.py`

结果：**8/8 通过，退出码 0**。普通文本与 Unicode、特殊字符、`div → span → label`
三层嵌套 HTML 均已通过 `get_text()` 与独立 DOM `innerText` 对比；每个场景重置后，
输入框为空且靶元素恢复为 `等待渲染 HTML…`。额外位置参数被 `TypeError` 拒绝，Package
和测试页面已清理。

测试结论已确认：`WebElement.get_text()` 初次验收通过，状态为 `VERIFIED`。

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- 空文本或不可见元素负例。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
