# `uiautoma.web.WebElement.get_html()` 验证证据

## 1. 用途与合同

读取**当前网页元素自身**的 HTML（元素自己的 `outerHTML` 序列化结果，含自身标签、属性与全部后代）。

```python
WebElement.get_html(self) -> str
```

公开签名**没有任何参数**。返回原生 `str`；SDK 取 RPC 结果的 `html` 字段，缺失时回退 `value`，
再回退空串，因此不会返回 `None`。

完整链路（被测 worktree 为 `uiautoma/desktop` 检出，基线 commit
`c101caa9dcd115a461fc71ecaed351b0dea880b8`）：

| 层 | 位置 | 事实 |
| --- | --- | --- |
| SDK 公开对象 | `sdk/src/uiautoma/web/element.py:536` | `get_html(self) -> str`，无参数，委托 `self._raw.get_html()` |
| SDK Raw | `sdk/src/uiautoma/_core/client.py:3906` | `get_html(*, timeout: float = 5.0)`；取 `html` → 回退 `value` → 回退 `""` |
| RPC 名 | — | `web.get_html` |
| 能力/参数 | `runtime/services/capabilities.py:273,482` | 必填 `package_token` / `element_id` / `timeout_ms`；capability `web_dom_actions_stage5` |
| Runtime 业务 | `runtime/services/action_service.py:2486` | `web_get_html_element` → `_run_web_value(op="get_html")`；要求 `locator_kind == "runtime_ref"`，即元素必须由实时 `find`/`find_all` 取得 |
| 桥接 | `runtime/web/bridge_api.py:341` | `m == "web.get_html"` → `action = "get_html"` |
| 引擎 | `chrome/engine/engine_packages/page_engine_runtime.js:3665` | `element.outerHTML`（非字符串则 `""`），同时回填 `value` |

## 2. 真实验收结果

**VERIFIED：17/17 通过，退出码 0；连续 3 次完整运行全绿（2026-09-20）。**

- 靶场：百度资讯搜索「区块链」结果页（外部真实站点，由测试方提供）。
- 元素库/元素：`260902_web元素` → `web靶场_测试超链接` —— 搜索结果第一条的标题链接，
  节点为 `<a class="news-title-font_1xS-F" target="_blank" aria-label="标题：…">`。
  测试只使用元素库**副本**，原件未被改动。
- 被测 worktree 基线：`c101caa9dcd115a461fc71ecaed351b0dea880b8`；该 commit 下
  `sdk/`、`runtime/`、`chrome/` 无本地改动。
- Runtime：`UIAutoma Runtime 0.1.0`，protocol 1，`web_dom_actions_stage5` 已声明。
- 运行脚本：外部 `sdk测试` 工作区 `web/test_web_element_get_html.py`。
- 归档原始输出：该工作区 `web/evidence/artifacts/element_get_html_20260920.txt`。

| # | 用例 | 实测结果 |
| --- | --- | --- |
| 01 | 公开签名 | 通过；`(self) -> 'str'` |
| 02 | 元素库副本与 Runtime | 通过 |
| 03 | 靶场页面 | 通过 |
| 04 | 库元素绑定 | 通过；`find_all` 命中 1 个 |
| 05 | 返回非空 `str` | 通过；长度 416 |
| 06 | 元素级范围 | 通过；以 `<a` 开头、`</a>` 结尾、不含 `<html` |
| 07 | 与页面侧枚举比对 | 通过；与页面 96 个锚点中第 46 个逐字节相等且唯一 |
| 08 | `innerHTML` 关系 | 通过；inner 59 字符，返回串多 357 字符 |
| 09 | HTML 与文本通道差异 | 通过；HTML 416 字符 vs `innerText` 30 字符 |
| 10 | 属性转义 | 通过；属性 API 返回原始 `&`，返回 HTML 中为 `&amp;` |
| 11 | 活推导读回 | 通过；增量 54 等于手写增量 |
| 12 | 撤销还原 | 通过；长度精确还原 |
| 13 | 重复读取 | 通过；连续 3 次一致 |
| 14–15 | 参数边界 | 通过；多余位置参数与未声明关键字均被 `TypeError` 拒绝 |
| 16 | 页面关闭后读取 | 通过；`ActionError` trace=`stale_page_reference` |
| 17 | 资源清理 | 通过；页面与 Package 关闭、库副本删除 |

## 3. 期望值来源与独立确证

**独立推导**（依据 HTML 序列化规范，不看产品返回）：返回串必须是元素自身 `outerHTML`
（以 `<a` 开头、`</a>` 结尾、不含 `<html`）；属性值中的 `&` 必须序列化为 `&amp;`；
`innerHTML` 必须是返回串的真子串。

**独立确证**（期望值不经过任何产品返回值）：页面侧用 `document.querySelectorAll('a')`
枚举**全部 96 个锚点**，逐个取回 `outerHTML` / `innerHTML` / `innerText`，要求产品返回串与之
**恰好一个**逐字节相等。三次运行均命中第 46 个且唯一。

**活推导**：在独立定位到的同一节点上写入唯一属性，产品必须立刻读回，长度增量精确等于
手写增量；撤销后必须消失且长度精确归零。

**修正记录**：初版判据曾按**元素库捕获的属性顺序**断言序列化顺序，实测失败——
实际序列化为 `href → target → class → aria-label`。浏览器按 DOM 解析/插入顺序序列化，
属正常语义，**是判据错误**，已改为不比较属性顺序。

## 4. 实测行为记录 / 已知边界

- **返回值内容**：含自身开始标签与全部属性、全部后代标记，也含**注释节点**（该站点会在
  标题里插入 `<!--323-->` 之类的高亮标记）与子元素 `<em>`（搜索词高亮）。
  `get_text()` 只返回纯文本，两个通道差异明显。
- **属性顺序**：按 DOM 解析/插入顺序序列化，**不是**元素库捕获记录的顺序。
- **转义**：属性值中 `&` 在返回 HTML 里是 `&amp;`；`get_attribute("href")` 返回原始 `&`。
- **`element.name` 不是库元素名**：绑定后 `WebElement.name` 返回节点 `innerText`。
- **需要 Package**：依赖 `package_token` + `element_id`，且必须是实时查找得到的引用。
- **页面失效**：`close()` 之后读取返回 `stale_page_reference`，不会静默返回旧内容。
- **外部站点脆弱性**：该库元素路径绑定的是站点当时的 DOM（含必需的位置索引与带哈希后缀的
  class）。站点改版后绑定会失败；脚本把这种情况记为 `BLOCKED`（退出码 2），不记为产品缺陷，
  恢复方式是重新采集该元素。
- **明确排除（未覆盖）**：Edge；闭合 Shadow DOM；该元素不在 iframe 内，未覆盖元素级跨 iframe
  读取；空 `outerHTML` 负例；元素库捕获期会话字段的直连行为。

## 5. 修订记录（相对 2026-08-08 旧结论）

旧记录（`source_commit_at_doc_time: b3bcb48d…`）如下，按「保留原结论」留档：

- 日期 2026-08-08；靶场 `https://www.baidu.com/`（首页）；种子元素 `百度一下`
  ——实际是 `//input[@id="su"]`，一个 `<input type="submit">`；返回 HTML 记为
  `<input type="submit" value="百度一下" id="su" class="btn self-btn bg s_btn">`；
  清理记为「本次资源 3/3」。
- 旧明确排除项包含「**完整 outerHTML 精确匹配**（class 可能随百度改版变化）」。

本次修订：

1. **原「完整 outerHTML 精确匹配」排除项已撤销**：本轮以「页面侧枚举全部锚点、要求唯一
   逐字节相等」真正覆盖了完整 `outerHTML` 精确匹配。
2. **页面与元素更换**：改用超链接元素 `web靶场_测试超链接`；旧元素是搜索按钮，旧结论不再
   代表当前覆盖。
3. **旧记录引用产品仓库路径与固定元素库**；本轮运行由外部 `sdk测试` 工作区的脚本产生，
   命令与参数见第 6 节。
4. **新增判据**：独立通道全量比对、`innerHTML` 子串关系、HTML 与文本通道差异、属性转义、
   活推导读写、零参数合同、`stale_page_reference`。
5. **产品侧 `tests/SDK/web/test_web_element_get_html.py` 本轮未更新**：它仍指向已退役的
   本机靶场地址与旧元素库，不能复现本次结果。是否把外部工作区的脚本移植进产品仓库，
   需要单独决定（涉及元素库归属与路径约定）。

## 6. 复测

在外部 `sdk测试` 工作区根目录运行：

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

元素库位置可用 `--library <目录>` 指定（默认使用该工作区约定的 `260902_web元素`）。

退出码约定：`0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED。
