# `uiautoma.web.remove_all_auto_handle_popup()` 验证证据（2026-10-04）

> 最新验收：2026-10-05 已按指定真实 DOM Modal 与库关闭按钮完成规则移除，最后连续三轮 19/19 PASS、清理 4→4；见[新证据](remove_all_auto_handle_popup_20261005.md)。下文保留当时条件不足的历史结论及原始输出。

## 用途与合同

移除当前连接注册的所有网页弹窗自动处理规则。

```python
remove_all_auto_handle_popup() -> None
```

- 被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论只绑定该源码快照和本次 dev Runtime。
- SDK 入口：`sdk\src\uiautoma\web\__init__.py:488`。
- 调用链：web.popup.remove_all → ActionService.web_popup_remove_all → PopupRules.remove。
- 完整签名、默认值、docstring 与入口源码保存在 [合同快照](../remaining_web_contracts_20261004.json)。

## 真实验收结果

**SKIPPED（2026-10-04；1/2 PASS + 0 FAIL + 1 KNOWN；1 轮；退出码 0）**

页面：未打开页面（条件不满足，直接跳过）。
元素库：`D:\code\元素库\260902_web元素`；只使用临时副本。

| 轮次 | 结果 | 原始报告 |
|---|---|---|
| 1 | 1/2 PASS + 0 FAIL + 1 KNOWN；退出码 0 | [web_remove_all_auto_handle_popup_20261004_run1.txt](artifacts/web_remove_all_auto_handle_popup_20261004_run1.txt) |

## 期望值来源与独立确证

当前条件不满足，没有执行真实正向场景；仅自检公开签名与已读取的源码快照。 参数错误按冻结源码合同检查；具体覆盖见下表和原始报告。

| 用例 | 状态 | 期望/确证方法 |
|---|---|---|
| `api_contract` | PASS | 公开签名与只读源码快照一致 |
| `skip` | KNOWN | 需要真实正向场景 |

## 实测行为与边界

跳过原因：

- 缺少可观察自动关闭效果的 DOM 弹窗/关闭按钮，无法证明规则移除后的真实行为

本次仅验收报告列出的场景；未列出的浏览器模式、DPI、参照系、控件种类、超大输入、网络异常或原生交互路径均不宣称通过。SKIPPED 的合同检查通过不等于实际功能通过。

## 资源清理与复测

直接跳过，没有创建页面、库副本或弹窗。

当前唯一脚本：[test_web_remove_all_auto_handle_popup.py](../test_web_remove_all_auto_handle_popup.py)。旧日期入口已移除，复测运行新脚本；历史原始报告保留运行时记录。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_remove_all_auto_handle_popup.py
```

历史脚本退出码 0 表示无 FAIL（允许 KNOWN/跳过），1 表示存在 FAIL。当前脚本退出码 0/1/2 分别为通过/失败/阻塞；通过范围见顶部的新证据。
