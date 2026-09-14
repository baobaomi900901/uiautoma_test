## 缺陷

`Win32Element.long_press(seconds=0, delay_after=0)` 在Runtime中将零值回退为默认1秒，未保留调用者明确指定的零时长。

## 复现与证据

前置：UIAutoma dev运行，启用测试元素库，Win32靶场拖拽页中的可拖拽元素已定位。

```python
element.long_press(seconds=0, delay_after=0)
```

测试者执行本地 `win32/test_win32_long_press.py`。第08/31项该调用耗时1101.3ms，其他0.2秒用例的原生按住时长约192–216ms。资源清理通过，焦点由人工切回原Tabby窗口并核验。

旧脚本因允许零时长事件未被采样，仅检查成功返回及最终释放，将此项误判PASS。旧汇总31/31不能作为零时长合同已验证的证据。本次日志没有打印零时长的原生按住时长，1101.3ms是整个调用耗时，不能冒充实测按键持续时长。

## 源码原因

- SDK `_core/client.py` 的 long_press 将 seconds 转为float，拒绝负数但允许0，并正确发送 seconds=0.0。
- `runtime/services/action_service.py` 的 `_run_pointer_action()` 在调用 `_perform_mouse()` 时使用：

```python
seconds=float(params.get("seconds") or 1.0)
```

- 0.0为假值，因此变成1.0，再传入鼠标long_press路径。这与调用耗时约1.1秒一致。

## 预期与验收

- 显式0保留为0，不添加默认1秒等待；缺省值仍按接口默认1秒处理。
- 修复应区分缺失/None与合法数值0，保持负数拒绝规则。
- 加入RPC到鼠标后端的传参回归：seconds=0时后端收到0；正数、缺省值分别正确。
- 真实测试用原生按键采样核验。零时长可快于采样周期，但若捕获到明显持续按压应判失败。

本地测试脚本已补强零时长检查：没有采到瞬时事件时仍允许；捕获到事件时要求一次完整按住/释放、持续不超过80ms（测试容差，不是新增API参数）。用离线事件验证可拒绝1000ms按住；修订后的真实UI复测尚待执行。

产品源码未修改。本issue记录产品零值处理缺陷，同时披露旧测试的漏检，不将旧PASS写成完整验收。
