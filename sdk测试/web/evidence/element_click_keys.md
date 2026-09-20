# WebElement.click() 点击靶场验收记录

## 当前结果与证据来源

**VERIFIED（本轮覆盖范围）：62/62 检查通过，0 项 BLOCKED，0 项 FAIL；退出码 0，总耗时 33417.3ms。**

登记日期：2026-09-19。依据用户本轮提交的完整终端输出登记，替代此前 61/62 的部分完成状态。真实 Win 键的点击事件及剪贴板日志已共同核对通过，原剪贴板 5 个格式也已恢复并逐项读回核验。

本轮原始输出中的生命周期仍为 READY_FOR_LIVE，这是脚本运行时的待验收标记；保留原日志原文，收到完整结果后在本记录和两处索引中登记为 VERIFIED。未修改日志中的状态文本来制造通过证据。

- [本轮完整终端输出归档](artifacts/element_click_keys_20260919.txt)：来自用户附件，只统一换行并补齐末尾换行，保留附件折行空格。
- [此前 61/62 阻塞片段及用户确认归档](artifacts/element_click_keys_blocked_20260919.txt)。
- 独立脚本：[test_web_element_click_keys.py](../test_web_element_click_keys.py)。
- 靶场：[keys-click-test](https://baobaomi900901.github.io/xpath/#/keys-click-test)。
- 元素库：260902_web元素，测试使用临时副本。
- 只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。SDK 从该检出导入；实测日志未提供 Runtime 二进制版本。
- 本记录来自用户一次完整复测，未声称 agent 运行了完整浏览器验收或连续三轮全通过。

## 用途与合同

```python
element.click(
    *, button: str = 'left', simulative: bool = True,
    keys: str = 'none', delay_after: float = 1,
    move_mouse: bool = False, anchor: object | None = None
) -> None
```

单击当前元素，成功返回 None。button 支持 left/right；keys 支持 none/alt/ctrl/shift/win；simulative 和 move_mouse 要求布尔值。anchor 支持位置字符串、元组或字典，真实鼠标路径按锚点定位；本轮 DOM 路径的锚点忽略行为已检查。

delay_after 默认 1 秒，允许 0 和 None 不附加等待。当前实现先执行点击再校验动作后延时，因此非法 delay_after 可能在点击已发生后抛出 InvalidParamsError。本轮分别核对异常和已发生的点击，不将它误写为动作前拒绝。

## 测试目标与独立参照

| 库元素后缀（前缀为 web靶场_测试点击_） | DOM id | click() 场景 |
| --- | --- | --- |
| 单击触发 | btn-click-target | 单击、辅助键、两种执行方式与延时 |
| 双击触发 | btn-dblclick-target | 单次 click，不要求触发 dblclick 日志 |
| 右键触发 | btn-rightclick-target | 右键 contextmenu 事件 |
| 测试九宫格按钮 | position-grid-panel | 九宫格位置、锚点形式和随机点 |
| 测试hover | hover-target | click 到达；真实鼠标附带 hover 日志 |
| 测试focus | focus-target | click 到达；真实鼠标附带 focus 日志 |
| 读取最近一条点击记录 | btn-copy-latest-keys-log | 复制待验证日志，不以 focus 目标代替 |

准备阶段先通过元素库定位，再核对目标 DOM id；捕获点在内部节点时，沿有限父级链取得对应控件。每项动作前清空靶场记录、写入唯一剪贴板哨兵、重新开启临时事件监听。

实际效果通过两个来源核对：原生 DOM 事件监听记录目标、类型、鼠标键、辅助键、isTrusted 和坐标；靶场复制按钮生成 JSON，由 Windows CF_UNICODETEXT 独立读回。要求剪贴板哨兵被替换，复制前后最近记录的 key 不变，避免旧日志或复制动作污染结果。

九宫格方位根据事件 clientX/clientY 与面板矩形独立计算。offsetX/offsetY 则与原事件字段比较，它们可能相对内部格子或 span，不作为面板相对坐标。

## 本轮结果摘要

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01–06 | 合同、原生状态、库副本、页面、元素与观察器 | PASS；保存了原剪贴板 5 个格式，七个库元素已核对 DOM id |
| 07–11 | 默认点击及真实鼠标 none/alt/ctrl/shift | PASS；一次 click，按键和辅助键正确，isTrusted=True，剪贴板日志一致 |
| 12 | 真实鼠标右键 | PASS；一次 contextmenu，button=2，剪贴板日志一致 |
| 13–15 | 真实鼠标点击双击/hover/focus 区域 | PASS；均观察到一次 click；双击区域没有误触发 dblclick，另两项的附带日志正确 |
| 16–21 | DOM none/alt/ctrl/shift/win 及右键 | PASS；辅助键正确，isTrusted=False，剪贴板日志一致 |
| 22–24 | DOM 点击双击/hover/focus 区域 | PASS；一次 click，不要求生成 dblclick/hover/focus 日志 |
| 25–27 | None 延时、正数延时、move_mouse=True | PASS；delay_after=0.2 的调用耗时 246.9ms；move_mouse=True 点击及日志正确 |
| 28–36 | 九宫格九个位置 | PASS；均命中预期方位，原生事件坐标与靶场日志一致 |
| 37–40 | 字符串、字典、随机锚点及 DOM 忽略锚点 | PASS；本轮随机点位于 left-(左)；DOM 模式命中中心 |
| 41–42 | 非法 delay_after | PASS；实际点击已发生，之后按当前实现抛出 InvalidParamsError |
| 43–54 | 非法参数及调用边界 | PASS；异常类型正确，未产生目标事件或靶场记录 |
| 55 | 非法调用后的可用性 | PASS；再次正确单击并核对剪贴板日志 |
| 56 | 真实鼠标 keys=win | PASS；点击事件与原日志均正确；恢复焦点后完成复制核验 |
| 57–60 | 观察器、页面、Package、临时副本清理 | PASS；监听移除，本次页面按唯一 URL 枚举确认无残留，Package 关闭，副本删除并核对 |
| 61 | 剪贴板恢复 | PASS；原有 5 个格式恢复并逐项读回核验，包括原文本/HTML（如有） |
| 62 | 输入状态恢复 | PASS；辅助键已释放、鼠标位置已恢复；原前台未恢复，仅记警告 |

默认 delay_after=1 的本轮调用耗时为 1123.9ms。上述耗时仅为本轮观测，不作为性能承诺。

## 真实 Win 键阻塞的本轮处理结果

本轮 mouse_keys_win 用例总耗时 715.7ms，其中被测 click() 调用耗时 118.2ms。日志记录：

```text
返回 None
独立事件：click、button=0、keys=win、trusted=True
剪贴板：btn-click-target/click/win/真实鼠标
焦点已恢复并核验，原日志未变
恢复过程诊断：ActionError / activate_tab_failed
trace_id=abc6cdbad9734207998a89abd10b1325
```

焦点恢复过程中的 page.activate() 曾报告 activate_tab_failed，但脚本随后独立核对 document.hasFocus() 已为 True，且待验证记录的 key 未变，之后复制和 JSON 对比成功。因此本项通过依据是实际焦点状态和原日志核验，不是忽略异常或降低判据。

脚本只允许重试复制，未重新执行被测 Win 点击。本轮日志没有“仅重试复制一次”或本机回退发送 Esc 的记录，不宣称本轮实际使用了这些分支。此次通过也不表示 WebBrowser.activate() 的错误返回已修复。

先前阻塞属于测试脚本未处理点击后的焦点条件，已在本轮完成验证；本次没有修改 SDK 或 Runtime 产品源码。

## 修订与复测经过

最初真实 Win 用例位于普通矩阵中间，之后的用例因 activate_tab_failed 无法进入被测点击。脚本将真实 Win 移至全部普通场景、参数检查和 after_invalid 之后，其后只执行清理；DOM win 保留在普通矩阵。

此前完整输出为 60/62：真实 Win 复制验证阻塞，剪贴板恢复失败。清理逻辑原先持有 OLE IDataObject 引用，未复制各格式实际数据；改为测试前保存支持格式的字节，结束后恢复并逐项核对后，用户确认达到 61/62，仅剩真实 Win 复制验证阻塞。该阶段片段保留在历史归档中。

本轮补充了复制前焦点恢复、浏览器窗口身份核对及原日志 key 核对，最多重试一次复制。完整实测达到 62/62，生命周期由 READY_FOR_LIVE 登记为 VERIFIED。

## 范围与限制

九宫格边角使用向内偏移，避免命中圆角外部；未验收所有无偏移边角、精确物理像素偏移或鼠标轨迹形状。测试双击、hover、focus 区域时只验收 click()，不是对 dblclick()/hover()/focus() 的专项验收。

本轮实际恢复了 5 个剪贴板格式，不代表任意格式均支持。脚本遇到无法无损保存的格式会在改写剪贴板前阻塞。

测试页焦点恢复与清理时恢复用户原前台是两个不同检查：前者本轮成功并完成 Win 日志核验，后者本轮仍为“前台未恢复（警告）”。不把这条警告描述为原前台已恢复。

本次为 Chrome 场景；未覆盖 Edge、静默页面模式、所有 DPI/缩放组合或页面失效后的点击行为。

旧场景证据仍见 [click.md](click.md)，其历史记录保留；本次结论以本文件及本轮 62 项完整输出为准。

## 复测命令

在 sdk测试 目录运行：

```powershell
uv run .\web\test_web_element_click_keys.py
```

只检查合同，不连接浏览器或改写剪贴板：

```powershell
uv run .\web\test_web_element_click_keys.py --contract-only
```
