# `WebElement.get_html()` 验收证据

## 1. 用途与合同

读取**当前网页元素自身**的 HTML（`outerHTML` 序列化结果，含元素自己的标签、属性与全部后代）。

```python
WebElement.get_html(self) -> str
```

公开签名**没有任何参数**（`self` 之外无位置参数、无关键字参数）。返回原生 `str`；SDK 取 RPC 结果的
`html` 字段，缺失时回退 `value`，再回退空串，因此**不会返回 `None`**。

完整链路（检出目录 `D:\code\desktop`，基线 commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`）：

| 层 | 位置 | 事实 |
| --- | --- | --- |
| SDK 公开对象 | `sdk/src/uiautoma/web/element.py:536` | `get_html(self) -> str`，无参数，委托 `self._raw.get_html()` |
| SDK Raw | `sdk/src/uiautoma/_core/client.py:3906` | `get_html(*, timeout: float = 5.0)`；`_timeout_to_ms(timeout, 5.0)`；取 `html` → 回退 `value` → 回退 `""` |
| RPC 名 | — | `web.get_html` |
| 能力/参数 | `runtime/services/capabilities.py:273,482` | `RpcMethodSpec("web.get_html", "_handle_web_get_html", ("package_token", "element_id", "timeout_ms"))`；capability `web_dom_actions_stage5` |
| Runtime 分发 | `runtime/services/pipe_server.py` | `_handle_web_get_html` → `action_service.web_get_html_element` |
| Runtime 业务 | `runtime/services/action_service.py:2486` | `web_get_html_element` → `_run_web_value(op="get_html")`，先解析 Package context（`package_token` + `element_id`） |
| 桥接 | `runtime/web/bridge_api.py:341` | `m == "web.get_html"` → `action = "get_html"` |
| 引擎 | `chrome/engine/engine_packages/page_engine_runtime.js:3665` | `const html = typeof element.outerHTML === "string" ? element.outerHTML : ""`，同时回填 `value` |

**要点：与页面级 `WebBrowser.get_html()` 不同，本 API 必须走元素库**（`package_token` + `element_id`），
使用前需先 `page.find()` / `find_all()` 取得实时元素。

## 2. 真实验收结果

**VERIFIED：17/17 通过，退出码 0；连续 3 次完整运行全绿（2026-09-20）。**

- 目标页面（用户提供）：百度资讯搜索「区块链」结果页
  `https://www.baidu.com/s?ie=utf-8&bsst=1&rsv_dl=news_t_sk&tn=news&cl=2&medium=0&rtt=1&wd=%E5%8C%BA%E5%9D%97%E9%93%BE`
- 元素库：`D:\code\元素库\260902_web元素`（本轮只用 `.pytest_tmp/` 下的**副本**，原件未改动）；
  元素 `web靶场_测试超链接`，库分组「百度资讯搜索_区块链」（origin `https://www.baidu.com`），
  节点为搜索结果第一条的标题链接 `<a class="news-title-font_1xS-F" target="_blank" aria-label="标题：…">`。
- 被测 worktree：`D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`；
  该 commit 下 `sdk/`、`runtime/`、`chrome/` 无本地改动。
- Runtime：`UIAutoma Runtime 0.1.0`，protocol 1，`web_dom_actions_stage5` 已声明。
- 脚本：[test_web_element_get_html.py](../test_web_element_get_html.py)。
- 原始输出：[artifacts/element_get_html_20260920.txt](artifacts/element_get_html_20260920.txt)。

| # | 用例 | 检查内容 | 实测结果 |
| --- | --- | --- | --- |
| 01 | `api_contract` | 签名 `(self)`、无参数、返回 `str` | 通过；`(self) -> 'str'` |
| 02 | `library_prepare` | 元素库副本可打开、Runtime 可用 | 通过；副本打开，协议 1 |
| 03 | `page_prepare` | 目标页面打开、标题符合 | 通过；`title='百度资讯搜索_区块链'` |
| 04 | `element_bind` | 库元素绑定 | 通过；`find_all` 命中 1 个，`find` 返回单一 `WebElement` |
| 05 | `return_type_nonempty` | 返回原生非空 `str` | 通过；长度 416 |
| 06 | `element_scope_outerhtml` | 是元素 `outerHTML` 而非页面 HTML | 通过；以 `<a` 开头、`</a>` 结尾、不含 `<html` |
| 07 | `independent_dom_match` | 与页面侧枚举的全部锚点比对 | 通过；与 **96** 个锚点中第 **46** 个逐字节相等且唯一 |
| 08 | `inner_html_contained` | `innerHTML` 是返回串真子串 | 通过；inner 59 字符，返回串多 357 字符（自身标签与属性） |
| 09 | `markup_vs_text` | HTML 通道与文本通道不同 | 通过；HTML 416 字符 vs `innerText` 30 字符，且含子标签标记 |
| 10 | `attribute_escaping` | 属性值按 HTML 规则转义 | 通过；属性 API 返回原始 `&`（2 个），返回 HTML 中序列化为 `&amp;` |
| 11 | `live_mutation_visible` | 改同一节点后必须立刻读回 | 通过；增量 54 等于手写增量 54 |
| 12 | `live_cleanup_restores` | 撤销后还原 | 通过；标记消失且长度精确还原为 416 |
| 13 | `repeat_read_stable` | 连续 3 次读取 | 通过；逐字节一致 |
| 14 | `param_positional` | 多余位置参数 | 通过；`TypeError: takes 1 positional argument but 2 were given` |
| 15 | `param_keyword` | 未声明关键字 | 通过；`TypeError: got an unexpected keyword argument 'timeout'` |
| 16 | `stale_page_reference` | 页面关闭后读取 | 通过；`ActionError` trace=`stale_page_reference`，消息「网页对象已失效」 |
| 17 | `cleanup` | 资源清理 | 通过；页面与 Package 已关闭，元素库副本已删除 |

## 3. 期望值来源与独立确证

**独立推导**（依据 HTML 序列化规范，不看产品返回）：

- 返回串必须是元素自身 `outerHTML`：以 `<a` 开头、以 `</a>` 结尾，且**不含 `<html`**（排除页面级 HTML）。
- 属性值中的 `&` 必须序列化为 `&amp;`；而属性读取 API 返回的是**解码后的原始值**——两者互为对照。
- `innerHTML` 必须是返回串的**真子串**，且返回串必然比它长（多出自身标签与属性）。

**独立确证**（与产品通道无关，期望值不经过任何产品返回值）：

页面侧用 `document.querySelectorAll('a')` 枚举当前页面**全部 96 个锚点**，逐个取回各自的
`outerHTML` / `innerHTML` / `innerText`，然后要求产品返回串与之**恰好一个**逐字节相等。
本轮三次运行结果一致：命中第 46 个，且唯一。定位不依赖任何产品 API 的返回值。

**活推导**：

在独立定位到的同一节点（下标 46）上用页面 JS 写入唯一属性 `data-uiautoma-probe`，
产品返回串必须立刻体现，且长度增量精确等于手写增量；撤销后必须消失且长度精确归零。
这同时证明了「读的是实时节点」和「读的确实是这一个节点」。

**修正记录（本轮自身的判据修正）**：初版曾断言返回串按**元素库捕获的属性顺序**序列化。
实测该锚点实际序列化为 `href → target → class → aria-label`，与捕获记录顺序不同——
浏览器按 DOM 解析/插入顺序序列化，属正常语义，**是我的判据错**，已改为不比较属性顺序，
并在下节记为实测行为。

## 4. 实测行为记录 / 已知边界

- **返回值内容**：包含自身开始标签与全部属性、全部后代标记、以及**注释节点**
  （本轮返回串含 `<!--323-->` 这类百度高亮标记）与子元素 `<em>区块链</em>`（搜索词高亮）。
  `get_text()` 只返回纯文本（30 字符），不含任何标记，两个通道差异明显。
- **属性顺序**：按 DOM 解析/插入顺序序列化（实测 `href → target → class → aria-label`），
  **不是**元素库捕获记录的顺序。不要按捕获顺序做断言。
- **转义**：属性值中 `&` 在返回 HTML 里是 `&amp;`；`get_attribute("href")` 返回原始 `&`。
  需要可比较的原始值时用属性 API，需要序列化形态时用 `get_html()`。
- **`element.name` 不是库元素名**：绑定后 `WebElement.name` 返回节点 `innerText`
  （本轮是新闻标题），库元素名要通过 `find`/`find_all` 的入参表达。
- **需要 Package**：与 `WebBrowser.get_html()` 不同，本 API 依赖 `package_token` + `element_id`。
- **零参数合同**：既不接受位置参数也不接受关键字参数。
- **页面失效**：`close()` 之后读取返回 `stale_page_reference`；不会静默返回旧内容。
- **外部站点脆弱性（重要）**：库元素路径绑定的是百度当时的 DOM 结构——中间一层 `div` 带
  **必需** `index=1`，末尾 `a` 带**必需** `class="news-title-font_1xS-F"`（含哈希后缀）与 `index=0`；
  `aria-label` / `innerText` 在库记录里是 `optional`。页面上同类锚点有 10 个，`find_all` 本轮恰好命中 1 个。
  百度改版、结果顺序变化或 class 哈希变化都会让绑定失败。**脚本把绑定失败记为 `BLOCKED`（退出码 2），
  不写成产品缺陷**；恢复方式是重新采集该库元素。
- **明确排除（未覆盖）**：Edge；闭合 Shadow DOM；该元素不在 iframe 内，故未覆盖元素级跨 iframe 读取；
  空 `outerHTML` 负例（引擎对非字符串返回 `""` 的防御分支未构造）；元素库捕获期会话字段的直连行为。

## 5. 修订记录（相对 2026-08-08 旧结论）

旧版本文件（YAML 风格，`source_commit_at_doc_time: b3bcb48d…`）记录的事实与本次不同，按「保留原结论」保留如下：

- 旧验证日期 2026-08-08，靶场 `https://www.baidu.com/`（百度**首页**），种子元素 `百度一下`
  ——实际是 `//input[@id="su"]`，一个 **`<input type="submit">`**，并非超链接；
  返回 HTML 记为 `<input type="submit" value="百度一下" id="su" class="btn self-btn bg s_btn">`；
  清理记为「本次资源 3/3」。
- 旧明确排除项包含「**完整 outerHTML 精确匹配**（class 可能随百度改版变化）」。

本次修订与差异：

1. **页面与元素更换**：改用用户新采集的超链接元素 `web靶场_测试超链接`（百度资讯搜索结果标题链接），
   不再是百度首页的搜索按钮。旧元素与旧页面结论不再代表当前覆盖。
2. **原「完整 outerHTML 精确匹配」排除项已撤销**：本轮通过「页面侧枚举全部锚点、要求唯一逐字节相等」
   真正覆盖了完整 `outerHTML` 精确匹配，不再需要排除。
3. **旧文件路径在本工作区不可复现**：旧记录引用 `tests/SDK/web/web测试元素库` 与
   `tests/SDK/web/test_web_element_get_html.py`（产品仓库路径）。旧脚本的默认元素库
   `sdk测试/web/web测试元素库` 在本工作区**不存在**，且脚本没有 `--library` 参数，
   因此旧 `VERIFIED` 在切换基线后无法复跑。本次已就地重写为靶场 fixture 版本，
   并新增 `--library` / `--element` / `--target-url` 参数。
4. **旧版缺失的判据**：新增独立通道比对、`innerHTML` 子串关系、HTML 与文本通道差异、
   属性转义关系、活推导读写、零参数合同、`stale_page_reference`。
5. 旧文件本身在 git 历史中保留，不删除。

## 6. 复测

在 `D:\code\元素库\sdk测试` 目录运行：

```powershell
uv run .\web\test_web_element_get_html.py
```

仅检查合同（不连接 Runtime、不打开浏览器、不复制元素库）：

```powershell
uv run .\web\test_web_element_get_html.py --contract-only
```

归档 JSON 报告：

```powershell
uv run .\web\test_web_element_get_html.py --json
```

退出码约定：`0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED
（外部站点元素绑定失败即记 2，可用 `--element` / `--library` 指向重新采集的元素后复跑）。
