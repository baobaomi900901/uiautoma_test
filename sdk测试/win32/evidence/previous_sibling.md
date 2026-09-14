# `uiautoma.win32.Win32Element.previous_sibling()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.previous_sibling"
lifecycle: "VERIFIED"
verification_summary:
  passed: 9
  total: 9
  elapsed_ms: 662.5
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
persistent_script:
  path: "win32/test_win32_previous_sibling.py"
  sha256: "d4401f0a79812f9c394308f3258ea058b54150a6c39b9ed1d80e52a95f79e000"
  command: 'uv run .\win32\test_win32_previous_sibling.py'
form_tab_helper:
  path: "win32/_form_tab.py"
  sha256: "7b27bd9faf78878eff6e049aa414ba8500595cc78d50140f2bbb75d0cd593bd1"
test_environment:
  library_dir: 'D:\code\元素库\260902_win元素'
  panel_element: "win32靶场_表单控件_表单面板"
  activated_tab: "win32靶场_tab_item表单控件"
  reference_children_count: 33
cleanup:
  status: "PASS"
  borrowed_package_closed: true
  application_left_running: true
  final_tab: "表单控件"
```

## API 与运行方式

```python
element.previous_sibling() -> Win32Element
```

- 无公开参数，底层默认预算为 5 秒。
- 返回同一父元素下、UIA 顺序中的前一个兄弟元素，不等同于视觉上的左侧控件。
- 返回 Runtime `Win32Element`，可继续调用 `previous_sibling()`。
- 没有前一个兄弟时抛出 `ElementNotFoundError`。
- 多余位置参数和 `timeout` 关键字均被 `TypeError` 拒绝。

从测试根目录运行，脚本参数为无：

```powershell
uv run .\win32\test_win32_previous_sibling.py
```

脚本借用当前启用元素库，自动切换并确认表单页，以表单面板的 `children()` 当次
结果建立顺序参照。通过返回类型、Runtime ID 前缀、`previous_sibling` 关系、
名称及控件类型校验结果；要求被比较的名称/类型组合在参照中唯一。
本脚本不调用 `child_at()`，也不固定子元素总数和顺序。

## 本次实测

| 测试项 | 验收结果 | 耗时 |
| --- | --- | --- |
| API 合同 | 无公开参数，返回 Win32Element | 0.0ms |
| 表单页与参照准备 | 已激活表单页，读取 33 个直属子元素 | 398.8ms |
| 第二项前驱 | 索引 1 的前驱为索引 0：text“用户信息表单” | 39.3ms |
| 中间项前驱 | 索引 16 的前驱为索引 15：checkbox“广州” | 48.1ms |
| 最后项前驱 | 索引 32 的前驱为索引 31：button“保存” | 49.3ms |
| 链式前驱 | 末项连续调用两次，得到倒数第三项 checkbox“同意用户协议” | 94.4ms |
| 首项无前驱 | 正确抛出 ElementNotFoundError | 31.7ms |
| 参数数量限制 | 位置参数和 timeout 关键字均被 TypeError 拒绝 | 0.0ms |
| 资源清理 | 借用 Package 已关闭；靶场保持运行、停留表单页 | 0.0ms |

全部 9 项为 `PASS`，总耗时 `662.5ms`，退出码 `0`。测试者提供完整日志并明确同意
归档，生命周期记录为 `VERIFIED`。

## 覆盖边界

- 本次验证表单面板中的第二项、中间项、末项、链式前驱和首项无前驱场景，
  未遍历全部元素或另外两个 Tab。
- 33 个元素及其具体排列是本轮观察值，不是长期 API 合同。
- 使用名称/控件类型在当次参照中的唯一组合识别元素；未使用独立原生 UIA
  Runtime ID 测量，也不要求 SDK 临时元素 ID 相等。
- 未制造失效元素、连接故障或读取超时。
- 只清理借用的 Package；不宣称恢复原 Tab、鼠标或前台窗口。
- 未修改产品源码。
