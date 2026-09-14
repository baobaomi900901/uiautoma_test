# `win32.is_os_64bit()` 验证证据

```yaml
api: "win32.is_os_64bit"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 5
  total: 5
  elapsed_ms: 58.2
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  native_architecture: "AMD64"
  sdk_result: true
persistent_script:
  path: "win32/test_win32_is_os_64bit.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "a1b778055a4fa00d38e2ba56d5aa129f4ac785d424bb5ef8459c393b797cf316"
  command: 'uv run .\win32\test_win32_is_os_64bit.py --non-interactive'
```

## 用途与合同

```python
is_64 = win32.is_os_64bit()
```

判断操作系统是否为64位，返回bool，不是判断当前Python解释器位数。
无公开参数；额外位置参数和timeout关键字被TypeError拒绝。

## 验证方法

脚本使用Windows `GetNativeSystemInfo` 独立读取操作系统处理器架构，并与SDK结果、
`platform.machine()` 及 `PROCESSOR_ARCHITEW6432` 诊断信息对照。纯环境查询，不需要dev、
元素库或靶场，不修改系统设置。

```powershell
uv run .\win32\test_win32_is_os_64bit.py --non-interactive
```

## 本轮结果

| 场景 | 实际结果 | 结果 |
| --- | --- | --- |
| API合同 | 无公开参数，返回bool | PASS |
| 原生架构交叉校验 | GetNativeSystemInfo=AMD64；SDK=True；platform.machine='AMD64' | PASS |
| 重复读取 | 连续五次均返回True | PASS |
| 参数限制 | 位置参数和timeout均TypeError | PASS |
| 资源清理 | 未修改系统或文件，无待清理资源 | PASS |

汇总5/5通过，总耗时58.2ms，退出码0，测试者明确确认。
`PROCESSOR_ARCHITEW6432`为空；本轮Python本身也是AMD64，未覆盖32位Python运行在64位Windows的场景。

## 验证边界

未覆盖32位进程、ARM64、Windows兼容层、环境变量伪造或操作系统架构动态变化。
AMD64和True是本机本轮观察值，不固化为跨机器预期。未测试错误平台及API不可用回退。
