# `win32.screenshot.manual_to_clipboard()` 验证证据

```yaml
api: "win32.screenshot.manual_to_clipboard"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 5
  total: 5
  elapsed_ms: 3525.3
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  clipboard_format: "CF_DIB"
  bit_count: 32
  image_size: [520, 222]
  original_unicode_text_restored: true
persistent_script:
  path: "win32/test_win32_manual_to_clipboard.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "892f6fac7a6ba761587262decc704e97ed2581e49cd12ae932b06cdf8374bb26"
  command: 'uv run .\win32\test_win32_manual_to_clipboard.py --non-interactive'
```

## 用途与合同

```python
ok = win32.screenshot.manual_to_clipboard(timeout=30)
```

启动屏幕框选层，用户拖选区域后将截图写入剪贴板。仅有关键字参数timeout，默认30秒；
成功返回True，Esc取消、超时或写入失败抛ActionError。截图格式为CF_DIB。

## 运行与测试方法

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_manual_to_clipboard.py --non-interactive
```

无需元素库或靶场。先复制普通文本供恢复；按提示拖选包含文字或图形的区域。
脚本使用原生剪贴板API独立读取CF_DIB位图头，核对宽高、planes、bit_count和compression，
并验证返回True。结束把原Unicode文本写回剪贴板；不保护图片、富文本等其他原格式。

## 本轮真实结果

| 测试项 | 实际结果 | 耗时 | 结论 |
| --- | --- | --- | --- |
| API合同 | timeout默认30秒，仅限关键字，返回bool | 0.0ms | PASS |
| 剪贴板准备 | 原Unicode文本已保存 | 0.5ms | PASS |
| 人工框选并写入 | True；CF_DIB；520×222；32 bit；planes=1；compression=0 | 3520.4ms | PASS |
| 参数限制 | 位置参数、未知关键字均TypeError | 0.0ms | PASS |
| 资源清理 | 原Unicode文本恢复；最后截图被替换 | 3.7ms | PASS |

完整5/5通过，总耗时3525.3ms，退出码0，测试者明确确认。
框选耗时包含人工拖选时间，不作为截图性能指标。

## 验证边界

本轮只验证一次人工PNG/CF_DIB框选写入，不覆盖不同timeout、Esc取消、超时、空/纯色选区、
剪贴板持续占用、图片与文本格式并存、跨显示器框选及剪贴板图片人工粘贴结果。
`--non-interactive`不自动完成框选；该接口仍要求人工操作。
