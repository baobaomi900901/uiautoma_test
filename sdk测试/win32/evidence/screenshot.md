# `uiautoma.win32.Win32Element.screenshot()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.screenshot"
lifecycle: "VERIFIED"
verification_summary:
  passed: 10
  total: 10
  elapsed_ms: 1669.4
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  manual_image_confirmed: true
persistent_script:
  path: "win32/test_win32_screenshot.py"
  fingerprint_kind: "SHA-256"
  fingerprint: "30f1fe3992cc809f286edbf360ce12e73f9a27d0a37275d669a453a8b53f374d"
  command: 'uv run .\win32\test_win32_screenshot.py'
test_environment:
  package_dir: 'D:\code\元素库\260902_win元素'
  tab: "win32靶场_tab_item表单控件"
  target_element: "win32靶场_表单控件_表单面板"
  target_application: "Win32 靶场 - UIA"
  physical_width: 984
  physical_height: 631
  output_directory: 'D:\code\元素库\sdk测试\win32\artifacts\screenshot\run-kmte9ati'
  manually_confirmed_image: 'suffix\panel.png'
cleanup:
  status: "PASS"
  mouse_restored: true
  foreground_restored: true
  borrowed_package_closed: true
  application_left_running: true
  final_tab: "表单控件"
  screenshots_retained: true
```

## API 与运行方式

```python
element.screenshot(folder_path: str, *, filename: str | None = None) -> str
```

- `folder_path` 必填，可按位置或关键字传入；不存在的目录自动创建。
- `filename` 仅限关键字；省略、`None` 和空字符串均自动生成文件名。
- 没有 `.png` 后缀时追加 `.png`：`panel` 变为 `panel.png`，
  `panel.jpg` 变为 `panel.jpg.png`。
- 返回 PNG 文件路径字符串。公开 API 不提供 `timeout`，底层默认预算为 5 秒。
- 截图按元素的屏幕矩形执行；目标应位于当前显示页面并保持无遮挡。

从测试根目录运行，脚本参数为无：

```powershell
uv run .\win32\test_win32_screenshot.py
```

脚本借用当前启用元素库，激活靶场并点击“表单控件”Tab，然后获取表单面板。
每个截图用例分别校验输出目录、返回路径、PNG 签名、块结构与 CRC、图片尺寸、
截图前后元素物理矩形一致，以及 `last_result.ok`。图片内容由测试者人工验收。

## 本次实测

| 测试项 | 验收结果 | 耗时 |
| --- | --- | --- |
| API 合同 | 必填目录、仅限关键字 filename、默认 None 和返回 str 均符合 | 0.0ms |
| 元素与页面准备 | 已切换表单页，面板物理尺寸为 984 × 631 | 702.4ms |
| 省略文件名 | 自动命名，目录已创建，PNG 984 × 631 | 162.4ms |
| None 文件名 | 自动命名，目录已创建，PNG 984 × 631 | 158.0ms |
| 空文件名 | 自动命名，目录已创建，PNG 984 × 631 | 153.6ms |
| 目录关键字调用 | 保存为 `表单面板.png`，PNG 984 × 631 | 160.4ms |
| 自动补齐后缀 | `panel` 保存为 `panel.png`，PNG 984 × 631 | 154.2ms |
| 其他扩展名 | `panel.jpg` 保存为 `panel.jpg.png`，PNG 984 × 631 | 156.2ms |
| 参数数量限制 | 缺少目录、多余位置参数、timeout 关键字均抛出 TypeError | 0.0ms |
| 资源恢复 | 鼠标与前台窗口恢复，Package 关闭，靶场停留表单页 | 21.2ms |

全部 10 项为 `PASS`，总耗时 `1669.4ms`，退出码 `0`。
测试者针对 `run-kmte9ati/suffix/panel.png` 明确确认截图内容为完整、无遮挡的表单面板。
据此标记为 `VERIFIED`；未宣称其他图片均经逐张人工确认。

## 证据与覆盖边界

- 人工确认图片：[panel.png](../artifacts/screenshot/run-kmte9ati/suffix/panel.png)。
- 截图保留供复查；不视为待清理临时文件。若手动删除产物，图片链接将失效。
- 本轮只截图“表单控件”页的面板；未验证“表格数据”和“拖拽测试”页。
- 未测试遮挡、最小化、屏幕外元素或文件系统写入失败。
- PNG 结构与尺寸检查不等同于完整图像解码或像素内容自动比对。
- 验收来源为测试者运行日志与人工确认；未修改产品源码。
