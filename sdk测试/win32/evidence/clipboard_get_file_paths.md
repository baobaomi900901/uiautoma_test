# `uiautoma.win32.clipboard.get_file_paths()` 验证证据

```yaml
api: "uiautoma.win32.clipboard.get_file_paths"
lifecycle: "VERIFIED"
verification_date: "2026-09-08"
verification_summary:
  passed: 12
  total: 12
  elapsed_ms: 76.9
  exit_code: 0
  tester_confirmed: true
  full_log_provided: true
  native_helper_retry_events: 1
  retries_per_reported_event: 1
  sdk_call_retries: 0
  original_unicode_text_restored: true
  temporary_directory_removed: true
persistent_script:
  path: "win32/test_win32_clipboard_get_file_paths.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "cb2d32154883737d7b8c68e83b857b5ab6e6e3688a7168dc0227a0e722d98975"
  command: 'uv run .\win32\test_win32_clipboard_get_file_paths.py'
```

## API 合同

```python
from uiautoma import win32

paths = win32.clipboard.get_file_paths()  # list[str]
```

无公开参数。返回剪贴板中的文件或目录路径列表，没有文件路径格式时返回空列表。
额外位置参数和 timeout 关键字抛出 TypeError。读取结果为新的 Python 列表，修改该列表
不应改变剪贴板或后续读取结果。本轮未验证 SDK 读取失败时的异常类型。

## 运行与独立校验

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_clipboard_get_file_paths.py
```

UIAutoma dev 应在运行，先复制普通文本，无需元素库或靶场。测试期间不要复制粘贴。
脚本创建临时英文文件、中文带空格文件及中文带空格目录，以原生 API 构造 CF_HDROP，
并使用 DragQueryFileW 独立读取路径，与 SDK 的返回类型、路径数量和顺序逐项比对。
不依赖 SDK set_files、clear 或 get_text 准备或验证场景。

读取前后确认文件列表及文本内容未改变。结束时恢复原 Unicode 文本，确认剪贴板不再
引用临时路径，并删除临时目录。仅保护 Unicode 文本，不备份富文本、图片等其他格式。
脚本依赖同目录其他 clipboard 测试中的原生和日志辅助函数。

## 本轮真实结果

| 测试项 | 验证内容 | 耗时 | 结果 |
| --- | --- | --- | --- |
| API 合同 | 无参数、返回list[str] | 0.0ms | PASS |
| 测试准备 | 保存原文本，创建临时资源 | 2.8ms | PASS |
| 单文件 | english.txt | 57.7ms | PASS |
| 单目录 | 测试 文件夹 | 1.5ms | PASS |
| 多个文件 | english.txt、中文 文件.txt，顺序一致 | 1.9ms | PASS |
| 文件目录混合 | 测试 文件夹、中文 文件.txt、english.txt，顺序一致 | 3.0ms | PASS |
| 纯文本剪贴板 | 无CF_HDROP，返回[]且内容不变 | 1.3ms | PASS |
| 空剪贴板 | 返回[]且未创建文件格式 | 0.9ms | PASS |
| 重复读取 | 连续三次路径和顺序一致 | 2.7ms | PASS |
| 返回列表隔离 | 清空旧列表不影响原数据及后续返回 | 1.7ms | PASS |
| 调用参数边界 | 多余位置参数和timeout被拒绝 | 0.2ms | PASS |
| 资源清理 | 原文本恢复、临时目录删除 | 1.8ms | PASS |

测试者提供完整12项日志并明确确认。汇总12/12通过，总耗时76.9ms，退出码0。
临时目录名称为 `uiautoma-get-file-paths-42bzinui`，位于系统临时目录，已删除。

## 重试观察与限制

本轮出现一次“原生辅助：剪贴板打开重试1次后成功”。日志未标明具体所属调用，
不推断占用者；SDK get_file_paths 调用本身没有重试且全部成功。

本轮通过不代表共享剪贴板竞争问题已修复，不关闭或替代 Issue #49。
未覆盖持续占用、损坏CF_HDROP、超长路径、网络路径、文件已删除后的路径读取等场景。
