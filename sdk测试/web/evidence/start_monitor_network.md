# `WebBrowser.start_monitor_network()` 初次测试

## 用途

开始监听当前网页的网络请求。

| 参数 | 默认 | 说明 |
|---|---|---|
| `url` | `""` | 资源网址，默认不按网址筛选 |
| `use_wildcard` | `False` | `False` 时按完整网址**精确匹配**；`True` 时 `*` / `?` 可用，例如 `*/api/*` |
| `resource_type` | `All` | 资源类型；可用 `\|` 连接多个，例如 `Fetch\|Script`；`Other` 含 TextTrack / EventSource / Manifest |

三个参数**全部仅限关键字**，返回 `None`。

实现路径：引擎通过 CDP 调试器实现（`Network.enable` + `Target.setAutoAttach` 自动附加 iframe），
不使用元素库，不需要导航历史前置，也不依赖视口。

## 真实验收结果

**VERIFIED：12/12 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`（真实请求由页面内
`fetch()` 与 `reload()` 产生）

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，三个参数均仅限关键字（默认 `''`/`False`/`'All'`），返回 `None` |
| 页面准备 / 初始状态 | 通过 |
| 默认启动确实生效 | 通过，启动后页面内 `fetch` 的 404 请求被捕获（独立经 `get_responses()` 取回） |
| 重复启动丢弃旧记录 | 通过，第二次启动后即时读取为 **0 条**，新请求正常捕获 |
| `resource_type` 过滤 | 通过，`'Fetch'` 下仅记录 Fetch（1 条），**刷新产生的 Document 未被记录** |
| `url` 精确过滤 | 通过，仅记录目标 URL（1 条），其它请求未被记录 |
| 通配符过滤 | 通过，`*/xpath/*` 下 7 条 URL 全部含 `/xpath/` |
| 非法 `resource_type` | 通过，`InvalidParamsError`（trace `invalid_params`） |
| 位置参数 / 未知关键字 | 通过，`TypeError` / `TypeError` |
| 资源清理 | 通过，停止监听并仅关闭本次创建的测试页面 |

## 关键语义：`start` 的过滤是「存储级」的

源码（`chrome/engine/plugin_packages/browser_command_package.js`）在 `requestWillBeSent` /
`responseReceived` 处理时先做 `if (!filter(...)) return;`，即**启动时被排除的请求根本不会写入记录**。
本次实测确认：

| 启动参数 | 刷新后 `get_responses()` 看到的记录 |
|---|---|
| `resource_type="Fetch"` | 仅 Fetch；Document / Script / Stylesheet **一条都没有** |
| `url="<robots.txt>"` | 仅该 URL；其它请求一条都没有 |
| `url="*/xpath/*", use_wildcard=True` | 7 条，全部匹配该模式 |

因此 `get_responses()` 自身的过滤是**叠加在存储过滤之上的第二层**：想事后按类型/网址筛查，
启动时就不能把范围收窄，否则数据已经不存在了。这一点与直觉不同，使用时应特别注意。

另：引擎对每个标签页只保留一个监听，重复启动会先停掉旧的并**丢弃其历史**；记录上限 500 条。

## 环境说明

本 API 走 CDP 调试器，与 `scroll_to(behavior="smooth")` 不同，**不依赖合成器或视口**，
因此本次运行时的「Chrome 窗口最小化」对其没有影响；也不受 issue #58 影响（无导航历史前置）。

## 复测

脚本：[test_web_browser_start_monitor_network.py](../test_web_browser_start_monitor_network.py)
原始产物：[artifacts/start_monitor_network_20260915.txt](artifacts/start_monitor_network_20260915.txt)

```powershell
uv run .\web\test_web_browser_start_monitor_network.py
uv run .\web\test_web_browser_start_monitor_network.py --json
uv run .\web\test_web_browser_start_monitor_network.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **500 条记录上限的淘汰行为**：未构造超过 500 个请求的场景。
- **iframe 自动附加的跨域请求归属**：引擎用 `Target.setAutoAttach` 附加 iframe，本次未用
  含跨域 iframe 的页面验证其记录归属与会话标识。
- **WebSocket 方向记录**：本次靶场未产生 WebSocket 流量。
- 单次监听的长时间稳定性与内存增长。
- 监听期间页面被关闭 / 导航到新文档的收尾语义。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
