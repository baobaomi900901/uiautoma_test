## 问题

Win32 SDK `win32.clipboard.get_text()` 在真实测试中发生一次 `OpenClipboard failed: 5`，向调用者抛出 `RpcProtocolError`。Runtime 仅尝试打开剪贴板一次，且公开文档声明的读取失败异常为 `ActionError`，与实际不一致。

此问题发生于被测 SDK/Runtime 的读取调用，不是测试脚本原生读写辅助函数失败。与 #46（测试脚本复制/恢复缺少重试）区分；与 #48（set_text 空字符串误判缺参）也不同。

## 实测记录

环境：UIAutoma dev 运行；本地脚本 `win32/test_win32_clipboard_get_text.py` 使用原生 CF_UNICODETEXT 准备文本并独立核验，SDK 调用没有自动重试。

执行：`uv run .\win32\test_win32_clipboard_get_text.py`

第04/14项“英文数字”失败：

```text
原因: 读取剪贴板文本失败：OpenClipboard failed: 5
异常: RpcProtocolError
```

原生准备值为 `Clipboard_123`。同轮中文、Unicode、多行、纯空白、空文本、无文本格式、重复读取及清理均通过。
汇总：13/14通过，总耗时18.1ms，退出码1；原剪贴板文本恢复成功。

目前只有一次失败报告，频率、占用进程和稳定触发条件未知。短暂剪贴板竞争是可能诱因，并非已确认根因；没有证据表明英文文本内容触发错误。

## 源码定位

- `runtime/services/clipboard_service.py::_open_clipboard()`：OpenClipboard(None) 单次失败后立即返回错误，无短暂不可用的限时重试。
- `ClipboardService.get_text()`：读取失败返回业务错误 `clipboard_get_text_failed`。
- `sdk/src/uiautoma/_core/client.py::_desktop_result()`：业务错误交给 `_raise_business_error()`。
- `_raise_business_error()` 未单独映射 clipboard_get_text_failed，最终落入 RpcProtocolError。
- `sdk/src/uiautoma/win32/clipboard.py::get_text()` 的 Raises 说明为 ActionError。

Runtime 正常返回了可解释的系统操作失败，不应误导调用者以为 RPC 协议损坏。

## 建议修复与验收

- 在 Runtime 剪贴板打开边界处理短暂不可用，采用有截止时间的有限重试；持续失败仍明确报告，不无限等待或返回空字符串掩盖错误。
- 将读取失败映射为与公开合同一致的异常，保留原生错误码、业务错误标识和必要诊断；检查映射改动的直接影响，不扩大为无关 RPC 重构。
- 增加可控竞争测试：辅助进程短时持有剪贴板后释放，读取在期限内成功；持续持有则在有限时间内抛出正确异常。
- 覆盖原生失败时异常类型与文档一致、资源正确释放；没有文本格式时仍正常返回空字符串。
- 回归运行14项真实测试，确认读取内容不变且原文本恢复成功。

当前测试保持 READY_FOR_LIVE；本次仅提交缺陷，未修改产品或测试代码。
