# `uiautoma.web.WebElement.get_html()`

读取当前网页元素自身的 HTML（元素自己的 `outerHTML` 序列化结果）。

本页描述当前源码合同；实机验收结论见[验证证据](../../../tests/SDK/web/evidence/get_html.md)。

## 签名

```python
WebElement.get_html() -> str
```

## 返回值

``str``：元素自身的 HTML —— 包含元素自己的标签、属性、全部后代，也包含注释节点。
没有内容时返回空字符串，不会返回 ``None``。

## 行为要点

- 范围是**元素自身**，不是整页 HTML；读整页请用 `WebBrowser.get_html()`。
- 属性按 DOM 的解析顺序序列化，**不是**元素库捕获时记录的顺序，不要按捕获顺序做断言。
- 属性值里的 `&` 在返回串中写作 `&amp;`；需要原始（未转义）值时用 `get_attribute()`。
- 元素必须由当前页面的 `find` / `find_all` 取得的**实时引用**；页面刷新或关闭后原引用失效。

## 异常

- **ActionError**：元素已失效或读取失败。

## 使用与复核

当前调用示例见[SDK 最小示例](../../../docs/SDK设计方案/UIAutoma%20SDK%20API%20最小示例参考.md)和[Web 示例目录](../../examples/README.md)。

通过网页的 `find`、`find_by_css` 或 `find_by_xpath` 获取当前元素后调用。

当前基线（`c101caa9`，2026-09-20）已在真实 Chrome 与真实库元素上复验通过，
记录、边界与修订说明见[验证证据](../../../tests/SDK/web/evidence/get_html.md)。
