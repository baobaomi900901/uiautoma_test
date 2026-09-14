# `uiautoma.win32.screenshot.save_window_to_file()` 验证证据

```yaml
api: "uiautoma.win32.screenshot.save_window_to_file"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  active_window_png: "PASS"
  none_explicit_png: "PASS"
  empty_string_inferred_bmp: "PASS"
  integer_handle_jpg: "PASS"
  decimal_string_handle_jpeg: "PASS"
  hexadecimal_string_handle_bmp: "PASS"
  explicit_window_region: "PASS"
  returned_path_check: "PASS"
  gdiplus_format_dimension_content_check: "PASS"
  cleanup: "PASS"
  passed: 7
  total: 7
  elapsed_ms: 496.7
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.screenshot.save_window_to_file 的 SDK→Runtime→窗口截图文件路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/screenshot.py"
      symbols: ["save_window_to_file"]
      fingerprint: "5b3b009205ff23ce4bb53641b2bb5d690f578a8c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.screenshot_window_to_file"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/screenshot_service.py"
      symbols: ["ScreenshotService.window_to_file", "_window_rect", "_window_handle", "_capture_window_to_file", "_output_path", "_normalize_format"]
      fingerprint: "0a7931b2bb06cf4e6059bace8cb5499ba78900c8"
    - path: "runtime/services/window_service.py"
      symbols: ["_capture_window_bgra", "_copy_dc_bgra"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
  verified_contract:
    signature: "save_window_to_file(hwnd: int | str | None, image_path: str, image_format: str = '', left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> str"
    required_parameters: ["hwnd", "image_path"]
    parameter_order:
      - "hwnd"
      - "image_path"
      - "image_format"
      - "left"
      - "top"
      - "right"
      - "bottom"
    defaults:
      image_format: ""
      left: 0
      top: 0
      right: 0
      bottom: 0
    accepted_handle_forms: ["int", "decimal str", "hexadecimal str", "0", "None", "empty str"]
    active_window_sentinels: [0, null, ""]
    supported_formats: ["png", "jpg", "jpeg", "bmp"]
    full_window_sentinel: [0, 0, 0, 0]
    region_coordinate_space: "relative to window top-left"
    region_rule: "right > left and bottom > top; result is clamped to window bounds"
    return_annotation: "str"
    returned_value: "实际保存路径"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_save_window_to_file.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "9c2700645de3171d008b9e4cfed33322dcf23c9675fd1f6aab66a41b15d6ef04"
  command: 'uv run .\win32\test_win32_save_window_to_file.py'
test_environment:
  target: "脚本自动打开的记事本"
  title: "uiautoma-save-window-to-file-cr07hvtp.txt - Notepad"
  handle: 11083336
  handle_hex: "0xa91e48"
  window_pid: 333800
  launcher_pid: 244008
  window_size: [900, 700]
  region_edges: [50, 100, 450, 400]
  region_size: [400, 300]
  decoder: "Windows GDI+"
observations:
  active_window_png:
    actual_format: "PNG"
    actual_size: [900, 700]
    non_uniform: true
    size_bytes: 63461
    elapsed_ms: 62.6
  none_explicit_png:
    actual_format: "PNG"
    actual_size: [900, 700]
    non_uniform: true
    size_bytes: 63461
    elapsed_ms: 38.7
  empty_string_inferred_bmp:
    actual_format: "BMP"
    actual_size: [900, 700]
    non_uniform: true
    size_bytes: 1890054
    elapsed_ms: 33.7
  integer_handle_jpg:
    requested_suffix: ".png"
    returned_suffix: ".jpg"
    actual_format: "JPEG"
    actual_size: [900, 700]
    non_uniform: true
    size_bytes: 192220
    elapsed_ms: 36.0
  decimal_string_handle_jpeg:
    requested_suffix: ".jpeg"
    returned_suffix: ".jpg"
    actual_format: "JPEG"
    actual_size: [900, 700]
    non_uniform: true
    size_bytes: 192220
    elapsed_ms: 43.5
  hexadecimal_string_handle_bmp:
    requested_suffix: ".png"
    returned_suffix: ".bmp"
    actual_format: "BMP"
    actual_size: [900, 700]
    non_uniform: true
    size_bytes: 1890054
    elapsed_ms: 37.4
  explicit_window_region:
    actual_format: "PNG"
    actual_size: [400, 300]
    non_uniform: true
    size_bytes: 6822
    elapsed_ms: 36.1
cleanup:
  status: "PASS"
  screenshots: "已删除"
  notepad: "已关闭"
  temporary_file: "已删除"
known_limitations:
  - "本次使用普通记事本窗口，不重新判定 GPU/WebView 窗口客户区内容保真；历史跟踪 Issue #32 仍属独立场景"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_save_window_to_file.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_save_window_to_file.py
```

脚本自动打开并调整一个记事本窗口。测试过程只调用
`win32.screenshot.save_window_to_file()`；窗口定位、激活和清理使用原生 Win32 API。
保存后使用 Windows 自带 GDI+ 解码 PNG、JPEG 和 BMP，独立验证返回路径、实际格式、
像素尺寸和非纯色内容，无需安装 Pillow。

## API 参数

```python
win32.screenshot.save_window_to_file(
    hwnd: int | str | None,
    image_path: str,
    image_format: str = "",
    left: int = 0,
    top: int = 0,
    right: int = 0,
    bottom: int = 0,
) -> str
```

- `hwnd` 和 `image_path` 是必填参数。
- `hwnd` 支持整数句柄、十进制字符串和十六进制字符串。
- `hwnd=0`、`None` 或空字符串时使用当前活动窗口。
- `image_format` 支持 `png`、`jpg`、`jpeg` 和 `bmp`；为空时从文件扩展名推断，
  无法推断时使用 PNG。
- JPG/JPEG 的实际输出扩展名统一为 `.jpg`；显式 BMP 会将扩展名修正为 `.bmp`。
- `left`、`top`、`right`、`bottom` 是相对窗口左上角的像素边界。
- 四个边界全为 `0` 时截取整个窗口；指定区域会限制在窗口范围内。
- 成功返回实际保存路径 `str`。

## 最小实现链

```text
uiautoma.win32.screenshot.save_window_to_file(...)
  -> UIAutomaCoreClient.screenshot_window_to_file(...)
  -> Runtime ScreenshotService.window_to_file(...)
  -> _window_handle(...) / _window_rect(...)
  -> _capture_window_bgra(...) / _capture_window_rect_dib(...)
  -> _output_path(...) / _normalize_format(...)
  -> Pillow 编码 PNG / JPEG / BMP
  -> 返回实际保存路径
```

## 覆盖矩阵

| 场景 | 关键参数 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| 活动窗口 PNG | `hwnd=0`，省略格式 | PNG，`900 × 700` | PNG，63461 bytes，非纯色 | `PASS` |
| `None` 显式 PNG | `hwnd=None`，`png` | PNG，`900 × 700` | PNG，63461 bytes，非纯色 | `PASS` |
| 空字符串推断 BMP | `hwnd=""`，`.bmp` 路径 | BMP，`900 × 700` | BMP，1890054 bytes，非纯色 | `PASS` |
| 整数句柄 JPG | `11083336`，`.png` 路径 + `jpg` | JPEG，路径修正为 `.jpg` | JPEG，192220 bytes，非纯色 | `PASS` |
| 十进制字符串 JPEG | `"11083336"`，`jpeg` | JPEG，路径归一为 `.jpg` | JPEG，192220 bytes，非纯色 | `PASS` |
| 十六进制字符串 BMP | `"0xa91e48"`，`.png` 路径 + `bmp` | BMP，路径修正为 `.bmp` | BMP，1890054 bytes，非纯色 | `PASS` |
| 显式窗口区域 | `(50, 100, 450, 400)` | PNG，`400 × 300` | PNG，6822 bytes，非纯色 | `PASS` |
| 资源清理 | — | 删除截图和临时文件，关闭记事本 | 均已完成 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_save_window_to_file.py`
- 测试对象：脚本自动打开的记事本，窗口尺寸 `900 × 700`
- 句柄形式：`0`、`None`、空字符串、整数、十进制字符串、十六进制字符串均通过
- 图片格式：PNG、JPEG、BMP 均经 GDI+ 解码验证尺寸和非纯色内容
- 显式区域：`(50, 100, 450, 400)`，实际输出 `400 × 300` PNG
- 路径修正：JPG/JPEG 统一为 `.jpg`，显式 BMP 修正为 `.bmp`
- 总状态：`PASS`
- 通过数：`7/7`
- 总耗时：`496.7ms`
- 临时截图：已删除
- 记事本：已关闭
- 临时文件：已删除
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 非法句柄、非法路径、非法格式和非法区域矩阵。
- 最小化或隐藏窗口截图。
- GPU/WebView 窗口客户区内容保真；历史 Issue #32 属独立场景。
- 剪贴板、屏幕和手动框选截图 API。
