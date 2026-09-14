# `uiautoma.win32.get_list()` 验证证据

```yaml
api: "uiautoma.win32.get_list"
lifecycle: "VERIFIED"
verification_date: "2026-09-09"
verification_summary:
  passed: 16
  total: 16
  elapsed_ms: 570.5
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  temporary_windows_and_threads_cleaned: true
  mouse_restored: true
  foreground_verified: true
persistent_script:
  path: "win32/test_win32_get_list.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "b2f1506515fb12ccdda2c5ed95f5f8e2d103249b99fcc9edf410529bc5a7d4f8"
  command: 'uv run .\win32\test_win32_get_list.py --non-interactive'
```

## 用途与参数

```python
windows = win32.get_list(
    title=None,
    class_name=None,
    process_name=None,
    use_wildcard=False,
    timeout=5,
)
```

批量获取匹配条件的顶层窗口，返回list[Win32Window]。title支持位置或关键字传入，
其余四项仅限关键字。支持标题片段、类名、进程名过滤，use_wildcard启用星号和问号匹配。
timeout=0单次查询，正数有限等待，-1无限等待，None采用默认值，数字字符串可转换。
没有匹配时返回空列表。

## 运行场景与独立参照

保持dev运行，在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_get_list.py --non-interactive
```

不需要元素库。脚本自动创建两个可见、不请求激活的临时顶层窗口，标题带随机唯一前缀，
类名Static，进程名由原生读取本进程模块路径取得。通过EnumWindows独立比较这两个
窗口的顺序和数量；仅销毁脚本创建的窗口及其消息线程，不关闭用户窗口。

## 本轮结果

标题前缀：`UIAutoma-list-62da6233a60c4707819aa005d30bfed5`，进程python.exe。
创建句柄顺序为 `[7018484,52567708]`，原生枚举顺序为 `[52567708,7018484]`。

| 场景 | 实际结果 | 结论 |
| --- | --- | --- |
| 合同与准备 | 五参数规则正确，两个可见临时窗口创建成功 | PASS |
| 全部默认参数 | 返回14个窗口；两个临时窗口均包含且相对顺序正确 | PASS |
| 标题片段 | 返回2个，顺序与原生一致 | PASS |
| 唯一标题 | 返回1个，句柄7018484 | PASS |
| 类名过滤 | 标题前缀+Static返回2个 | PASS |
| 进程过滤 | 标题前缀+python.exe返回2个 | PASS |
| 全关键字 | 组合条件返回2个 | PASS |
| 通配符 | 标题前缀-?及Sta*返回2个 | PASS |
| None、数字字符串超时 | 已存在目标返回2个 | PASS |
| -1无限值 | 已存在目标立即返回2个 | PASS |
| 未命中零超时 | 返回[]，约1.1ms | PASS |
| 未命中0.3秒等待 | 返回[]，约404.3ms | PASS |
| 错误参数 | -2、非数字timeout及多余位置参数被正确拒绝 | PASS |
| 清理 | 两个临时窗口及线程清理，鼠标恢复，前台核验通过 | PASS |

汇总16/16通过，总耗时570.5ms，退出码0，测试者明确确认。
0.3秒等待实际404.3ms与当前轮询周期造成的余量一致，不将其写为精确300ms保证。
默认枚举14个只是当时桌面环境的观察值，不固定为后续运行预期。

原前台131974在恢复前已处于前台，SetForegroundWindow返回True并核验一致；不能据此
推断该轮发生过跨应用抢回焦点。

## 验证范围

默认枚举只完整检查临时窗口是否包含、相对顺序及所有返回句柄有效性，没有逐项对比
桌面上所有窗口的枚举完整性。类名和进程过滤与唯一标题前缀组合，本轮未创建不同类名
或不同进程的负样本，不能单独证明这两种过滤对所有不匹配窗口的排除行为。
未覆盖等待过程中窗口出现、无限等待后出现、空标题窗口、隐藏窗口及跨权限枚举。
