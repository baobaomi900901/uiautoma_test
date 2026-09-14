# `win32.GetDeviceScaleFactor()` 验证证据

```yaml
api: "win32.GetDeviceScaleFactor"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 21
  total: 21
  elapsed_ms: 1.9
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  requires_ui: false
persistent_script:
  path: "win32/test_win32_device_scale_factor.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "6d6d34de8369c72fa238e09dd81f883b0ab0fd80f1de06587246b0be39379ea1"
  command: 'uv run .\win32\test_win32_device_scale_factor.py --non-interactive'
```

## 用途与合同

```python
factor = win32.GetDeviceScaleFactor(scale_percent)
```

把缩放百分比转换为浮点比例因子，计算规则为 `scale_percent / 100.0`。
例如100→1.0、150→1.5、225→2.25。它不读取或修改系统当前缩放设置，也不需要
窗口、元素库或UI运行环境。

`scale_percent`必填，支持位置或关键字传入。正数、浮点数和可转换数字字符串接受；
零、负数、None、空字符串、百分号字符串及非数字被InvalidParamsError拒绝。
额外位置参数和timeout关键字被TypeError拒绝。本轮未覆盖NaN、Infinity和布尔值。

## 运行方式

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_device_scale_factor.py --non-interactive
```

脚本是纯数值测试，不连接Runtime、不创建窗口、不操作鼠标、剪贴板或显示设置。

## 本轮结果

| 类别 | 输入 | 预期→实际 | 结果 |
| --- | --- | --- | --- |
| 常用整数 | 100、125、150、175、200、225、250 | 1.0、1.25、1.5、1.75、2.0、2.25、2.5 | PASS |
| 小数 | 137.5、0.5 | 1.375、0.005 | PASS |
| 字符串 | `'150'`、`' 125 '` | 1.5、1.25 | PASS |
| 关键字 | `scale_percent=225` | 2.25 | PASS |
| 非法值 | 0、-100、`'bad'`、`'125%'`、None、`''` | InvalidParamsError | PASS |
| 调用参数 | 缺参、多余位置参数、timeout | TypeError | PASS |
| 资源清理 | 无窗口、文件、剪贴板改动 | 无待清理资源 | PASS |

完整21项日志：21/21通过，总耗时1.9ms，退出码0，测试者明确确认。

## 验证边界

本轮验证的是确定性数值转换，不是实际显示器DPI探测。
未覆盖NaN、Infinity、布尔值、Decimal等特殊可转换对象；这些输入是否应被接受需要
另行定义合同。正数范围没有上限，超常规缩放百分比只按数学公式转换。
