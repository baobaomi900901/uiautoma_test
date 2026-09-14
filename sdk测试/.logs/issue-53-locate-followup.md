## 补充：Win32Element.locate() 也在控件销毁后泄漏同类异常（2026-09-09）

测试者执行：

```powershell
uv run .\win32\test_win32_locate.py --non-interactive
```

复现：获取靶场drag-target元素并成功定位，点击“隐藏_drag-target”按钮（实际DestroyWindow），原生IsWindow确认原句柄68150失效，再对销毁前获取的同一个SDK元素对象调用locate。

### 实际结果

第13/16项 `element.locate(timeout=0)` 与第14/16项 `element.locate(timeout=0.3)` 均失败：

```text
internal:COMError:(-2147220991, '事件无法调用任何订户', (None, None, None, 0, None))
异常: RpcProtocolError
```

两项耗时分别1.0ms和0.5ms。

预期：对于已确认销毁、不能定位的目标，返回表达未找到状态的LocateResult（found=False，无旧有效边界），而非泄漏内部COM异常或误报为RPC协议错误。

### 对照场景

- 销毁前，默认timeout、0、0.5、None、数字字符串及重复定位均通过。
- 成功结果：found=True，rect={x:2364,y:569,w:120,h:80}，strategy=win，trace_info为空；与原生GetWindowRect一致。
- 重置按钮重建控件后，重新获取的新元素locate(timeout=0)成功。
- 必要清理通过，目标已恢复；自动模式焦点未恢复仅记警告，与API失败无关。
- 汇总14/16通过，总耗时2569.3ms，退出码1，保持READY_FOR_LIVE。

请将本issue的验收范围同时覆盖exists()和locate()：已销毁目标分别返回False与未找到的定位结果。两者异常表现相同、涉及相关定位路径，但是否完全同一根因尚待开发确认。

仍需区分可识别的目标销毁/不可用与其他COM、权限、通信故障，不应将所有异常一律转换为未找到。测试者不要求旧元素对象在重建后自动绑定新控件。

本次仅补充真实测试证据，未修改产品代码。
