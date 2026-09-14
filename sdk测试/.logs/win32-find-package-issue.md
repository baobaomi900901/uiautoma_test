## 缺陷

顶层 `win32.find(..., session=package)` 拒绝由公开 `uiautoma.current()` 返回的 Package。
错误提示却要求传入 `uiautoma.open()` 或 `uiautoma.current()` 返回的对象，公开用法与实现矛盾。

## 最小复现

前置：dev与Win32靶场运行，启用包含姓名输入框的元素库，表单页可见。

```python
import uiautoma
from uiautoma import win32

package = uiautoma.current(required=True, refresh=True, timeout=5)
try:
    selector = package.selector("win32靶场_表单控件_输入框_姓名", kind="win")
    element = win32.find(selector, session=package, timeout=0)
finally:
    package.close()
```

实际：`InvalidParamsError: session 必须是由 uiautoma.open() 或 uiautoma.current() 返回的对象`。
日志确认显式session类型为Package。
预期：接受公开Package，使用该Package的上下文查找，并返回匹配的Win32Element。

## 对照测试

本地脚本：`uv run .\win32\test_win32_module_find.py --non-interactive`。
默认session省略及显式None均成功；相同Selector的默认上下文调用成功。
姓名输入框source_element_id为df849752-32d7-46a0-9bec-7bcd6d0d7d7d，保存按钮同样可成功查找。
仅第07/17“显式Package上下文”失败。汇总16/17通过，总耗时1796.0ms，退出码1。
鼠标恢复与Package清理通过，焦点未恢复按自动模式记录警告，与API入参拒绝无关。

## 源码原因

`sdk/src/uiautoma/win32/__init__.py` 的 find 调用 `_package_session(session)`：

```python
package = session or get_package()
if not hasattr(package, "win_elements"):
    raise InvalidParamsError("session 必须是由 uiautoma.open() 或 uiautoma.current() 返回的对象")
return package
```

公开Package不直接具备win_elements方法；省略session时get_package()提供内部PackageSession。
因此默认调用可用，显式公开Package却被误拒绝。
find_all也使用同一辅助函数，建议开发检查其直接受影响行为；该接口尚无本轮实测结果，不能视为已复现。

## 验收要求

- 正确接受公开current()/open()返回的Package，通过内部适配取得会话，不要求用户传私有字段。
- 缺省和None保留当前上下文语义，显式Package确实使用指定上下文，而不是静默回退到全局上下文。
- 非法对象继续明确拒绝；关闭后的Package按已定义会话生命周期处理。
- 覆盖公开Package、默认上下文和非法session的SDK回归，并检查共用辅助函数的直接调用者。
- 复跑本地17项测试并验证必要清理通过。

当前状态READY_FOR_LIVE。本次仅提交缺陷，未修改产品代码。
