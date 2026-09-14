# `uiautoma.web.close_all()` 验证证据

```yaml
api: "uiautoma.web.close_all"
lifecycle: "READY_FOR_LIVE"
baseline_revalidation:
  source_commit: "a4598ec3221c8ffc9eb39f0b0beff7f8ca107a43"
  contract_only: "PASS"
  live_status: "BLOCKED"
  blocker: "远端 main 缺少本地 Web Stack 安装入口，无法刷新 Runtime 与插件"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.close_all 的最小 SDK、Runtime 和 Chromium 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/__init__.py"
      symbols: ["close_all"]
      fingerprint: "a5e8b8fbcf23059b35ce7f2d9742ccf18039fd38"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.web_browser_close_all"]
      fingerprint: "16b3ce68f682e1485cd25c55de5ab2c9a9de6a33"
    - path: "runtime/services/pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_browser_close_all"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_browser_close_all", "ActionService._run_web_browser_command"]
      fingerprint: "003039f702f44764c258ab8fb30a9ffca384aded"
    - path: "chrome/engine/plugin_packages/browser_command_package.js"
      symbols: ["closeAllBrowserWindows", "close_all"]
      fingerprint: "f75c8c047d341c97535974c28c9d572d4dd927a1"
  verified_contract:
    signature: "close_all(mode='cef', *, task_kill=False, ignore_beforeunload=False) -> None"
    parameter_order: ["mode", "task_kill", "ignore_beforeunload"]
    keyword_only_parameters: ["task_kill", "ignore_beforeunload"]
    tested_mode: "chrome"
    tested_options:
      task_kill: false
      ignore_beforeunload: false
    success_result: "None"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_questions:
    - "首次指定 Chrome Profile 时 Runtime 尚不能确认 profileDirectoryHash"
persistent_script:
  path: "tests/SDK/web/test_web_close_all.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "df08ec3286a7ece2b6cf5157499ce4d3b1e994a9"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_close_all.py`

```powershell
uv run python tests\SDK\web\test_web_close_all.py `
  --mode chrome `
  --profile-directory Default `
  --base-url http://localhost:7199/ `
  --second-url http://localhost:7199/anchor-test `
  --post-close-timeout 5 `
  --allow-close-all-pages
```

脚本先预检两个靶场页面和 Runtime，再请求使用 Chrome `Default` Profile。首次 Profile
启动真实链路返回 `browser_profile_identity_unknown` 时，只针对该 trace 复用已经启动的
唯一 Chrome 会话；随后通过 `web.create()` 准备两个带本次 UUID 查询标记的页面。

关闭前由 `web.get_all()` 确认两个页面都存在。目标断言只直接调用
`web.close_all(mode="chrome", task_kill=False, ignore_beforeunload=False)`。关闭后的有界轮询
等待页面枚举为空或浏览器会话断开，最终清理在 `finally` 中逐项确认本次两个页面已经由
目标调用关闭。

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值和参数种类 |
| 破坏性操作授权 | `PASS` | 真实运行显式传入 `--allow-close-all-pages` |
| 外部靶场预检 | `PASS` | 根页面与 `/anchor-test` 均返回 HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| Default Profile 启动 | `PASS` | 请求 `Default`，已知身份缺口下复用唯一已启动会话 |
| 两个唯一页面准备 | `PASS` | 返回类型、Chrome 模式和两个唯一 URL 均正确 |
| 关闭前页面快照 | `PASS` | 当前页面 `2`，本次页面 `2/2`，缺失 `0` |
| 全部页面关闭 | `PASS` | `close_all()` 调用完成并返回 `None` |
| 关闭后验收 | `PASS` | 页面枚举为 `0` |
| 页面清理 | `PASS` | 两个本次页面均确认由目标调用关闭，`2/2` |

## 基线切换前最近一次用户验证

- 日期：2026-08-05
- 模式：`chrome`
- Profile 目录：`Default`
- 插件：`UIAutoma 自动化插件 <codex/sdk-test @ 26-08-05 17:58>`
- 总状态：`PASS`
- 退出码：`0`
- 靶场预检：约 `54.3ms`，两个页面均为 HTTP 200
- Runtime 预检：约 `2.3ms`
- 页面准备：约 `20990.1ms`，`2/2`
- 关闭前快照：约 `3.4ms`，当前页面 `2`、本次页面 `2/2`
- `close_all()`：约 `12.0ms`，返回 `None`
- 关闭后验收：约 `37.6ms`，页面枚举为 `0`
- 清理结果：`PASS`，本次页面 `2/2` 项确认清理

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `task_kill=True`。
- `ignore_beforeunload=True`。
- `close_all()` 返回后并发新开的页面。
- `beforeunload` 页面的人工作用。
- Chrome Profile 显示名或账号与 Profile 目录的对应关系。
- Default Profile 的 Runtime `profileDirectoryHash` 身份确认。
