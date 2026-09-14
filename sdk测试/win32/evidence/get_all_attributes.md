# `Win32Element.get_all_attributes()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_all_attributes"
lifecycle: "VERIFIED"
verification_date: "2026-09-09"
verification_summary:
  passed: 14
  total: 14
  elapsed_ms: 1464.3
  exit_code: 0
  tester_confirmed: true
  observed_attribute_count: 161
  necessary_cleanup: "PASS"
  foreground_restore: "本次粘贴未包含单独焦点诊断，未确认恢复结果"
persistent_script:
  path: "win32/test_win32_get_all_attributes.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "482e4665bb9a1e775d40788d70a27f71e9d66bcc71023a288b34d99e4e862d8a"
  command: 'uv run .\win32\test_win32_get_all_attributes.py --non-interactive'
```

## API 用途与合同

```python
attributes = element.get_all_attributes()  # dict[str, Any]
```

一次读取元素全部可用属性。没有公开参数，返回属性名到属性值的字典，属性值保留
Runtime提供的JSON安全类型。与get_attribute()的字符串返回不同，整数、布尔、列表
和矩形字典不会全部转为字符串。

不保证所有控件拥有相同属性或固定属性数量。额外位置参数及timeout关键字抛TypeError。
底层读取默认超时5秒。读取不修改last_result。

## 场景与运行

UIAutoma dev和Win32靶场运行，启用 `D:\code\元素库\260902_win元素`。
脚本自动切换表单页，读取 `win32靶场_表单控件_输入框_姓名`，不修改控件数据。
在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_get_all_attributes.py --non-interactive
```

自动模式焦点失败仅警告，不等待人工；鼠标恢复和Package释放仍严格检查。
结束保留表单页。默认不带参数时允许人工恢复焦点。

## 本轮结果

| 场景 | 实际结果 | 结论 |
| --- | --- | --- |
| API合同、当前库与元素准备 | 无参数、dict[str,Any]，目标准备成功 | PASS |
| 返回容器 | 非空字典，共161项；last_result不变 | PASS |
| 字典键 | 非空字符串，属性名唯一 | PASS |
| 字符串属性 | Name为姓名，ClassName为Edit | PASS |
| 整数属性 | ControlType为50004，ProcessId为正整数 | PASS |
| 布尔属性 | IsEnabled为True，IsPassword为False | PASS |
| RuntimeId | 非空整数列表 | PASS |
| BoundingRectangle | x/y/w/h整数字典，宽高有效 | PASS |
| 结果独立性 | 清空此前返回字典不影响后续读取，代表稳定属性一致 | PASS |
| 参数限制 | 多余位置参数、timeout均TypeError | PASS |
| 必要清理 | 鼠标恢复，Package关闭，靶场保持运行 | PASS |

完整14项日志及测试者确认：14/14通过，总耗时1464.3ms，退出码0。
首次属性读取28.2ms，重复调用独立性检查87.4ms，清理1018.3ms。
161仅为本轮观察值，不应固化成后续测试必须返回的数量。

## 验证边界

验证代表属性的类型、部分已知值及基本结构，未独立核对ProcessId、RuntimeId和矩形的
具体值，也未验证全部161项属性的语义。字典键唯一性是返回容器层面的检查，不能证明
底层枚举前不存在被覆盖的重复键。
结果独立性仅覆盖顶层字典清空及后续读取，不宣称验证所有嵌套对象的深拷贝。
未覆盖其他控件、销毁元素、动态属性变化和属性读取失败。
本次未提供焦点诊断，清理PASS不等于已确认前台自动恢复。
