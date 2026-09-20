# `uiautoma.web.WebElement.focus()` keys-click-test 验收证据

## 当前结论

**VERIFIED：15/15 项通过，0 项失败，退出码 0。**

登记日期：2026-09-20。结果依据用户在 Chrome 中运行独立脚本后粘贴的完整终端结果；本记录不声称 agent 在本轮重新运行了浏览器验收。

- [本轮终端输出归档](artifacts/element_focus_keys_20260920.txt)
- [独立测试脚本](../test_web_element_focus_keys.py)
- [测试靶场](https://baobaomi900901.github.io/xpath/#/keys-click-test)
- 元素库：`D:\code\元素库\260902_web元素`
- 测试元素：`web靶场_测试点击_测试focus`
- 复制元素：`web靶场_测试点击_读取最近一条点击记录`
- 只读源码快照：`D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`

## 合同与验证范围

```python
element.focus(*, timeout: float = 5.0) -> None
```

本轮覆盖公开签名、默认和显式超时、`timeout=None`、重复调用、非法超时、位置参数和未知关键字参数。所有正向调用均返回 `None`；负数和非数字超时按预期拒绝。

脚本使用独立 DOM `focusin` 监听器核对事件次数和目标，并读取 `document.activeElement`；随后点击靶场复制按钮，通过剪贴板 JSON 独立核对最近一次记录。这样期望值不由 SDK 返回值生成。

## 实测结果

| 用例 | 结果 | 实测摘要 |
| --- | --- | --- |
| `api_contract` | PASS | `timeout` 仅限关键字，默认 `5.0`，返回 `None` |
| `page_and_elements` | PASS | 页面、元素库和两个目标元素已准备，DOM id 已核对 |
| `focus_default` | PASS | `focusin` 1 次，`activeElement=#focus-target`，剪贴板记录目标为 `focus-target` |
| `focus_keyword` | PASS | 显式超时调用成功，返回 `None` |
| `focus_none_timeout` | PASS | `timeout=None` 调用成功 |
| `focus_repeat` | PASS | 重复调用成功，事件与活动元素均正确 |
| `negative_timeout` / `negative_fraction` | PASS | 负数超时被 `InvalidParamsError` 拒绝 |
| `nonnumeric_timeout` | PASS | 非数字超时被 `InvalidParamsError` 拒绝 |
| `positional_timeout` / `unknown_keyword` | PASS | 分别被 `TypeError` 拒绝 |
| `after_invalid` | PASS | 非法参数测试后仍可正常聚焦 |
| 清理 | PASS | 页面、Package 和临时元素库副本均已清理 |

本轮浏览器实际记录的正向事件为 `trusted=True`，并且 `clickSource=真实鼠标`。这是浏览器/扩展实际返回的事件属性；脚本按实测布尔值核对来源，不把 `isTrusted` 硬编码为 `False`。此前一次 10/15 的失败来自测试脚本错误地要求 `isTrusted=False`，修正判据后本轮 15/15 通过。

## 边界与限制

本轮只覆盖 Chrome、指定 focus 按钮和当前靶场；未覆盖 Edge、CEF、Auto、静默运行、失效页面以及不同 DPI/缩放组合。剪贴板读取包含短暂权限失败重试；这不改变目标 API 的结果。

## 复测命令

```powershell
uv run .\web\test_web_element_focus_keys.py
```

仅检查公开合同：

```powershell
uv run .\web\test_web_element_focus_keys.py --contract-only
```
