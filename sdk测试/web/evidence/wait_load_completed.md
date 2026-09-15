# `WebBrowser.wait_load_completed()` 初次测试

## 用途

等待页面加载完成。`timeout` 为**位置或关键字**参数，默认 20 秒；`0` 不等待加载完成，
`-1` 一直等待；调用成功返回 `None`。

源码另有等价别名 `wait_ready = wait_load_completed`，本脚本核对了两者指向同一实现。

## 真实验收结果

**VERIFIED：12/12 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`timeout` 位置或关键字且默认 20，返回 `None`；别名 `wait_ready` 指向同一实现 |
| 页面准备 | 通过，成功创建测试页面 |
| 初始状态 | 通过，初始 URL 可读且页面 id 非空 |
| 默认等待（已加载完成） | 通过，返回 `None`（0.015s） |
| 位置参数 `20` | 通过，返回 `None`（0.016s） |
| 等待未完成页面 | 通过，等待前 `is_load_completed=False`，等待返回 `None`（0.448s），等待后为 `True` |
| `timeout=0` | 通过，返回 `None`（0.015s，不等待加载完成） |
| `timeout=-1` | 通过，已加载完成的页面上立即返回 `None`（0.015s） |
| 非法超时 `-2` | 通过，`ValueError` 拒绝 |
| 非法超时类型 `"bad"` | 通过，`ValueError` 拒绝 |
| 未知关键字 | 通过，`TypeError` 拒绝 |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 「等待」确实发生过的证据

只看「返回 `None`」无法区分「真的等了」与「本来就已完成就立刻返回」。因此
`wait_pending_load` 用例先制造未完成窗口，再用 `is_load_completed()` 夹逼：

```text
reload(load_timeout=0)
  → is_load_completed() = False      # 窗口已制造
  → wait_load_completed(20)
  → 返回 None（0.448s）
  → is_load_completed() = True       # 等待覆盖了加载过程
```

对照组：已加载完成的页面上同一个调用只需 0.015s。即等待耗时随实际加载状态变化，
不是固定立即返回。

`timeout=0` 的实测行为与文档一致（「不等待加载完成」，返回 `None` 而非报错），
因此引擎里对显式 `timeout_ms === 0` 的分支（`readinessTimeoutMs`）与公开文档一致。

## 与 issue #58 的关系

本 API 只读、不需要导航历史前置，本脚本不调用后退/前进，因此不受 #58 影响。

## 复测

脚本：[test_web_browser_wait_load_completed.py](../test_web_browser_wait_load_completed.py)
原始产物：[artifacts/wait_load_completed_20260915.txt](artifacts/wait_load_completed_20260915.txt)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_wait_load_completed.py
uv run .\web\test_web_browser_wait_load_completed.py --json   # 归档 JSON 报告
uv run .\web\test_web_browser_wait_load_completed.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **超时真的发生的路径未验证**：需要一个持续不完成的页面才能在 `timeout` 内等到超时
  （预期抛 `ActionError` + `web_wait_ready_timeout`）。本机 `localhost:7199` 靶场当前不可达，
  静态站点无法制造该场景。
- `timeout=0` 施加在**未完成**页面上的行为（只验证了已完成页面）。
- 等待期间页面被关闭 / 引用失效的并发语义。
- `iframe` 子框架未完成时的等待语义。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
