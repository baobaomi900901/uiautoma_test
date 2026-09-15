# `WebBrowser.activate()` 初次测试

## 用途

激活当前网页标签页及其所在的浏览器窗口，使该页面成为当前活动页面。

## 真实验收结果

**VERIFIED：6/6 通过，退出码 0。**

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，无公开参数，返回 `None` |
| 页面准备 | 通过，成功创建独立测试页面 |
| 返回值 | 通过，`activate()` 返回 `None` |
| 活动页面核对 | 通过，`get_active()` 返回页面 ID 匹配 |
| 重复激活 | 通过，连续两次调用成功 |
| 资源清理 | 通过，测试页面已关闭并尝试恢复原活动页面 |

测试页面：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
测试脚本：`web/test_web_browser_activate.py`
