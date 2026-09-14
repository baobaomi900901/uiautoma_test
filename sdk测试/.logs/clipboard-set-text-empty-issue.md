## 缺陷

`uiautoma.win32.clipboard.set_text("")` 将已经传入的空字符串误判为缺参，抛出 `InvalidParamsError: missing text`。公开签名为 `set_text(text: str) -> None`，当前说明没有禁止空字符串。

从用户角度，将字符串变量写入剪贴板时，空值是正常输入；不应被解释为未提供参数。

## 最小复现

在 UIAutoma dev 运行的测试环境执行以下调用。预期行为修复后会替换剪贴板内容，请事先保存需要保留的数据。

```python
from uiautoma import win32

win32.clipboard.set_text("")
```

实际：`InvalidParamsError: missing text`。
预期：正常返回 None，将空 Unicode 文本写入剪贴板；原生读回为空字符串。
此能力不要求等同于 clear() 清空所有剪贴板格式。

## 真实测试证据

本地专项脚本 `win32/test_win32_clipboard_set_text.py`：11/12通过，退出码1，总耗时22.7ms。

- 空字符串项失败，原因为 missing text。
- 中英文、Unicode符号、多行文本（含非空白内容）、关键字参数均通过原生 CF_UNICODETEXT 读回核验。
- 整数与 None 按当前 SDK 的 str() 转换后写入成功，None 写入的是字符串 "None"。
- 原剪贴板文本成功恢复。

## 源码定位

当前检查的 Desktop worktree 中：

- `sdk/src/uiautoma/win32/clipboard.py`：set_text 调用 clipboard_set_text(str(text))。
- `runtime/services/capabilities.py`：clipboard.set_text 将 text 声明为必填参数。
- `runtime/services/pipe_server.py`：通用 `_missing_params()` 使用以下条件拒绝空字符串或纯空白字符串：

```python
if isinstance(value, str) and not value.strip():
    return name
```

- 因此请求尚未进入 `_handle_clipboard_set_text()` 即返回 missing text。
- `runtime/services/clipboard_service.py` 的 set_text 本身把文本交给 _write_text，没有禁止空字符串。

纯空格、纯换行、纯制表符预计也会被相同规则拒绝，这是源码推断，尚未在本轮真实测试中单独执行。

## 建议修复及验收

- 对 clipboard.set_text 区分“字段不存在”和“字段存在且为空字符串”，允许空文本及纯空白文本。
- 缩小修复范围，避免直接放宽所有 RPC 的必填字符串校验。
- 覆盖空字符串、纯空格、纯换行、纯制表符，以及一般Unicode文本；原生读回应保留实际内容。
- 保持缺少 text 参数的错误行为；明确直接 RPC 的 null 行为，不与 SDK 的 str(None) 转换混淆。
- 添加参数分发回归测试，并由测试者重新执行剪贴板专项测试确认清理成功。

当前仅提交缺陷，产品源码未修改。
