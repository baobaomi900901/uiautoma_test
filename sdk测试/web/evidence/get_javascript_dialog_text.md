# `WebBrowser.get_javascript_dialog_text()` 初次测试

## 用途

获取网页弹出的对话框文本。`wait_appear_timeout` **仅限关键字**，默认 20 秒
（`0` 不等待，`-1` 一直等待）；返回 `str`。

实现路径：Runtime 的原生 UIA 路径（`runtime/desktop/browser_dialogs.py`）识别
`JavaScriptTabModalDialogViewViews` 后，取其中 `TextControl` 的名称拼接为文本
（若无文本控件则退回第一个输入框的名称）。

## 真实验收结果

**VERIFIED：13/13 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`wait_appear_timeout` 仅限关键字且默认 20，返回注解 `str` |
| 页面准备 / 初始状态 | 通过 |
| `alert` 文本 | 通过，读到 `'UIA-alert-msg'`（`str`，等待 0.404s） |
| `confirm` 文本 | 通过，读到 `'UIA-confirm-msg'`（等待 0.396s） |
| `prompt` 文本 | 通过，读到 `'UIA-prompt-msg'`（等待 0.404s） |
| 延迟出现的对话框 | 通过，延迟 **1.5s** 出现的 `alert` 仍被等到并读回（等待 1.544s） |
| 无对话框 + `timeout=0` | 通过，立即 `ActionError`（trace `web_dialog_timeout`，0.028s） |
| 无对话框 + `timeout=2` | 通过，等待 **2.02s** 后 `ActionError`（trace `web_dialog_timeout`） |
| `wait_appear_timeout=-2` | 通过，`InvalidParamsError` |
| 位置参数 / 未知关键字 | 通过，`TypeError` / `TypeError` |
| 资源清理 | 通过，兜底清扫对话框后仅关闭本次创建的测试页面 |

## 等待路径的证据

脚本在触发对话框后**不做 sleep**，直接调用被测 API，由 API 自己等待对话框出现：

| 用例 | 对话框出现时刻 | API 实际耗时 | 结论 |
|---|---|---|---|
| `alert_text` | 触发后 300ms | 0.404s | 确实等待了出现 |
| `confirm_text` | 触发后 300ms | 0.396s | 同上 |
| `prompt_text` | 触发后 300ms | 0.404s | 同上 |
| `waits_for_late_dialog` | 触发后 **1500ms** | **1.544s** | 长时间等待路径成立 |
| `no_dialog_timeout_zero` | 不出现 | 0.028s | `0` 不等待，立即拒绝 |
| `no_dialog_timeout_positive` | 不出现 | **2.02s** | 按给定超时等待后再拒绝 |

即「等待出现 → 读到文本」与「超时 → 明确拒绝」两条路径都被独立证实，耗时与实际时序吻合。

## 环境说明：最小化窗口下依然可用

本次运行时 Chrome 主窗口为**最小化**状态（见 `scroll_to.md` 的环境说明）。本 API 走 UIA
控件树读取，不需要像素或合成帧，因此在最小化窗口下工作正常——与同样最小化时不可验证的
`behavior="smooth"` 形成对比。

## 安全约定

未处理的模态对话框会阻塞页面。每个用例断言后都会处理掉对话框（`ok` 或 `cancel`），
收尾处再做一次兜底清扫，最后才关闭页面。

## 复测

脚本：[test_web_browser_get_javascript_dialog_text.py](../test_web_browser_get_javascript_dialog_text.py)
原始产物：[artifacts/get_javascript_dialog_text_20260915.txt](artifacts/get_javascript_dialog_text_20260915.txt)

```powershell
uv run .\web\test_web_browser_get_javascript_dialog_text.py
uv run .\web\test_web_browser_get_javascript_dialog_text.py --json
uv run .\web\test_web_browser_get_javascript_dialog_text.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`wait_appear_timeout=-1`（一直等待）**：未验证（需要不出现且可中断的场景）。
- 无文本控件的对话框形态（源码会退回第一个输入框名称，本次三种对话框均有文本控件）。
- 多行文本、超长文本与富文本对话框的拼接结果。
- `beforeunload` 与文件选择框（分别见 `close.md` 与对话框处理相关 API）。
- 多个对话框排队时的取值归属。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
