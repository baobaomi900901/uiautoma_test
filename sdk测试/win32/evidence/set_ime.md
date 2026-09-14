# `win32.set_ime()` 验证证据

```yaml
api: "win32.set_ime"
lifecycle: "VERIFIED"
verification_date: "2026-09-11"
verification_summary:
  passed: 16
  total: 16
  elapsed_ms: 151.6
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  original_hkl_restored: true
  original_hkl: "0x8040804"
persistent_script:
  path: "win32/test_win32_set_ime.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "e73db1072ec8aa045c8f6217bcf8f2375d13c5759a325e876a9498981756e6b4"
  command: 'uv run .\win32\test_win32_set_ime.py --non-interactive'
```

## 用途与合同

```python
win32.set_ime("en")   # 激活英文布局
win32.set_ime("zh")   # 激活中文布局
```

切换当前脚本线程的输入布局语言，返回None，不负责改变其他线程或输入法内部中英文模式。
支持英文别名`en`、`eng`、`english`和中文别名`zh`、`cn`、`chinese`。
lang必填；空字符串、空白、None、数字和不支持的语言被InvalidParamsError拒绝。
额外位置参数及timeout关键字被TypeError拒绝。

## 运行与恢复

纯Windows输入布局测试，无需dev、靶场或元素库。执行：

```powershell
uv run .\win32\test_win32_set_ime.py --non-interactive
```

脚本以GetKeyboardLayout保存当前线程HKL，调用SDK切换并用GetKeyboardLayout与get_ime
交叉核对。结束用原生ActivateKeyboardLayout恢复原HKL，不卸载系统布局。测试期间不要
切换输入法。原HKL为`0x8040804`，初始及恢复标签为zh。

## 本轮结果

| 场景 | 实际结果 | 结果 |
| --- | --- | --- |
| API合同 | lang必填，位置参数，返回None | PASS |
| 原始布局 | zh | PASS |
| 英文别名 | en、eng、english均返回en，HKL为0x4090409 | PASS |
| 中文别名 | zh、cn、chinese均返回zh，HKL为0x8040804 | PASS |
| 重复切换 | zh再次切换成功 | PASS |
| 非法语言 | 空、空白、None、123、jp均InvalidParamsError且HKL不变 | PASS |
| 参数数量 | 缺参、多余位置参数、timeout均TypeError | PASS |
| 资源清理 | 原HKL恢复并核验，未卸载布局 | PASS |

完整16项日志：16/16通过，总耗时151.6ms，退出码0，测试者明确确认。
其中英文别名调用耗时17.2–22.0ms；这些是本机观察值，不构成性能保证。

## 验证边界

本机已加载/可加载英文和简体中文布局已验证，未覆盖其他语言、布局加载失败、输入法
安装权限、其他线程布局或前台窗口布局隔离。SDK实现可能LoadKeyboardLayout加载布局，
本轮没有卸载该布局；系统布局列表的持久变化未作为断言。
