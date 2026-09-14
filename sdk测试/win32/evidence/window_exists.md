# `Win32Window.exists()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.exists"
lifecycle: "VERIFIED"
verification_date: "2026-09-09"
verification_summary:
  passed: 9
  total: 9
  elapsed_ms: 13.9
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  temporary_window_destroyed: true
  temporary_thread_stopped: true
  mouse_restored: true
  foreground_verified: true
persistent_script:
  path: "win32/test_win32_window_exists.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "1b357966af89108e55d45d2cae9586cdea4d1492f32b2c7fc7825c9e9cbbbd04"
  command: 'uv run .\win32\test_win32_window_exists.py --non-interactive'
```

## 用途与合同

```python
exists = window.exists()  # bool
```

判断窗口对象对应的窗口是否仍存在。没有公开参数；额外位置参数和timeout关键字
被TypeError拒绝。与win32.exists(window)、Win32Element.exists()分别计数。

对于本轮绑定原生句柄的Win32Window，窗口隐藏仍返回True；DestroyWindow后原对象
返回False，与Windows IsWindow一致。该结论不外推为元素对象失效处理正确。

## 场景与运行

保持dev和Win32靶场运行，在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_window_exists.py --non-interactive
```

无需元素库。先对运行中的靶场作只读存在性检查，再由独立消息线程创建脚本拥有的隐藏
顶层窗口，通过get_by_handle获取窗口对象，检查存在及参数规则。原生线程销毁该窗口后，
对同一个SDK对象检查False。只销毁临时窗口，不关闭靶场，不使用剪贴板。

## 本轮结果

| 项目 | 实际结果 | 耗时 |
| --- | --- | --- |
| API合同 | 无参数，返回bool | 0.1ms |
| 靶场仍存在 | SDK与IsWindow均True | 3.7ms |
| 临时窗口准备 | 创建并绑定成功，句柄49550970 | 8.3ms |
| 隐藏窗口仍存在 | SDK与IsWindow均True | 0.1ms |
| 重复查询 | 连续三次True | 0.1ms |
| 参数限制 | 两种错误传参均TypeError；窗口仍存在 | 0.0ms |
| 销毁临时窗口 | 原句柄失效 | 1.1ms |
| 原对象不再存在 | SDK与IsWindow均False | 0.0ms |
| 资源清理 | 临时窗口及线程清理、鼠标恢复，靶场保持运行 | 0.3ms |

9/9通过，总耗时13.9ms，退出码0，测试者明确确认。
原前台句柄131974；恢复前已是同一窗口，SetForegroundWindow返回True，最终句柄核验通过。
因此不能把该轮解释为曾从其他前台窗口成功抢回焦点。

## 验证范围

只覆盖有原生句柄的窗口对象，未覆盖Desktop伪窗口及基于元素候选集的存在性分支。
未验证系统句柄复用、跨权限窗口、窗口销毁与查询并发竞争等场景。
临时窗口句柄和耗时仅为此次观察值，不固化为后续运行预期。
