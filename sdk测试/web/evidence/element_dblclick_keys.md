# WebElement.dblclick() 双击靶场验收记录

## 当前结果与证据来源

**VERIFIED（本轮覆盖范围）：41/41 检查通过，0 项 BLOCKED，0 项 FAIL；退出码 0，总耗时 22395.0ms。**

登记日期：2026-09-20。依据用户提交的一次完整 Chrome 实测输出登记；未声称 agent 运行了本轮浏览器验收或连续三轮全部通过。

- [本轮完整终端输出归档](artifacts/element_dblclick_keys_20260920.txt)：来自用户附件，只统一换行并补齐末尾换行。
- 独立脚本：[test_web_element_dblclick_keys.py](../test_web_element_dblclick_keys.py)。
- 靶场：[keys-click-test](https://baobaomi900901.github.io/xpath/#/keys-click-test)。
- 元素库：260902_web元素，使用临时副本。
- 双击元素 DOM id：`btn-dblclick-target`。
- 复制元素 DOM id：`btn-copy-latest-keys-log`。
- 只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。

## 用途与合同

```python
element.dblclick(
    *, simulative: bool = True,
    delay_after: float = 1,
    move_mouse: bool = False,
    anchor: object | None = None
) -> None
```

四个参数仅限关键字；成功返回 None。anchor 支持位置字符串、元组和字典；当前 API 不接受 button、keys 或 timeout 参数。delay_after 的非法值在双击动作发生后由当前实现拒绝，本轮单独核对了这一顺序。

## 期望值与独立确证

脚本通过元素库定位双击按钮和复制按钮，并核对 DOM id。临时 DOM 监听器只观察 `click`、`dblclick` 事件的目标、顺序、鼠标键、坐标和 isTrusted；未用 SDK 返回值生成期望事件。

每个正向场景要求事件顺序严格为：

```text
click → click → dblclick
```

随后读取靶场“读取最近一条点击记录”写入的 JSON，并以 Windows 剪贴板独立通道核对目标、事件类型、来源、按键和时间。复制前后比较记录 key，避免复制按钮覆盖待验记录。

## 实测结果摘要

| 范围 | 实测结果 |
| --- | --- |
| 合同、元素库、页面、元素和监听器 | 全部通过；两个元素 DOM id 已核对 |
| 默认、显式真实鼠标、DOM 模拟双击 | 全部通过；均为两次 click 加一次 dblclick，返回 None |
| delay_after=None、0.2、move_mouse、重复双击 | 全部通过；0.2 秒调用实测 240.8ms |
| anchor 字符串、元组、字典、random、DOM 忽略锚点 | 全部通过；坐标在按钮范围内，中心/区域判据符合 |
| 非法 delay_after | 双击已发生后正确拒绝 |
| 非法类型、缺失/多余参数和不支持参数 | 全部按预期拒绝，未产生事件或靶场记录 |
| 剪贴板快照和恢复 | 原剪贴板 4 个可恢复格式逐项恢复并读回；忽略两个已知 Chromium 临时格式 |
| 资源清理 | 监听器、页面、Package、临时副本均清理成功；原前台恢复未成功，仅记录警告 |

第 05 项记录了：

```text
已复制原剪贴板 4 个格式的实际数据；
忽略已知 Chromium 临时格式：
49943 (Chromium internal source RFH token)
50051 (Chromium internal source URL)
```

这两个格式属于已知 Chromium 内部临时格式，脚本不把它们作为用户剪贴板数据恢复；未知私有格式仍会在改写前阻塞。

## 范围与限制

本轮只覆盖指定双击按钮，不是 dblclick、hover、focus 的专项验收。锚点覆盖中心、左上区域、右下区域和随机位置，不证明所有像素偏移或鼠标轨迹形状。

本轮为 Chrome 场景；未覆盖 Edge、静默运行、页面失效后的双击及全部 DPI/缩放组合。清理时原前台窗口未恢复是警告，不影响本轮页面、Package 和剪贴板清理通过。

## 复测命令

在 sdk测试目录运行：

```powershell
uv run .\web\test_web_element_dblclick_keys.py
```

仅检查合同：

```powershell
uv run .\web\test_web_element_dblclick_keys.py --contract-only
```
