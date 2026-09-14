# `uiautoma.win32.Win32Element.highlight()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.highlight"
lifecycle: "VERIFIED"
verification_date: "2026-09-08"
verification_summary:
  passed: 15
  total: 15
  elapsed_ms: 33906.5
  exit_code: 0
  full_log_provided: true
  visual_target_confirmed: true
  visual_overlay_disappeared: true
  foreground_restore: "manual; original foreground handle verified"
  foreground_handle: 985468
  terminal_application: "Tabby; identified by tester"
  cleanup_passed: true
persistent_script:
  path: "win32/test_win32_highlight.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "8a2674d70cf4799580911246d7d9cf2c9fab0a9f290abdef3d91f0035fe81f15"
  command: 'uv run .\win32\test_win32_highlight.py'
```

## API 说明

```python
element.highlight(duration=1.0, delay_after=0)  # 返回 None
```

让目标元素显示高亮框，便于人工确认定位位置。两个参数均支持位置或关键字传入。

| 参数 | 默认值 | 当前实现与本轮验证行为 |
| --- | --- | --- |
| duration | 1.0 | 高亮持续秒数；支持0、小数；None使用1秒；数字字符串可转换；负数、非数字被InvalidParamsError拒绝 |
| delay_after | 0 | 高亮完成后的额外等待秒数；None/0不等待；非法值在高亮动作完成后才被拒绝 |

正常返回None，更新element.last_result。调用耗时包含定位、显示/隐藏高亮和通信开销，
不能将整个调用耗时直接当作红框显示时间。

## 运行方式与人工观察

保持UIAutoma dev及Win32靶场运行，启用 `D:\code\元素库\260902_win元素`，在
`D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_highlight.py
```

脚本切换到拖拽测试页，高亮 `win32靶场_拖拽测试_可拖拽元素`，不拖拽目标、不使用剪贴板。
包含2秒高亮供观察。测试者已明确确认红色高亮框覆盖正确元素，脚本结束后红框消失。

脚本自动检查返回值、last_result成功、原生目标边界不变及耗时；视觉效果不能仅依靠这些
自动检查判定。脚本输出固定保留READY_FOR_LIVE，待人工确认后由证据文档记录VERIFIED，
因此本轮日志中的READY_FOR_LIVE与这里的最终验收状态并不矛盾。

## 最新真实验证

目标物理边界为 `(725,730,120,80)`，DPI模式为Per-Monitor v2（进程）。

| 场景 | 观察结果 | 结果 |
| --- | --- | --- |
| API合同及场景准备 | 两参数默认值/传参规则符合合同，目标定位成功 | PASS |
| 默认高亮 | 调用1119.0ms | PASS |
| 两秒位置参数 | highlight(2,0)，调用2123.7ms | PASS |
| 全关键字 | duration=0.4，调用519.2ms | PASS |
| 零时长 | duration=0，调用119.3ms；不要求肉眼看到 | PASS |
| None延时 | duration=0.3，调用417.9ms | PASS |
| None时长 | 使用默认1秒，调用1116.9ms | PASS |
| 数字文本时长 | duration="0.3"，调用422.6ms | PASS |
| 动作后延时 | 基线426.6ms，延时调用728.3ms，差值301.7ms，预期约300ms | PASS |
| 非法duration | 负数及非数字在动作前拒绝 | PASS |
| 非法delay_after | 高亮结束后拒绝，动作结果已更新 | PASS |
| 视觉效果 | 测试者确认红框覆盖正确元素且最终消失 | 人工确认通过 |
| 资源清理 | 手动切回原窗口后句柄核验通过，鼠标恢复、Package关闭 | PASS |

15/15通过，退出码0，总耗时33906.5ms。清理项耗时25401.7ms包含等待人工切窗，
不是高亮持续时间或产品性能数据。

## 焦点恢复历史与终端说明

此前多次运行中，高亮功能检查通过，但清理无法恢复原窗口985468：该窗口有效、可见且
未最小化，SetForegroundWindow返回False，实际前台仍是Win32靶场4331724。
这些失败轮保留为清理失败，不能回写为全部通过；确切的系统拒绝原因没有得到确认。

调整后的测试脚本先尝试自动恢复并观察1秒；失败时提示测试者在30秒内切回原窗口，
无需按Enter。仅在实际前台句柄等于原句柄时判定恢复成功；失效或超时仍为失败。
本轮自动切换仍返回False，随后人工恢复成功，已核对原句柄985468。
焦点恢复完成后再恢复鼠标位置，最后释放Package。

测试者实际使用Tabby。日志中的窗口标题是pwsh.exe路径，不能据此将窗口宿主认定为
Windows Terminal或独立PowerShell窗口。恢复目标依据保存的窗口句柄，不依赖终端品牌。

本轮没有证明自动焦点恢复问题已修复；通过的是明确记录、实际核验的人工恢复路径。
未认定为highlight产品缺陷。未验证其他控件、跨显示器高亮或叠加层像素级定位精度。
