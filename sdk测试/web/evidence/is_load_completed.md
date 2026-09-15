# `WebBrowser.is_load_completed()` 初次测试

## 用途

判断页面是否加载完成。无参数；返回 `bool`：已加载完成时为 `True`，否则为 `False`。

内部实现固定使用 `timeout_ms=2000` 读取状态，并取 `loaded` / `is_load_completed` / `ready`
三者之一作为真值。

## 真实验收结果

**VERIFIED：9/9 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form` → `#/element-html-test`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无参数、返回注解 `bool` |
| 页面准备 | 通过，成功创建测试页面 |
| 初始状态 | 通过，初始 URL 可读且页面 id 非空 |
| 加载完成后取值 | 通过，连续三次均返回 `bool` 类型的 `True` |
| 零等待刷新后取值 | 通过，立即取值为 `False`（捕捉到未完成窗口），并在 0.444s 内恢复为 `True` |
| 导航后取值 | 通过，导航到第二页面后返回 `True`，页面 id 不变 |
| 多余位置参数 | 通过，`TypeError` 拒绝 |
| 未知关键字 | 通过，`TypeError` 拒绝 |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 两条路径都被实际覆盖

`True` 与 `False` 都不是靠推断认定的：

- `True`：静置页面连续三次取值；
- `False`：`reload(load_timeout=0)` 制造未完成窗口后立即取值。

未完成窗口是时序相关的，因此脚本对该路径采用「尽力捕捉 + 恢复必断言」：捕捉到 `False`
记入证据，未捕捉到时在 detail 中注明「页面过快」，但**始终强断言随后必须恢复为 `True`**。

本次共运行 3 次，**3/3 均捕捉到 `False`**，恢复耗时 0.335s / 0.444s / 0.65s。

## 与 issue #58 的关系

本 API 只读、不需要导航历史前置，本脚本也不调用后退/前进，因此不受 #58 影响。
可继续作为「引擎分支内非导航历史命令正常」的对照证据（另见 `reload.md`）。

## 补充实测（2026-09-15）：Chrome 错误页上**恒为 `False`**

跟踪 Issue：https://github.com/uiautoma/desktop/issues/59

本文件原先把「加载失败页面（DNS 失败、HTTP 错误页）的状态语义」列入「明确排除」。
在 `WebBrowser.stop_load()` 验收中该场景被实际覆盖，结论如下——原排除项就此撤销。

导航到 `http://127.0.0.1:9/uiautoma-error-page.html`（端口 9 关闭，连接立即被拒绝），
Chrome 进入自身错误页后多次采样：

| 观测 | 值 |
|---|---|
| `document.readyState` | `complete` |
| `performance.getEntriesByType('navigation')[0].loadEventEnd` | `62`（> 0），`navCount = 1` |
| `location.href` | `chrome-error://chromewebdata/` |
| `execute_javascript()` | 正常返回 |
| `close()` | 成功（0.05s） |
| **`is_load_completed()`** | **`False`（多次采样始终 `False`）** |

追因（依据当前源码）：引擎判据为 `liveTab.status === "complete" && probeTabDocumentReady(...)`，
而 `probeTabDocumentReady()` 对 `canProbeDocumentReady() === false` 的地址直接返回 `true`；
`chrome-error://` 既非 `chrome://` 前缀也不是 `http(s)://`，因此探测被跳过，
判定完全落在标签状态上。页面侧条件（`readyState`、`loadEventEnd`、脚本可执行）均已满足，
故失败条件只能是标签状态未变为 `complete`（`tab.status` 未透出到 SDK，此处为推定）。

**影响**：任何以失败导航收尾的页面（被 `stop_load()` 中止的导航、连接被拒、DNS 失败等）
都会让本 API 永远返回 `False`，`wait_load_completed()` 会一路等到超时才报错。

完整上下文与判据区分见 [`stop_load.md`](stop_load.md)「已知发现 1」。

## 复测

脚本：[test_web_browser_is_load_completed.py](../test_web_browser_is_load_completed.py)
原始产物：[artifacts/is_load_completed_20260915.txt](artifacts/is_load_completed_20260915.txt)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_is_load_completed.py
uv run .\web\test_web_browser_is_load_completed.py --json   # 归档 JSON 报告
uv run .\web\test_web_browser_is_load_completed.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **长时间未完成页面上的持续 `False`**：静态靶场加载过快，只能用零等待刷新制造短暂窗口，
  未验证秒级持续未加载时是否稳定返回 `False`。
  （补充：与之不同的「真·加载中」状态已在 `stop_load.md` 中由「挂起导航」构造并实测为 `False`。）
- 加载失败页面（DNS 失败、HTTP 错误页）的状态语义 —— **原排除项已撤销**，见上方补充实测。
- `iframe` 子框架未完成而主文档已完成时的语义。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- 已失效页面引用（`stale_page_reference`）下的行为。
