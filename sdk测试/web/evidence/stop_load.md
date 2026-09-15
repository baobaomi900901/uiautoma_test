# `WebBrowser.stop_load()` 初次测试

## 用途

停止当前网页的加载。

| 参数 | 说明 |
|---|---|
| （无） | **没有任何参数**，返回 `None` |

实现链：`WebBrowser.stop_load` → `web.browser.stop_load`（SDK 侧 `timeout_ms=2000`）
→ `ActionService.web_browser_stop_load` → 引擎 `stopTabLoading()` → CDP `Page.stopLoading`
（引擎对调试器指令另设 1500ms 上限）。因此它**中止的是待处理的网络请求**，
不能中断正在执行的同步 JS。

## 真实验收结果

**VERIFIED：14/14 通过 + 1 项如实记录，退出码 0**（**连续 6 次完整运行全绿**）。

靶场：维护者的官方靶场（测试侧不自建页面）
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）
落点页：`https://baobaomi900901.github.io/xpath/#/form-controls`
挂起目标：保留地址 `http://10.255.255.1/uiautoma-slow.html`、`http://192.0.2.1/uiautoma-slow.html`
（不可路由、不应答，用于制造真实的待处理网络请求）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无任何参数、返回注解 `None` |
| 环境基线 | 通过，记录进入时标签数用于核对孤儿标签 |
| 页面准备 / 基线 | 通过，`is_load_completed()=True`、`readyState=complete`、JS 可用 |
| 已完成页面上调用（幂等） | 通过，返回 `None`（0.016s），页面状态不变、JS 仍可用 |
| 连续 3 次调用 | 通过，均返回 `None` |
| **制造待处理网络请求** | 通过，导航挂起地址超时（3.0s），`is_load_completed()=False` 且 `execute_javascript()` 失败 |
| **中止挂起（核心正向）** | 通过，`stop_load()` 返回 `None`（0.02s）后，页面在 **0.1s 内恢复可用**（JS 恢复、`readyState=complete`） |
| 中止后仍可正常使用 | 通过，可导航回靶场页并读取标题，`is_load_completed()=True` |
| **`stop_if_timeout=True` 配对语义** | 通过，`create(load_timeout=3, stop_if_timeout=True)` 超时抛错后，新标签已不在加载中 —— 超时后确实自动停载 |
| **`stop_if_timeout=False`（默认）+ `stop_load()`** | 通过，超时后标签仍处于待处理导航，`stop_load()` 返回 `None` 并在 0.1s 内把标签转为已停止，标签可正常关闭 |
| 页面关闭复核 | 通过，`web.get_all()` 证实无残留 |
| 页面关闭后调用 | 通过，`ActionError`（"网页对象已失效"，0.0s） |
| 错误页判定（如实记录，不计入退出码） | 见「已知发现 1」 |
| 资源清理 | 通过，与进入时相比新增标签 0 个 |
| 同步 JS 死循环边界（`--include-hung-page`，可选） | 见「已知发现 2」；该场景产物另存 `artifacts/stop_load_hung_page_20260915.txt`（15/15 + 3 项记录，退出码 0） |

## 关键方法论：三种页面状态的判据必须区分

本 API 返回 `None`，「停止成功」只能靠可观测状态判定。而本轮实测确立了一个**必须区分**的事实：
`is_load_completed()=False` 有两种完全不同的成因。

| 页面状态 | `is_load_completed()` | `execute_javascript()` | `close()` | 成因 |
|---|---|---|---|---|
| 正常加载完成 | `True` | 正常返回（`readyState=complete`） | 成功 | — |
| **待处理导航（真·加载中）** | `False` | **失败**（`浏览器操作失败，请重试`） | **失败** | 导航未提交，旧文档已被替换 |
| Chrome 错误页 | `False`（恒为 False） | 正常返回（`readyState=complete`） | 成功 | 见已知发现 1 |

因此脚本的判据是：
- **制造「加载中」**：必须同时满足 `is_load_completed()=False` **且** `execute_javascript()` 失败；
- **确认「已停止」**：要求 `execute_javascript()` 恢复且 `readyState=complete`（页面重新可用），
  而不是只看 `is_load_completed()`；
- **确认「挂起彻底释放」**：`close()` 能成功（待处理导航状态下它会失败，见已知发现 3）。

脚本最初只看 `is_load_completed()`，因此出现两次「假失败 / 漏判」；
改用上述组合判据后连续 6 次运行全绿。这段修正记录保留在此，便于复测者理解判据由来。

## 已知发现 1：Chrome 错误页上 `is_load_completed()` 恒为 `False`

**复现**：导航到 `http://127.0.0.1:9/uiautoma-error-page.html`（端口 9 关闭，连接立即被拒绝），
Chrome 进入自身错误页后采集：

| 观测 | 值 |
|---|---|
| `document.readyState` | `complete` |
| `performance.getEntriesByType('navigation')[0].loadEventEnd` | `62`（> 0） |
| `navCount` | `1` |
| `location.href` | `chrome-error://chromewebdata/` |
| `execute_javascript()` | 正常返回 |
| `close()` | 成功（0.05s） |
| **`is_load_completed()`** | **`False`（多次采样始终 False）** |

**追因（依据当前源码）**：引擎 `is_load_completed` 的判据是

```js
const loaded = !!(liveTab.status === "complete" && await probeTabDocumentReady(liveTab, 100));
```

而 `probeTabDocumentReady()` 在 `canProbeDocumentReady(tab) === false` 时直接返回 `true`。
错误页的 `chrome-error://` 既不匹配 `chrome://` 等前缀、也不是 `http(s)://`，
所以该函数返回 `false` → 探测被跳过 → 判定**完全落在 `tab.status === "complete"` 上**。
实测「页面侧条件」（`readyState`、`loadEventEnd`、脚本可执行）都已满足，
因此失败条件只能是标签状态未变为 `complete`（引擎返回的原始响应里 Runtime 只保留了
`loaded/is_load_completed/ready` 三个布尔，未透出 `tab.status`，故此处为**推定**）。

**影响**：任何以失败导航收尾的页面（被 `stop_load()` 中止的导航、连接被拒、DNS 失败等）
都会让 `is_load_completed()` 永远返回 `False`；`wait_load_completed()` 会一路等到超时才报错。
本轮 `stop_load` 验收中它就造成了 2 次「判据歧义」。

**处置**：这是 `is_load_completed()` / `wait_load_completed()` 的问题，**不由 `stop_load` 负责**，
因此脚本中以 `KNOWN`（记录）状态呈现、不计入退出码。是否提单由维护者决定。

## 已知发现 2：同步 JS 死循环页面（`slow-load-30s.html`）——`stop_load()` 无效，且标签无法回收

靶场 `slow-load-30s.html` 的 `hang.js` 是**主线程同步死循环**：

```js
while (Date.now() - start < hangMs) { tick(); }   // 默认 30000ms
while (true) { tick(); }                          // 之后永不返回
```

实测（`--include-hung-page`）：

| 观测 | 值 |
|---|---|
| `create(该页, load_timeout=5)` | 超时抛错 `UIAError` |
| `is_load_completed()` | `False`（0.01s，能正常回答） |
| `execute_javascript()` | **超时失败（5.00s）** → 主线程确被卡住 |
| `stop_load()` | **返回 `None`、0.02s、不报错** |
| `stop_load()` 之后 | `is_load_completed()` 仍 `False`，`execute_javascript()` 仍失败 → **未解救** |
| `navigate(正常页, load_timeout=10)` | **超时失败** |
| `close()` | **失败**（`ActionError: 浏览器操作失败，请重试`，2.01s；连续 5 轮重试全部失败） |
| 最终出口 | Chrome 自身弹出「**页面无响应 / 等待 · 退出网页**」，需人工点「退出网页」 |

结论：`Page.stopLoading` 无法中断正在执行的同步 JS，这属于 **CDP 能力边界**；
真正值得关注的是**回收缺口**——无响应标签既不能 `close()` 也不能导航离开，
引擎关闭标签前需要先挂 debugger（对无响应渲染进程会卡住），SDK 侧只能超时。

**该场景不进默认验收**：每跑一次就会留下一个无响应标签并需要人工点弹窗。
需要时用 `--include-hung-page` 单独运行，其产物另存
`artifacts/stop_load_hung_page_20260915.txt`。

## 已知发现 3：待处理导航状态下 `close()` 也会失败，必须先 `stop_load()`

脚本开发过程中因一次异常导致收尾清理未先释放挂起，实测：**导航挂起时 `close()` 失败**
（`ActionError: 浏览器操作失败，请重试`），标签被留在 loading 状态；
对该标签先执行 `stop_load()` 后，`is_load_completed()` 立即转 True，`close()` 随即成功。

这从反面印证了 `stop_load()` 的价值：它是**释放挂起导航、让标签重新可控**的前置动作，
脚本的收尾与异常路径因此都先 `stop_load()` 兜底，再 `close()`。

## 实测行为记录

1. **`stop_if_timeout` 的公开面不对称**：`web.create()` 与 `web.get()` 都有 `stop_if_timeout`
   参数（超时后自动停载，默认 `False`），但 `WebBrowser.navigate()` / `reload()` / `go_back()`
   / `go_forward()` **都没有**该参数，只能自行调 `stop_load()`。
   引擎侧 `ready`/`navigate`/`reload` 等命令其实支持 `cmd.stop_if_timeout`，
   即能力在引擎里存在、只是未在 SDK 的页面对象方法上开放。
2. **超时错误消息不统一**：同一挂起地址，`create(..., stop_if_timeout=True)` 抛
   `UIAError: 网页操作超时，请检查页面是否加载完成或存在弹窗`，而默认
   `stop_if_timeout=False` 有时抛 `UIAError: 浏览器操作失败，请重试`；
   `navigate()` 超时则抛 `ActionError`（同为超时语义、文案不同）。
3. **加载完成后注入的慢资源不会让页面回到 loading**：在已加载完成的靶场页上用 JS 注入
   `http://10.255.255.1/...`、`https://httpbin.org/delay/20`，实测 `img.complete=false`
   （请求确实挂起）但 `document.readyState` 仍为 `complete`、`is_load_completed()` 仍为 `True`。
   所以「被 `stop_load()` 中止的挂起」必须出现在**首次加载**中——本次用挂起地址导航实现，
   **不需要新增靶场页面**。
4. **中止挂起后标签的落点分两种**：导航未提交 → 保留原页面（`is_load_completed()` 转 `True`）；
   导航已提交 → 落到 Chrome 错误页（`is_load_completed()` 恒为 `False`，但页面可用、可关闭）。
   两种落点判定都必须通过，脚本因此用「页面重新可用」而非单一布尔值作为核心判据。
5. **`slow-load-30s.html` 的页面文案已过时**：页面说明里提到的
   `stop_if_timeout=False/True` 只存在于 `web.create()`/`web.get()`，`navigate()` 已无此参数；
   另外 `hang.js` 的 `while(true)` 使该页永远无法加载完成，也永远无法被 `stop_load()` 中止。

## 复测

脚本：[test_web_browser_stop_load.py](../test_web_browser_stop_load.py)
原始产物：[artifacts/stop_load_20260915.txt](artifacts/stop_load_20260915.txt)（默认，14/14 + 1 记录，退出码 0）
边界产物：[artifacts/stop_load_hung_page_20260915.txt](artifacts/stop_load_hung_page_20260915.txt)（含阻塞页边界，15/15 + 3 记录，退出码 0）

```powershell
uv run .\web\test_web_browser_stop_load.py
uv run .\web\test_web_browser_stop_load.py --json
uv run .\web\test_web_browser_stop_load.py --contract-only
# 可选：额外刻画「同步 JS 死循环」边界；跑完需人工在 Chrome 点「退出网页」
uv run .\web\test_web_browser_stop_load.py --include-hung-page --json
```

脚本不写入任何文件，收尾只关闭本次页面并核对标签数是否回到进入时基线（允许
`--include-hung-page` 已知留下的无响应标签）。

退出码：`0` = 全部 PASS（允许 KNOWN）；`1` = 存在 FAIL；`2` = 无非 FAIL 但存在 BLOCKED。
状态 `KNOWN` 表示已如实刻画、但不由本 API 负责的边界或发现，不计入退出码。

## 明确排除

- **`stop_load()` 对同步 JS 死循环无效**属 CDP 能力边界，本文件只记录现象与回收缺口，
  未尝试任何绕过（例如结束渲染进程）。
- **真实慢速服务器资源**（服务器端延迟返回的图片/脚本）：本次用保留地址的「连接挂起」构造，
  未覆盖「服务器慢慢返回数据」的中途中止场景。若需要，靶场可加一个
  「首次加载即引用外部慢接口」的页面（此前给过的 `slow-resource.html` 建议仍然适用，
  但**不再阻塞**本 API 的验收）。
- **`stop_load()` 对下载、弹窗、上传等并存状态的交互**：未覆盖。
- **Edge、CEF 与 Auto 模式**（脚本 `--mode` 仅开放 `chrome`）。
- **内部 `timeout_ms` 固定 2000 的边界**（例如引擎停载耗时超过 2s 时 SDK 是否误报）：
  未构造。
