# `uiautoma.win32.get_by_element()` 验证证据

```yaml
api: "uiautoma.win32.get_by_element"
lifecycle: "VERIFIED"
verification_summary:
  passed: 13
  total: 13
  elapsed_ms: 1587.6
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  necessary_cleanup: "PASS"
  foreground_restore: "未恢复；自动模式警告"
persistent_script:
  path: "win32/test_win32_get_by_element.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "8cb05b2b83fb09431be7f1634197f9077e79340d417bbd7250b0528308943548"
  command: 'uv run .\win32\test_win32_get_by_element.py --non-interactive'
```

## 用途与参数

```python
window = win32.get_by_element(element)
# 或 win32.get_by_element(element=element)
```

根据已获取的Win32Element取得所属顶层窗口，返回Win32Window。element必填，支持位置
及关键字传入。不是按名称查找元素，因此不能直接传元素名或Selector。
公开没有timeout参数，内部窗口解析默认5秒。当前实现还接受底层RawWinElement，
该分支未纳入本轮公开高层对象测试。

## 测试场景

dev和Win32靶场运行，启用 `D:\code\元素库\260902_win元素`。
在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_by_element.py --non-interactive
```

脚本激活表单页，使用姓名输入框和保存按钮，通过元素物理边界唯一匹配原生子控件，
再以GetAncestor(GA_ROOT)得到根窗口作为独立身份参照，核对SDK返回窗口的句柄、标题、
类名及PID。原生子控件选择仍以SDK提供的边界为匹配线索，不属于完全独立的元素定位。

## 本次真实结果

| 场景 | 实际结果 | 耗时 |
| --- | --- | --- |
| API合同 | 必填参数和Win32Window返回符合合同 | 0.0ms |
| 场景准备 | 两个子控件原生根窗口均为331172 | 541.4ms |
| 输入框位置参数 | 返回靶场窗口331172，身份一致 | 3.7ms |
| 保存按钮关键字 | 返回同一靶场窗口331172，身份一致 | 4.0ms |
| 重复获取 | 连续三次返回同一所属窗口 | 11.9ms |
| None、字符串、整数、字典、Selector、窗口对象 | 六项均被InvalidParamsError拒绝 | 各0.0ms |
| 参数数量 | 缺参、多余位置参数、timeout均TypeError | 0.0ms |
| 必要清理 | 鼠标恢复、Package释放、靶场保持运行 | 1015.7ms |

共13/13通过，总耗时1587.6ms，退出码0；测试者明确确认。
返回顶层窗口标题为Win32 靶场 - UIA，类名XPathWin32ShootingRange，PID12992，
与原生参照一致。查询未改变来源element.last_result。

原终端窗口68608有效，SetForegroundWindow返回False，最终前台留在靶场331172。
按已同意的自动模式规则记录警告，不等待人工；必要清理通过不表示前台已经恢复。

## 验证范围

只验证同一靶场内两个高层元素。未覆盖底层RawWinElement、跨进程目标、销毁元素或
元素重新挂接窗口场景。返回的句柄、PID与耗时仅为本轮观察，不固定为后续测试预期。
脚本不修改控件内容、不关闭靶场；准备阶段切换表单页，结束保留该页。
