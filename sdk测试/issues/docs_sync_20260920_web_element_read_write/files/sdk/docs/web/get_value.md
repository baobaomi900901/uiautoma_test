# `uiautoma.web.WebElement.get_value()`

获取网页元素当前的值（DOM 的 `value` property）。

本页描述当前源码合同；实机验收结论见[验证证据](../../../tests/SDK/web/evidence/get_value.md)。

## 签名

```python
WebElement.get_value() -> str | None
```

## 返回值

``str | None``：元素的当前值。**空字符串与 ``None`` 语义不同，不要混用**：

- 元素存在但内容为空 → ``""``（空字符串）；
- 元素没有 ``value`` property（例如 ``<label>``、``<div>``）→ ``None``。

## 行为要点

- 读的是 DOM 的 **property**，不是 HTML 的 `value` 内容属性。因此它反映的是**当前**值，
  包含用户或脚本刚刚写入的内容，而不是页面初始的 `value="…"`。
- `<input type="range">` 的初始值不是空字符串，而是 `"0"`。
- 不要用 `get_attribute("value")` 当内容属性的对照：属性读取在属性不存在时会回退到同名
  property，两者会被混同，看起来「属性也有值」。
- 元素必须由当前页面的 `find` / `find_all` 取得的**实时引用**；页面刷新或关闭后原引用失效。

## 异常

- **ActionError**：元素已失效或读取失败。

## 使用与复核

当前调用示例见[SDK 最小示例](../../../docs/SDK设计方案/UIAutoma%20SDK%20API%20最小示例参考.md)和[Web 示例目录](../../examples/README.md)。

通过网页的 `find`、`find_by_css` 或 `find_by_xpath` 获取当前元素后调用。

当前基线（`c101caa9`，2026-09-20）已在真实 Chrome 与真实库元素上复验通过，
记录、边界与修订说明见[验证证据](../../../tests/SDK/web/evidence/get_value.md)。
