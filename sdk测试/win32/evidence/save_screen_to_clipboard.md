# `uiautoma.win32.screenshot.save_screen_to_clipboard()` 验证证据

```yaml
api: "uiautoma.win32.screenshot.save_screen_to_clipboard"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  full_virtual_screen: "PASS"
  explicit_region: "PASS"
  dib_header_dimension_check: "PASS"
  clipboard_manual_paste: "PASS"
  clipboard_output_retained: "PASS"
  passed: 2
  total: 2
  elapsed_ms: 234.3
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.screenshot.save_screen_to_clipboard 的 SDK→Runtime→CF_DIB 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/screenshot.py"
      symbols: ["save_screen_to_clipboard"]
      fingerprint: "5b3b009205ff23ce4bb53641b2bb5d690f578a8c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.screenshot_screen_to_clipboard"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/screenshot_service.py"
      symbols: ["ScreenshotService.screen_to_clipboard", "_screen_rect", "_rect_to_clipboard", "_copy_rect"]
      fingerprint: "0a7931b2bb06cf4e6059bace8cb5499ba78900c8"
    - path: "runtime/desktop/screen_capture.py"
      symbols: ["virtual_screen_bounds", "copy_screen_rect_to_clipboard"]
      fingerprint: "63bd6eb32bce956a65c3fd51a5d46bdc490a3868"
  verified_contract:
    signature: "save_screen_to_clipboard(left=0, top=0, right=0, bottom=0) -> None"
    parameter_order:
      - "left"
      - "top"
      - "right"
      - "bottom"
    defaults:
      left: 0
      top: 0
      right: 0
      bottom: 0
    full_screen_sentinel: [0, 0, 0, 0]
    region_rule: "right > left and bottom > top"
    clipboard_format: "CF_DIB"
    return_annotation: "None"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_save_screen_to_clipboard.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "2803005c26e4cfbbfc932b135917633512c55639"
  command: 'uv run .\win32\test_win32_save_screen_to_clipboard.py'
test_environment:
  virtual_screen_bounds: [0, 0, 6000, 1600]
  clipboard_format: "CF_DIB"
  bit_count: 32
observations:
  full_screen:
    expected_size: [6000, 1600]
    actual_size: [6000, 1600]
    elapsed_ms: 170.5
  region:
    edges: [100, 100, 500, 400]
    expected_size: [400, 300]
    actual_size: [400, 300]
    elapsed_ms: 63.1
  manual_paste: "PASS"
cleanup:
  status: "PASS"
  detail: "No files, processes, windows, or Package sessions created; final region screenshot intentionally retained as API output"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_save_screen_to_clipboard.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_save_screen_to_clipboard.py
```

脚本只调用 `win32.screenshot.save_screen_to_clipboard()`。截图完成后使用原生 Win32
剪贴板 API 锁定 `CF_DIB` 数据并读取 `BITMAPINFOHEADER`，以独立验证位深和截图宽高；
不调用 `ping()`、`win32.clipboard` 或其他 UIAutoma SDK API。

## API 参数

```python
win32.screenshot.save_screen_to_clipboard(
    left: int = 0,
    top: int = 0,
    right: int = 0,
    bottom: int = 0,
) -> None
```

- 四个边界全部为 `0` 时截取完整虚拟桌面，包括多显示器。
- 指定区域时，四个参数表示屏幕物理像素边界。
- 区域必须满足 `right > left` 且 `bottom > top`。
- 成功返回 `None`，并将 32-bit `CF_DIB` 位图写入剪贴板。

## 最小实现链

```text
uiautoma.win32.screenshot.save_screen_to_clipboard(...)
  -> UIAutomaCoreClient.screenshot_screen_to_clipboard(...)
  -> Runtime ScreenshotService.screen_to_clipboard(...)
  -> _screen_rect(...)
       全 0: virtual_screen_bounds()
       区域: (left, top, right-left, bottom-top)
  -> screen_capture.copy_screen_rect_to_clipboard(...)
  -> EmptyClipboard + SetClipboardData(CF_DIB)
```

## 覆盖矩阵

| 场景 | 调用 | 预期尺寸 | DIB 实际尺寸 | 结果 |
| --- | --- | --- | --- | --- |
| 完整虚拟桌面 | `save_screen_to_clipboard()` | `6000 × 1600` | `6000 × 1600`，32 bit | `PASS` |
| 指定屏幕区域 | `save_screen_to_clipboard(100, 100, 500, 400)` | `400 × 300` | `400 × 300`，32 bit | `PASS` |
| 人工粘贴 | — | 区域截图可正常显示 | 已确认 | `PASS` |
| 资源清理 | — | 无需清理额外资源 | 最终区域截图作为 API 输出保留 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_save_screen_to_clipboard.py`
- 虚拟桌面：`(0, 0)`，`6000 × 1600`
- 完整桌面截图：`6000 × 1600`，32-bit `CF_DIB`，`170.5ms`
- 区域截图：`(100, 100, 500, 400)`，`400 × 300`，32-bit `CF_DIB`，`63.1ms`
- 人工粘贴：截图正常显示
- 总状态：`PASS`
- 通过数：`2/2`
- 总耗时：`234.3ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 剪贴板：保留最后一次 `400 × 300` 区域截图
- 产品源码修改：无

## 明确排除

- 非法参数与异常类型矩阵。
- 多显示器负坐标原点场景。
- `save_screen_to_file`、窗口截图和手动框选截图 API。
