# `WebBrowser.close()` 初次测试

## 用途

关闭当前网页。`ignore_beforeunload` **仅限关键字**，默认 `False`；`True` 时自动确认
「确认离开页面」对话框；调用成功返回 `None`。

## 真实验收结果

**VERIFIED：10/10 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/` 下 `#/iframe-shadow-form`、
`#/element-html-test`、`#/cookie-test` 三个路由，每个页面都带本次运行的唯一标记
`uiautoma_close_run=<run_id>`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无公开位置参数，`ignore_beforeunload` 仅限关键字且默认 `False`，返回 `None` |
| 页面准备 | 通过，创建带唯一运行标记的测试页面 |
| 默认关闭 | 通过，返回 `None`，且 0.018s 内该标签页已从 `web.get_all()` 消失 |
| 关闭后复用页面对象 | 通过，被 `ActionError` 拒绝，trace 为 `stale_page_reference` |
| `beforeunload` 处理器注入 | 通过，在 `execution_world="MAIN"` 注册成功 |
| `close(ignore_beforeunload=True)` | 通过，返回 `None`，带处理器的页面在 0.019s 内关闭 |
| `close(ignore_beforeunload=False)`（干净页面） | 通过，返回 `None`，0.013s 内关闭 |
| 位置参数 `close(True)` | 通过，`TypeError` 拒绝 |
| 未知关键字 | 通过，`TypeError` 拒绝 |
| 资源清理 | 通过，运行标记零残留（收尾扫描无遗留页面） |

## 「标签页真的关了」的三项独立观测

只看命令返回 `None` 不足以证明标签页被关闭，因此用三条互相独立的证据：

1. **`web.get_all()` 复核**：带运行标记的页面在关闭后从列表消失（0.008~0.019s）。
2. **失效拒绝**：关闭后继续对该页面对象调用 `get_url()`，被 `ActionError` 拒绝，
   trace 为 `stale_page_reference`——说明页面引用确实失效，而不是仍指向存活标签页。
3. **零残留扫描**：收尾时对运行标记做全量扫描，确认没有任何遗留页面（本次 0 个需清理）。

## `beforeunload` 的诚实边界

引擎对默认关闭与 `beforeunload` 有显式处理
（`chrome/engine/plugin_packages/browser_command_package.js:825-833`）：

- `ignore_beforeunload === true` 且收到 `Page.javascriptDialogOpening`（`type === "beforeunload"`）
  → 通过 CDP `Page.handleJavaScriptDialog {accept: true}` 自动接受；
- 否则标记 `pending`，返回 `beforeunload_pending: true`，不阻塞调用。

本次**只验证了 `ignore_beforeunload=True` 的最外层行为**（命令成功返回 `None`、标签页确实关闭）。
**无法确认 Chrome 是否真的弹出了 `beforeunload` 对话框**，因此也无法确认 CDP 自动接受分支
是否被真正执行：Chrome 要求页面先有用户激活才会弹该对话框，而本脚本是用
`execute_javascript` 以编程方式注册处理器，没有真实用户输入。旁证是关闭耗时仅 0.019s，
与「走普通移除路径」而非「等待对话框流程」一致。

因此本项证据的准确表述是：**`ignore_beforeunload=True` 在存在 `beforeunload` 处理器的页面上
能正常关闭标签页**；「对话框真实弹出时被自动接受」这一分支未经验证。

## 对其它验收证据的意义

`close()` 是所有验收脚本的清理原语（此前 `reload` / `is_load_completed` /
`wait_load_completed` / `go_forward` 等脚本的 `cleanup` 用例都依赖它）。它现在已被独立验收，
因此先前各脚本「本次资源精确清理 = PASS」的结论得到了原语层面的支撑。

## 复测

脚本：[test_web_browser_close.py](../test_web_browser_close.py)
原始产物：[artifacts/close_20260915.txt](artifacts/close_20260915.txt)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_close.py
uv run .\web\test_web_browser_close.py --json   # 归档 JSON 报告
uv run .\web\test_web_browser_close.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

脚本会为每个页面附加 `uiautoma_close_run=<run_id>` 标记，收尾时全量扫描该标记，
即使中途失败也不会留下本次创建的标签页。

## 明确排除

- **`beforeunload` 对话框真实弹出并被自动接受的路径**：需要真实用户激活才会弹出（见上节）。
- **`ignore_beforeunload=False` 且页面存在 `beforeunload` 处理器**：引擎会返回
  `beforeunload_pending: true` 并挂起原生对话框，需要人工处理，本次未自动触发。
- 关闭非活动标签页、多标签页与多窗口批量关闭（属 `web.close_all()` 范围）。
- 关闭前页面正在加载 / 正在执行脚本时的并发语义。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- 已关闭页面重复调用 `close()` 的幂等性（仅验证了复用页面对象被 `stale_page_reference` 拒绝）。
