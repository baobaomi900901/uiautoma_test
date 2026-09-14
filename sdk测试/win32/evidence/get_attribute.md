# `Win32Element.get_attribute()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_attribute"
lifecycle: "VERIFIED"
verification_date: "2026-09-09"
verification_summary:
  passed: 17
  total: 17
  elapsed_ms: 1375.8
  exit_code: 0
  tester_confirmed: true
  necessary_cleanup: "PASS"
  foreground_restore: "本次粘贴未包含单独的焦点诊断，不能据清理PASS断言已恢复"
persistent_script:
  path: "win32/test_win32_get_attribute.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "cddea730c9591e2f0b9ec99ed2334291a0796b0c0963bd8ad74b7503448ebf92"
  command: 'uv run .\win32\test_win32_get_attribute.py --non-interactive'
```

## 用途与合同

```python
name = element.get_attribute("Name")
class_name = element.get_attribute(name="ClassName")
```

读取单个Win32元素属性。name必填，可按位置或关键字传入，去除首尾空格后匹配属性名；
本轮验证了ClassName的大小写归一化。已有属性返回str，不存在或不可提供时返回None。
数字、布尔值以字符串返回；列表和矩形属性在本轮以JSON文本返回。

空字符串、纯空格、None和0属性名被InvalidParamsError拒绝。非零整数转换为属性名字符串，
本轮123未命中，返回None。公开接口无timeout参数；底层默认读取超时5秒。

## 运行场景

前置：dev及Win32靶场运行，启用 `D:\code\元素库\260902_win元素`。
脚本自动切换表单页，读取 `win32靶场_表单控件_输入框_姓名`，不修改输入框内容。

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_get_attribute.py --non-interactive
```

自动模式焦点恢复失败只警告；鼠标恢复及Package释放仍严格检查。默认人工模式允许
手动切回原终端。测试结束保留表单页。

## 本轮实际结果

| 属性/场景 | 实际结果 | 结论 |
| --- | --- | --- |
| Name | `'姓名'` | PASS |
| ClassName关键字 | `'Edit'` | PASS |
| `'  classname  '` | `'Edit'` | PASS |
| ControlType | `'50004'`（Edit控件类型值） | PASS |
| IsEnabled / IsPassword | `'True'` / `'False'` | PASS |
| ProcessId | `'4604'`，正整数文本 | PASS |
| RuntimeId | `'[42,524586]'`，可解析整数数组 | PASS |
| BoundingRectangle | `'{"x":1958,"y":355,"w":430,"h":30}'`，有效JSON矩形 | PASS |
| 未知属性 | None | PASS |
| 整数属性名123 | None | PASS |
| 空属性名 | 空字符串、空格、None、0均拒绝 | PASS |
| 非法字符 | `< > " ' `、反引号、左右括号和分号对应检查均拒绝 | PASS |
| 调用参数数量 | 缺参、多余位置参数、timeout关键字均TypeError | PASS |
| 资源清理 | 鼠标恢复、Package关闭，靶场保持运行 | PASS |

连同合同、Package及元素准备，共17/17通过，总耗时1375.8ms，退出码0；测试者明确确认。
成功属性读取约3.0–4.9ms，布尔属性分组8.7ms；这不是性能上限保证。

## 验证范围

当前测试代表性的字符串、数值、布尔、列表及矩形属性，不保证所有UIA属性均支持。
ProcessId仅验证正整数文本；RuntimeId验证数组结构；矩形验证结构及有效宽高，本轮
没有独立原生交叉验证这些属性的具体数值。数值不应固化为后续运行预期。
未验证销毁元素、动态属性变化、密码框及其他控件类型。焦点诊断未随本次粘贴提供，
只记录必要清理通过，不声称焦点已自动恢复。
