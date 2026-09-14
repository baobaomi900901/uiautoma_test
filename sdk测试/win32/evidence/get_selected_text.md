# `win32.get_selected_text()` 验证证据

```yaml
api: "win32.get_selected_text"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 11
  total: 11
  elapsed_ms: 1142.4
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  clipboard_restored: true
  temporary_notepad_closed: true
  temporary_file_removed: true
persistent_script:
  path: "win32/test_win32_get_selected_text.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "3ec1b7dce88d39dcd4814fba87737aeaa89468c8e53d29235ac4c7140b52fd6c"
  command: 'uv run .\win32\test_win32_get_selected_text.py --non-interactive'
```

## 用途与合同

```python
selected = win32.get_selected_text(wait_time=0, **kwargs)
```

读取当前前台文本控件的选中内容，返回str。函数内部使用Ctrl+C和临时哨兵文本，
并恢复调用前的Unicode剪贴板文本。wait_time默认0，可位置或关键字传入；正数用于
读取前等待。未知关键字当前兼容并忽略；非法wait_time由float转换阶段拒绝。

## 运行与场景

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_get_selected_text.py --non-interactive
```

脚本自动打开临时记事本，使用原生EM_SETSEL准备选区，以原生CF_UNICODETEXT独立核对，
不依赖元素库或靶场。结束关闭记事本、删除临时文件并恢复原剪贴板文本。

## 本轮结果

| 场景 | 观察 | 结果 |
| --- | --- | --- |
| API合同 | wait_time默认0、任意关键字兼容、返回str | PASS |
| 全文选择 | 返回完整Unicode文本 | PASS |
| 部分选择 | 返回`UIAutoma` | PASS |
| Unicode选择 | 返回`😀✓` | PASS |
| 零等待 | 返回`UIAutom` | PASS |
| 有限等待 | 返回`UIAutom` | PASS |
| 无选中 | 返回空字符串 | PASS |
| 重复读取 | 连续三次结果一致 | PASS |
| 关键字兼容 | 未知关键字忽略；非法wait_time拒绝 | PASS |
| 资源清理 | 剪贴板恢复、记事本关闭、临时文件删除 | PASS |

测试准备209.1ms，临时记事本PID126996、Edit句柄921744；总计11/11通过，
总耗时1142.4ms，退出码0，测试者明确确认。原生辅助出现一次剪贴板打开重试并成功，
SDK调用未自动重试。

## 验证边界

本轮覆盖Windows记事本Unicode文本的全文、部分、Emoji、无选中和等待参数。
未覆盖浏览器、富文本、图片/文件选择、剪贴板持续占用或跨权限窗口。
未知关键字“兼容并忽略”是当前实现行为，不代表所有未来参数均会被接受。
临时PID、句柄和耗时仅为本轮观察值，不固定为后续运行预期。
