# `win32.get_ime()` 验证证据

```yaml
api: "win32.get_ime"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 7
  total: 7
  elapsed_ms: 0.7
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  original_hkl_restored: true
  observed_hkl: "0x8040804"
  observed_language: "zh"
persistent_script:
  path: "win32/test_win32_get_ime.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "e0657dbfebcafc3cfe8aa500c6e971f596016adfc75bdbbee7473edcc6c9a491"
  command: 'uv run .\win32\test_win32_get_ime.py --non-interactive'
```

## 用途与合同

```python
language = win32.get_ime()  # "en"、"zh"或"0x语言ID"
```

读取当前调用线程的键盘布局语言，不是前台窗口的布局，也不是输入法内部中英文切换状态。
无公开参数，返回str。英文语言ID 0x0409返回`en`；中文语言ID集合返回`zh`；其他布局
返回`0x`加四位语言ID。额外位置参数和timeout关键字被TypeError拒绝。

## 运行方式

纯环境读取，无需dev、靶场或元素库；不安装输入法。执行：

```powershell
uv run .\win32\test_win32_get_ime.py --non-interactive
```

脚本以Windows `GetKeyboardLayout(0)` 和 `GetKeyboardLayoutList` 独立读取当前线程HKL，
逐个激活本机已加载布局并与SDK语言映射核对，最后恢复原HKL。测试期间不修改其他线程
或系统输入法配置。

## 本轮真实结果

| 场景 | 实际结果 | 结果 |
| --- | --- | --- |
| API合同 | 无参数，返回str | PASS |
| 布局准备 | 原HKL `0x8040804`；已加载列表仅该布局 | PASS |
| 初始布局 | 原生映射为zh，SDK返回zh | PASS |
| 已加载布局读取 | `0x0804`中文布局返回zh | PASS |
| 重复读取 | 连续五次与原生HKL一致 | PASS |
| 参数限制 | 位置参数和timeout均TypeError | PASS |
| 资源清理 | 原HKL恢复并核验，未安装/卸载输入法 | PASS |

完整7项日志：7/7通过，总耗时0.7ms，退出码0，测试者明确确认。

## 验证边界

本机运行时只有一个已加载中文布局，未覆盖英文布局、其他语言布局、32位进程、线程布局
与前台窗口布局不同或动态切换竞争。`0x8040804`和`zh`是本轮环境观察值，不固定为所有
机器的结果。未验证布局切换失败或Windows API不可用时的异常路径。
