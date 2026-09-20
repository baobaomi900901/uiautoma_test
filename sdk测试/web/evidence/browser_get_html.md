# `WebBrowser.get_html()` 验收证据

## 1. 用途与合同

读取当前网页**主框架**的 HTML 源码（`document.documentElement.outerHTML` 序列化结果）。

```python
WebBrowser.get_html(self) -> str
```

公开签名**没有任何参数**（`self` 之外无位置参数、无关键字参数、无默认值）。返回原生 `str`；
SDK 取 RPC 结果的 `html` 字段，缺失时回退 `value`，再回退空串，因此**不会返回 `None`**。

完整链路（检出目录 `D:\code\desktop`，基线 commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`）：

| 层 | 位置 | 事实 |
| --- | --- | --- |
| SDK 公开对象 | `sdk/src/uiautoma/web/browser.py:95` | `get_html(self) -> str`，调用时固定传 `timeout_ms=5000` |
| SDK 客户端 | `sdk/src/uiautoma/_core/client.py:1248` | `web_get_browser_html(*, mode, page_url, target_browser, target_session_id, page_ref, target_tab_id, timeout_ms=2000)` |
| RPC 名 | `sdk/src/uiautoma/_core/client.py:47` | `web.browser.get_html` |
| 能力位 | `runtime/services/capabilities.py:320,506` | `RpcMethodSpec("web.browser.get_html", "_handle_web_browser_get_html", ("timeout_ms",))`；capability `web_browser_capabilities_stage4` |
| Runtime 分发 | `runtime/services/pipe_server.py:1906` | `_handle_web_browser_get_html` → `action_service.web_browser_get_html` |
| Runtime 业务 | `runtime/services/action_service.py:2891` → `5539` | `_run_web_browser_command(command="get_html")`：校验 `mode`、取整 `timeout_ms`、剔除 `package_token`/`element_id`/`state_revision`/`package_variables`、把 `page_ref` 解析成实时目标；失效返回 `stale_page_reference` |
| 引擎 | `chrome/engine/plugin_packages/browser_command_package.js:1619` | `command === "get_html"` → 选目标标签页 → `readTabHtml(tab, false)` |
| 引擎实现 | 同文件 `:537-548` | `chrome.scripting.executeScript({target:{tabId, frameIds:[0]}, func: text => text ? innerText : documentElement.outerHTML})` |

**要点：`frameIds: [0]` 意味着只读主框架；`get_html` 与 `get_text` 共用同一函数，由 `text` 布尔量分流**，而 SDK 侧没有暴露该开关。

## 2. 真实验收结果

**VERIFIED：17/17 通过，退出码 0；连续 3 次完整运行全绿（2026-09-20）。**

- 靶场：<https://baobaomi900901.github.io/xpath/#/element-html-test>（主 fixture）、
  `#/iframe-shadow-form`（帧作用域）、`chrome://newtab/`（非脚本化页面边界）。
- 元素库：**不需要**。`WebBrowser.get_html()` 不依赖 Package/元素库，脚本不复制也不打开元素库。
- 被测 worktree：`D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`；
  该 commit 下 `sdk/`、`runtime/`、`chrome/` 三个目录无本地改动
  （工作区仅有测试台 `build-test.py` 临时替换的 Provider 二进制与 manifest，来源 rust_uia `ec67117b`）。
- Runtime：`UIAutoma Runtime 0.1.0`，protocol 1，`web_browser_capabilities_stage4` 已声明。
- 脚本：[test_web_browser_get_html.py](../test_web_browser_get_html.py)。
- 原始输出：[artifacts/browser_get_html_20260920.txt](artifacts/browser_get_html_20260920.txt)。

| # | 用例 | 检查内容 | 实测结果 |
| --- | --- | --- | --- |
| 01 | `api_contract` | 签名 `(self)`、无参数、返回 `str` | 通过；`(self) -> 'str'` |
| 02 | `env_baseline` | Runtime 版本/协议、进入时标签基线 | 通过；协议 1，15 个标签 |
| 03 | `page_prepare` | fixture 打开且标题符合源码 | 通过；`url=…#/element-html-test`，`title='元素 HTML 测试'` |
| 04 | `return_type_nonempty` | 返回原生非空 `str` | 通过；长度 117307 |
| 05 | `outerhtml_semantics` | 与实时 `documentElement.outerHTML` 逐字节相等；不含 DOCTYPE | 通过；delta=0，实时 `document.doctype.name='html'` 但返回串不以 `<!DOCTYPE` 开头 |
| 06 | `authored_ids_present` | 靶场源码写死的 6 个固定 id | 通过 |
| 07 | `independent_parse` | 标准库解析计数/id 集合 vs 浏览器实时 DOM | 通过；47 == 47，id 集合完全一致 |
| 08 | `repeat_read_stable` | 空闲态连续 4 次读取 | 通过；4 次逐字节一致 |
| 09 | `live_mutation_visible` | CDP 改 DOM 后 `get_html` 必须读回 | 通过；增量 120 vs 手写 120（预算内） |
| 10 | `live_cleanup_restores` | 撤销后内容还原 | 通过；标记消失、固定 id 与计数不变、长度偏差 -2（预算内） |
| 11 | `param_positional` | 多余位置参数 | 通过；`TypeError: takes 1 positional argument but 2 were given` |
| 12 | `param_keyword` | 未声明关键字 | 通过；`TypeError: got an unexpected keyword argument 'timeout'` |
| 13 | `silent_background_read` | `silent_running=True` 后台标签页 | 通过；可读，长度 117305 |
| 14 | `iframe_frame_scope` | 只读主框架 | 通过；主文档含 iframe 元素但不含 iframe 内部 id `form-shadow-host`，而 iframe 文档自身确有该 id（shadow 子节点 36） |
| 15 | `unsupported_url` | 非脚本化真实页面 | 通过；`ActionError` trace=`unsupported_url`，消息「当前页面不支持此浏览器操作」 |
| 16 | `stale_page_reference` | 页面关闭后读取 | 通过；`ActionError` trace=`stale_page_reference`，消息「网页对象已失效」 |
| 17 | `cleanup` | 资源清理自证 | 通过；本次创建的 4 个页面对象关闭后均报 `stale_page_reference`，临时目录已删除 |

## 3. 期望值来源与独立确证

**独立推导**（不依赖产品返回）：

- 6 个固定 id 直接来自靶场源码 `WEB/src/pages/ElementHtmlTestPage.tsx` 与 `WEB/src/App.tsx` 的路由表；
  页面标题「元素 HTML 测试」同源。
- 「不含 DOCTYPE」按 DOM 规范：`outerHTML` 定义上不包含文档类型声明，而实时 `document.doctype.name` 为 `html`。
- 注入片段的长度增量手写推算：属性 ` data-uiautoma-probe="…"`（51 字符）+
  节点 `<div id="uiautoma-probe-node">…</div>`（69 字符）= 120 字符。

**独立确证**（与产品无关的通道）：

- 用 Python 标准库 `html.parser` 解析 `get_html()` 的返回串，得到元素计数与 id 集合，
  与浏览器实时 `document.getElementsByTagName('*').length` / `querySelectorAll('[id]')` 对照。
  两者不是同一个通道：一个在 Python 侧解析字符串，一个在浏览器侧数实时节点。
- 读回对照走的是**另一条通道**：制造 DOM 变更用 `execute_javascript`（CDP Page 域），
  读取用 `get_html`（`chrome.scripting.executeScript`）。
- iframe 内部结构由 `iframe.contentDocument` 直接读出，未调用被测方法生成期望值。

**控制实验**（用于给长度类判据定性）：只经 CDP 读取 `documentElement.outerHTML` 时，
设置属性恰好 +51 字符、移除后恰好 0 偏差。说明长度偏差不来自 `get_html` 通道本身。

## 4. 实测行为记录 / 已知边界

**实测抖动口径（重要）**

- 空闲态连续读取**精确稳定**：12/12 次长度完全相同。
- 紧跟 DOM 变更后的**首次**读取实测最多偏差 2 字符，随后立即回落。来源是靶场页自身
  antd cssinjs 的 `<style>` 增删（页面自身节奏），与 `get_html` 无关（见控制实验）。
- 因此长度类断言使用预算 ±8 字符，相对 11.7 万字符的文档为 0.007%——小到不足以掩盖
  缺 DOCTYPE（约 15 字符）、少包裹元素或读错帧这类系统性偏差。**主判据是内容级**
  （探针标记、固定 id、元素计数），长度只作辅助。

**语义边界**

- **只读主框架**：iframe 内容不在返回串中（`iframe_frame_scope` 正向证明）。
- **不返回 DOCTYPE**：需要完整文档时须自行补 `<!DOCTYPE html>`。
- **零参数合同**：既不接受位置参数也不接受关键字参数（连 `timeout` 都没有）。
- **非脚本化页面**：`chrome://newtab/` 等返回 `unsupported_url` 明确能力错误，不返回空串。
- **页面失效**：`close()` 之后读取返回 `stale_page_reference`；不会静默返回旧内容。
- **后台标签页可读**：`silent_running=True` 的页面无需激活即可读取。
- **不需要 Package**：本 API 与元素库无关，`page.find*` 才需要已打开的 Package。

**清理判据说明**：本脚本按「本次创建的页面对象关闭后必须报 `stale_page_reference`」自证清理，
不把全局标签数当作判据——实测期间用户在同一个人工浏览器里正常浏览（标签增删、标题变化），
全局计数不是稳定不变量。标签数仅作为诊断值随报告输出。

**明确排除（未覆盖）**

- Edge（`--mode edge`）未运行；仅覆盖 Chrome。
- 闭合 Shadow DOM、跨域 iframe、超大页面（分片/内存）未覆盖。
- 未验证 `--target-url` 指向非靶场地址的行为（按测试侧边界裁定，页面材料一律来自标准靶场）。
- 本 API 不涉及坐标与 DPI，故多显示器/缩放不在覆盖面。

**修订记录（相对旧证据）**

- 旧证据 `browser_get_html_baidu.md` 与脚本 `test_web_browser_get_html_baidu.py` 以
  `https://www.baidu.com/` 为页面，只有 8 项，且「DOM 对比」用的
  `execute_javascript` 与实现表达式相同、期望值仍由产品自身产出，强度弱于本轮。
  本轮改以标准靶场固定 fixture 为页面，期望值改由靶场源码与标准库解析独立推导，
  并把帧作用域、非脚本化页面、后台标签页、零参数合同纳入矩阵。旧文件保留为历史证据，不删除。
- 旧脚本顶部 `PRODUCT_ROOT = Path(__file__).resolve().parents[3]` 在本测试工作区指向不存在的
  `D:\code\sdk\src`；它能运行只是因为 `.venv` 已 editable 安装 SDK。本轮新脚本不复制该写法。

## 5. 复测

在 `D:\code\元素库\sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_get_html.py
```

仅检查合同（不打开浏览器、不产生副作用）：

```powershell
uv run .\web\test_web_browser_get_html.py --contract-only
```

归档 JSON 报告：

```powershell
uv run .\web\test_web_browser_get_html.py --json
```

退出码约定：`0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED。
