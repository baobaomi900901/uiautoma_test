# `uiautoma.web.handle_upload_dialog()` 验证证据（2026-10-05）

## 用途与合同

处理已经出现的浏览器原生文件选择窗口：`ok` 填入完整文件路径并确认，`cancel` 关闭窗口；返回 `None`。本次验收文件选择，不涉及服务端上传。

```python
handle_upload_dialog(file_names: str | list[str], dialog_result: str='ok', mode: str='auto', *, simulative: bool=False, clipboard_input: bool=True, wait_appear_timeout: float=20, force_ime_eng: bool=False, send_key_delay: int=50, focus_timeout: int=1000) -> None
```

- Runtime/SDK worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论绑定该源码快照和本次 dev 环境。
- Provider 来源 worktree：`D:\code\rust_uia`；commit：`a18ff222a6c237cce0c5b39b93d92aa26f34946b`；本机 manifest 版本 `0.1.1`。实际二进制 `D:\code\desktop\assets\provider\UIAutoma.UIAutomation.Provider.exe` 的 SHA-256：`C939D69F3199544D301E5B976A9C1C180E4F788A0A067171BF4C1397BF403FEE`，与 manifest 一致。
- SDK 入口：`sdk\src\uiautoma\web\__init__.py:420`；调用链：`web.dialog.upload` → `ActionService.web_file_upload_dialog()` → 原生窗口绑定、文件名输入、确认或取消。
- 参数、默认值及 SDK 源码完整快照：[合同记录](../remaining_web_contracts_20261004.json)。公开签名未变，三轮均检查一致。
- 靶场：[上传对话框测试](https://baobaomi900901.github.io/xpath/#/upload-dialog-test)。只读页面源码快照：worktree `D:\code\xpath`，commit `c886261211541cd48224dda51dc566af4710df16`，`WEB\src\pages\UploadDialogTestPage.tsx`。
- 元素库：`D:\code\元素库\260902_web元素`，打开临时副本，保留原库。

## 真实验收结果

**VERIFIED：连续 3 轮，每轮 10/10 PASS、0 FAIL、0 KNOWN，退出码 0。**

| 轮次 | 结果 | 产物 |
|---|---|---|
| 1 | 10/10 PASS；cleanup PASS；标签数 2→2 | [原始输出](artifacts/web_handle_upload_dialog_20261005_run1.txt)、[JSON](artifacts/web_handle_upload_dialog_20261005_run1.json) |
| 2 | 10/10 PASS；cleanup PASS；标签数 2→2 | [原始输出](artifacts/web_handle_upload_dialog_20261005_run2.txt)、[JSON](artifacts/web_handle_upload_dialog_20261005_run2.json) |
| 3 | 10/10 PASS；cleanup PASS；标签数 2→2 | [原始输出](artifacts/web_handle_upload_dialog_20261005_run3.txt)、[JSON](artifacts/web_handle_upload_dialog_20261005_run3.json) |

用户指定元素及现场核对：

| 库元素名 | DOM 节点 | 属性 |
|---|---|---|
| `web靶场_单文件上传测试_按钮` | `input-upload-single` | `INPUT`、`type=file`、`multiple=False` |
| `web靶场_多文件上传测试_按钮` | `input-upload-multiple` | `INPUT`、`type=file`、`multiple=True` |

## 用例与独立确证

| 用例 | 期望与实测 |
|---|---|
| `api_contract` | 公开签名与源码快照一致 |
| `environment` | Runtime、Chrome、现有靶场、临时库副本可用 |
| `single_element` | 按指定名称定位，核对单文件 input 的 ID、类型和 multiple 属性 |
| `choose_file` | 真实窗口出现；传入单个完整路径字符串；API 返回 None、窗口关闭、FileList 与磁盘文件名和大小一致 |
| `cancel` | 再次唤起单文件窗口；`cancel` 返回 None、窗口关闭、原 FileList 不变 |
| `multiple_element` | 按指定名称定位，核对多文件 input 的 ID、类型和 multiple 属性 |
| `choose_multiple_files` | 真实窗口出现；传入两个完整路径组成的列表；API 返回 None、窗口关闭、FileList 两个文件与磁盘一致 |
| `cancel_multiple` | 再次唤起多文件窗口；`cancel` 返回 None、窗口关闭、原两个文件保留 |
| `invalid_result` | `dialog_result='bad'` 抛 `InvalidParamsError`，文案为“dialog_result 必须为 ok 或 cancel” |
| `cleanup` | 本次页面、库连接和临时目录清理完成；无本次弹窗和标签残留 |

真实操作顺序：按库名定位 → `click(simulative=True)` → 用 `ctypes` 枚举新增且由本次 Chrome 窗口拥有的可见 `#32770` 窗口 → 停留 1 秒供人工观察 → 调用 `handle_upload_dialog()` → 独立复核窗口消失 → 页面侧读取 `input.files`。

文件写入本次临时目录：`upload_甲.txt`、`upload_乙.txt`，本轮各为 30 字节。期望文件名取自 `Path.name`，大小取自磁盘 `stat().st_size`，与页面的 FileList 比较；多文件比较先按名称排序，不为 API 增加未声明的顺序要求。取消前后直接比较原 FileList。

本次使用 Chrome，API 参数为 `simulative=False`、`clipboard_input=False`、`wait_appear_timeout=8`；取消时 `file_names=[]`。脚本不写剪贴板。

## 修订记录与边界

- [2026-10-04 历史验收](web_handle_upload_dialog_20261004.md)为 4/6 PASS、2 KNOWN，停止在点击阶段，尚未执行上传 API。该历史结果保留。
- 2026-10-05 用户明确提供上述两个库元素；脚本已改用它们并增加多文件确认、取消和元素映射检查，报告从 6 项扩展为 10 项。
- 本机 Provider 来源从 `e8a7545c` 更新为 `a18ff222` 后，本次真实点击和四条核心场景均通过，此前能力缺失阻塞未再复现；不把旧 Provider 的结论推广到新二进制。
- 只有单文件确认、单文件取消、多文件确认、多文件取消四项全部 PASS，脚本才允许本 API 进入 VERIFIED。
- 本次未验收 Edge、auto 模式、多窗口歧义、剪贴板输入、模拟键入、无限等待、超时和其他参数异常矩阵；未宣称这些分支通过。

## 清理与复测

三轮 cleanup 均 PASS：各轮关闭本次页面和库连接、删除 UUID 临时目录；标签数均 2→2，`external_added=[]`、`external_removed=[]`、`new_dialogs=[]`。本次一次性探针另行删除；其他历史探针保留。

沿用原运行入口：[test_web_handle_upload_dialog_20261004.py](../test_web_handle_upload_dialog_20261004.py)。

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_handle_upload_dialog_20261004.py
```

可覆盖路径与页面：`--element-library`、`--target-url`；合同检查：`--contract-only`；结构化输出：`--json` 或 `--report-file <路径>`。本次三轮均退出码 0，且真实场景与清理全 PASS；后续重跑需结合生命周期、逐项结果与退出码读取。
