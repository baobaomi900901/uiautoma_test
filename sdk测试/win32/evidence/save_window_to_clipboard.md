# `uiautoma.win32.screenshot.save_window_to_clipboard()` 验证证据

```yaml
api: "uiautoma.win32.screenshot.save_window_to_clipboard"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  default_active_window: "PASS"
  none_active_window: "PASS"
  empty_string_active_window: "PASS"
  integer_handle: "PASS"
  decimal_string_handle: "PASS"
  hexadecimal_string_handle: "PASS"
  explicit_window_region: "PASS"
  clipboard_cleared_before_each_case: "PASS"
  dib_header_dimension_check: "PASS"
  dib_non_uniform_content_check: "PASS"
  clipboard_manual_paste: "PASS"
  cleanup: "PASS"
  passed: 7
  total: 7
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.screenshot.save_window_to_clipboard 的 SDK→Runtime→CF_DIB 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/screenshot.py"
      symbols: ["save_window_to_clipboard"]
      fingerprint: "5b3b009205ff23ce4bb53641b2bb5d690f578a8c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.screenshot_window_to_clipboard"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/screenshot_service.py"
      symbols: ["ScreenshotService.window_to_clipboard", "_window_rect", "_window_handle", "_copy_window_to_clipboard", "_capture_window_rect_dib"]
      fingerprint: "0a7931b2bb06cf4e6059bace8cb5499ba78900c8"
    - path: "runtime/services/window_service.py"
      symbols: ["_capture_window_bgra", "_copy_dc_bgra"]
      fingerprint: "1ecd610418bde1a3b03524650d3bc308a5c7e217"
    - path: "runtime/desktop/screen_capture.py"
      symbols: ["copy_dib_to_clipboard", "copy_screen_rect_to_clipboard"]
      fingerprint: "63bd6eb32bce956a65c3fd51a5d46bdc490a3868"
  verified_contract:
    signature: "save_window_to_clipboard(hwnd: int | str | None = 0, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> None"
    parameter_order:
      - "hwnd"
      - "left"
      - "top"
      - "right"
      - "bottom"
    defaults:
      hwnd: 0
      left: 0
      top: 0
      right: 0
      bottom: 0
    accepted_handle_forms: ["int", "decimal str", "hexadecimal str", "0", "None", "empty str"]
    active_window_sentinels: [0, null, ""]
    full_window_sentinel: [0, 0, 0, 0]
    region_coordinate_space: "relative to window top-left"
    region_rule: "right > left and bottom > top; result is clamped to window bounds"
    clipboard_format: "CF_DIB"
    return_annotation: "None"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_save_window_to_clipboard.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "8a588532c6b6e7db6645917490a3e7065ea1c5938adb4d49f69eb81590ca5cf2"
  command: 'uv run .\win32\test_win32_save_window_to_clipboard.py'
test_environment:
  target: "脚本自动打开的记事本"
  title: "uiautoma-save-window-to-clipboard-f1rirwtl.txt - Notepad"
  handle: 270476
  handle_hex: "0x4208c"
  window_pid: 307532
  launcher_pid: 29352
  window_size: [900, 700]
  region_edges: [50, 100, 450, 400]
  region_size: [400, 300]
observations:
  full_window_cases:
    cases: 6
    expected_size: [900, 700]
    actual_size: [900, 700]
    clipboard_format: "CF_DIB"
    bit_count: 32
    non_uniform: true
    size_bytes: 2520040
  explicit_region:
    expected_size: [400, 300]
    actual_size: [400, 300]
    clipboard_format: "CF_DIB"
    bit_count: 32
    non_uniform: true
    size_bytes: 480040
  manual_paste: "PASS"
cleanup:
  status: "PASS"
  clipboard: "保留最后一次 400 x 300 区域截图"
  notepad: "已关闭"
  temporary_file: "已删除"
known_limitations:
  - "本次使用普通记事本窗口，不重新判定 GPU/WebView 窗口客户区内容保真；历史跟踪 Issue #32 仍属独立场景"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_save_window_to_clipboard.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_save_window_to_clipboard.py
```

脚本自动打开并调整一个记事本窗口。测试过程只调用
`win32.screenshot.save_window_to_clipboard()`；窗口定位、激活、剪贴板清空以及
`CF_DIB` 读取均使用原生 Win32 API，不调用 `ping()`、`win32.get()`、
`win32.clipboard` 或其他 UIAutoma SDK API。

每次目标 API 调用前均清空剪贴板，避免上一张图片残留造成假阳性。调用后读取
`BITMAPINFOHEADER` 和像素数据，验证尺寸、32-bit 位深、无压缩格式及非纯色内容。

## API 参数

```python
win32.screenshot.save_window_to_clipboard(
    hwnd: int | str | None = 0,
    left: int = 0,
    top: int = 0,
    right: int = 0,
    bottom: int = 0,
) -> None
```

- `hwnd` 支持整数句柄、十进制字符串和十六进制字符串。
- `hwnd=0`、`None` 或空字符串时使用当前活动窗口。
- `left`、`top`、`right`、`bottom` 是相对窗口左上角的像素边界。
- 四个边界全为 `0` 时截取整个窗口。
- 指定区域必须满足 `right > left` 和 `bottom > top`，结果限制在窗口边界内。
- 成功返回 `None`，并将 32-bit `CF_DIB` 位图写入剪贴板。

## 最小实现链

```text
uiautoma.win32.screenshot.save_window_to_clipboard(...)
  -> UIAutomaCoreClient.screenshot_window_to_clipboard(...)
  -> Runtime ScreenshotService.window_to_clipboard(...)
  -> _window_handle(...)
       0 / None / "": 当前活动窗口
       其他值: int(str(value), 0)
  -> _window_rect(...)
       全 0: 整个窗口
       区域: 相对窗口边界并限制在窗口范围内
  -> _capture_window_bgra(...) / _capture_window_rect_dib(...)
  -> copy_dib_to_clipboard(CF_DIB)
```

## 覆盖矩阵

| 场景 | `hwnd` 形式 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| 默认活动窗口 | 省略，默认 `0` | `900 × 700`，32-bit，非纯色 | `900 × 700`，2520040 bytes | `PASS` |
| `None` 活动窗口 | `None` | `900 × 700`，32-bit，非纯色 | `900 × 700`，2520040 bytes | `PASS` |
| 空字符串活动窗口 | `""` | `900 × 700`，32-bit，非纯色 | `900 × 700`，2520040 bytes | `PASS` |
| 整数句柄 | `270476` | `900 × 700`，32-bit，非纯色 | `900 × 700`，2520040 bytes | `PASS` |
| 十进制字符串 | `"270476"` | `900 × 700`，32-bit，非纯色 | `900 × 700`，2520040 bytes | `PASS` |
| 十六进制字符串 | `"0x4208c"` | `900 × 700`，32-bit，非纯色 | `900 × 700`，2520040 bytes | `PASS` |
| 显式窗口区域 | `(270476, 50, 100, 450, 400)` | `400 × 300`，32-bit，非纯色 | `400 × 300`，480040 bytes | `PASS` |
| 人工粘贴 | — | 区域截图内容正常 | 已确认 | `PASS` |
| 资源清理 | — | 关闭记事本并删除临时文件 | 均已完成 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_save_window_to_clipboard.py`
- 测试对象：脚本自动打开的记事本，窗口尺寸 `900 × 700`
- 默认、`None`、空字符串、整数、十进制字符串和十六进制字符串共 6 个整窗调用：
  均得到 `900 × 700`、32-bit、非纯色的 `CF_DIB`
- 显式区域：`(50, 100, 450, 400)`，得到 `400 × 300`、32-bit、非纯色的
  `CF_DIB`
- 人工粘贴：区域截图内容正常
- 总状态：`PASS`
- 通过数：`7/7`
- 记事本：已关闭
- 临时文件：已删除
- 剪贴板：保留最后一次 `400 × 300` 区域截图
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 非法句柄、非法区域与异常类型矩阵。
- 最小化或隐藏窗口截图。
- GPU/WebView 窗口客户区内容保真；历史 Issue #32 属独立场景。
- 文件、屏幕和手动框选截图 API。
