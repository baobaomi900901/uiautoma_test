# `uiautoma.win32.clipboard.clear()` 验证证据

```yaml
api: "uiautoma.win32.clipboard.clear"
lifecycle: "VERIFIED"
verification_summary:
  passed: 9
  total: 9
  elapsed_ms: 222.4
  exit_code: 0
  tester_confirmed: true
  full_log_provided: true
  native_helper_retry_events: 4
  retries_per_reported_event: 1
  sdk_call_retries: 0
  original_unicode_text_restored: true
persistent_script:
  path: "win32/test_win32_clipboard_clear.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "d686a319e0b2a4254346e9bbb5e498a0d9864fc5e660c2c54fabb28984049dac"
  command: 'uv run .\win32\test_win32_clipboard_clear.py'
```

## API 合同

```python
from uiautoma import win32

win32.clipboard.clear()  # 返回 None
```

无公开参数，清空剪贴板后返回 None。额外位置参数和 timeout 关键字由 Python 签名
抛出 TypeError。本轮未验证 SDK 清空失败时的异常类型。

## 运行方式与测试方法

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_clipboard_clear.py
```

保持 UIAutoma dev 运行，先复制一段普通文本；不需要元素库或靶场。
测试期间不要复制粘贴。脚本以原生 API 写入文本，调用 SDK clear 后独立检查
CountClipboardFormats 为0、CF_UNICODETEXT 不存在。区分空字符串文本格式与没有任何
剪贴板格式的状态。结束时原生恢复原 Unicode 文本并读回核验；不打印原文。

测试仅恢复 Unicode 文本，不备份图片、富文本等其他原始格式。
复用同目录 clipboard_set_text、clipboard_get_text 和 clipboard_input 的辅助函数。

## 本轮覆盖与结果

| 测试项 | 验证内容 | 耗时 | 结果 |
| --- | --- | --- | --- |
| API 合同 | 无参数，返回 None | 0.0ms | PASS |
| 剪贴板准备 | 保存原 Unicode 文本 | 0.4ms | PASS |
| 英文文本 | 清空后格式数0、无Unicode文本 | 55.7ms | PASS |
| Unicode文本 | 同上 | 1.8ms | PASS |
| 空文本格式 | 已存在的空字符串文本格式被清除 | 103.6ms | PASS |
| 已经为空 | 原生清空后调用仍返回 None | 2.3ms | PASS |
| 连续清空 | 首次清空后再调用三次，格式数始终0 | 56.9ms | PASS |
| 调用参数边界 | 位置参数和timeout被拒绝，文本未改变 | 0.7ms | PASS |
| 资源清理 | 原文本恢复且原生读回一致 | 0.6ms | PASS |

运行汇总：9/9通过，总耗时222.4ms，退出码0；测试者明确确认。
总耗时取脚本汇总，不要求与逐项四舍五入后的耗时相加完全一致。

## 重试观察与验证范围

日志显示四条“原生辅助：剪贴板打开重试1次后成功”。这些来自场景准备、原生核验或
清理辅助流程，日志没有标注每条所属的具体调用，不推断其占用者或逐项对应关系。
SDK clear 本身没有自动重试，本轮所有被测调用均成功。

本轮结果不意味着剪贴板竞争问题已全面解决，也不替代 get_text 的 Issue #49。
尚未准备图片、文件列表、自定义格式场景；不声称已经验证这些来源的清空行为。
