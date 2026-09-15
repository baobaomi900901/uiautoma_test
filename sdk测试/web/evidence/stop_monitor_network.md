# `WebBrowser.stop_monitor_network()` 初次测试

## 用途

停止监听当前网页的网络请求。**无参数**，返回 `None`。

## 真实验收结果

**VERIFIED：13/13 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无参数，返回 `None` |
| 页面准备 / 初始状态 | 通过 |
| 监听准备 | 通过，启动后捕获 1 条记录（HTTP 404） |
| 停止监听 | 通过，返回 `None` |
| 停止后不再可取回响应 | 通过，`get_responses()` 抛 `ActionError`（trace `web_network_monitor_not_found`） |
| 停止后页面仍可用 | 通过，`execute_javascript()` 正常返回（会话未被破坏） |
| 重复停止（已无监听） | 通过，返回 `None`（幂等，不报错） |
| 从未启动时停止 | 通过，返回 `None` |
| 停止后重新启动监听 | 通过，可再次捕获记录（1 条） |
| 位置参数 / 未知关键字 | 通过，`TypeError` / `TypeError` |
| 资源清理 | 通过，停止监听并仅关闭本次创建的测试页面 |

## 「监听确实停了」的三项独立证据

单看命令返回 `None` 不足以证明监听已停止，因此本脚本用三条互相独立的证据：

1. **停止后 `get_responses()` 被拒绝**：trace `web_network_monitor_not_found`，说明引擎侧
   该标签页已无监听记录；
2. **页面仍可正常使用**：停止监听后 `execute_javascript()` 正常返回，说明释放调试器监听
   没有破坏会话（停止是「收尾」而不是「破坏」）；
3. **可以重新启动**：停止后再 `start_monitor_network()` 能重新捕获真实请求
   （1 条），说明停止是干净可逆的，而不是把标签页置于不可恢复状态。

## 幂等性

| 场景 | 结果 |
|---|---|
| 启动监听后停止 | `None` |
| 紧接着再停止一次 | `None`（不报错） |
| 在从未启动监听的页面上停止 | `None`（不报错） |

引擎对 `network_stop` 在无监听时直接返回成功，因此调用方无需先探测监听是否存在；
SDK 侧该方法也未调用 `raise_for_error()`，与「无监听不算错误」的设计一致。

## 环境说明

走 CDP 调试器实现，不依赖合成器或视口，本次运行时的「Chrome 窗口最小化」对其无影响；
也无导航历史前置，不受 issue #58 影响。

## 复测

脚本：[test_web_browser_stop_monitor_network.py](../test_web_browser_stop_monitor_network.py)
原始产物：[artifacts/stop_monitor_network_20260915.txt](artifacts/stop_monitor_network_20260915.txt)

```powershell
uv run .\web\test_web_browser_stop_monitor_network.py
uv run .\web\test_web_browser_stop_monitor_network.py --json
uv run .\web\test_web_browser_stop_monitor_network.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- 停止监听时仍有请求在途的收尾语义（未构造该并发场景）。
- 监听未停止就关闭标签页时调试器监听的释放路径。
- 多标签页同时监听时逐页停止的相互影响。
- 停止后再次启动的**记录隔离**（重启会丢弃旧记录，已在 `start_monitor_network.md` 记录）。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
