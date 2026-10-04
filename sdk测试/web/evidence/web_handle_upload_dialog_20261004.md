# `uiautoma.web.handle_upload_dialog()` 验证证据（2026-10-04）

## 用途与合同

处理浏览器的文件上传对话框。

```python
handle_upload_dialog(file_names: str | list[str], dialog_result: str='ok', mode: str='auto', *, simulative: bool=False, clipboard_input: bool=True, wait_appear_timeout: float=20, force_ime_eng: bool=False, send_key_delay: int=50, focus_timeout: int=1000) -> None
```

- 被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论只绑定该源码快照和本次 dev Runtime。
- SDK 入口：`sdk\src\uiautoma\web\__init__.py:420`。
- 调用链：web.dialog.upload → ActionService 文件对话框绑定/输入/确认。
- 完整签名、默认值、docstring 与入口源码保存在 [合同快照](../remaining_web_contracts_20261004.json)。

## 真实验收结果

**SKIPPED（2026-10-04；4/6 PASS + 0 FAIL + 2 KNOWN；2 轮；退出码 0）**

页面：[靶场](https://baobaomi900901.github.io/xpath/#/upload-dialog-test)。
元素库：`D:\code\元素库\260902_web元素`；只使用临时副本。

| 轮次 | 结果 | 原始报告 |
|---|---|---|
| 1 | 4/6 PASS + 0 FAIL + 2 KNOWN；退出码 0 | [web_handle_upload_dialog_20261004_run1.txt](artifacts/web_handle_upload_dialog_20261004_run1.txt) |
| 2（阶段诊断） | 4/6 PASS + 0 FAIL + 2 KNOWN；退出码 0 | [原始输出](artifacts/web_handle_upload_dialog_20261004_provider_diagnosis.txt)、[结构化报告](artifacts/web_handle_upload_dialog_20261004_provider_diagnosis.json) |

## 期望值来源与独立确证

计划观察真实文件对话框选择/取消后的 DOM FileList；当前 Provider 无法点击打开对话框，所以正向操作跳过。 参数错误按冻结源码合同检查；具体覆盖见下表和原始报告。

| 用例 | 状态 | 期望/确证方法 |
|---|---|---|
| `api_contract` | PASS | 公开签名与只读源码快照一致 |
| `environment` | PASS | Runtime/Chrome/现有靶场与临时库可用 |
| `choose_file` | KNOWN | 处理真实文件对话框，DOM FileList 与磁盘一致 |
| `cancel` | KNOWN | 取消文件对话框保留原文件 |
| `invalid_result` | PASS | 非法 dialog_result 抛 InvalidParamsError |
| `cleanup` | PASS | 关闭本次页面和库、删除临时目录、复核标签和文件弹窗 |

## 实测行为与边界

跳过原因：

- 两条正向用例均停在 `click_upload_input`：元素已定位为 `input-upload-single`，但 `e.click(simulative=True)` 抛 `ActionError`，trace 为 `uiautomation_provider_unavailable`。`api_called=False`，尚未调用 `handle_upload_dialog()`，没有唤起本次文件选择窗口。
- 原始异常的第三层 `raw` 明确给出 `missing_capabilities`：`capture_web_from_ref`、`win32_observation_actions`、`win32_observation_sessions`。Runtime 对 Provider 的启动能力校验拒绝了当前二进制。
- 被测 Runtime/SDK：worktree `D:\code\desktop`，commit `cb9332d1a04c09e04df54af958e028b2bc45af9b`；实际 Provider 路径为 `D:\code\desktop\assets\provider\UIAutoma.UIAutomation.Provider.exe`，本机清单记录来源 worktree `D:\code\rust_uia`，commit `e8a7545cdd58d744addf972deebaec4faf67a048`。
- 需要在产品侧对齐 Runtime 与 Provider 的能力合同后复测。诊断材料：[交接草稿](../../issues/drafts/handle_upload_dialog_provider_capabilities_20261004.md)。本测试工作区不修改产品文件。

本次仅验收报告列出的场景；未列出的浏览器模式、DPI、参照系、控件种类、超大输入、网络异常或原生交互路径均不宣称通过。SKIPPED 的合同检查通过不等于实际功能通过。

## 资源清理与复测

各轮 cleanup 均 PASS：仅关闭本次标签页和库连接，删除本次 UUID 临时目录；标签数 1→1，未留下本次文件对话框。原始库和用户原页面保留。

脚本：[test_web_handle_upload_dialog_20261004.py](../test_web_handle_upload_dialog_20261004.py)。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_handle_upload_dialog_20261004.py
```

退出码 0 表示无 FAIL（允许 KNOWN/跳过），1 表示存在 FAIL。通过范围与生命周期必须结合报告读取。
