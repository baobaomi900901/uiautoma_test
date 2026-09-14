# `uiautoma.win32.Win32Element.get_bounding()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_bounding"
lifecycle: "VERIFIED"
verification_summary:
  tester_confirmed: true
  runs:
    - {dpi: 96, scale_percent: 100, passed: 14, total: 14, elapsed_ms: 811.4, exit_code: 0}
    - {dpi: 144, scale_percent: 150, passed: 14, total: 14, elapsed_ms: 830.2, exit_code: 0}
    - {dpi: 192, scale_percent: 200, passed: 14, total: 14, elapsed_ms: 826.5, exit_code: 0}
    - {dpi: 216, scale_percent: 225, passed: 14, total: 14, elapsed_ms: 847.5, exit_code: 0}
persistent_script:
  path: "win32/test_win32_get_bounding.py"
  fingerprint_kind: "SHA-256"
  fingerprint: "c68f962e4a33cecbe3ef385d9eca69b686ffc0b7605bac3464836681d1e6268d"
  command: 'uv run .\win32\test_win32_get_bounding.py'
test_environment:
  package_dir: 'D:\code\元素库\260902_win元素'
  tab: "win32靶场_tab_item表单控件"
  target_element: "win32靶场_表单控件_表单面板"
  target_application: "Win32 靶场 - UIA"
cleanup:
  all_runs_passed: true
  mouse_restored: true
  foreground_restored: true
  thread_dpi_context_restored: true
  borrowed_package_closed: true
  application_left_running: true
  final_tab: "表单控件"
```

## API 与运行方式

```python
element.get_bounding(
    to96dpi: bool = True,
    relative_to: str = "screen",
) -> tuple[int, int, int, int]
```

- 返回 `(x, y, width, height)` 整数四元组；宽高应为正数。
- 两个参数都支持位置或关键字传入。
- `to96dpi=False` 返回物理像素，`True` 按屏幕 DC DPI / 96 换算并取整。
- `relative_to` 支持 `screen`（屏幕）、`window`（所属顶层窗口）、
  `client`（所属窗口客户区）。后两者先减去相应原点，再按需转换 DPI。
- 坐标系名称忽略大小写与首尾空格。纯空白、非法名称和本轮测试的整数值被
  `InvalidParamsError` 拒绝。
- 公开 API 没有 `timeout` 参数，底层读取预算为 3 秒。

从测试根目录运行，脚本参数为无：

```powershell
uv run .\win32\test_win32_get_bounding.py
```

脚本自动激活靶场并切换至表单页，读取面板物理矩形作为转换参照；原生
`GetWindowRect`、`ClientToScreen` 提供窗口及客户区原点，`GetDeviceCaps` 提供
屏幕 DC DPI。测试期间设置线程 DPI 感知以读取物理坐标，结束后恢复原上下文。

## 四轮真实验证

缩放比例按日志中的 DPI / 96 计算。附件中的重复粘贴片段不计为额外测试轮次。

| DPI | 对应缩放 | 通过数 | 总耗时 | 退出码 |
| --- | --- | --- | --- | --- |
| 96 | 100% | 14/14 | 811.4ms | 0 |
| 144 | 150% | 14/14 | 830.2ms | 0 |
| 192 | 200% | 14/14 | 826.5ms | 0 |
| 216 | 225% | 14/14 | 847.5ms | 0 |

| DPI | 物理屏幕矩形 | 96 DPI 屏幕矩形 | 96 DPI 窗口相对矩形 | 96 DPI 客户区相对矩形 |
| --- | --- | --- | --- | --- |
| 96 | (2363, 144, 984, 631) | (2363, 144, 984, 631) | (20, 69, 984, 631) | (12, 38, 984, 631) |
| 144 | (1944, 180, 1476, 947) | (1296, 120, 984, 631) | (20, 69, 984, 631) | (12, 38, 984, 631) |
| 192 | (1446, 138, 1968, 1182) | (723, 69, 984, 591) | (20, 69, 984, 591) | (12, 38, 984, 591) |
| 216 | (1197, 155, 2214, 1330) | (532, 69, 984, 591) | (20, 69, 984, 591) | (12, 38, 984, 591) |

以上所有预期矩形与实际返回一致。例如 DPI=144 时宽度 `1476 / 1.5 = 984`，
DPI=216 时宽度 `2214 / 2.25 = 984`；高度和相对坐标也按当前取整规则一致。
不同轮次的窗口布局可能不同，验收使用每轮实时物理矩形，不要求跨轮次高度固定。

## 每轮覆盖的 14 项

| 测试项 | 验收条件 | 四轮结果 |
| --- | --- | --- |
| API 合同 | 默认值、参数类型及调用方式、返回标注正确 | PASS |
| 元素与坐标准备 | 当前元素库正确，面板可定位，记录原生原点及 DPI | PASS |
| 全部默认参数 | 等于 96 DPI 屏幕坐标预期 | PASS |
| 物理像素 screen | 等于物理屏幕矩形参照 | PASS |
| 物理像素 window | 屏幕位置减去原生窗口原点 | PASS |
| 物理像素 client | 屏幕位置减去原生客户区原点 | PASS |
| 96 DPI screen | 物理屏幕矩形按 DPI 换算并取整 | PASS |
| 96 DPI window | 窗口相对物理矩形按 DPI 换算并取整 | PASS |
| 96 DPI client | 客户区相对物理矩形按 DPI 换算并取整 | PASS |
| 完整位置参数 | `get_bounding(False, "client")` 正确 | PASS |
| 大小写与空格 | `get_bounding(False, " WiNdOw ")` 正确 | PASS |
| 非法坐标系 | desktop、position、纯空白、123 均抛出 InvalidParamsError | PASS |
| 参数数量限制 | 多余位置参数和 timeout 关键字均抛出 TypeError | PASS |
| 资源恢复 | 鼠标、焦点及线程 DPI 上下文恢复，Package 关闭 | PASS |

## 证据来源与覆盖边界

- 来源为测试者提供的真实运行日志及明确同意归档；附件位置：
  `C:\Users\moby\.codex\attachments\431e0207-715a-4203-95a4-612e39c2777b\pasted-text.txt`。
- 已覆盖读取到的 96、144、192、216 DPI 下的转换行为。
- 未覆盖不同缩放显示器之间移动窗口的混合 DPI 场景；当前实现使用屏幕 DC DPI，
  并非按元素所在显示器独立获取 DPI。
- 物理屏幕矩形由被测 API 提供，作为转换参照；本轮不构成对 UIA 元素边界的独立测量。
- 未覆盖不可见、失效元素、窗口原点不可用等失败路径；未测试 to96dpi 的非布尔值。
- 四轮结束时靶场均保持运行并停留在表单页；未修改产品源码。
