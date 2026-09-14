# `uiautoma.win32.Win32Element.screenshot_to_clipboard()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.screenshot_to_clipboard"
lifecycle: "VERIFIED"
verification_summary:
  passed: 6
  total: 6
  elapsed_ms: 756.8
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  manual_image_confirmed: true
persistent_script:
  path: "win32/test_win32_screenshot_to_clipboard.py"
  fingerprint_kind: "SHA-256"
  fingerprint: "1361ae293eefbd01552b8e309952590466e042821b16400bad96f5d8f82a205e"
  command: 'uv run .\win32\test_win32_screenshot_to_clipboard.py'
  clipboard_helper: "win32/test_win32_save_screen_to_clipboard.py"
test_environment:
  package_dir: 'D:\code\元素库\260902_win元素'
  tab: "win32靶场_tab_item表单控件"
  target_element: "win32靶场_表单控件_表单面板"
  target_application: "Win32 靶场 - UIA"
  physical_width: 984
  physical_height: 631
  clipboard_format: "CF_DIB"
  bit_count: 32
cleanup:
  status: "PASS"
  mouse_restored: true
  foreground_restored: true
  borrowed_package_closed: true
  application_left_running: true
  final_tab: "表单控件"
  last_image_retained_in_clipboard: true
  original_clipboard_restored: false
```

## API 与运行方式

```python
element.screenshot_to_clipboard() -> None
```

- 无公开参数；多余位置参数和 `timeout` 关键字均触发 `TypeError`。
- 成功返回 `None`，动作结果保存在 `last_result`；底层默认预算为 5 秒。
- 截取元素的屏幕区域并以 `CF_DIB` 图片替换剪贴板内容，目标应保持可见、无遮挡。

从测试根目录运行，脚本参数为无：

```powershell
uv run .\win32\test_win32_screenshot_to_clipboard.py
```

脚本借用当前启用元素库，激活靶场并点击“表单控件”Tab，获取表单面板后连续截图两次。
每次校验返回值、`last_result.ok`、剪贴板更新序号、DIB 位图头及尺寸，并检查截图前后
元素物理矩形一致。结束时恢复鼠标与原前台窗口，关闭借用的 Package；靶场停留在表单页。
最后一张图片保留在剪贴板供人工粘贴，不恢复原剪贴板内容。

## 本次实测

| 测试项 | 验收结果 | 耗时 |
| --- | --- | --- |
| API 合同 | 无公开参数，返回标注为 None | 0.1ms |
| 元素与页面准备 | 已切换表单页，面板物理尺寸 984 × 631 | 684.8ms |
| 截图到剪贴板 | 返回 None，动作成功，剪贴板更新，CF_DIB 32 bit、984 × 631 | 24.5ms |
| 重复截图 | 再次返回 None，动作成功，剪贴板再次更新且格式尺寸一致 | 25.2ms |
| 参数数量限制 | 位置参数和 timeout 关键字均被 TypeError 拒绝 | 0.0ms |
| 资源恢复 | 鼠标与原前台窗口恢复，Package 关闭，靶场停留表单页 | 21.0ms |

全部 6 项为 `PASS`，总耗时 `756.8ms`，退出码 `0`。
测试者明确确认剪贴板图片内容符合预期，据此记录生命周期为 `VERIFIED`。

## 覆盖边界

- 本轮只验证“表单控件”页的表单面板，未验证另外两个 Tab。
- DIB 位图头和尺寸由脚本检查，图片内容由测试者人工确认；没有自动像素内容比对。
- 未主动制造剪贴板占用、截图失败、元素遮挡或失效等异常场景。
- 剪贴板是临时系统状态，后续复制操作会替换本次图片；未另存永久截图文件。
- 验收来源为用户提供的运行日志与人工确认；未修改产品源码。
