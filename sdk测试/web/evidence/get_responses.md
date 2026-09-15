# `WebBrowser.get_responses()` 初次测试

## 用途

获取监听到的网络响应。

| 参数 | 默认 | 说明 |
|---|---|---|
| `url` | `""` | 资源网址，默认不按网址筛选 |
| `use_wildcard` | `False` | `False` 精确匹配；`True` 时 `*` / `?` 可用 |
| `resource_type` | `All` | 资源类型；可用 `\|` 连接多个 |

三个参数**全部仅限关键字**；返回 `list[dict]`；未匹配时返回 `[]`。

## 真实验收结果

**VERIFIED：19/19 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`（真实流量由页面内
`fetch()` 与 `reload()` 产生）

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，三个参数仅限关键字，返回注解 `list` |
| 页面准备 / 初始状态 | 通过 |
| 流量准备 | 通过，捕获 10 条记录（fetch HTTP 404 + 页面刷新） |
| 记录结构 | 通过，9 个文档所述键齐全，关键字段类型正确 |
| 非 2xx 记录 | 通过，404 响应被记录且 `body` 有 9379 字符 |
| Document 记录 | 通过，`status=200`、`body` 406 字符、`base64Encoded=False` |
| `resource_type='Fetch'` | 通过，命中 1 条且类型全为 Fetch |
| `resource_type='Document'` | 通过，命中 2 条且类型全为 Document |
| `resource_type='XHR\|Fetch'` | 通过，并集生效 |
| `resource_type='Other'` | 通过，本次无该类流量，返回 `[]` |
| `url` 精确匹配 | 通过，仅命中目标 URL |
| `url` 通配匹配 | 通过，7 条均匹配 `*/xpath/*` |
| `url` 精确不匹配 | 通过，返回 `[]` |
| 非法 `resource_type` | 通过，`InvalidParamsError`（trace `invalid_params`） |
| 无活动监听 | 通过，`ActionError`（trace `web_network_monitor_not_found`） |
| 位置参数 / 未知关键字 | 通过，`TypeError` / `TypeError` |
| 资源清理 | 通过，停止监听并仅关闭本次创建的测试页面 |

## 记录结构与实测值

文档所述 9 个键全部存在：`url`、`type`、`headers`、`body`、`status`、`base64Encoded`、
`requestHeaders`、`requestBody`、`method`。实测样本：

| 请求 | `type` | `status` | `body` 长度 | `base64Encoded` |
|---|---|---|---|---|
| `.../xpath/robots.txt`（页面内 fetch） | `Fetch` | `404` | 9379 | `False` |
| `.../xpath/`（刷新产生的文档） | `Document` | `200` | 406 | `False` |
| `.../assets/index-*.js` | `Script` | `200` | 1332235 | `False` |
| `.../assets/index-*.css` | `Stylesheet` | `200` | 297 | `False` |

要点：

- **非 2xx 响应同样被记录**（`status=404` 且带响应体），与 `http_request()` 文档中
  「非 2xx 的 content 为空」是两套不同语义；
- 只返回**已收到响应**的记录（`status` 非空，或 WebSocket 的 `direction` 非空）；
  未收到响应的失败请求不返回（源码在 `Network.loadingFailed` 上只记 `error`，`status` 仍为空）。

## 与 `start_monitor_network()` 的两层过滤关系

| 层 | 位置 | 作用 |
|---|---|---|
| 第一层（存储级） | `start_monitor_network(url/use_wildcard/resource_type)` | 不匹配的请求**根本不写入记录** |
| 第二层（查询级） | `get_responses(url/use_wildcard/resource_type)` | 在已存记录上再做一次筛选 |

因此：启动时收窄范围的类型/网址**事后无法取回**；想事后按类型筛查就不要在启动时限定类型。
详见 `start_monitor_network.md` 的「关键语义」一节。

## 环境说明

走 CDP 调试器实现，不依赖合成器或视口，因此本次运行时的「Chrome 窗口最小化」对其无影响；
也无导航历史前置，不受 issue #58 影响。

## 复测

脚本：[test_web_browser_get_responses.py](../test_web_browser_get_responses.py)
原始产物：[artifacts/get_responses_20260915.txt](artifacts/get_responses_20260915.txt)

```powershell
uv run .\web\test_web_browser_get_responses.py
uv run .\web\test_web_browser_get_responses.py --json
uv run .\web\test_web_browser_get_responses.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **未收到响应的失败请求**：本次未构造（例如中途取消的请求）以验证其确实不出现。
- **500 条记录上限下的淘汰顺序**：未构造超过 500 个请求。
- WebSocket 的 `direction` 记录形态：本次靶场无 WebSocket 流量。
- `headers` / `requestHeaders` / `requestBody` 的具体字段内容与大小写归一：本次只核对了类型。
- 重定向链（`redirect` 记录的拆分）与 iframe 会话标识归属。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
