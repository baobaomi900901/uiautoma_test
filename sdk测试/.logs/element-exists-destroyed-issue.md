## 缺陷

`Win32Element.exists()` 在目标控件销毁后，对原有元素对象查询时抛出内部 COM 错误及 RpcProtocolError，没有返回预期的 False。

这是原生控件确实被销毁的场景，不是遮挡、移出屏幕或仅 ShowWindow 隐藏。

## 真实复现

UIAutoma dev与Win32靶场运行，当前启用测试元素库。测试脚本：

```powershell
uv run .\win32\test_win32_element_exists.py --non-interactive
```

步骤：

1. 获取 `win32靶场_拖拽测试_可拖拽元素`，原生目标句柄334074；默认及显式超时查询均返回True。
2. 点击 `win32靶场_拖拽测试_隐藏_drag-target`。靶场源码中此按钮实际调用DestroyWindow。
3. 原生IsWindow确认334074失效。
4. 保持原SDK element对象，分别调用 `element.exists(timeout=0)` 与 `element.exists(timeout=0.3)`。
5. 点击 `win32靶场_拖拽测试_重置位置` 重建，重新获取的新元素返回True，原生新句柄399610。

两次缺失检查的实际错误均为：

```text
internal:COMError:(-2147220991, '事件无法调用任何订户', (None, None, None, 0, None))
异常: RpcProtocolError
```

预期：对于已经确认销毁、无法定位的目标，exists返回bool False，不泄漏内部COM异常。
不要求原对象在重建后自动绑定新控件。

## 测试结果

2026-09-08测试者日志：14/16通过，总耗时2625.8ms，退出码1。
失败项13/16“移除后零超时”和14/16“移除后有限超时”，耗时分别1.2ms与0.5ms。
重建及必要清理通过。自动模式焦点未恢复仅记警告，与这两个API错误无关。

本地脚本当前SHA-256：e5d0613bdad8de0173c0414fcd9b80bb9db8c3558fe566dcdea8a9c2973e1fd0。
该哈希为提交issue时快照，运行时哈希未随日志提供。

## 已确认的相关源码路径

- `sdk/src/uiautoma/win32/element.py::Win32Element.exists()` 委托原始SDK元素，公开返回bool。
- `runtime/services/action_service.py::exists_element()` 对带element_ref的运行时对象先调用 `_read_win_value(..., op="get_text")`，失败结果继续走locate_element；定位错误非零时直接返回错误。
- `runtime/bridge/worker.py` 的读取及运行时引用处理存在将捕获异常包装为 `internal:<异常类型>:...` 的分支。

日志确认内部COM错误到达调用者，但尚无完整调用栈确定具体抛错语句。请开发补充诊断并定位失效引用的分类/处理缺口。

## 建议验收

- 真实控件：存在True → DestroyWindow确认销毁 → 原对象exists False → 重建后新对象True。
- 覆盖timeout=0及有限正数；不以隐藏代替销毁。
- 对可识别的目标销毁/元素不可用情况正确返回False；其他COM故障、权限错误和通信失败不能一律吞成False。
- 检查失效引用的重新定位路径，保留可诊断错误，不向用户误报为RPC协议损坏。
- 增加聚焦回归测试，并由测试者复跑当前16项，确保目标恢复及连接清理成功。

本次仅提交缺陷，未修改产品代码；该API保持READY_FOR_LIVE。
