# `uiautoma.web.WebElement.children()` 验证证据

```yaml
api: "uiautoma.web.WebElement.children"
lifecycle: "VERIFIED"
verification_summary:
  chrome_children_via_parent_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.children 的最小 SDK、Runtime 与 DOM 子节点实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.children", "WebElement.parent"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.children", "WebElement._many_related", "LibrarySession._run_web_related"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_element_get_children"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_get_children_element", "ActionService._run_web_related"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "children(*, timeout=5.0) -> list[WebElement]"
    parameter_order: ["self", "timeout"]
    defaults:
      timeout: 5.0
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_children.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "442418e4ccc75f1e853df50b43dbcb07c88c6f10"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "cbcaba3f4b319cb9845a254ed0fd2ca06efc6370"
  seed_element_name: "九宫格_中"
source_commit_at_doc_time: "ed442beaaa11baccddac957bd12ae48ced6b0553"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_children.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_children.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_children.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

父元素与子元素 `print(...)` 输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及对种子
  元素调用 `parent()` 取得九宫格面板。
- 目标 API：只直接对父级调用无参 `WebElement.children()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.children
  -> RawWebElement.children
  -> LibrarySession._run_web_related("web.element.get_children")
  -> AutomationDispatcher._handle_web_element_get_children
  -> ActionService.web_get_children_element
  -> ActionService._run_web_related(relation="children")
  -> 浏览器插件/引擎在当前页面 DOM 上计算子节点
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、关键字参数种类、`list[WebElement]` 返回注解 |
| 靶场预检 | `PASS` | `/keys-click-test` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | `九宫格_中` 唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | 种子元素名称绑定正确 |
| `parent()` + `children()` | `PASS` | 父级 `div#position-grid-panel`；子列表 `9` 项且含 center |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 种子元素：`九宫格_中`
- 父级：`div#position-grid-panel`
- 子元素数：`9`
- 子元素名称：`div:左上 topLeft`、`div:上 top`、`div:右上 topRight`、`div:左 left`、
  `div:中 center`、`div:右 right`、`div:左下 bottomLeft`、`div:下 bottom`、
  `div:右下 bottomRight`
- 关系来源：当前页面 DOM 实时读取
- `children()` 调用耗时：约 `20.0ms`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- 显式传入非默认 `timeout`。
- 对种子元素直接调用 `children()`（本轮经 `parent` 再 `children`）。
- 子元素顺序与页面视觉九宫格方位一一对应的独立断言（本轮断言数量与名称集合）。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
