# `uiautoma.web.WebElement.hover()` keys-click-test 验收证据

## 当前结论

**VERIFIED：23/23 项通过，0 项失败，退出码 0。**

登记日期：2026-09-20。依据用户在 Chrome 中运行独立脚本后的完整终端结果登记；本记录不声称 agent 重新运行了用户这次验收。

- [本轮终端输出归档](artifacts/element_hover_keys_20260920.txt)
- [独立测试脚本](../test_web_element_hover_keys.py)
- [测试靶场](https://baobaomi900901.github.io/xpath/#/keys-click-test)
- 元素库：`D:\code\元素库\260902_web元素`
- 测试元素：`web靶场_测试点击_测试hover`
- 复制元素：`web靶场_测试点击_读取最近一条点击记录`
- 只读源码快照：`D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`

## 用途与合同

```python
element.hover(
    simulative: bool = True,
    delay_after: float = 1,
    anchor: object | None = None,
) -> None
```

三个参数允许位置或关键字传入，默认值分别为 `True`、`1`、`None`，成功返回 `None`。本轮覆盖真实鼠标悬停、脚本/插件模拟悬停、无等待、正数等待、锚点字符串/元组/字典/随机值，以及非法参数。

## 期望值与独立确证

脚本通过元素库定位目标元素和复制元素，并核对 DOM id：目标为 `hover-target`，复制按钮为 `btn-copy-latest-keys-log`。每次动作后点击靶场复制按钮，通过 Windows 剪贴板读取靶场 JSON，独立核对 `buttonId`、`eventType`、`clickSource`、`isTrusted` 和 `detectedKeys`。

真实鼠标用例要求 `source=真实鼠标` 且 `isTrusted=True`；`simulative=False` 用例要求 `source=JS/插件模拟` 且 `isTrusted=False`。`delay_after` 通过动作调用耗时核对。

锚点用例前，脚本先用真实鼠标把指针移到复制按钮，再进入目标元素。这样每个锚点动作都从目标元素外重新进入，避免只在同一元素内部移动而读到前一个悬停记录。

## 实测结果

| 范围 | 实测结果 |
| --- | --- |
| 合同、靶场、Runtime、元素库、页面和 DOM id | 全部通过 |
| 默认真实鼠标悬停 | `eventType=hover`，`source=真实鼠标`，`trusted=True` |
| `simulative=False`、`delay_after=None`、正数等待和重复调用 | 全部通过，脚本来源和等待边界符合预期 |
| 锚点字符串、元组、字典和随机值 | 全部通过，均为真实鼠标 `trusted=True` |
| 非法 `simulative`、`delay_after`、`anchor` 和未知关键字 | 全部按预期拒绝 |
| 位置参数调用 | 通过；源码合同允许位置参数 |
| 页面、Package、临时元素库 | 全部清理成功 |

用户第一次运行时锚点用例读到旧的脚本模拟记录，原因是测试脚本没有将指针移出目标元素；补充指针离开准备后，锚点用例全部通过。这是测试脚本判据/状态准备问题，不构成 SDK 缺陷证据。

## 范围与限制

本轮只覆盖 Chrome 和指定 keys-click-test 靶场；未覆盖 Edge、CEF、Auto、静默运行及全部 DPI/缩放组合。锚点验证了字符串、元组、字典和随机输入能产生正确真实鼠标悬停记录，不作逐像素坐标或轨迹形状验收。

## 复测命令

```powershell
uv run .\web\test_web_element_hover_keys.py
```

仅检查公开合同：

```powershell
uv run .\web\test_web_element_hover_keys.py --contract-only
```
