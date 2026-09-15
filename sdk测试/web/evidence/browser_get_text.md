# `WebBrowser.get_text()` 初次测试

## 用途

读取整个网页的可见文本；它与 `WebElement.get_text()` 不同，后者只读取指定元素文本。

## 真实验收结果

**VERIFIED：7/7 通过，退出码 0。**

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无公开参数，返回整页文本字符串 |
| 页面准备 | 通过，成功创建 `WebBrowser` |
| 整页文本 | 通过，与独立 DOM `document.body.innerText` 一致 |
| 重复读取 | 通过，结果稳定 |
| 刷新读取 | 通过，刷新后整页文本保持一致 |
| 参数边界 | 通过，额外位置参数被 `TypeError` 拒绝 |
| 资源清理 | 通过，测试页面已关闭 |

测试页面：`https://baobaomi900901.github.io/xpath/#/element-html-test`
测试脚本：`web/test_web_browser_get_text.py`
