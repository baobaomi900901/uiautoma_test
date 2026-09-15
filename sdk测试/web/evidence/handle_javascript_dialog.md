# `WebBrowser.handle_javascript_dialog()` 初次测试

## 用途

处理网页弹出的提示框、确认框或输入框。

| 参数 | 默认 | 说明 |
|---|---|---|
| `dialog_result` | `ok` | `ok`（确定）、`cancel`（取消）；**位置或关键字** |
| `text` | `None` | 输入框中要填写的文本，`None` 保留原内容；取消时忽略；**仅限关键字** |
| `wait_appear_timeout` | `20` | 等待对话框出现的秒数；`0` 不等待，`-1` 一直等待；**仅限关键字** |

返回 `None`。非法 `dialog_result` 在 SDK 侧即抛 `InvalidParamsError`（trace `invalid_params`）。

实现路径：三项都走 Runtime 的原生 UIA 路径（`runtime/desktop/browser_dialogs.py`），
在浏览器窗口树中识别 `RootView` → `JavaScriptTabModalDialogViewViews`，再用
`InvokePattern` 点击按钮（`accept` 点第一个、`cancel` 点最后一个），**不使用 CDP**。

## 真实验收结果

**VERIFIED：15/15 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`dialog_result` 位置或关键字且默认 `ok`；`text` / `wait_appear_timeout` 仅限关键字（默认 `None` / `20`）；返回 `None` |
| 页面准备 / 初始状态 | 通过 |
| `alert` + `ok` | 通过，返回 `None`，且页面恢复响应 |
| `confirm` + `ok` | 通过，**页面内 `confirm()` 真实返回 `True`** |
| `confirm` + `cancel` | 通过，**页面内 `confirm()` 真实返回 `False`** |
| `prompt` + `text="typed-value"` | 通过，**页面内 `prompt()` 真实返回 `'typed-value'`** |
| `prompt` + `cancel` | 通过，**页面内 `prompt()` 返回 `null`**（Python `None`） |
| 取消时忽略 `text` | 通过，`prompt()` 仍返回 `None` |
| 无对话框时 | 通过，`ActionError`，trace `web_dialog_timeout` |
| 非法 `dialog_result` | 通过，`InvalidParamsError`（trace `invalid_params`） |
| `wait_appear_timeout=-2` | 通过，`InvalidParamsError` |
| `text` 用位置传入 | 通过，`TypeError`（`text` 仅限关键字） |
| 未知关键字 | 通过，`TypeError` |
| 资源清理 | 通过，兜底清扫对话框后仅关闭本次创建的测试页面 |

## 处理结果不只看返回值

命令返回 `None` 不能证明「对话框被正确接受/取消」，因此本脚本在页面内回读真实语义：

| 用例 | 页面内回读 | 期望 |
|---|---|---|
| `confirm_accept_true` | `window.__confirm_result` | `True` |
| `confirm_cancel_false` | `window.__confirm_result` | `False` |
| `prompt_accept_text` | `window.__prompt_result` | `'typed-value'` |
| `prompt_cancel_null` | `window.__prompt_result` | `None`（`prompt()` 取消返回 `null`） |
| `cancel_ignores_text` | `window.__prompt_result` | `None`（`text` 未被写入） |

## 环境说明：最小化窗口下依然可用

本次运行时 Chrome 主窗口为**最小化**状态（见 `scroll_to.md` 的环境说明）。与
`behavior="smooth"`（依赖合成器，最小化时不可验证）不同，**对话框处理在最小化窗口下完全正常**：
它走 UIA 控件树与 Invoke 模式，不需要像素或合成帧。每次点击耗时约 1.07~1.58s，其中包含
引擎为规避 Chromium 的双击间隔保护而做的等待。

## 安全约定

未处理的模态对话框会阻塞页面。本脚本的每个用例在断言后都会处理掉对话框，收尾处再做一次
`handle_javascript_dialog("ok", wait_appear_timeout=0)` 兜底清扫，最后才关闭页面；
即使单个用例失败也不会留下阻塞页面的对话框。

## 复测

脚本：[test_web_browser_handle_javascript_dialog.py](../test_web_browser_handle_javascript_dialog.py)
原始产物：[artifacts/handle_javascript_dialog_20260915.txt](artifacts/handle_javascript_dialog_20260915.txt)

```powershell
uv run .\web\test_web_browser_handle_javascript_dialog.py
uv run .\web\test_web_browser_handle_javascript_dialog.py --json
uv run .\web\test_web_browser_handle_javascript_dialog.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`wait_appear_timeout=-1`（一直等待）**：需要「不出现对话框且可中断」的场景，未验证。
- `beforeunload` 对话框：属关闭流程，见 `close.md`；本 API 未覆盖。
- 文件选择框（保存/上传）：由 `handle_save_dialog()` / `handle_upload_dialog()` 负责。
- 多个对话框排队、对话框出现期间页面导航或关闭的并发语义。
- `alert` 上使用 `text` 参数（会走 prompt 分支）的语义。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
