# WebElement.find()

## 合同

`uiautoma.web.WebElement.find(self, selector: str | Selector, *, timeout: float = 10) -> WebElement`。

## 实测结果

- 靶场：`https://baobaomi900901.github.io/xpath/#/anchor-test`
- 元素库：`D:\\code\\元素库\\260902_web元素`（测试使用临时副本）
- 父元素：`web靶场_测试find_父级`
- 子元素：`web靶场_测试find_子级`
- 脚本：`web/test_web_element_find.py`
- 自动脚本：6/6 通过，退出码 0；连续 3 次运行通过。
- 人工复测：按同一命令运行通过。

## 覆盖

- 合同：`selector` 必填，`timeout` 关键字参数默认 10。
- 父元素内成功找到子元素，返回有效 `rt:web:` 运行时 ID。
- 缺失选择器在 `timeout=0` 下抛出 `ElementNotFoundError`。
- 页面关闭、临时元素库副本删除完成。

## 复测命令

```powershell
cd "D:\\code\\元素库\\sdk测试"
uv run .\\web\\test_web_element_find.py
```
