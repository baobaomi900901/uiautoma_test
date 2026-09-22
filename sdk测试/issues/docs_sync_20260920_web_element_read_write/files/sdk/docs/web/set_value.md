# `uiautoma.web.WebElement.set_value()`

设置当前网页元素的值（DOM 的 `value` property），不改变输入焦点，也不触发输入事件。

本页描述当前源码合同；实机验收结论见[验证证据](../../../tests/SDK/web/evidence/set_value.md)。

## 签名

```python
WebElement.set_value(value: str) -> None
```

## 参数

- **value**：需要设置到网页元素上的值，类型为 ``str``。非字符串会先做 ``str()`` 转换，
  因此传 ``None`` 写入的是字符串 ``"None"``，**不是清空**；清空请传空字符串 ``""``。

## 返回值

``None``。

## 行为要点

- **只写 property：不聚焦元素，也不触发 `input` / `change` 事件。** 直接后果是受控表单
  （React、Ant Design 等）的框架状态**不会更新**——页面自己的校验、联动、字数统计不会运行，
  页面自己的「提交」也读不到这个值。需要页面感知这次写入时，请改用真实输入，例如
  `input()` 或 `clipboard_input()`。
- 写入是**覆盖**，不是追加；公开签名没有追加开关。
- 换行按浏览器规则处理：`<input type="text">` 会去掉换行，`<textarea>` 会保留换行。
- 在非输入元素（如 `<label>`）上调用不会报错，但只会在该节点对象上产生一个临时属性，
  **不进入 DOM**，也不会出现在 `get_html()` 里。
- 元素必须由当前页面的 `find` / `find_all` 取得的**实时引用**；页面刷新或关闭后原引用失效。

## 异常

- **ActionError**：写入失败，例如页面已失效。

## 使用与复核

当前调用示例见[SDK 最小示例](../../../docs/SDK设计方案/UIAutoma%20SDK%20API%20最小示例参考.md)和[Web 示例目录](../../examples/README.md)。

通过网页的 `find`、`find_by_css` 或 `find_by_xpath` 获取当前元素后调用。

当前基线（`c101caa9`，2026-09-20）已在真实 Chrome 与真实库元素上复验通过，
记录、边界与修订说明见[验证证据](../../../tests/SDK/web/evidence/set_value.md)。
