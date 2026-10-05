# `uiautoma.web.WebBrowser.stop_load()` 验证证据（2026-10-05）

## 用途与合同

`stop_load(self) -> None` 停止当前网页的导航与待完成资源加载，不终止页面 JavaScript。网页对象失效或停止加载失败时抛 `ActionError`。

被测只读 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`；当前 dev Runtime / Chrome。结论绑定此源码快照与以下实测覆盖范围。

| 层级 | 快照入口 | 行为 |
|---|---|---|
| SDK | `sdk/src/uiautoma/web/browser.py:220` | 无公开参数；RPC 超时固定 2000ms；成功返回 None |
| Client / Pipe | `sdk/src/uiautoma/_core/client.py:1524`；`runtime/services/pipe_server.py:2200` | RPC `web.browser.stop_load`，带当前 page_ref |
| Runtime | `runtime/services/action_service.py:3201`、`:5727` | 解析页面身份；失效返回 stale_page_reference / 网页对象已失效 |
| 引擎 | `chrome/engine/plugin_packages/browser_command_package.js:817`、`:1734` | `stopTabLoading` 发送 CDP `Page.stopLoading`；失败报告 stop_load_failed |

| 分支 | 期望 | 本轮覆盖 |
|---|---|---|
| 正在加载资源 | 返回 None，待完成加载被中止 | PASS，30 秒及 6 秒慢资源 |
| 已完成、已中止 | 返回 None，已加载内容保留 | PASS，准备页、完成页、连续重复调用 |
| 多余参数 | Python TypeError，未调用 Runtime | PASS，位置参数和 timeout 关键字 |
| 页面关闭后 | ActionError / 网页对象已失效 / stale_page_reference | PASS |
| 调试器失败、目标标签丢失、桥接故障 | 源码错误路径 | 未人为触发，不宣称通过 |

完整签名、docstring 与 SDK 入口保存在[合同快照](../remaining_web_contracts_20261004.json)。此前“SDK 直接抛 UnsupportedActionError”是证据编写错误，已更正；产品源码未修改。

## 真实验收结果

**VERIFIED：最后连续 3 轮，每轮 18/18 PASS、0 FAIL、0 BLOCKED，退出码 0。**

靶场：[停止加载测试准备页](https://baobaomi900901.github.io/xpath/stop-load-test/index.html)。元素库：`D:\code\元素库\260902_web元素`，仅使用临时副本。

- `web靶场_停止加载测试_开始测试_按钮` → `BUTTON#start-test`
- `web靶场_停止加载测试_清理测试环境_按钮` → `BUTTON#cleanup-worker`

| 轮次 | 结果 | stop_load 调用 / 停载后收敛耗时 | 标签清理 | 原始输出 / 完整状态 |
|---|---|---|---|---|
| 1 | 6/7 PASS + 1 BLOCKED，退出码 2 | 未执行真实停载 | 4→4 | [输出](artifacts/stop_load_20261005_run1.txt) / [JSON](artifacts/stop_load_20261005_run1.json) |
| 2 | 18/18 PASS，退出码 0 | 14.5ms / 30.8ms | 4→4 | [输出](artifacts/stop_load_20261005_run2.txt) / [JSON](artifacts/stop_load_20261005_run2.json) |
| 3 | 18/18 PASS，退出码 0 | 18.5ms / 32.7ms | 4→4 | [输出](artifacts/stop_load_20261005_run3.txt) / [JSON](artifacts/stop_load_20261005_run3.json) |
| 4 | 18/18 PASS，退出码 0 | 16.5ms / 30.8ms | 4→4 | [输出](artifacts/stop_load_20261005_run4.txt) / [JSON](artifacts/stop_load_20261005_run4.json) |

三轮 30 秒资源分别在页面等待约 1598ms、1544ms、1640ms 时出现 resource_error，均早于自然释放响应。

## 期望值来源与独立确证

成功不只看 None。先在同一真实靶场证明资源不调用停载时能够自然完成，再证明 30 秒请求在观察期内保持 pending、文档 interactive、主线程心跳持续增长；调用被测 API 后，组合核对：

1. 页面自身 DOM `#event-log` 出现当前 run 的 resource_error，且早于 delayMs；没有 worker_response_released。
2. 浏览器原生 `document.readyState` 已 complete；`img.complete=true`、`naturalWidth=0`。
3. 浏览器原生 Resource Timing 为同一图片 URL 记录 responseEnd，decodedBodySize 为 0；中止前此项尚无完成记录。
4. 停载后 JS 心跳继续增长；再次开始生成新的 run，新的慢资源也能中止。

这些是页面和浏览器状态，经 SDK JavaScript 通道读取，不以 stop_load 的产品返回值作为期望。正式 SDK 运行未独立接入原始 CDP `Network.loadingFailed`，因此不声称这些运行直接读到了 canceled=true 或 net::ERR_ABORTED；原始 CDP 取消证据属于下文独立靶场验证。DOM error 或 Resource Timing 零字节单独均不足以证明中止，必须结合自然完成对照、停载前观察和调用时序。

## 用例矩阵

| 用例 | 三轮结果 | 覆盖 |
|---|---|---|
| api_contract | PASS | 签名、docstring、方法源码与只读快照一致 |
| invalid_positional | PASS | 多余位置参数由 Python TypeError 拒绝 |
| invalid_keyword | PASS | 不存在的 timeout 参数由 Python TypeError 拒绝 |
| library_targets | PASS | 两个库名称各有一个 Web 条目 |
| environment | PASS | Runtime、Chrome、本次标签及临时库 |
| fixture_setup | PASS | worker 控制、默认 30 秒、两个按钮 DOM 映射 |
| stop_prepared_page | PASS | 已完成准备页停载返回 None，状态保留 |
| natural_control | PASS | 2 秒慢资源自然完成，图片有宽度，一次 load |
| stop_completed_resource | PASS | 资源完成后停载返回 None，图片和事件保留 |
| start_long_loading | PASS | 点击库开始按钮，30 秒资源 pending、JS 活跃 |
| control_without_stop | PASS | 至少 1 秒不调用停载，pending 保持、心跳增长 |
| stop_pending_resource | PASS | 返回 None，资源在延迟到期前中止，多项确证一致 |
| javascript_after_stop | PASS | 停载后仍有心跳增长 |
| repeated_stop | PASS | 再次调用两次均 None，无新资源事件 |
| restart_and_stop | PASS | 原页面新 run、6 秒慢资源再次中止 |
| cleanup_worker_button | PASS | 点击库清理按钮，本目录 registration 消失 |
| closed_page_error | PASS | 关闭后 ActionError、精确文案与 trace |
| cleanup | PASS | 临时目录移除，页面/库关闭，标签 4→4 |

## 修正记录与边界

- [探针 1](artifacts/stop_load_20261005_probe1.txt)：SDK 脚本位于隔离世界，window.stopLoadTest 为 undefined，原探针等不到状态。这是我的读取方式错误；改读共享 DOM 快照。[探针 2](artifacts/stop_load_20261005_probe2.txt)确认全部主路径，[探针 4](artifacts/stop_load_20261005_probe4.txt)补充浏览器原生计时与图片状态。
- [探针 3](artifacts/stop_load_20261005_probe3.txt)及正式轮 1：靶场准备页报告 Service Worker 控制超时，发生在 stop_load 场景前。正式后续三轮记录了 worker 已 activated、本次文档 controller 缺失；仅再次导航到准备页一次，随后 controller 正确、状态 ready。此恢复严格绑定该状态；其他准备错误仍 BLOCKED；不重试被测 stop_load，也不放宽停载判据。完整恢复前后状态保存在各 JSON 的 preparation_recovery。
- 本场景是 Service Worker 异步延迟静态资源响应，不是远端服务器实际耗时，也不覆盖主文档流式下载。未测试 Edge、多浏览器环境、并发导航、调试器异常及永久同步 JavaScript 循环。
- 三轮测试前未发现已注册的本目录 worker；脚本保留原有 registration 时的恢复逻辑，但该分支本轮未触发。清理仅操作本目录，未移除其他作用域注册。

## 历史条件检查与靶场验证

旧 `slow-load-30s.html` 的 hang.js 忙等 30 秒后继续 while(true)，不适合验收待完成资源的中止。此前条件检查为 SKIPPED，5/6 PASS + 1 KNOWN；[输出](artifacts/stop_load_20261005_target_gate2.txt)和[下载源码](artifacts/stop_load_20261005_target_gate2.json)保留。[首次网络不可达记录](artifacts/stop_load_20261005_target_gate.txt)的 WinError 10061 属于环境；脚本误标 FAIL 已改为 BLOCKED。

用户授权新增靶场时，源码仓库 `D:\code\xpath\WEB` 的基线 commit 为 `c886261211541cd48224dda51dc566af4710df16`。独立 Chrome 验证 public 目录与 dist 均 6/6 PASS，Pages 构建成功：[源码目录](artifacts/stop_load_fixture_20261005_green1.json)、[构建](artifacts/stop_load_fixture_20261005_build.txt)、[构建产物](artifacts/stop_load_fixture_20261005_built.json)。此阶段直接读取原始 CDP 网络事件 canceled=true / net::ERR_ABORTED，属于靶场机制证明。入口缺失的[红阶段记录](artifacts/stop_load_fixture_20261005_red2.txt)保留。

## 资源清理与复测

每轮使用临时元素库和本次标签；库清理按钮注销本目录 worker 后关闭本次标签和库、移除临时副本，并核对无外部新增/删除标签。三个成功轮次均 4→4；原始元素库未修改。

唯一无日期脚本：[test_web_browser_stop_load.py](../test_web_browser_stop_load.py)。

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_browser_stop_load.py
```

可加 `--observe-seconds 3` 延长停载前观察；`--contract-only` 仅做 3 项合同检查，不表示真实场景通过。退出码 0/1/2 对应无失败 / FAIL / BLOCKED。公开 API 文档交接稿等待用户另行确认。

[最终一致性复核](artifacts/stop_load_20261005_verification.txt)：连续三轮结果、唯一脚本入口、聚合入口合同检查、证据链接与清单状态均一致；清单共 112 项，94 VERIFIED / 10 SKIPPED / 6 DRAFT / 2 READY_FOR_LIVE。
