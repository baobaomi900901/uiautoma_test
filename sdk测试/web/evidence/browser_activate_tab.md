# `WebBrowser.activateTab()` 初次测试

## 用途

激活当前网页标签页及所在的浏览器窗口。调用方式为 `page.activateTab()`。

## 本轮验收结果

依据用户提供的真实运行输出登记：**VERIFIED（本轮脚本覆盖范围），6/6 通过，退出码 0。**

| 测试项 | 结果 |
| --- | --- |
| API 合同 | 通过，方法无公开参数 |
| 页面准备 | 通过，创建独立测试页面 |
| 返回值 | 通过，activateTab 返回 None |
| 活动页面核对 | 通过，调用后 get_active 返回的页面 ID 匹配 |
| 重复激活 | 通过，连续两次 activateTab 调用成功 |
| 资源处理 | 脚本报告通过：尝试关闭测试页面并恢复原活动页面 |

## 范围说明

- 原活动页面恢复只做了尝试，没有单独核验恢复是否成功。
- 当前脚本会忽略关闭/恢复阶段的异常，因此本条记录不额外宣称已独立证明页面关闭与焦点恢复。
- 本轮未专门构造后台标签页、不同浏览器窗口、最小化窗口等场景。
- 未记录逐项耗时和实际页面 ID，不能从此次终端输出补造这些数据。

## 复测

测试页面：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

脚本：[test_web_browser_activate_tab.py](../test_web_browser_activate_tab.py)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_activate_tab.py
```
