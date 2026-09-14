# `uiautoma.win32.Win32Element.locate()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.locate"
lifecycle: "READY_FOR_LIVE"
verification_date: "2026-09-09"
verification_summary:
  passed: 14
  failed: 2
  total: 16
  elapsed_ms: 2569.3
  exit_code: 1
  full_log_provided: true
  necessary_cleanup: "PASS"
  foreground_restore: "未恢复；自动模式警告"
issue: "https://github.com/uiautoma/desktop/issues/53"
issue_evidence: "https://github.com/uiautoma/desktop/issues/53#issuecomment-5594288020"
persistent_script:
  path: "win32/test_win32_locate.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "491bdb040cd36f99960de72c619d0da9bce38cf75fdc25b9056b8947752a3657"
  command: 'uv run .\win32\test_win32_locate.py --non-interactive'
```

## API用途及合同

```python
result = element.locate(timeout=3.0)
```

重新定位元素，返回LocateResult，提供found、rect、strategy、trace_info、
fallback_reason和raw。不同于只返回布尔值的exists()，locate()还提供边界和诊断信息。

timeout默认3秒且仅限关键字；0单次检查，正数有限超时。当前SDK支持None和数字字符串
转换，负数（包括-1）及非数字被InvalidParamsError拒绝。高层方法没有返回注解，脚本
通过真实调用检查返回LocateResult类型。

成功场景已验证found=True、物理边界与原生一致、诊断字段类型正确，读取不改变last_result。
未找到场景的预期是found=False且不保留旧有效边界；本轮实际抛异常，尚未验证通过。

## 运行场景

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_locate.py --non-interactive
```

前置：dev及Win32靶场运行，启用 `D:\code\元素库\260902_win元素`。
脚本自动切换拖拽页，使用：

- `win32靶场_拖拽测试_可拖拽元素`：定位目标。
- `win32靶场_拖拽测试_隐藏_drag-target`：按钮实际调用DestroyWindow。
- `win32靶场_拖拽测试_重置位置`：重新创建目标。

IsWindow独立核验目标销毁，GetWindowRect提供成功定位的边界参照。重建后重新获取
SDK对象，不要求旧对象自动绑定新控件。结束恢复目标到默认位置、恢复鼠标并关闭Package。
不恢复测试前自定义拖拽位置。脚本不使用剪贴板，也不关闭靶场。

## 本次真实结果

原目标句柄68150，物理边界 `(2364,569,120,80)`。成功定位返回
`found=True`、`rect={'x':2364,'y':569,'w':120,'h':80}`、`strategy='win'`、空trace。

| 序号 | 场景 | 结果 |
| --- | --- | --- |
| 01 | API合同 | PASS |
| 02 | SDK与原生目标准备 | PASS |
| 03–07 | 默认、0、0.5、None、'0.5'超时下成功定位 | PASS |
| 08 | 连续三次定位，边界与原生一致 | PASS |
| 09–11 | 负数、非数字超时及位置传参拒绝 | PASS |
| 12 | 点击隐藏按钮，原生确认原句柄失效 | PASS |
| 13 | 原对象locate(timeout=0)，预期未找到结果 | FAIL：RpcProtocolError，1.0ms |
| 14 | 原对象locate(timeout=0.3)，预期未找到结果 | FAIL：RpcProtocolError，0.5ms |
| 15 | 重建后新对象定位成功，边界正确 | PASS |
| 16 | 必要资源清理 | PASS |

两项失败的原始错误均为：

```text
internal:COMError:(-2147220991, '事件无法调用任何订户', (None, None, None, 0, None))
异常: RpcProtocolError
```

汇总14/16通过，总耗时2569.3ms，退出码1。因此保持READY_FOR_LIVE，不能记为VERIFIED。

原前台为终端窗口131974，自动恢复返回False，实际前台为靶场2951616。
按已同意的non-interactive规则，焦点失败只记警告，不等待人工；必要清理通过不代表
终端焦点已恢复。两项API失败与焦点警告分开记录。

## 缺陷与复测要求

已补充到 [Issue #53](https://github.com/uiautoma/desktop/issues/53#issuecomment-5594288020)。
表现与exists()销毁后异常一致，可能涉及同一失效引用路径，确切抛错位置和根因仍待开发确认。

复测需确认目标存在时定位成功、销毁后原对象返回未找到状态、重建后新对象成功，以及
场景和必要资源恢复。不能将所有COM、权限或通信错误一律吞成未找到。
未覆盖等待过程中动态重现、跨进程或旧对象重绑定。产品源码未因本次测试或证据记录而修改。
