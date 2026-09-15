# `WebBrowser.go_forward()` 初次测试

## 用途

浏览器前进。`load_timeout` 仅限关键字传入，默认 20 秒；`0` 表示不等待加载完成，
`-1` 表示一直等待；调用成功返回 `None`。

`go_forward()` 需要当前页面存在「前进项」，因此它必须建立在一次后退之后。

## 真实验收结果

**VERIFIED：13/13 通过，退出码 0（前置路径为预热路径，见下节）。**

靶场：同一站点 hash 路由
`#/iframe-shadow-form`(A) → `#/element-html-test`(B) → `#/cookie-test`(C)
→ `#/form-controls`(D) → `#/keys-click-test`(E)

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无公开位置参数，`load_timeout` 仅限关键字且默认 20，返回 `None` |
| 页面准备 | 通过，成功创建测试页面 |
| 初始状态 | 通过，初始 URL 可读且页面 id 非空 |
| 历史准备 | 通过，建立 A→B→C 三页历史 |
| 默认前进（无参调用） | 通过，返回 `None`、到达 `form-controls`、页面 id 保持不变（前置路径 warm） |
| 关键字 `load_timeout` | 通过，返回 `None`、到达 `keys-click-test`、页面 id 保持不变（前置路径 warm） |
| `load_timeout=0` | 通过，返回 `None`；随后独立轮询确认前进收敛到 `element-html-test`（前置路径 warm） |
| 无前进项负例 | 通过，被 `ActionError` 拒绝，且当前页面未被改变 |
| 非法超时 `-2` | 通过，`ValueError` 拒绝 |
| 非法超时类型 `"bad"` | 通过，`ValueError` 拒绝 |
| 多余位置参数 | 通过，`TypeError` 拒绝 |
| 未知关键字 | 通过，`TypeError` 拒绝 |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 前置依赖：issue #58 的绕行与实测规律

制造「前进项」必须先后退一次，而 `go_back()` 在特定序列下稳定失败
（https://github.com/uiautoma/desktop/issues/58 ）。本项验收中**三次目标用例的直接
`go_back()` 全部失败**，原始原因均为：

```json
{"trace_info": "web_browser_command_failed",
 "failure_reason": "Cannot find a next page in history."}
```

因此脚本在每次后退前置失败后补一次 `execute_javascript()` 再重试（`precond_path=warm`）。
本次实测到的触发规律（每例全新开页）：

| 序列 | `back` 结果 |
|---|---|
| `js@A` → nav B → back | 成功 |
| `js@A` → nav B → nav C → back | 成功 |
| … → back → **forward** → nav F → back | **失败** |
| … → back → nav F → back（无 forward） | **失败** |
| … → back → forward → nav F → **js@F** → back | 成功 |

即：**一次 `back`/`forward` 之后再 `navigate`，紧跟的 `back` 必定失败；在该导航后补一次
页面级脚本命令即可恢复。** 该规律比 issue #58 正文最初记录的「页面未做过脚本访问时首次
调用失败」更精确。

该预热是已知缺陷的**绕行**，属于场景准备动作，不属于 `go_forward()` 的验收内容。

## 关键诊断观察

负例 `no_forward_entry`（当前确实没有前进项）被拒绝时的签名是：

```json
{"trace_info": "web_browser_command_failed",
 "failure_reason": "Cannot find a next page in history."}
```

与 #58 中「历史确实存在却后退失败」的签名**完全一致**。即引擎当前无法区分
「真的没有前进/后退项」与「有历史项却因渲染进程未提交而看不到」，两种情况的公开文案
都回落到「浏览器操作失败，请重试」。这一条对 #58 的根因定位与文案改进都有直接价值。

## 复测

脚本：[test_web_browser_go_forward.py](../test_web_browser_go_forward.py)
原始产物：[artifacts/go_forward_20260915.txt](artifacts/go_forward_20260915.txt)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_go_forward.py
uv run .\web\test_web_browser_go_forward.py --json   # 归档 JSON 报告
uv run .\web\test_web_browser_go_forward.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED（前置不可达）。

## 明确排除

- **冷状态（不预热）的 `go_forward()` 本次未验证**：其必需前置 `go_back()` 在冷状态
  被 #58 阻塞，不可达。
- `page.url` / `page.title` 属性在 `go_forward()` 后是否为过期值（源码显示该命令不更新
  这两个属性，与 `navigate()` 不同）：本次未断言。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `load_timeout=-1`（无限等待）路径。
- 页面关闭后 `go_forward()` 的 `stale_page_reference` 行为。
- 跨文档（非同站点）导航后的前进：本次全部使用同一站点的 hash 路由。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/58 （前置依赖缺陷）
