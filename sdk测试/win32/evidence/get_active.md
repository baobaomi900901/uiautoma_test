# `uiautoma.win32.get_active()` 验证证据

```yaml
api: "uiautoma.win32.get_active"
lifecycle: "VERIFIED"
verification_date: "2026-09-09"
verification_summary:
  passed: 13
  total: 13
  elapsed_ms: 89.0
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  foreground_restored: true
  mouse_restored: true
persistent_script:
  path: "win32/test_win32_get_active.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "cdce0fdd29d746ac8377fbeef023d2679c8e31575baa47dac2a0b3c233b2dca1"
  command: 'uv run .\win32\test_win32_get_active.py --non-interactive'
```

## 用途及参数

```python
window = win32.get_active(timeout=5)
```

获取当前前台窗口，返回Win32Window。timeout默认5秒，可按位置或关键字传入；
0单次查询，正数有限等待，None使用默认值，数字字符串可转换，-1无限等待。
本轮只在已存在前台窗口时验证-1。小于-1及非数字值被InvalidParamsError拒绝。
不支持多余位置参数和未知关键字。

get_active本身读取前台，不设置始终置顶。脚本中的target.activate()是切换测试场景，
让前台从Tabby变为靶场；测试者观察到的窗口被带到前面符合该准备动作预期。

## 运行方法

dev及可见、未最小化的Win32靶场运行，从Tabby等另一窗口启动：

```powershell
uv run .\win32\test_win32_get_active.py --non-interactive
```

运行目录为 `D:\code\元素库\sdk测试`，不需要元素库。测试期间不要切换窗口。
原生GetForegroundWindow、窗口标题、类名及PID与SDK结果逐项核对。
结束恢复鼠标和原前台，不关闭靶场、不使用剪贴板。自动模式焦点未恢复仅警告；
本次实际自动恢复成功。

## 实测结果

| 场景 | 结果 |
| --- | --- |
| API合同 | 默认值、传参规则及返回注解符合合同 |
| 初始前台 | 返回Tabby窗口131974、PID31432，与原生一致 |
| 激活靶场 | 准备完成，原生确认靶场成为前台 |
| 默认超时 | 返回靶场2951616、PID4604 |
| timeout=0位置参数 | 返回正确前台窗口 |
| timeout=0.5关键字 | 返回正确前台窗口 |
| timeout=None | 返回正确前台窗口 |
| timeout='0.5' | 返回正确前台窗口 |
| timeout=-1 | 已有前台时正常返回 |
| 重复查询 | 连续三次返回同一靶场窗口 |
| 非法超时 | -2和'bad'被InvalidParamsError拒绝 |
| 多余参数 | 多余位置参数、unknown关键字被TypeError拒绝 |
| 清理 | 鼠标恢复、靶场保持运行，原前台恢复并核验 |

13/13通过，总耗时89.0ms，退出码0，测试者确认符合预期。
窗口对象的句柄、标题、类名及PID均与原生读取一致。终端标题为pwsh.exe路径，
其宿主由测试者确认为Tabby，不能仅由标题推断应用品牌。

恢复时SetForegroundWindow返回True，前台短暂为0，约20.1ms后变为原窗口131974；
清理耗时21.5ms。本轮确实从靶场切回原窗口，不是始终停留原前台的情况。

## 覆盖边界

没有人为制造无前台窗口，不验证超时耗尽、无限等待后出现、跨权限窗口或动态标题场景。
前台短暂为0发生在清理阶段，不能作为get_active已验证无前台重试的证据。
窗口句柄、PID和耗时只记录本次观察值，不固定为后续验收条件。
