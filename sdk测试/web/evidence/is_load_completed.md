# `WebBrowser.is_load_completed()` 验证证据

## 当前结论（2026-10-05）

**VERIFIED：连续 3 次完整运行，每次 19/19 PASS，退出码均为 0。**
每轮只创建一个测试标签，清理后标签均为 **3→3**；临时库副本删除，靶场本目录 Service Worker 注销。

当前被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。
本证据描述该源码快照与本轮 dev Runtime/Chrome 的实测，不代表其他分支、模式或版本。

| 场景 | 当前实测 | 独立确证 |
|---|---|---|
| 正常准备页已完成 | 连续三次 `bool True` | 原生 `readyState=complete`，Navigation Timing `loadEventEnd > 0` |
| 30 秒慢资源仍等待 | 持续 2 秒采样全部 `bool False` | 原生 `interactive`，`loadEventEnd=0`，图片未完成；共享 DOM 的资源状态 pending、load 次数 0 |
| 资源自然完成 | `False → True`，完成后连续三次 True | 图片宽度 280，资源成功事件、worker 释放事件和一次 window load；原生 complete 且 loadEventEnd > 0 |
| 零等待刷新 | 新文档 `False → True` | `timeOrigin` 改变，同一 URL/run 的慢资源重新等待并成功完成 |
| 本靶场被 `stop_load()` 中止 | 三次抛 `ActionError: 网页加载失败`，trace=`web_page_load_failed` | 原生 complete 但 loadEventEnd=0；图片宽度 0、资源错误在 30 秒到期前发生、没有 window load |
| Chrome 原生连接失败错误页 | 三次抛相同加载失败异常 | 连接本次独占但未 listen 的本机端口；原生 URL=`chrome-error://chromewebdata/`，虽然 complete 且 loadEventEnd > 0 |
| 从中止/错误页重新导航 | 恢复正常 False/True 或 True | 新文档与成功资源/正常准备页状态独立确认 |
| 关闭本次页面后 | `ActionError: 网页对象已失效`，trace=`stale_page_reference` | 本次页面已关闭；清理复核其引用不再出现在标签基线中 |

**调用方须处理异常。** 本 API 不能仅用 `document.readyState` 推断返回值；加载失败有单独的异常路径。
本靶场中止后的异常属于当前失败判定分支的实测，不能推广成所有资源取消场景都会抛异常。

## 靶场、元素库和脚本

- 靶场：[停止加载测试准备页](https://baobaomi900901.github.io/xpath/stop-load-test/index.html)。
- 元素库：`D:\code\元素库\260902_web元素`。
- 开始按钮：`web靶场_停止加载测试_开始测试_按钮`，实际映射到 `BUTTON#start-test`。
- 清理按钮：`web靶场_停止加载测试_清理测试环境_按钮`，实际映射到 `BUTTON#cleanup-worker`。
- 唯一、无日期脚本：[test_web_browser_is_load_completed.py](../test_web_browser_is_load_completed.py)。
- 环境准备/清理复用 [stop_load 脚本中的靶场上下文](../test_web_browser_stop_load.py)，本 API 的值和异常由当前脚本独立断言。

脚本连接 dev Runtime，复制库并清除副本中的捕获会话绑定，打开本次测试标签，使用库按钮触发加载与清理。
原始元素库不会被测试改写。Service Worker 操作限于 `/xpath/stop-load-test/`；如基线已存在该目录注册，清理后恢复注册。
本轮三次基线均无该注册，恢复已有注册的分支未实测。

## 合同与源码链路

冻结合同：[is_load_completed_contract_20261005.json](../is_load_completed_contract_20261005.json)。
下表路径均相对于上述只读 worktree/commit；冻结文件保存对应源码片段。

| 层 | 位置与合同 |
|---|---|
| SDK | `sdk/src/uiautoma/web/browser.py:234`，`is_load_completed(self) -> bool`；无公开参数，无等待时长参数；docstring 明确 `ActionError` 分支 |
| Client | `sdk/src/uiautoma/_core/client.py:1338`，RPC=`web.browser.is_load_completed`；内部 `timeout_ms=2000`；通过 `_run_web_browser_value` 处理业务错误 |
| Runtime | `runtime/services/pipe_server.py:2164` → `runtime/services/action_service.py:3045` → 同文件 `:5727` 的 `_run_web_browser_command`；失效 page_ref 返回 stale_page_reference/网页对象已失效 |
| Engine | `chrome/engine/plugin_packages/browser_command_package.js:1694`；先 `checkTabLoadFailure`，再检查标签 complete 与主文档 complete/loadEventEnd > 0 |
| 失败检查 | 同文件 `:512` 读取浏览器错误 URL 或 `chrome.webNavigation.getFrame(...).errorOccurred`；`:1906` 将 web_page_load_failed 返回为业务错误 |

返回值是 `bool`，成功完成为 True，正常加载中为 False。SDK 将 `loaded` / `is_load_completed` / `ready` 的真值合并。
内部 2000ms 是状态读取的 RPC 超时预算，不是等待整个页面完成的公开参数。

| 输入/失败路径 | 错误类型与预期 | 本轮覆盖 |
|---|---|---|
| 多余位置参数 | Python `TypeError`，在方法体前拒绝 | PASS；用不具 Runtime 的 object 作为 self 确认未连接服务 |
| 未知 `timeout` 关键字 | Python `TypeError`，在方法体前拒绝 | PASS |
| 网页加载失败 | `ActionError` / 网页加载失败 / web_page_load_failed | PASS；中止场景和原生连接失败错误页，各三次采样 |
| 网页对象已失效 | `ActionError` / 网页对象已失效 / stale_page_reference | PASS |
| 其他状态读取失败 | docstring 声明 `ActionError`；引擎保留目标标签不可用、命令失败等业务错误分支 | 未主动制造目标失联或读取超时，不计入已验证场景 |
| 桥接/插件不可用 | SDK Client 的 `_raise_business_error`（`:1997`）把 web_bridge_unavailable/native_host_unavailable/plugin_not_connected 映射为 `UnsupportedActionError`，不能笼统称为 ActionError | 未主动中断环境，不计入已验证场景 |

## 19 项用例和三轮结果

合同、位置参数、关键字、库目标、环境、靶场准备、准备页 True、开始慢资源、持续 False、
查询只读、中止异常、自然 False→True、完成页 True、刷新 False→True、原生错误页异常、
错误后恢复、库按钮清理 worker、关闭引用异常、最终资源清理，共 19 项。

| 运行 | PASS / 总数 | 等待中 False 采样 | 自然完成耗时（页面记录） | 刷新后完成耗时（页面记录） | 标签/退出码 |
|---|---|---|---|---|---|
| run1 | 19/19 | 15 次 | 3322ms | 3251ms | 3→3 / 0 |
| run2 | 19/19 | 15 次 | 3251ms | 3251ms | 3→3 / 0 |
| run3 | 19/19 | 16 次 | 3251ms | 3431ms | 3→3 / 0 |

自然完成/刷新使用 3 秒资源延迟；两阶段每轮都强制实际捕获 False 和 True，不允许“页面太快”作为通过。
每次 API 调用前后读取原生状态：两端是同一文档且稳定阶段时断言对应布尔值；跨越阶段的采样记录为 transition，仍断言 bool 类型。
资源成功还要求 worker 释放、图片有宽度和一次 window load，API 返回值不参与独立状态判据。
只读用例核对 URL、timeOrigin、run、资源事件未改变，资源保持等待而心跳增长。

### 准备抖动与探针发现

三轮均记录一次相同的准备页恢复：注册已经 activated，但首次文档没有 controller，页面报“测试环境准备超时，请重新打开准备页。”。
仅在精确满足该条件时重新导航准备页一次，由新文档接管现有 active worker；原始准备错误与恢复结果均保留在 JSON 中。
这发生在被测场景开始前，不重试 `is_load_completed()`，也不吞掉其他准备错误。

初始探针错误地只考虑“中止后返回布尔值”，遇到已在 docstring 中声明的加载失败异常而退出 1。
后续探针读完整失败检查链路，确认中止和原生错误页均是 ActionError 分支，正式断言据此修正。
该失败是探针判据不完整；原始输出保留，不记为产品缺陷或正式用例通过。

## 原始产物

- [探针初轮（退出 1）](artifacts/is_load_completed_20261005_probe1.txt)、[行为矩阵探针（退出 0）](artifacts/is_load_completed_20261005_probe2.txt)、[刷新探针（退出 0）](artifacts/is_load_completed_20261005_probe_reload.txt)。
- run1：[终端输出](artifacts/is_load_completed_20261005_run1.txt) / [完整 JSON](artifacts/is_load_completed_20261005_run1.json)。
- run2：[终端输出](artifacts/is_load_completed_20261005_run2.txt) / [完整 JSON](artifacts/is_load_completed_20261005_run2.json)。
- run3：[终端输出](artifacts/is_load_completed_20261005_run3.txt) / [完整 JSON](artifacts/is_load_completed_20261005_run3.json)。
- [本轮汇总产物](artifacts/is_load_completed_20261005.txt)。

## 复测命令

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_browser_is_load_completed.py
# 完整原生状态归档；默认人工报告保留摘要
uv run .\web\test_web_browser_is_load_completed.py --report-file .\web\evidence\artifacts\is_load_completed_manual.json
uv run .\web\test_web_browser_is_load_completed.py --json
uv run .\web\test_web_browser_is_load_completed.py --contract-only
```

退出码：0=所有已执行项 PASS；1=存在 FAIL；2=无 FAIL 但存在 BLOCKED。
`--contract-only` 只运行三项合同/参数检查，生命周期保留 READY_FOR_LIVE。

## 覆盖边界

已覆盖 Chrome 主文档、受控慢图片、持续 False、自然/刷新完成、真实连接拒绝错误页、中止后的失败状态、页面恢复和失效引用。
未覆盖 Edge/CEF/auto、iframe 子文档独立等待、下载导航、其他失败类型（DNS/TLS/HTTP 状态）、内部浏览器页、Provider/桥接中断。
“停止网络加载”不等于“成功完成页面加载”；本轮只证明上表具体场景。
不触碰代理/网络配置，不关闭用户原有页面；外部标签变化会报告 BLOCKED，不把用户操作定性为产品故障。

## 旧错误页结论的更新

2026-09-15 的错误页多次 False 是旧快照记录。本轮当前源码增加/包含浏览器失败检查，当前错误页三次均抛 ActionError，
所以清单中的“错误页恒为 False”已经移至历史记录。
这里不认定 GitHub Issue #59 的工作流状态，不推断其他旧问题已经关闭，也不扩展 `wait_load_completed()` 的验收结论。

公开 API 文档尚未生成，须按 `AGENTS.md` 的 PUBLIC DOCUMENTATION GATE 另获用户确认后做交接稿。

---

## 历史快照：2026-09-15，9/9

以下保留旧版本测试记录与当时推断；所有“恒为 False”“当前源码”等措辞仅属于旧快照，不能作为本轮当前行为。
旧推断中关于失败导航类型的概括未在本轮扩展验证。历史产物链接保留；当前脚本与命令以本文上半部分为准。


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

追因（依据 2026-09-15 被测源码快照）：引擎判据为 `liveTab.status === "complete" && probeTabDocumentReady(...)`，
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
