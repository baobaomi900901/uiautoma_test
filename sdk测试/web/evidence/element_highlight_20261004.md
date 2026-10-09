# `uiautoma.web.WebElement.highlight()` 验证证据（2026-10-04）

> 历史记录，保留原始 SKIPPED 结论。当前入口为 [test_web_element_highlight.py](../test_web_element_highlight.py)，当前结果见 [2026-10-09 证据](highlight.md)。旧包装脚本已移至[历史目录](../../issues/highlight_history_20261009/README.md)。

## 用途与合同

高亮显示当前网页元素。

```python
highlight(self, duration: float = 1.0, delay_after: float = 0) -> None
```

- 被测 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。结论只绑定该源码快照和本次 dev Runtime。
- SDK 入口：`sdk\src\uiautoma\web\element.py:1105`。
- 调用链：web.action.highlight → ActionService.web_highlight_element → Provider 几何 → Win32 高亮覆盖窗口。
- 完整签名、默认值、docstring 与入口源码保存在 [合同快照](../remaining_web_contracts_20261004.json)。

## 真实验收结果

**SKIPPED（2026-10-04；6/8 PASS + 0 FAIL + 2 KNOWN；1 轮；退出码 0）**

页面：[靶场](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
元素库：`D:\code\元素库\260902_web元素`；只使用临时副本。

| 轮次 | 结果 | 原始报告 |
|---|---|---|
| 1 | 6/8 PASS + 0 FAIL + 2 KNOWN；退出码 0 | [element_highlight_20261004_run1.txt](artifacts/element_highlight_20261004_run1.txt) |

## 期望值来源与独立确证

计划用 ctypes 独立枚举 UIAutoma_HighlightWin32 窗口，观察出现/移除和持续时间；Provider 不可用，实际视觉正向验收跳过。 参数错误按冻结源码合同检查；具体覆盖见下表和原始报告。

| 用例 | 状态 | 期望/确证方法 |
|---|---|---|
| `api_contract` | PASS | 公开签名与只读源码快照一致 |
| `environment` | PASS | Runtime/Chrome/现有靶场与临时库可用 |
| `visible_overlay` | KNOWN | 独立 Win32 观察高亮窗出现并移除，持续时间与后置等待生效 |
| `zero` | KNOWN | duration=0 返回 None |
| `invalid_-1` | PASS | 非法 duration 抛 InvalidParamsError |
| `invalid_True` | PASS | 非法 duration 抛 InvalidParamsError |
| `invalid_nan` | PASS | 非法 duration 抛 InvalidParamsError |
| `cleanup` | PASS | 关闭本次页面和库、删除临时目录、复核标签和文件弹窗 |

## 实测行为与边界

跳过原因：

- 当前原生 Provider/浏览器窗口环境不可用，跳过此分支

本次仅验收报告列出的场景；未列出的浏览器模式、DPI、参照系、控件种类、超大输入、网络异常或原生交互路径均不宣称通过。SKIPPED 的合同检查通过不等于实际功能通过。

## 资源清理与复测

各轮 cleanup 均 PASS：仅关闭本次标签页和库连接，删除本次 UUID 临时目录；标签数 1→1，未留下本次文件对话框。原始库和用户原页面保留。

历史脚本：[test_web_element_highlight_20261004.py](../../issues/highlight_history_20261009/test_web_element_highlight_20261004.py)。当前运行命令如下，不会重放历史 SKIPPED 验收。

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\web\test_web_element_highlight.py
```

历史报告退出码 0 表示无 FAIL（允许 KNOWN/跳过），1 表示存在 FAIL；当前脚本退出码和覆盖以新证据为准。
