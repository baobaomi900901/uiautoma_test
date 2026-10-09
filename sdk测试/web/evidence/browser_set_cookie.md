# `WebBrowser.set_cookie()` 验证证据

## 当前结论（2026-10-06）

**READY_FOR_LIVE：最后连续三次完整运行（run2/run3/run4），每次 20/21 PASS + 1 FAIL，退出码均为 1。**
本方法独立验收，计数不使用顶层 `uiautoma.web.set_cookie` 的历史结果。
三轮清理均 PASS：本次 Cookie 原生确认删除、外部 Cookie 基线保留、自有标签关闭、标签数 **3→3**。

只读 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。
日期按本对话；原始浏览器时钟原样保留在 JSON，不据本机时钟重命名证据。
本结论限于此源码快照、实际 dev Runtime、Chrome 154.0.8037.95 与下列覆盖范围（原生网页 userAgent 只显示 154.0.0.0）。

### 追加根因确认（同日）

**已确认 UIAutoma 引擎把原生成功的空返回值误判为写入失败。**

使用本机同一个 Chrome 154.0.8037.95 可执行文件，以隔离配置、无窗口模式加载仅有 Cookie 权限的临时扩展，
直接调用 `chrome.cookies.set`，不加载 UIAutoma Engine，也不打开靶场文档。
因此靶场 JavaScript 与正式 Python 测试脚本都没有参与这组原生写入。

三轮 × 三个情形 × callback/Promise，共 18 项确认均达到预期；每次写入都被独立 CDP 读取确认。

| 原生 Cookie API 的 URL | 显式 Path | callback/Promise 返回 | 实际写入 |
|---|---|---|---|
| `/xpath/#/cookie-test` | `/xpath/` | Cookie 对象 | 成功 |
| `/xpath/#/cookie-test` | `/xpath/stop-load-test/` | undefined；callback lastError 为空；Promise 不拒绝 | 成功 |
| `/xpath/stop-load-test/slow.svg` | `/xpath/stop-load-test/` | Cookie 对象 | 成功 |

随后在当前 dev SDK 中用同一 Cookie 名称、值、Path、会话参数，只改变 WebBrowser 的网页绑定：
三对都在主页面抛 `cookie_set_failed`、在匹配 Path 的观察页面返回 `None`。
第二对反转调用顺序，仍得到相同结果，排除首次写入与覆盖顺序作为此次现象的解释。
两次调用后 Cookie 都实际存在于原生观察中。SDK 探针清理 PASS、标签 3→3；隔离原生浏览器的 18 个 Cookie 全部删除，浏览器关闭。

原因链路：UIAutoma 用当前标签 URL 作为 `chrome.cookies.set` 的 url；Chrome 成功写入后按该 URL 查找返回项，
URL 不匹配 Cookie Path 时可以没有返回项；UIAutoma `if (!cookie)` 将此成功的空返回转换成 `cookie_set_failed`。
Chrome [官方合同](https://developer.chrome.com/docs/extensions/reference/api/cookies#method-set) 明确返回类型允许 undefined；
[Chromium 实现](https://raw.githubusercontent.com/chromium/chromium/main/extensions/browser/api/cookies/cookies_api.cc)
的 CookiesSetFunction 先写入、再按 url 查询，写入成功但无匹配返回项时使用 NoArguments。
外部源码是查阅时的 main，用来解释机制；本机 154.0.8037.95 的行为由上述原生探针直接确认。

探针初次只给临时扩展 HTTPS 主机权限，导致非 Secure Cookie 的无 URL getAll 被权限筛掉，准备对照失败；
同次 get 和 CDP 已能读到项。调整为同一测试域名的 HTTP/HTTPS 权限后，18 项全通过。
[Chromium Cookie 主机权限筛选实现](https://raw.githubusercontent.com/chromium/chromium/main/extensions/browser/api/cookies/cookies_helpers.cc)
按 Cookie 的 Secure 属性构造权限检查 URL，与此修正结果一致。该初次探针未到异常 Path，用作诊断历史保留。

- [原生探针完整 JSON](artifacts/browser_set_cookie_native_confirmation_20261006.json) / [输出](artifacts/browser_set_cookie_native_confirmation_20261006.txt)。
- [SDK 三对完整 JSON](artifacts/browser_set_cookie_sdk_path_confirmation_20261006.json) / [输出](artifacts/browser_set_cookie_sdk_path_confirmation_20261006.txt)。
- [原生探针初次失败 JSON](artifacts/browser_set_cookie_native_confirmation_20261006_attempt1.json) / [输出](artifacts/browser_set_cookie_native_confirmation_20261006_attempt1.txt)。
- [确认汇总](artifacts/browser_set_cookie_confirmation_20261006.txt)。
- [已执行探针源码与复现步骤](../../issues/drafts/browser_cookie_20261006/confirmation_probe/README.md)。

这些确认项是诊断计数，正式验收仍为三轮各 20/21 PASS + 1 FAIL，状态保持 READY_FOR_LIVE。产品源码未修改。

## 用途、参数与返回

设置当前网页所属域的 Cookie，同名/同域/同 Path 覆盖；成功返回 None。当前存在非匹配 Path 写入后仍抛异常的缺陷。

```python
set_cookie(self, *, name=None, value=None, sessionCookie: 'bool' = False, expires: 'float' = 100, domain=None, path=None, httpOnly: 'bool' = False, secure: 'bool' = False) -> 'None'
```

| 参数 | 默认值 | 合同与当前行为 |
|---|---|---|
| `name/value` | `None / None` | name 必须非空；value=None 规范化为空字符串 |
| `sessionCookie` | `False` | 默认持久 Cookie；True 为会话 Cookie |
| `expires` | `100` | 持久有效期，单位秒；小数可用，Runtime 校验有限 int/float 且排除 bool |
| `domain/path` | `None / None` | 不传给 Chrome 时采用浏览器默认；本 URL 的默认 Path 实测为 /xpath（无末尾斜杠） |
| `httpOnly/secure` | `False / False` | 必须 bool；HttpOnly 用脚本读取/覆盖保护与解除保护核验 |

| 输入/失败路径 | 错误类型、文案与失败位置 |
|---|---|
| 多余位置参数、未知关键字 | Python TypeError，在方法体前拒绝；使用无 Runtime 的 object 作为 self 核验 |
| 已关闭的本次网页对象，有效业务参数 | ActionError / 网页对象已失效 / stale_page_reference；Runtime 的 page_ref 分支 |
| 缺少或空名称（remove_cookie 仅测试空名称） | InvalidParamsError / missing name / invalid_params；pipe 注册参数校验先拒绝，不能误写为下游“Cookie 名称不能为空” |
| NaN、Infinity、bool、None 有效期 | InvalidParamsError / Cookie 有效期必须为有限秒数 / invalid_params；Runtime 校验 |
| 三个布尔开关传字符串 true | InvalidParamsError / Cookie 开关必须为布尔值 / invalid_params；Runtime 校验 |
| 本轮合法非匹配 Path 写入 | ActionError / 浏览器操作失败，请重试 / cookie_set_failed；产品缺陷，详见下文 |

## 靶场、准备与独立确证

- 主靶场：[Cookie 测试页](https://baobaomi900901.github.io/xpath/#/cookie-test)。
- 另一 Path 的独立文档：[已发布的静态 SVG](https://baobaomi900901.github.io/xpath/stop-load-test/slow.svg)。
  只读取该 SVG 文档，不打开停止加载准备页或注册 Service Worker。
- 不依赖元素库，也不需要抓取 Cookie 页按钮；准备和观察通过后台 API/JavaScript 完成。
- 唯一无日期入口：[test_web_browser_set_cookie.py](../test_web_browser_set_cookie.py)。
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
| SDK | `sdk/src/uiautoma/web/browser.py:515`，当前公开方法；正式脚本自检签名/docstring/源码与快照一致 |
| Client | `sdk/src/uiautoma/_core/client.py:1176`，RPC `web.cookie.set`，page_ref，内部 timeout_ms=5000 |
| Pipe | `runtime/services/pipe_server.py:447` 注册参数校验；`:2206–2218` 五个 Cookie handler |
| Runtime | `runtime/services/action_service.py:3294` → `:5727` 的 `_run_web_browser_command` |
| 分区规范化 | `sdk/src/uiautoma/web/__init__.py:184` 与 `runtime/services/action_service.py:601`；SDK Mapping 校验先执行 |
| Engine | `chrome/engine/plugin_packages/browser_command_package.js:84` 与 `:1781`；从 live page 绑定 URL、Cookie Store，再调用 Chrome Cookie API |
| Capability | `runtime/services/capabilities.py:349–353`，必需名称及相关参数 |

## 用例与三轮结果

默认持久 100 秒、会话、2.5 秒小数、1.2 秒自然到期、空值、Secure、显式当前域和同键覆盖均通过。HttpOnly 防脚本读取/覆盖通过，但隐藏值没有独立服务端或 CDP 验证。非当前 URL 匹配的合法 Path 已写入却抛 cookie_set_failed，不能将本方法整体标为 VERIFIED。

| 用例 | 期望与独立检查 | 三轮最终状态 |
|---|---|---|
| `api_contract` | 签名、默认值、docstring 和 SDK 源码均匹配只读快照 | PASS |
| `extra_positional` | 多余位置参数由 Python TypeError 拒绝，方法体未执行 | PASS |
| `unknown_keyword` | 未知 keyword 由 Python TypeError 拒绝，方法体未执行 | PASS |
| `environment` | 创建后台测试页、读取原生 Cookie Store、记录 Chrome 标签基线 | PASS |
| `native_fixtures` | 原生 JS 准备会话/持久、域 Cookie、分区和其他 Path；Cookie Store 确认 | PASS |
| `default_persistent` | 默认持久 Cookie、100 秒、默认 URL Path /xpath、hostOnly、Secure False、返回 None | PASS |
| `session_cookie` | sessionCookie=True 的过期时间为空，值正确，返回 None | PASS |
| `fractional_expiry` | expires 接受有限小数，原生有效期落在调用前后时钟 + 2.5 秒范围 | PASS |
| `secure_cookie` | Secure True 写入原生属性正确，返回 None | PASS |
| `domain_cookie` | 显式当前域名写为域 Cookie，原生 domain 正确 | PASS |
| `empty_value` | value=None 规范化为空字符串，原生值为空 | PASS |
| `overwrite` | 同名/同域/同 Path 覆盖后仅一个项且原生值是 second | PASS |
| `other_path_write` | 另一路径写入只在真实匹配文档的原生观察中可见 | FAIL |
| `http_only_protection` | 写入后脚本不能读取或覆盖；删除后同名同 Path 可由 JS 创建，排除未写入 | PASS |
| `natural_expiry` | 1.2 秒有效期自然到期；原生 Cookie 消失，无 SDK 删除操作 | PASS |
| `missing_name` | 未提供名称抛 InvalidParamsError / missing name | PASS |
| `blank_name` | 空名称抛 InvalidParamsError / missing name | PASS |
| `invalid_expiry` | NaN/Infinity/bool/None 有效期均拒绝，未生成 Cookie | PASS |
| `invalid_flags` | 三个布尔开关均拒绝字符串 true | PASS |
| `closed_page` | 有效参数操作已关闭页面抛 ActionError / 网页对象已失效 / stale_page_reference | PASS |
| `cleanup` | 删除本次 Cookie、原生确认；保留外部 Cookie、关闭自有标签并复核基线 | PASS |

| 运行 | PASS/总数 | FAIL | 退出码 | 标签/清理 |
|---|---|---|---|---|
| run2 | 20/21 | 1 | 1 | 3→3 / PASS |
| run3 | 20/21 | 1 | 1 | 3→3 / PASS |
| run4 | 20/21 | 1 | 1 | 3→3 / PASS |

### FAIL 定性与第一轮保留

- **产品缺陷**：`other_path_write` 合法显式 Path `/xpath/stop-load-test/` 的项已经写入，
  另一真实文档的原生 Cookie Store 读到准确名称、值和会话属性；当前文档看不到它。
  API 仍抛 `ActionError: 浏览器操作失败，请重试`，trace=`cookie_set_failed`。
  run2/run3/run4 每轮只此一项 FAIL，不能标为 VERIFIED。
- 源码快照 `chrome/engine/plugin_packages/browser_command_package.js:1813` 调用 `chrome.cookies.set`，
  `:1814` 将空返回值当作失败。初轮仅据源码推断；上述追加确认已直接观察同版本 Chrome 的空返回与 URL/Path 关系。
- **测试侧清理错误**：run1 为 12/14 PASS + 2 FAIL，遇到产品错误后提前停止；
  清理误用会规范化 Path 的 Cookie Store.delete，没删到默认 `/xpath` 项。
  已改为 `document.cookie` 按账本精确 Path 到期删除。
  run1 默认项在补充后台清理检查时已自然到期；后续三次完整运行清理全 PASS。
  两种失败分别记录，不把清理脚本错误算成产品缺陷。
- 最终脚本在独立用例 FAIL 后继续采集其余用例；环境 BLOCKED 或准备失败才停止依赖场景。

已交接 [desktop 缺陷 #74](https://github.com/uiautoma/desktop/issues/74)，并在[提测总单 #51](https://github.com/uiautoma/desktop/issues/51#issuecomment-6006002391)补充关联；[本地完整技术证据与原始产物归档](../../issues/issue_74/README.md)。Issue 为 OPEN，尚未修复；本方法状态仍为 READY_FOR_LIVE。


## 原始产物

- run1：[终端输出](artifacts/browser_set_cookie_20261006_run1.txt) / [完整 JSON](artifacts/browser_set_cookie_20261006_run1.json)。
- run2：[终端输出](artifacts/browser_set_cookie_20261006_run2.txt) / [完整 JSON](artifacts/browser_set_cookie_20261006_run2.json)。
- run3：[终端输出](artifacts/browser_set_cookie_20261006_run3.txt) / [完整 JSON](artifacts/browser_set_cookie_20261006_run3.json)。
- run4：[终端输出](artifacts/browser_set_cookie_20261006_run4.txt) / [完整 JSON](artifacts/browser_set_cookie_20261006_run4.json)。
- [汇总原始输出与当前脚本校验和](artifacts/browser_set_cookie_20261006.txt)。
- [初始行为探针](artifacts/browser_cookie_probe_20261006.txt)、[分区/范围探针](artifacts/browser_cookie_semantics_20261006.txt)、[同名多 Path 原生探针](artifacts/browser_cookie_native_scope_20261006.txt)。

## 复测方式

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_browser_set_cookie.py
uv run .\web\test_web_browser_set_cookie.py --report-file .\web\evidence\artifacts\browser_set_cookie_manual.json
uv run .\web\test_web_browser_set_cookie.py --json
uv run .\web\test_web_browser_set_cookie.py --contract-only
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
