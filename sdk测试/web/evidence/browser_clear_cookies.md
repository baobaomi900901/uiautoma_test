# `WebBrowser.clear_cookies()` 验证证据

## 当前结论（2026-10-06）

**VERIFIED：最后连续三次完整运行（run2/run3/run4），每次 13/13 PASS，退出码均为 0。**
本方法独立验收，计数不使用顶层 `uiautoma.web.clear_cookies` 的历史结果。
三轮清理均 PASS：本次 Cookie 原生确认删除、外部 Cookie 基线保留、自有标签关闭、标签数 **3→3**。

只读 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。
日期按本对话；原始浏览器时钟原样保留在 JSON，不据本机时钟重命名证据。
本结论限于此源码快照、实际 dev Runtime、Chrome 154.0.0.0 与下列覆盖范围。

## 用途、参数与返回

清理当前 URL 匹配、属于指定分区的 Cookie；返回 None，空结果/重复清理也返回 None。

```python
clear_cookies(self, *, partition_key=None) -> 'None'
```

| 参数 | 默认值 | 合同与当前行为 |
|---|---|---|
| `partition_key` | `None` | 默认清理未分区；字典指定第一方分区；当前不接受网址字符串 |

| 输入/失败路径 | 错误类型、文案与失败位置 |
|---|---|
| 多余位置参数、未知关键字 | Python TypeError，在方法体前拒绝；使用无 Runtime 的 object 作为 self 核验 |
| 已关闭的本次网页对象，有效业务参数 | ActionError / 网页对象已失效 / stale_page_reference；Runtime 的 page_ref 分支 |
| 分区列表类型 / 空字典 / 祖先标记字符串 | TypeError / partition_key must be a mapping；ValueError / partition_key.top_level_site is required；TypeError / partition_key.has_cross_site_ancestor must be a bool；SDK 层先拒绝 |

## 靶场、准备与独立确证

- 主靶场：[Cookie 测试页](https://baobaomi900901.github.io/xpath/#/cookie-test)。
- 另一 Path 的独立文档：[已发布的静态 SVG](https://baobaomi900901.github.io/xpath/stop-load-test/slow.svg)。
  只读取该 SVG 文档，不打开停止加载准备页或注册 Service Worker。
- 不依赖元素库，也不需要抓取 Cookie 页按钮；准备和观察通过后台 API/JavaScript 完成。
- 唯一无日期入口：[test_web_browser_clear_cookies.py](../test_web_browser_clear_cookies.py)。
- 共用准备、账本、原生观察和精确清理：[_web_browser_cookie_common.py](../_web_browser_cookie_common.py)。
- 所有正式测试新标签都使用 `silent_running=True`，没有鼠标、键盘、剪贴板或前台点击。

准备使用原生 `document.cookie` / `cookieStore.set` 写入随机 UUID 前缀的会话、持久、域、
真实 Partitioned 与另一 Path 项。`cookieStore.getAll()` 提供独立属性，`document.cookie` 提供可见名称/值。
读取测试逐项比较 name/value/domain/path/Secure/会话/hostOnly/SameSite/到期与分区；
Cookie Store 的到期毫秒映射为扩展返回的秒，允许 2ms 表示精度差。
写入有效期用调用前后浏览器时钟加秒数作范围断言，并另验自然到期。
不以被测 Cookie API 的读回作为正确性 oracle；批量清理前 SDK 读取仅用于附加保护外部隐藏项。

该 hash 路由的实际 Cookie Path 是 `/xpath/`，不是 `#/cookie-test`。
不同 Path 的观察使用两个真实文档，没有用 history 改 URL 冒充新的原生 Cookie Store 作用域。
原生 Cookie Store 的属性/文档范围依据 [WHATWG Cookie Store 规范](https://cookiestore.spec.whatwg.org/)，
扩展查询的域/精确 Path 筛选及单项最长 Path 选择依据 [Chrome Cookies API](https://developer.chrome.com/docs/extensions/reference/api/cookies)。
具体浏览器行为仍以本轮真实原生证据为准。

## 源码合同链路

[冻结合同](../browser_cookie_contracts_20261006.json) 保存签名、默认值、docstring 与完整链路源码片段。
以下位置均相对于上述只读 worktree/commit：

| 层 | 位置与当前合同 |
|---|---|
| SDK | `sdk/src/uiautoma/web/browser.py:545`，当前公开方法；正式脚本自检签名/docstring/源码与快照一致 |
| Client | `sdk/src/uiautoma/_core/client.py:1176`，RPC `web.cookie.clear`，page_ref，内部 timeout_ms=5000 |
| Pipe | `runtime/services/pipe_server.py:447` 注册参数校验；`:2206–2218` 五个 Cookie handler |
| Runtime | `runtime/services/action_service.py:3318` → `:5727` 的 `_run_web_browser_command` |
| 分区规范化 | `sdk/src/uiautoma/web/__init__.py:184` 与 `runtime/services/action_service.py:601`；SDK Mapping 校验先执行 |
| Engine | `chrome/engine/plugin_packages/browser_command_package.js:84` 与 `:1781`；从 live page 绑定 URL、Cookie Store，再调用 Chrome Cookie API |
| Capability | `runtime/services/capabilities.py:349–353`，必需名称及相关参数 |

## 用例与三轮结果

默认清理未分区项后，Partitioned 项与另一 Path 项保留；明确指定分区后清理对应 Partitioned 项。错误站点分区不改变数据。每次调用前检查外部数据；原生可见项或扩展当前分区结果存在非本次 Cookie 时报告 BLOCKED，不执行批量清理。

| 用例 | 期望与独立检查 | 三轮最终状态 |
|---|---|---|
| `api_contract` | 签名、默认值、docstring 和 SDK 源码均匹配只读快照 | PASS |
| `extra_positional` | 多余位置参数由 Python TypeError 拒绝，方法体未执行 | PASS |
| `unknown_keyword` | 未知 keyword 由 Python TypeError 拒绝，方法体未执行 | PASS |
| `environment` | 创建后台测试页、读取原生 Cookie Store、记录 Chrome 标签基线 | PASS |
| `native_fixtures` | 原生 JS 准备会话/持久、域 Cookie、分区和其他 Path；Cookie Store 确认 | PASS |
| `wrong_partition_noop` | 错误分区返回 None，全部原生数据和其他 Path 项保留 | PASS |
| `clear_unpartitioned` | 清理匹配当前 URL 的未分区项，返回 None；分区与另一 Path 项保留 | PASS |
| `clear_again` | 重复清理未分区空结果返回 None；分区与另一 Path 项保留 | PASS |
| `clear_partition` | 显式字典分区清理对应项；另一路径项仍保留 | PASS |
| `clear_partition_again` | 重复清理分区空结果返回 None，其他 Path 项保留 | PASS |
| `partition_parameters` | 非法分区类型、空站点和非法祖先类型均拒绝 | PASS |
| `closed_page` | 有效参数操作已关闭页面抛 ActionError / 网页对象已失效 / stale_page_reference | PASS |
| `cleanup` | 删除本次 Cookie、原生确认；保留外部 Cookie、关闭自有标签并复核基线 | PASS |

| 运行 | PASS/总数 | FAIL | 退出码 | 标签/清理 |
|---|---|---|---|---|
| run2 | 13/13 | 0 | 0 | 3→3 / PASS |
| run3 | 13/13 | 0 | 0 | 3→3 / PASS |
| run4 | 13/13 | 0 | 0 | 3→3 / PASS |


### partition_key 合同差异

docstring 声称接受顶层站点网址字符串，SDK 当前仅接受 Mapping。
后台补充探针对三个方法分别传入网址字符串，均在 SDK 层抛
`TypeError: partition_key must be a mapping`；未触发真实批量清理。
[三方法探针](artifacts/browser_cookie_partition_strings_20261006.txt)；
[本地交接稿](../../issues/drafts/browser_cookie_20261006/partition_key_contract_mismatch.md)。
本页 VERIFIED 限定于默认未分区和已列出的字典分区用例，不宣称字符串方式已验证成功。

## 原始产物

- run2：[终端输出](artifacts/browser_clear_cookies_20261006_run2.txt) / [完整 JSON](artifacts/browser_clear_cookies_20261006_run2.json)。
- run3：[终端输出](artifacts/browser_clear_cookies_20261006_run3.txt) / [完整 JSON](artifacts/browser_clear_cookies_20261006_run3.json)。
- run4：[终端输出](artifacts/browser_clear_cookies_20261006_run4.txt) / [完整 JSON](artifacts/browser_clear_cookies_20261006_run4.json)。
- [汇总原始输出与当前脚本校验和](artifacts/browser_clear_cookies_20261006.txt)。
- [初始行为探针](artifacts/browser_cookie_probe_20261006.txt)、[分区/范围探针](artifacts/browser_cookie_semantics_20261006.txt)、[同名多 Path 原生探针](artifacts/browser_cookie_native_scope_20261006.txt)。

## 复测方式

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_browser_clear_cookies.py
uv run .\web\test_web_browser_clear_cookies.py --report-file .\web\evidence\artifacts\browser_clear_cookies_manual.json
uv run .\web\test_web_browser_clear_cookies.py --json
uv run .\web\test_web_browser_clear_cookies.py --contract-only
```

默认后台运行。需要 build-test.py 启动的 dev Runtime/Chrome；不自动启动或替换用户浏览器环境。
退出码：0=全部 PASS；1=存在 FAIL；2=无 FAIL 但存在 BLOCKED。
`--contract-only` 仅三项 SDK 合同/调用约束，不进入 VERIFIED。

## 覆盖边界与交接

- Chrome 主文档和第一方分区；未验 Edge/CEF/auto、多 Cookie Store、隐身模式、跨站祖先为 True 的正向分区。
- 读取方法未独立验 HttpOnly 隐藏值/属性；静态靶场和原生 Cookie Store 无法提供这一独立证据。
- HttpOnly 写入仅验脚本不可见且不能覆盖、删除后解除保护；没有服务端或 CDP 读取隐藏值。
- 不主动中断 Provider/桥接；同长 Path 的创建顺序、复杂跨域和会话重启不在本轮矩阵内。
- 账本按精确 name/domain/Path/partition 删除本次项；外部 Cookie 内容只在内存中对照，报告仅存数量/指纹。
- 外部标签在测试期间变化会报告 BLOCKED；不关闭用户标签，也不将用户操作算成产品缺陷。

公开 API 文档尚未生成；按 `AGENTS.md` 的 PUBLIC DOCUMENTATION GATE 另获用户确认后通过交接稿同步。
产品源码保持只读；本地缺陷稿不表示已提交产品 Issue。
