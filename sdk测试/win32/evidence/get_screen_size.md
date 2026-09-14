# `win32.get_screen_size()` 验证证据

```yaml
api: "uiautoma.win32.get_screen_size"
lifecycle: "VERIFIED"
verification_date: "2026-09-10"
verification_summary:
  passed: 7
  total: 7
  elapsed_ms: 4.6
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  primary_size: [3440, 1440]
  virtual_desktop_rect: [-2560, 0, 6000, 1600]
persistent_script:
  path: "win32/test_win32_get_screen_size.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "9ecb15b42578f0a3ee237f682ef5cef9176d821803040be6ac9235e17eee8f3e"
  command: 'uv run .\win32\test_win32_get_screen_size.py --non-interactive'
```

## 用途与运行

```python
width, height = win32.get_screen_size()
```

读取主屏幕像素宽高，返回正整数二元组，不是虚拟桌面的总宽高。无公开参数；
传入位置参数或timeout关键字应抛TypeError。当前高层函数没有返回注解，脚本检查实际类型。

在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_get_screen_size.py --non-interactive
```

无需靶场、元素库或剪贴板。建议dev运行；本接口可能在Runtime不可用时使用原生回退，
本轮没有强制区分使用哪一条路径。脚本启用Per-Monitor v2，测试期间不要修改显示配置。

## 实测结果

| 项目 | 观察 | 结果 |
| --- | --- | --- |
| API合同 | 无参数 | PASS |
| 原生参照 | EnumDisplayMonitors/GetMonitorInfoW与GetSystemMetrics主屏指标一致 | PASS |
| 返回类型 | 正整数(width,height)元组 | PASS |
| 尺寸一致 | SDK与原生均为(3440,1440) | PASS |
| 重复读取 | 连续三次均为主屏尺寸 | PASS |
| 参数限制 | 位置参数及timeout均TypeError | PASS |
| 清理 | 只读，未创建窗口/文件，无待清理资源 | PASS |

原生显示器布局：

- 副屏：(-2560,0,2560,1600)。
- 主屏：(0,0,3440,1440)。
- 虚拟桌面：(-2560,0,6000,1600)。

SDK实际返回(3440,1440)，本次清楚区分主屏与虚拟桌面。
7/7通过，总耗时4.6ms，退出码0，测试者明确确认。

## 验证边界

只验证当前显示配置，未覆盖运行中改分辨率、切换主屏、断开显示器或不同DPI感知模式。
布局包含负坐标副屏，但接口没有返回副屏坐标，本轮不声称验证副屏坐标API。
3440×1440等数值只记录本次环境，不固定为后续预期。未区分Runtime路径和SDK原生回退。
