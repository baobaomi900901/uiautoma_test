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

## 2026-09-15：innerText 语义矩阵复验（35/35，连续 3 次退出码 0）

脚本：`web/test_web_element_get_text.py`（独立于上面那份 8/8 脚本，两者都在本工作区保留）
原始产物：[`artifacts/element_get_text_20260915.txt`](artifacts/element_get_text_20260915.txt)

靶场：`https://baobaomi900901.github.io/xpath/#/element-html-test`（维护者官方靶场）
元素库：`D:\code\元素库\260902_web元素`，其中为本次验收准备了 4 条 web 元素；
脚本先 `find(名称)` 再用 `get_attribute("id")` 核对指向，实测均命中预期节点：

| 库元素名 | 实测指向 |
|---|---|
| `web靶场_测试get_text_靶元素` | `#element-html-target` |
| `web靶场_测试get_text_按钮_确定` | `#element-html-apply` |
| `web靶场_测试get_text_按钮_重置` | `#element-html-reset` |
| `web靶场_测试get_text_输入框` | `#element-html-input` |

**期望值来源（两类，互不依赖）**：
1. 受控 fixture —— 脚本往靶元素注入 HTML，期望值按 `innerText` 的**公开语义**手写推导，
   **不拿浏览器的 `innerText` 当答案**（浏览器值只作为报告里的对照）；
2. 真实页面元素（按钮等无法手推期望值的）—— 断言等于浏览器自身 `innerText`，
   这正是源码声明的 `text_strategy: "innerText"`。

主路线走**库元素名称目标**，另有 CSS 路线对照，两条路线结果一致。

| 场景 | 实测结果 | 与 `textContent` 的差异 |
|---|---|---|
| 纯文本 `<span>str</span>` | `'str'` | — |
| 行内嵌套 `<b>加粗</b><i>斜体</i><span>后缀</span>` | `'加粗斜体后缀'` | 无分隔符 |
| 块级 `<div>第一行</div><div>第二行</div>` | `'第一行\n第二行'` | textContent 无换行 |
| `<br>` 换行 | `'第一行\n第二行'` | 同上 |
| **`display:none` 子元素** | `'可见'`（隐藏文本不计入） | textContent 为 `'可见隐藏'` |
| **`visibility:hidden` 子元素** | `'可见'` | textContent 为 `'可见半隐藏'` |
| 连续空白 `a     b\t\tc` | `'a b c'`（折叠） | textContent 保留原样 |
| `&nbsp;` | `'a\xa0b'`（保留 U+00A0） | 一致 |
| **`<script>`/`<style>`** | `'正文'`（内容不计入） | textContent 含脚本与样式文本 |
| 空 `<span></span>` | `''`（空字符串，非 `None`） | — |
| `<pre>a\nb</pre>` | `'a\nb'` | — |
| 行内 + 块级混合 | `'标题后缀\n次行'` | textContent 无换行 |
| **`<input value='输入值'>`** | `'输入值'`（`innerText` 为空时回退取 `value`） | — |
| `<textarea>` 多行 | `'多行\n文本'`（同上回退） | — |
| 普通 `<button>` | `'确 定'`（原样，保留空格） | — |
| **1200 字符长文本** | 完整返回（`len=1200`，**不截断**） | — |

其余用例：`「确定」/「重置」` 按钮经库元素读取与浏览器 `innerText` 一致
（`'确 定'` / `'重 置'`）；经页面自身流程（输入 `<b>流程</b>验证` → 点「确定」）后
库元素读到 `'流程验证'`；节点被移除后再 `get_text()` 抛
`ActionError: 未找到指定ID的元素`（0.003s）；多余位置参数与未知关键字均 `TypeError`；
页面关闭后抛 `ActionError: 网页对象已失效`；清理复核无残留。

**本次填补了本文件原先列入「明确排除」的两项**：空文本元素与不可见元素负例（见下方修订说明）。

## 明确排除（2026-09-15 修订）

- Edge、CEF 和 Auto 真实行为。
- ~~空文本或不可见元素负例~~ —— **已由上面的语义矩阵覆盖**（空 `<span>` → `''`；
  `display:none` / `visibility:hidden` 子文本不计入）。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
- `get_text()` 与 `get_html()`/`get_value()` 三者的组合语义：本文件只覆盖 `get_text()`。
- 超长文本的**边界值**（本次覆盖 1200 字符；更大规模与 Runtime 报文上限未构造）。
