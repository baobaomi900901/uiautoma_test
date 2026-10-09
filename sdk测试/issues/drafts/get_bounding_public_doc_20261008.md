# `uiautoma.web.WebElement.get_bounding()`

获取网页元素的位置和尺寸，返回整数矩形。

## 签名

```python
WebElement.get_bounding(to96dpi: bool = True,
                        relative_to: str = "screen") -> dict[str, int]
```

## 参数

| 参数 | 默认值 | 含义 |
|---|---|---|
| to96dpi | True | 将位置和尺寸转换为 96 DPI 对应的像素值；False 保留原生物理像素 |
| relative_to | "screen" | "screen" 使用屏幕原点；"window" 使用浏览器原生客户区原点 |

两个参数都可以按位置或关键字传入。`window` 的客户区原点与网页内容 viewport 原点不同，坐标会包含浏览器工具栏对应的偏移。

## 返回值

包含 `x`、`y`、`width`、`height` 四项的 `dict[str, int]`。x/y 是指定参照系中的位置；width/height 是尺寸。

```python
# page 为已经获取的 WebBrowser，元素库连接已打开。
element = page.find("web靶场_表单测试_ant_输入框")

rect = element.get_bounding()  # screen，转换为 96 DPI
print(rect)

physical = element.get_bounding(to96dpi=False, relative_to="screen")
client = element.get_bounding(to96dpi=False, relative_to="window")
print(physical, client)
```

在 iframe/open Shadow 中的元素也先通过元素库或其他查找方法获取，再调用本方法。不要用网页 `getBoundingClientRect()` 的 CSS viewport 坐标直接代替 screen 或 window 坐标。

## 异常

- 非法 relative_to 抛 `InvalidParamsError`，消息为“relative_to 必须是 screen 或 window”。
- 关闭页面后使用旧元素抛 `ActionError`，trace 为 `stale_page_reference`。
- 关闭元素库连接后调用抛 `HostUnavailableError`，需要重新打开连接并获取元素。

## 真实验收（2026-10-08）

**VERIFIED：Chrome 原生窗口 96 DPI 范围，连续三轮各 38/38 PASS，退出码 0。**

测试页面：[iframe/open Shadow 表单](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。目标为保存于元素库的 Ant input，唯一命中真实节点。

独立参考由 DOM 原生矩形与 ctypes 读取的 Win32 主窗口、网页 viewport 原点和 DPI 推导。screen/window × to96dpi=False/True 四组合均通过，另覆盖默认参数、位置传参、iframe 内外滚动、小数尺寸、移出可视区的负 viewport 坐标和生命周期异常。

本轮采用静默自有标签，未发送系统输入或激活窗口。每轮标签数 6→6，源库未变、临时副本删除，样式/滚动和站点动态 ID 偏好均恢复。原始报告保留前台状态变化记录，不将“全部前台不变”作为结论。

### 已验证行为

- 返回四个整数；位置和尺寸与独立测量相同。
- window 坐标相对于原生客户区，包含工具栏对应的垂直偏移。
- 读取不会自动把移出 viewport 的元素滚回可视区，返回完整矩形。
- 重复读取不改变该测试元素的 value、焦点、滚动和样式。

### 验证范围

原生窗口 DPI=96、devicePixelRatio=1，所以 to96dpi=True/False 在本轮结果相同。**非 96 DPI 的实际换算、跨屏、浏览器缩放、Edge、跨域 iframe、closed Shadow、旋转或缩放的 iframe、隐藏/零尺寸元素未验收。**

本轮结论限于只读源码快照：desktop worktree `D:\code\desktop`、commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`；Provider worktree `D:\code\rust_uia`、commit `b700f9238134f57da83ab478a5ee55337ade1082`，以及实际运行的 dev Runtime/Chrome。未独立确认 Provider 二进制构建 commit。

历史 2026-08 的八字段/仅 screen 合同不适用于该快照；2026-10-04 因 Provider 不可用而 SKIPPED 的记录继续保留。本次通过不改写历史报告。

当前[验证证据](../../../tests/SDK/web/evidence/get_bounding.md)应随本交接一并同步；旧证据保留于历史归档。
