# Win32Element 属性专项验证证据

```yaml
api: "Win32Element.id / element_id / name / raw / process_key"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 9
  total: 9
  elapsed_ms: 1316.6
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  target_element: "win32靶场_表单控件_输入框_姓名"
  package_dir: "D:\\code\\元素库\\260902_win元素"
  necessary_cleanup: "PASS"
  foreground_restore: "未恢复；自动模式警告"
persistent_script:
  path: "win32/test_win32_element_properties.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "b4329559b456a918d684b0b898cc57298628cdfafeb9c2d7f0bf8801c8547faf"
  command: 'uv run .\win32\test_win32_element_properties.py --non-interactive'
```

## 用途与访问形式

```python
element.id          # 当前Runtime元素ID（部分版本也提供可调用兼容形式）
element.element_id  # 元素ID别名
element.name        # 元素库/运行时显示名称
element.raw         # 底层描述字典副本
element.process_key # 所属应用标识，可能为空字符串
```

这些是元素身份和描述数据的只读访问器，不执行UI动作。读取不应修改last_result或靶场状态。
`raw`返回独立字典，修改调用方副本不应影响后续读取。

## 本轮真实结果

测试者执行 `uv run .\win32\test_win32_element_properties.py --non-interactive`，
自动切换表单页并定位姓名输入框。`id`实际为
`rt:win:6e391dfe3c984893ac8803dbef357e77`；`element_id`与其一致；`name`为
`win32靶场_表单控件_输入框_姓名`；`raw`含10个字段；`process_key`为`''`。

| 测试项 | 结果 |
| --- | --- |
| 元素准备 | Runtime元素获取成功，Package路径一致 | PASS |
| 身份与名称 | id、element_id别名、name类型和值符合预期 | PASS |
| raw结构 | 非空独立dict，含底层id | PASS |
| raw独立性 | 修改副本不影响后续raw | PASS |
| process_key | 返回字符串（允许为空） | PASS |
| 无副作用 | 五个访问器未创建/修改last_result | PASS |
| 重复读取 | 结果稳定 | PASS |
| 访问规则 | 访问器可读取，无额外调用参数 | PASS |
| 资源清理 | 鼠标恢复、Package释放，靶场保持表单页 | PASS |

汇总9/9通过，总耗时1316.6ms，退出码0，测试者明确确认。
自动模式焦点恢复失败仅记警告，未影响必要资源清理；不将警告描述为焦点恢复成功。

## 验证范围

属性专项确认当前输入框对象的访问形式、类型、别名关系、raw浅层独立性和无副作用。
未覆盖其他控件类型、元素销毁/重建后的ID变化、跨Package、嵌套raw深拷贝、process_key
非空场景及不同SDK版本的id调用兼容形式。数值和字段数仅为本轮观察，不固定为验收常量。
