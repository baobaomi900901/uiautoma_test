## 补充：set_files() 也出现同类失败（2026-09-08）

测试者执行本地 `win32/test_win32_clipboard_set_files.py`，原生准备临时文件/目录，通过 CF_HDROP + DragQueryFileW 独立核验。被测 SDK 调用没有重试。

本轮15项中13项通过，以下两项失败：

```text
05/15 多文件列表
原因: 设置剪贴板文件列表失败：OpenClipboard failed: 5
异常: RpcProtocolError

06/15 文件与目录元组
原因: 设置剪贴板文件列表失败：OpenClipboard failed: 5
异常: RpcProtocolError
```

单文件字符串、单文件夹字符串，以及关键字传入的两个路径列表均成功；因此不能据此判定多文件列表或元组能力不支持。错误参数检查通过，原剪贴板文本已恢复，临时目录已删除。

汇总：13/15通过，总耗时339.7ms，退出码1，READY_FOR_LIVE。原生辅助流程另外报告六次单次打开重试成功，这些不是 SDK 自动重试，不能与上述两项被测调用的失败混淆。

### 新增源码定位

- `runtime/services/clipboard_service.py::_write_file_paths()` 直接单次调用 OpenClipboard(None)，失败立即返回；该写入函数没有复用读取路径的 `_open_clipboard()`。修复时仅修改读取辅助函数不足以覆盖此路径。
- Runtime set_files 返回业务错误 `clipboard_set_files_failed`。
- `sdk/src/uiautoma/win32/clipboard.py::set_files()` 说明写入失败为 ActionError，实际暴露 RpcProtocolError，与本 issue 的读取异常映射问题同类。

请将本 issue 排查和验收范围扩展至文件列表写入：短暂竞争释放后能在有界时间内完成写入，持续失败则报告与合同一致的异常，并验证原生路径、数量、顺序及内存/剪贴板资源释放。

具体占用进程、失败频率和稳定触发条件仍未确认，不认定两轮错误必然由同一个占用者引起。本次仅补充证据，未修改产品或测试代码。
