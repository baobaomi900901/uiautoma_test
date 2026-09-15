# `WebBrowser.get_html()` 初次测试

## 用途

读取整个网页的 HTML 源码；它与 `WebElement.get_html()` 不同，后者只读取指定元素的 `outerHTML`。

## 真实验收结果

**VERIFIED：8/8 通过，退出码 0。**

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无公开参数，返回 HTML 字符串 |
| 页面准备 | 通过，成功打开百度页面 |
| 当前网页对象 | 通过，通过 `get_active()` 获取当前页面 |
| HTML 读取 | 通过，非空且包含 html 根元素 |
| DOM 对比 | 通过，与 `document.documentElement.outerHTML` 一致 |
| 重复读取 | 通过，每次均为有效 HTML；允许百度动态内容变化 |
| 参数边界 | 通过，额外位置参数被 `TypeError` 拒绝 |
| 资源清理 | 通过，百度测试页面已关闭 |

测试页面：`https://www.baidu.com/`
测试脚本：`web/test_web_browser_get_html_baidu.py`
