# `Win32Window.screenshot()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.screenshot"
lifecycle: "VERIFIED"
verification_date: "2026-09-09"
verification_summary:
  passed: 10
  total: 10
  elapsed_ms: 1612.4
  exit_code: 0
  full_log_provided: true
  tester_visual_confirmation: true
  expected_image_size: [1024, 720]
  keep_images: true
  generated_images: 6
  mouse_restored: true
  foreground_verified: true
persistent_script:
  path: "win32/test_win32_window_screenshot.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "7a49709348b1af0b61e20207560b8d87bd2effe35ec769614b14370022ae81af"
  command: 'uv run .\win32\test_win32_window_screenshot.py --non-interactive --keep-images'
```

## API用途及参数

```python
path = window.screenshot(folder_path=None, filename=None)
```

截取真实顶层窗口并保存为PNG，返回文件路径字符串。
folder_path可按位置或关键字传入；None使用Runtime默认截图目录。
filename仅限关键字；None自动命名，没有.png后缀时当前实现追加.png。
未提供的保存目录会被创建。不支持timeout关键字。

## 运行与验收方法

前置：dev及可见、未最小化的Win32靶场运行；不需要元素库。
在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_window_screenshot.py --non-interactive --keep-images
```

测试期间不要移动或缩放靶场。自动核验返回路径、PNG格式、GDI+解码尺寸与
GetWindowRect一致以及非纯色内容。测试者进一步确认截图画面完整且确实为靶场窗口。
非纯色本身不构成完整视觉校验。

--keep-images保留本次图片供查看；不传则删除本次登记截图及临时目录。
--non-interactive使焦点恢复失败只警告、不等待人工，鼠标恢复等必要清理仍严格检查。

## 最新真实结果

靶场句柄2951616，原生边界 `(1766,244,1024,720)`。
六张图片均为PNG、1024×720、非纯色，文件大小均为20582字节。

| 场景 | 结果 | 耗时 |
| --- | --- | --- |
| API合同 | 可选目录、仅限关键字文件名、str返回 | 0.0ms |
| 测试准备 | 靶场及输出目录准备完成 | 8.1ms |
| 全部默认参数 | 自动命名并保存到默认目录 | 274.3ms |
| 位置目录参数 | 保存到指定目录 | 274.0ms |
| 显式None | 使用默认目录与自动文件名 | 274.0ms |
| 全关键字PNG | 中文带空格文件名正确 | 269.1ms |
| 自动追加扩展名 | no-extension保存为no-extension.png | 259.4ms |
| 创建保存目录 | nested/output目录及nested.png成功创建 | 251.0ms |
| 参数规则 | filename位置传参和timeout均TypeError | 0.0ms |
| 资源清理 | 按参数保留图片，鼠标恢复，靶场保持运行 | 0.9ms |

汇总10/10通过，总耗时1612.4ms，退出码0，测试者明确确认视觉结果。
前台在恢复前已是原终端131974，调用返回True且句柄核验一致；不解释为跨应用抢回焦点成功。

## 保留文件

默认目录：`C:\Users\moby\AppData\Local\UIAutoma\artifacts\images`。

- `window_2951616_1788922241314.png`
- `window_2951616_1788922241860.png`

本次指定输出目录：`C:\Users\moby\AppData\Local\Temp\uiautoma-window-screenshot-rcdokr0_`。

- `window_2951616_1788922241587.png`
- `中文 截图-eafa61e40259429ba784c5f820daf075.png`
- `no-extension.png`
- `nested\output\nested.png`

以上为日志记录的保留位置，不保证系统临时目录清理后仍存在。
此前不带--keep-images的运行也10/10通过，总耗时1583.5ms，截图及临时目录已删除。

## 验证边界

只验证当前靶场窗口，未覆盖最小化、遮挡、无原生句柄、权限隔离、多倍率和GPU窗口场景。
未验证自动文件名冲突、覆盖已有文件或目录不可写。尺寸、句柄和文件大小都是本次观察值，
不固定为后续验收值。保留模式下文件未删除是明确请求的结果，不是清理泄漏。
