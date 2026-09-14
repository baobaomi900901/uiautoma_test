# `win32.screenshot.manual_to_file()` 验证证据

```yaml
api: "win32.screenshot.manual_to_file"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 5
  total: 5
  elapsed_ms: 9343.5
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  selected_image_format: "PNG"
  selected_image_size: [476, 150]
  selected_image_non_uniform: true
  temporary_screenshot_removed: true
persistent_script:
  path: "win32/test_win32_manual_to_file.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "6d29cb2fb91570458bba4b2fe56585b0c67727182e7625a01d4d42a4745e9432"
  command: 'uv run .\win32\test_win32_manual_to_file.py --non-interactive'
```

## 用途与参数

```python
path = win32.screenshot.manual_to_file(
    image_path,
    image_format="",
    timeout=30,
)
```

启动屏幕框选层，等待用户拖选区域并将截图保存到文件，返回实际路径字符串。
`image_path`和`image_format`可位置或关键字传入；`timeout`仅限关键字，默认30秒。
支持png、jpg/jpeg和bmp，格式为空时从路径扩展名推断。Esc取消或超时属于失败。

## 运行与人工操作

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_manual_to_file.py --non-interactive
```

无需元素库或靶场。脚本创建临时目录并提示拖选包含文字或图形的区域；完成后使用
GDI+解码核对PNG、尺寸和非纯色，删除本次截图及临时目录。测试不修改显示设置、
剪贴板或其他窗口状态。

## 本轮真实结果

| 项目 | 结果 |
| --- | --- |
| API合同 | 路径/格式可位置传入，timeout仅限关键字，返回str路径 | PASS |
| 测试准备 | 临时输出路径创建 | PASS |
| 人工框选并保存 | 返回路径正确；PNG，476×150，非纯色，11771 bytes | PASS |
| 参数限制 | 缺参、多余位置参数、重复image_format均TypeError | PASS |
| 资源清理 | 截图及临时目录已删除 | PASS |

完整5/5通过，总耗时9343.5ms，退出码0，测试者明确确认。
框选动作调用耗时9329.1ms，包含用户实际拖选时间，不作为截图性能指标。

## 验证边界

本轮只执行PNG人工框选，不覆盖JPG/BMP、扩展名推断、Esc取消、超时、跨屏框选、
最小选区、纯色选区或框选层被其他窗口抢占。`--non-interactive`只影响焦点等待，
并不让框选自动化；本接口仍要求人工操作。
