# `uiautoma.win32.Win32Element.drag_to()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.drag_to"
lifecycle: "VERIFIED"
verification_summary:
  passed: 38
  total: 38
  elapsed_ms: 50344.1
  exit_code: 0
  tester_confirmed: true
  full_log_provided: true
  evidence_basis: "最新38项完整日志及测试者确认；保留前次失败历史"
  log_limitation: "首次日志缺失末尾锚点明细；最新日志已补齐"
stability_issue:
  url: "https://github.com/uiautoma/desktop/issues/46"
  scope: "本地测试脚本剪贴板辅助流程"
  status: "OPEN; 未实现重试"
persistent_script:
  path: "win32/test_win32_drag_to.py"
  fingerprint_kind: "SHA-256 of file at documentation time; execution-time hash not supplied"
  fingerprint: "ae413be45337ec68cd3bc029efbaca244a443218b7263616483c18eb8579a6a9"
  command: 'uv run .\win32\test_win32_drag_to.py'
source_commit_at_doc_time: "3e273655516395c61542f5531202fb2bc529fef2"
source_commit_at_live_run: null
```

## 运行方式与场景

在 `D:\code\元素库\sdk测试` 中执行：

```powershell
uv run .\win32\test_win32_drag_to.py
```

前置：UIAutoma dev 运行，当前启用 `D:\code\元素库\260902_win元素`，Win32 靶场已启动。
先复制一段普通文本，脚本保存和恢复 Unicode 文本；其他剪贴板格式不在保护范围内。

使用以下元素切换页面、拖拽、读取 JSON 和重置：

- `win32靶场_tab_item拖拽测试`
- `win32靶场_拖拽测试_可拖拽元素`
- `win32靶场_拖拽测试_复制拖拽元素当前结果到剪切板`
- `win32靶场_拖拽测试_重置位置`

每例重置位置；每次复制前写入唯一标记，防止误读旧 JSON。JSON 位移与 SDK 物理边界
变化交叉核对。结束时重置至靶场默认中心，保留拖拽页，恢复鼠标、前台和普通剪贴板文本，
关闭借用的 Package。脚本复用同目录 get_value 和 clipboard_input 的辅助函数。

## API 合同

```python
drag_to(
    simulative: bool | None = None,
    behavior: str = "smooth",
    top: int = 0,
    left: int = 0,
    delay_after: float = 1,
    anchor: object | None = None,
    move_speed: str = "middle",
) -> None
```

七个参数均支持位置和关键字调用。`left` 为水平相对物理像素偏移，正数向右；`top`
为垂直相对偏移，正数向下；源码均调用 `int()` 转换。它们不是屏幕绝对目标坐标。

`simulative=None` 在当前实现中通过 `default_bool(..., default=True)` 得到 True；
显式 False 或 `behavior="instant"` 使拖拽请求时长为零。`behavior` 仅接受
`smooth`、`instant`。`move_speed` 接受 slow、middle、fast、instant，分别对应
0.6、0.25、0.1、0 秒的请求时长；这些不是整个 RPC 调用的耗时保证。

`anchor=None` 默认中心；支持九宫格名称、random、`(anchor, offset_x, offset_y)`
和包含这些字段的字典。`delay_after` 是动作后的秒数，None/0 不等待。
负数及非数字延时在动作完成后才被 InvalidParamsError 拒绝，不能视为未执行拖拽。

返回 None，更新 last_result。公开包装委托底层 drag_to，发送 `action.drag_element`；
`left/top` 映射为 `offset_x/offset_y`，锚点映射为 pt，速度映射为 duration。

## 本次覆盖与观察

| 场景 | 实际观察 | 证据范围 |
| --- | --- | --- |
| 默认与全位置参数 | 默认零位移；全位置参数位移 `(30, 20)` | 可见日志通过 |
| 正负及单轴位移 | JSON 折算与物理边界变化均符合输入 | 可见日志通过 |
| 非模拟、瞬时轨迹 | 移动一次，靶场 durationMs 为 0 | 可见日志通过 |
| 四档速度 | instant=16ms、fast=110ms、middle=266ms、slow=625ms | 靶场耗时区间及移动事件数断言通过 |
| 默认及显式锚点 | 三元组 `(66,44)`、字典 `(54,36)`、随机点在块内 | 可见日志通过 |
| 九宫格 | 第28项 `(60,78)` bottomCenter，第29项 `(118,78)` bottomRight；其余锚点通过 | 最新完整日志逐项通过 |
| None 与正数延时 | 配对无延时基线差值：None=2.4ms、0.2秒=205.3ms、默认1秒=1012.9ms | 配对延时断言通过 |
| 坐标转换 | `'30'` 与 `20.9` 转换为 `(30,20)` | 可见日志通过 |
| 非法轨迹、速度、锚点及坐标 | 动作前拒绝，位置和last_result未改变 | 可见日志通过 |
| 非法延时 | 拖拽30像素后抛出预期异常 | 可见日志通过 |
| 资源清理 | 清理项通过；位置重置，靶场保持运行 | 可见日志通过 |

日志初始物理边界为 `(2941, 400, 120, 80)`，靶场内部初始位置为 `(217, 167)`，
DPI 模式为 Per-Monitor v2（进程）。38/38、退出码0和资源清理通过，加上测试者明确确认，
最新成功运行记录为 VERIFIED。总耗时50344.1ms包含场景准备、配对调用、复制、重置及清理。

## 间歇性失败与后续复测

增强速度和延时断言后，曾出现一次失败：

- 第24/38项 middleLeft 在取得靶场结果时失败，剪贴板仍是本轮标记
  `drag-test-6033b0e0fda045798297cef205b54056`，未得到新的 JSON。
- 第38/38项清理失败：`剪贴板文本: OpenClipboard 失败：5`，该轮原文本未成功恢复。
- 该失败轮不能记为通过，也不足以判断 middleLeft 拖拽动作本身失败。

未修改脚本重跑后，38/38、退出码0、清理通过，总耗时50344.1ms。
第24项实际位移(30,0)、锚点middleLeft；第29项实际位移(30,0)、锚点bottomRight。
另外，第29项独立最小示例亦通过：锚点(118,78)、移动15次、靶场250ms、调用538.9ms，
资源清理通过。

已提交 [Issue #46：测试脚本剪贴板复制与恢复缺少限时重试](https://github.com/uiautoma/desktop/issues/46)。
确认的缺口在本地测试脚本：复制按钮仅点击一次，失败后只反复读取；恢复文本没有限时重试。
短暂占用是可能诱因，尚未确定占用者、复现频率或复制端失败的确切原因。
当前证据不支持将其定性为 drag_to 产品实现缺陷。

重跑通过仅证明该轮验收成功，不代表稳定性问题修复。重试功能尚未实施，失败历史继续保留。

## 验证限制

首次粘贴文本缺少第29项标题且第28项后接bottomRight明细，此为历史记录缺失。
第29项独立复测及最新完整38项日志已补充验证，不再作为最新一轮的缺失项。

本轮未提供高 DPI 拖拽复测日志；DPI 初始化的存在不等于本 API 已完成多倍率验收。
不覆盖跨窗口、跨显示器拖放和区域边界夹取。不会把 get_value 的多倍率结果移用到本 API。
运行时源码提交和脚本哈希未随日志提供，上述版本信息仅为文档更新时的本地快照。
