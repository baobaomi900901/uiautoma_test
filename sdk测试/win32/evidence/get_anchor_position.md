# `uiautoma.win32.Win32Element.get_anchor_position()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.get_anchor_position"
lifecycle: "VERIFIED"
verification_summary:
  tester_confirmed: true
  full_log_provided: true
  runs: 2
  passed_per_run: 34
  total_per_run: 34
  exit_code_per_run: 0
  display_scales: ["100%", "225%"]
persistent_script:
  path: "win32/test_win32_get_anchor_position.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "b50acf070a9cd27a38ecd15daa86c151eea3db5935694f15a12832e295a66adf"
  command: 'uv run .\win32\test_win32_get_anchor_position.py'
source_commit_at_doc_time: "2c28837e3ec2529b7cf3518943aac54dee8b6635"
source_commit_at_live_run: null
```

## 运行方式与前置条件

在 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_anchor_position.py
```

UIAutoma dev 和 Win32 靶场应已启动，当前启用元素库为
`D:\code\元素库\260902_win元素`。脚本通过 `win32靶场_tab_item拖拽测试` 切换页面，
读取 `win32靶场_拖拽测试_可拖拽元素`。运行期间保持鼠标与靶场窗口不动。

脚本使用 Per-Monitor v2，原生枚举唯一的 Button“drag-target”，通过 GetWindowRect
读取物理边界，通过 GetScaleFactorForMonitor 读取目标显示器缩放比例，独立计算预期值。
不操作剪贴板，不执行拖拽或重置位置。结束时恢复鼠标和原前台，关闭借用的 Package，
靶场保持运行并保留拖拽页。依赖同目录 get_value 测试中的 DPI、日志和原生辅助函数。

## API 参数和返回值

```python
get_anchor_position(
    *,
    anchor: object | None = None,
    to96dpi: bool = True,
) -> tuple[int, int]
```

- 两个参数均仅限关键字；没有公开 timeout 参数。
- anchor 默认 None，等价于 middleCenter。支持九宫格、random、三元组和字典偏移。
- to96dpi=False 返回物理屏幕像素；True 返回96 DPI逻辑坐标。
- 逻辑预期值按显示器倍率分别缩放并取整矩形 x/y/w/h，再计算锚点。偏移在对应的
  返回坐标系中相加。
- 返回 `(x, y)`，两项均为整数；读取不移动鼠标、不改变窗口或 last_result。
- 边缘锚点使用矩形边界，例如 bottomRight 为 `(x+w, y+h)`，不是点击动作内缩后的安全点。

## 两次真实运行结果

| 项目 | 100% 显示器 | 225% 显示器 |
| --- | --- | --- |
| 原生物理边界 | `(3003,343,120,80)` | `(2498,731,270,180)` |
| 96 DPI预期边界 | `(3003,343,120,80)` | `(1110,325,120,80)` |
| 物理中心 | `(3063,383)` | `(2633,821)` |
| 默认/逻辑中心 | `(3063,383)` | `(1170,365)` |
| 物理右下角 | `(3123,423)` | `(2768,911)` |
| 逻辑右下角 | `(3123,423)` | `(1230,405)` |
| 通过数 | 34/34 | 34/34 |
| 资源清理 | PASS | PASS |
| 退出码 | 0 | 0 |

以上预期坐标与 SDK 实际返回完全一致。两份日志都包含完整的01/34至34/34记录，
并由测试者明确确认。日志未输出总耗时，因此不补造总耗时。

## 覆盖矩阵

| 场景 | 验证内容 | 结果 |
| --- | --- | --- |
| API合同 | 参数顺序、仅限关键字、默认值、返回注解 | 两轮PASS |
| 默认参数 | 默认逻辑中心 | 两轮PASS |
| 物理/逻辑 None | 显式None中心 | 两轮PASS |
| 两种模式九宫格 | 九个锚点与原生边界计算结果逐点一致 | 两轮PASS |
| 三元组 | 中心偏移 `(6,-4)` | 两轮PASS |
| 字典 | 中心偏移 `(-6,4)` | 两轮PASS |
| 随机锚点 | 两种模式返回点在目标边界内 | 两轮PASS |
| 读取副作用 | 鼠标、原生边界和last_result不变 | 两轮PASS |
| 非法锚点名称/类型 | InvalidParamsError | 两轮PASS |
| 位置参数/timeout | TypeError | 两轮PASS |
| 清理 | 恢复鼠标/前台，关闭Package，保留靶场 | 两轮PASS |

225% 示例：三元组物理坐标 `(2639,817)`、逻辑坐标 `(1176,361)`；字典物理坐标
`(2627,825)`、逻辑坐标 `(1164,369)`。随机点分别为 `(2675,877)` 和 `(1120,399)`。

## 验证边界

仅确认本轮100%和225%环境下的结果，不外推为所有多显示器布局或缩放配置均正确。
未验证250%、运行中跨屏迁移、负坐标显示器、元素不可见/失效场景及随机分布统计质量。
运行时源码提交和脚本哈希未随日志提供，顶部版本信息仅为文档更新时的本地快照。
