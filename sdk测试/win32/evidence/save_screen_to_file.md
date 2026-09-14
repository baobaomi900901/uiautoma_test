# `uiautoma.win32.screenshot.save_screen_to_file()` 验证证据

```yaml
api: "uiautoma.win32.screenshot.save_screen_to_file"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  default_full_screen_png: "PASS"
  explicit_region_png: "PASS"
  explicit_jpg_and_suffix_normalization: "PASS"
  jpeg_alias_and_suffix_normalization: "PASS"
  bmp_extension_inference: "PASS"
  image_header_dimension_check: "PASS"
  cleanup: "PASS"
  passed: 5
  total: 5
  elapsed_ms: 579.8
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.screenshot.save_screen_to_file 的 SDK→Runtime→屏幕截图文件路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/screenshot.py"
      symbols: ["save_screen_to_file"]
      fingerprint: "5b3b009205ff23ce4bb53641b2bb5d690f578a8c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.screenshot_screen_to_file"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/screenshot_service.py"
      symbols: ["ScreenshotService.screen_to_file", "_screen_rect", "_capture_rect_to_file", "_output_path", "_normalize_format"]
      fingerprint: "0a7931b2bb06cf4e6059bace8cb5499ba78900c8"
    - path: "runtime/desktop/screen_capture.py"
      symbols: ["virtual_screen_bounds", "_capture_screen_rect_dib"]
      fingerprint: "63bd6eb32bce956a65c3fd51a5d46bdc490a3868"
  verified_contract:
    signature: "save_screen_to_file(image_path: str, image_format: str = '', left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> str"
    parameter_order:
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
    supported_formats: ["png", "jpg", "jpeg", "bmp"]
    full_screen_sentinel: [0, 0, 0, 0]
    region_rule: "right > left and bottom > top"
    return_annotation: "str"
    returned_value: "实际保存路径"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_save_screen_to_file.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "5e6e70651a8de594dfa32dbdd452efc76c38b12d0543623b2acd893a88a8b8a0"
  command: 'uv run .\win32\test_win32_save_screen_to_file.py'
test_environment:
  virtual_screen_bounds: [0, 0, 6000, 1600]
  region_edges: [100, 100, 500, 400]
  region_size: [400, 300]
observations:
  default_full_screen_png:
    expected_format: "PNG"
    actual_format: "PNG"
    expected_size: [6000, 1600]
    actual_size: [6000, 1600]
    size_bytes: 515303
    elapsed_ms: 535.1
  explicit_region_png:
    expected_format: "PNG"
    actual_format: "PNG"
    expected_size: [400, 300]
    actual_size: [400, 300]
    size_bytes: 11991
    elapsed_ms: 8.0
  explicit_jpg:
    requested_suffix: ".png"
    returned_suffix: ".jpg"
    expected_format: "JPEG"
    actual_format: "JPEG"
    expected_size: [400, 300]
    actual_size: [400, 300]
    size_bytes: 19714
    elapsed_ms: 11.4
  jpeg_alias:
    requested_suffix: ".jpeg"
    returned_suffix: ".jpg"
    expected_format: "JPEG"
    actual_format: "JPEG"
    expected_size: [400, 300]
    actual_size: [400, 300]
    size_bytes: 19714
    elapsed_ms: 12.0
  inferred_bmp:
    image_format_argument: "omitted"
    inferred_from_suffix: ".bmp"
    expected_format: "BMP"
    actual_format: "BMP"
    expected_size: [400, 300]
    actual_size: [400, 300]
    size_bytes: 360054
    elapsed_ms: 8.6
cleanup:
  status: "PASS"
  detail: "独立临时目录及 5 张测试截图均已删除"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_save_screen_to_file.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_save_screen_to_file.py
```

脚本只调用 `win32.screenshot.save_screen_to_file()`。每张截图保存后，脚本使用 Python
标准库读取 PNG、JPEG 或 BMP 文件头，独立校验实际文件格式和像素尺寸；不调用
`ping()` 或其他 UIAutoma SDK API。所有输出位于独立临时目录，测试结束后统一删除。

## API 参数

```python
win32.screenshot.save_screen_to_file(
    image_path: str,
    image_format: str = "",
    left: int = 0,
    top: int = 0,
    right: int = 0,
    bottom: int = 0,
) -> str
```

- `image_path` 是必填的目标文件路径。
- `image_format` 支持 `png`、`jpg`、`jpeg` 和 `bmp`；为空时从文件扩展名推断，
  无法推断时使用 PNG。
- `image_format="jpg"` 或 `"jpeg"` 时，实际输出扩展名归一为 `.jpg`。
- 四个边界全为 `0` 时截取完整虚拟桌面。
- 指定区域时，区域尺寸为 `right - left × bottom - top`，且必须满足
  `right > left` 和 `bottom > top`。
- 成功返回实际保存路径 `str`；路径扩展名可能根据格式被修正。

## 最小实现链

```text
uiautoma.win32.screenshot.save_screen_to_file(...)
  -> UIAutomaCoreClient.screenshot_screen_to_file(...)
  -> Runtime ScreenshotService.screen_to_file(...)
  -> _screen_rect(...)
       全 0: virtual_screen_bounds()
       区域: (left, top, right-left, bottom-top)
  -> _output_path(...) / _normalize_format(...)
  -> _capture_screen_rect_dib(...)
  -> Pillow 编码 PNG / JPEG / BMP
  -> 返回实际保存路径
```

## 覆盖矩阵

| 场景 | 关键调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| 默认完整桌面 PNG | `save_screen_to_file(path)` | PNG，`6000 × 1600` | PNG，`6000 × 1600`，515303 bytes | `PASS` |
| 显式区域 PNG | `save_screen_to_file(path, "png", 100, 100, 500, 400)` | PNG，`400 × 300` | PNG，`400 × 300`，11991 bytes | `PASS` |
| 显式 JPG | `.png` 路径 + `image_format="jpg"` | JPEG，路径归一为 `.jpg` | JPEG，`400 × 300`，`.jpg` | `PASS` |
| JPEG 别名 | `.jpeg` 路径 + `image_format="jpeg"` | JPEG，路径归一为 `.jpg` | JPEG，`400 × 300`，`.jpg` | `PASS` |
| 扩展名推断 BMP | `.bmp` 路径，省略 `image_format` | BMP，`400 × 300` | BMP，`400 × 300`，360054 bytes | `PASS` |
| 资源清理 | — | 删除临时截图 | 独立临时目录已删除 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_save_screen_to_file.py`
- 虚拟桌面：`(0, 0)`，`6000 × 1600`
- 测试区域：`(100, 100, 500, 400)`，`400 × 300`
- 默认完整桌面 PNG：`6000 × 1600`，515303 bytes，`535.1ms`
- 显式区域 PNG：`400 × 300`，11991 bytes，`8.0ms`
- 显式 JPG：扩展名从 `.png` 修正为 `.jpg`，19714 bytes，`11.4ms`
- JPEG 别名：扩展名从 `.jpeg` 归一为 `.jpg`，19714 bytes，`12.0ms`
- 扩展名推断 BMP：`400 × 300`，360054 bytes，`8.6ms`
- 总状态：`PASS`
- 通过数：`5/5`
- 总耗时：`579.8ms`
- 临时截图：已删除
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 非法参数与异常类型矩阵。
- 多显示器负坐标原点场景。
- 截图内容的图像语义比对。
- 剪贴板、窗口截图和手动框选截图 API。
