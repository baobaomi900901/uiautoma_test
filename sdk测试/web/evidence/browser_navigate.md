# `WebBrowser.navigate()` 初次测试

## 用途

在同一个 `WebBrowser` 页面对象上导航到指定 URL。`url` 为必填参数，`load_timeout`
仅限关键字传入，默认值为 20 秒；调用成功返回 `None`。

## 真实验收结果

**VERIFIED：14/14 通过，退出码 0。**

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，签名、默认超时和返回值符合源码 |
| 页面准备 | 通过，成功创建测试页面 |
| 初始状态 | 通过，初始 URL 可读且页面 id 非空 |
| 默认导航 | 通过，导航到第二页面后返回 `None`，页面 id 保持不变 |
| 关键字超时 | 通过，使用 `load_timeout` 关键字导航成功 |
| 无协议 URL | 通过，自动补充 `https://` 后导航成功 |
| 零等待 | 通过，`load_timeout=0` 返回 `None`，独立轮询确认最终 URL |
| 非法 URL | 通过，空白和 `None` 被 `InvalidParamsError` 拒绝 |
| 非法超时 | 通过，负数及非数字超时被 `ValueError` 拒绝 |
| 调用参数边界 | 通过，缺参、多余位置参数和未知关键字被 `TypeError` 拒绝 |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 复测

测试页面：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

脚本：[test_web_browser_navigate.py](../test_web_browser_navigate.py)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_navigate.py
```
