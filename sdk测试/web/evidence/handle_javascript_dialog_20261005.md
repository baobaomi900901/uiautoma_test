# `WebBrowser.handle_javascript_dialog()` 指定库元素复验（2026-10-05）

## 用途、合同与源码快照

处理浏览器 JavaScript 原生 `alert`、`confirm`、`prompt`；返回 `None`。

```python
handle_javascript_dialog(self, dialog_result: str='ok', *, text: str | None=None, wait_appear_timeout: float=20) -> None
```

- `dialog_result`：`ok` 或 `cancel`。非法值抛 `InvalidParamsError`，trace=`invalid_params`。
- `text`：确定 Prompt 时写入文本；`None` 保留默认值；取消时忽略。
- `wait_appear_timeout`：秒，0 不等待、-1 一直等待；无对话框时抛 `ActionError`，trace=`web_dialog_timeout`。
- SDK/Runtime worktree：`D:\code\desktop`，commit `cb9332d1a04c09e04df54af958e028b2bc45af9b`。SDK 入口 `sdk\src\uiautoma\web\browser.py:349`，通过 `web.dialog.accept/dismiss/prompt` 调用 Runtime 的原生 UIA 路径。
- Provider 来源 worktree：`D:\code\rust_uia`，commit `a18ff222a6c237cce0c5b39b93d92aa26f34946b`；本机 manifest 版本 0.1.1。
- 只读靶场源码 worktree：`D:\code\xpath`，commit `c886261211541cd48224dda51dc566af4710df16`，`WEB\src\pages\WebDialogTestPage.tsx`。
- 页面：[网页对话框测试](https://baobaomi900901.github.io/xpath/#/web-dialog-test)。库：`D:\code\元素库\260902_web元素`，打开临时副本。

## 真实验收结果

**VERIFIED：连续 3 轮，每轮 16/16 PASS、0 FAIL、0 KNOWN，退出码 0。**

| 轮次 | 结果 | 产物 |
|---|---|---|
| 1 | 16/16 PASS；cleanup PASS；标签数 4→4 | [输出](artifacts/handle_javascript_dialog_20261005_run1.txt)、[JSON](artifacts/handle_javascript_dialog_20261005_run1.json) |
| 2 | 16/16 PASS；cleanup PASS；标签数 4→4 | [输出](artifacts/handle_javascript_dialog_20261005_run2.txt)、[JSON](artifacts/handle_javascript_dialog_20261005_run2.json) |
| 3 | 16/16 PASS；cleanup PASS；标签数 4→4；纯 JSON 输出与报告一致 | [输出](artifacts/handle_javascript_dialog_20261005_run3.txt)、[JSON](artifacts/handle_javascript_dialog_20261005_run3.json) |

用户指定库元素映射均已现场核对：

| 名称 | DOM ID |
|---|---|
| `web靶场_触发alert对话框_按钮` | `btn-alert` |
| `web靶场_触发confirm对话框_按钮` | `btn-confirm` |
| `web靶场_触发Prompt对话框_按钮` | `btn-prompt` |

## 用例与确证方式

| 用例 | 期望与实测 |
|---|---|
| `api_contract` | 参数顺序、默认值、关键字限制、返回注解与公开合同一致 |
| `environment` | Chrome、靶场、临时元素库可用 |
| `alert_element` | 指定 Alert 库元素指向 btn-alert |
| `confirm_element` | 指定 Confirm 库元素指向 btn-confirm |
| `prompt_element` | 指定 Prompt 库元素指向 btn-prompt |
| `alert_accept` | 返回 None；页面状态为 Alert 已关闭 |
| `confirm_accept_true` | 返回 None；页面状态为“确定（true）” |
| `confirm_cancel_false` | 返回 None；页面状态为“取消（false）” |
| `prompt_accept_text` | 返回 None；页面显示输入值 `uiautoma 音乐` |
| `prompt_default_text` | text=None，页面显示默认值 `UiPilot` |
| `prompt_cancel_null` | 返回 None；页面显示“取消（null）” |
| `cancel_ignores_text` | cancel 同时传 text，页面仍显示“取消（null）” |
| `no_dialog_timeout` | 没有弹窗且等待 0 秒，ActionError，trace=web_dialog_timeout |
| `invalid_result` | dialog_result='maybe'，InvalidParamsError，trace=invalid_params |
| `invalid_timeout` | wait_appear_timeout=-2，InvalidParamsError |
| `cleanup` | 对话框检查、页面、库连接和临时目录清理完成；标签数恢复 |

每次通过**已保存的库元素**执行 `click(simulative=True, delay_after=1)`；触发前激活本次页面。辅助读取对话框文本确认类型，停留 1 秒供人工观察，再调用被测 API。

正向结果由页面自身 `#status` 确证：它的 React 事件处理器直接记录原生 `confirm()` 的 true/false 和 `prompt()` 的输入/null。脚本读取其文本前缀，时间戳作为实测数据保留，不参与固定值比较。测试不注入 `alert/confirm/prompt`，不修改页面状态或新增自建靶场。

## 探针、历史与边界

- [2026-09-15 历史测试](handle_javascript_dialog.md)为 15/15，使用 JS 定时触发与页面全局变量；保留该结论及原脚本。本轮使用用户提供的专门页面与三个库按钮，计数为 16/16。
- [首探针输出](artifacts/handle_javascript_dialog_20261005_probe_initial.txt)中 Alert 已通过，但随后辅助 `get_javascript_dialog_text()` 读取 Confirm 超时，trace=`web_dialog_timeout`；当时尚未调用被测处理 API，不据此判定处理 API 缺陷。该文件是 stdout，异常详情见本段记录。
- [调整后的探针](artifacts/handle_javascript_dialog_20261005_probe_focused.txt)在每次点击前激活页面，并保留 1 秒点击后等待，七条真实场景均通过；后续三轮正式验收全部通过。未确认首探针瞬时失败的具体成因，不宣称某个产品问题已被修复。
- 本轮只验证 Chrome、当前库与上述七条正向场景。未验证 Edge、无限等待、多个对话框排队、beforeunload、页面导航中的对话框或 Alert 的 text 参数。
- `auto_handle_popup()` 的 DOM Modal 场景与本 API 分开记录；可用场景已在 `#/keys-click-test` 找到，但尚缺已保存的关闭按钮，未宣称自动关闭验收通过。

## 清理与复测

三轮均仅关闭本次页面和库连接、删除本次 UUID 临时目录；标签数 4→4，`external_added=[]`、`external_removed=[]`。收尾尝试取消本次原生对话框时都返回无对话框超时，`javascript_swept=False`、`sweep_error=None`，没有遗留待处理的本次弹窗。一次性探针的脚本和日志在归档后删除，其他历史探针保留。

脚本：[test_web_browser_handle_javascript_dialog_20261005.py](../test_web_browser_handle_javascript_dialog_20261005.py)。

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_browser_handle_javascript_dialog_20261005.py
```

可选：`--dialog-observe-seconds 3` 延长窗口观察时间；`--element-library`、`--target-url` 覆盖测试输入；`--contract-only` 自检；`--json` 纯 JSON 输出；`--report-file <路径>` 保存报告。

退出码 0 为通过，1 为失败，2 为环境阻塞；只有本轮真实场景和清理全部 PASS 才记 VERIFIED。
