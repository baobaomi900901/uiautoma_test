# `uiautoma.web.WebElement.get_anchor_position()` 验证证据

## 当前结论（2026-10-08）

**VERIFIED（Chrome、96 DPI 范围）：连续三轮正式完整运行，每轮 76/76 PASS，退出码均为 0。**

- 靶场：[iframe/open Shadow 表单](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：`D:\code\元素库\260902_web元素`；元素：`web靶场_表单测试_ant_输入框`。每轮唯一命中 `INPUT#form-controls-ant-text`。
- desktop 只读 worktree：`D:\code\desktop`；commit：`7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- Provider 只读 worktree：`D:\code\rust_uia`；commit：`b700f9238134f57da83ab478a5ee55337ade1082`。
- 结论限于上述源码快照和实际 dev Runtime/Chrome；未独立确认正在运行的 Provider 二进制构建 commit。
- 默认 `silent_running=True`；未调用窗口激活、移动/恢复窗口或系统鼠标/键盘/剪贴板操作。Win32 测量的 DPI 感知设置仅作用于测试线程，收尾恢复。
- 每轮清理 PASS：标签 **8→8**，无外部增删；自有页面与库连接关闭、副本删除，源 elements.json SHA-256 不变；样式、滚动、动态 ID 开关及 localStorage 恢复。

| 正式轮次 | 结果 | 原始 UTF-8 日志 | 完整 JSON |
|---|---|---|---|
| 1 | 76/76 PASS，退出码 0 | [run1.txt](artifacts/element_get_anchor_position_20261008_run1.txt) | [run1.json](artifacts/element_get_anchor_position_20261008_run1.json) |
| 2 | 76/76 PASS，退出码 0 | [run2.txt](artifacts/element_get_anchor_position_20261008_run2.txt) | [run2.json](artifacts/element_get_anchor_position_20261008_run2.json) |
| 3 | 76/76 PASS，退出码 0 | [run3.txt](artifacts/element_get_anchor_position_20261008_run3.txt) | [run3.json](artifacts/element_get_anchor_position_20261008_run3.json) |

每轮 **53 次确定性坐标对照**，x/y 差值全部为 0；另有 4 组、每组 12 次真实随机调用，全部在独立预期范围内，每组实测 12 个不同点。有限样本仅确认范围和变化，不证明随机分布均匀。

前台观测按 53 次确定性调用和 4 组随机调用分别取前后状态：三轮稳定数为 **56/57、57/57、57/57**。第一轮一次由 HWND 527102 切到 723882，二者均不是测试 Chrome（6886240）；没有测量期间从其他窗口切到测试 Chrome 的记录。不推断外部切换原因，不宣称全部前台状态不变。

## 用途与合同

获取元素指定锚点的**屏幕坐标**，成功返回两个 int 组成的 tuple，不是元素边界字典或网页 viewport 坐标。

```python
get_anchor_position(self, *, anchor: object | None = None,
                     to96dpi: bool = True) -> tuple[int, int]
```

| 参数 | 当前合同与实测 |
|---|---|
| anchor=None | 元素中心，无偏移；默认调用和显式 None 均验收 |
| 固定位置 | top_left/top_center/top_right、middle_left/middle_center/middle_right、bottom_left/bottom_center/bottom_right；九种位置各覆盖两种 DPI 参数 |
| random | 在完整矩形内取随机点，可附偏移；不使用点击操作的 2 px inset |
| 字符串/元组/列表/字典 | 字符串位置、`(位置,dx,dy)`、列表和 `{anchor,offset_x,offset_y}`；字典省略位置、空列表也实测为中心 |
| 偏移 | 正 x 向右、正 y 向下，负值方向相反；含小数、超出边界的偏移，不截断到元素内部 |
| to96dpi=True | 对最终屏幕点按原生窗口 DPI 换算到 96 DPI；当前窗口为 96，True/False 相同，不能据此证明高 DPI 换算 |
| 参数位置 | anchor/to96dpi 均为关键字专用参数；位置传入 anchor 抛 TypeError |
| 返回值 | 精确检查 tuple、长度 2、两个值均为 int 且非 bool；JSON 归档中 tuple 按 JSON 数组保存 |

九个固定位置可 casefold，实测 `TOP_RIGHT` 正常；当前快照的 `RANDOM` 大写被拒绝。前后空格不自动去除。这里记录快照行为，不扩展为其他别名或输入形态的验收。

| 异常/失败路径 | 实测合同 |
|---|---|
| 不支持的位置、空字符串、带空格位置、错误元组/字典位置 | InvalidParamsError；消息包含“不支持的锚点” |
| 不支持的对象类型 | InvalidParamsError；`anchor 必须是 None、字符串、元组或映射对象` |
| 位置传参、未知关键字 relative_to | TypeError |
| 关闭自有页面后使用旧元素 | ActionError / stale_page_reference |
| 关闭库连接后使用元素 | HostUnavailableError；消息包含“连接已关闭” |

参数拒绝测试使用真实 SDK 方法及一个禁止 RPC 的本地边界哨兵，确认无效参数没有发 RPC；这些不是浏览器正向验收。Provider 不可用、几何元数据无效、RPC 协议错误仅核对源码合同，本轮未故障注入。to96dpi 非 bool、非有限偏移、未列出的容错/别名均未验收。

## 期望值来源与独立确证

1. 被测元素始终通过指定元素库查找，再核对 ID 和唯一性。JavaScript 观测从真实同源 iframe/open Shadow 中读取原生 input.getBoundingClientRect，加上 iframe 在顶层 viewport 的位置及边框偏移。
2. ctypes 独立读取 Chrome 主窗口和对应 Chrome_RenderWidgetHostHWND 的位置、客户区尺寸、原点和 DPI；以 chrome.exe 进程、窗口位置/尺寸、viewport 尺寸唯一绑定目标窗口。当前参考明确只支持 96 DPI，不能唯一识别时 BLOCKED。
3. 原生物理矩形由 DOM 矩形 × devicePixelRatio 取最近像素后，加上独立测得的 viewport 屏幕原点推导。九宫格位置按手写比例 0、1/2、1 计算，叠加指定偏移；当前快照按 floor(v+0.5) 取整，再按 96/window_dpi 换算最终点。**没有调用 get_bounding、SDK anchor_position/anchor_to_pt 或 Runtime 的点位 helper 来生成预期。**
4. 确定性调用前后都读取 DOM/Win32 参考，要求完全稳定；若发生移动，记 BLOCKED。实际点与预期必须相等，无容差、无对 API 的隐式重试。
5. 随机样本使用独立矩形边缘加偏移得到整数闭区间；检查 tuple 类型、范围及至少两个不同点。原始 JSON 保存所有 12 个点、原生参考、DOM 前后和前台状态。

本轮默认样例：独立物理矩形 `{x:99,y:622,width:1590,height:32}`，中心 `(894,638)`、左上 `(99,622)`、右下 `(1689,654)`。小数偏移 `(0.5,-0.5)` 得 `(895,638)`；中心偏移 `(700,-80)` 得 `(1594,558)`。数字随真实窗口/布局变化计算，脚本不写死这些样例。

## 正式矩阵（76 项）

| 类别 | 数量 | 覆盖 |
|---|---:|---|
| 合同与参数 | 10 | 签名/源方法/commit/hash；7 种非法 anchor，位置传参和未知关键字 |
| 环境与参考 | 3 | 静默标签/库副本、唯一元素映射、原生窗口与 viewport |
| 确定性锚点 | 53 | 默认 1；九固定位置×两种 DPI 参数 18；九传参/偏移形式×2 为 18；四个布局场景×两锚点×2 为 16 |
| random | 4 | 无偏移/偏移 `(11,-7)`×两种 DPI 参数，每组 12 次调用 |
| 只读稳定性 | 1 | 三次中心读取相同，滚动/value/focus/style 不变 |
| 恢复 | 2 | 样式/滚动恢复，动态 ID 开关/localStorage 精确恢复 |
| 生命周期 | 2 | 页面关闭、连接关闭后的错误类型和 trace/消息 |
| 清理 | 1 | 资源删除、源库 hash、外部标签基线 |

四个布局场景与上一轮使用同一准备 helper，仅操作自有标签的现有节点：临时增高 iframe 后顶层滚动 60 px、iframe 内滚动 73 px、Ant input 平移 `(13.25,17.75)` 并设 border-box 宽高 `237.5×37.5`、平移 `(-200.25,-550.75)` 得负 viewport 坐标。每场景核对中心和右下锚点。禁用目标过渡/动画以等待稳定参考，收尾恢复，未新增替代靶场或改库 XPath。

## 首轮阻塞与修正

- [探针 1](artifacts/element_get_anchor_position_20261008_probe1.json)：18/76 PASS、0 FAIL、58 BLOCKED，退出码 2；清理 8→8。继承的原生参考仅按 GetWindowRect 匹配，不能识别最大化窗口；确定性/随机核心用例尚未执行，不是产品失败。
- [原生窗口探针](artifacts/element_get_anchor_position_20261008_native_probe.json)确认 Chrome 最大化时 GetWindowRect 为 `(-8,-8,3456,1408)`，DOM 外框为 `(0,0,3440,1392)`；DWM_EXTENDED_FRAME_BOUNDS 与 DOM 外框相同。不可见调整大小边框导致识别差异。
- 本 API 的参考类在最大化时用 DwmGetWindowAttribute(9) 读取可见外框进行匹配，实际点位原点继续使用 ClientToScreen。未放宽坐标断言、未移动/恢复原生窗口，也未修改上一轮 get_bounding 脚本。
- [探针 2](artifacts/element_get_anchor_position_20261008_probe2.json)：76/76 PASS、退出码 0；随后安装正式无日期入口并完成三轮完整实测。
- 2026-10-04 的 [SKIPPED 证据](element_get_anchor_position_20261004.md)保留；旧入口在[历史归档](../../issues/get_anchor_position_history_20261008/README.md)。

## 源码快照链路与边界

[冻结合同](../element_get_anchor_position_contract_20261008.json)保存签名、docstring、源方法、失败路径、11 段只读源码和文件 SHA-256。以下位置限定于首节 worktree/commit：

- desktop：`sdk/src/uiautoma/web/element.py:763` → `_compat.py:94` / :305 的 anchor 转换；`sdk/src/uiautoma/_core/client.py:3903` → web.get_geometry(kind=anchor)；`runtime/services/pipe_server.py:2106` → Runtime。
- desktop：`runtime/services/action_service.py:2487` / :2500 读取 Provider 物理矩形；`runtime/desktop/mouse_actions.py:183` 使用 inset=0 计算点；随后按 96 DPI 换算。
- rust_uia：`src/main.rs:6077` 只读几何分支，:6123 跳过激活、scrollIntoView=false；:6159 Win32 原点/DPI。
- desktop：`chrome/engine/shared/dom_xpath_core.js:1434` 原生矩形；`chrome/engine/plugin_packages/command_legacy_package.js:926` iframe 坐标映射到顶层 viewport。

**覆盖边界：**Chrome 最大化窗口、原生 DPI=96、dpr=1、指定同源 iframe/open Shadow Ant input。非 96 DPI 的实际转换、跨屏/缩放、Edge、跨域 iframe、closed Shadow、旋转/缩放 iframe、隐藏/零尺寸节点未验收；随机均匀性未证明。

测试复用 `test_web_element_get_bounding.py` 的环境、DOM/Win32、场景和清理 helper；入口只调用本脚本的锚点、random、只读及生命周期方法，不调用继承的 bounding measurement 或 get_bounding。库复制与动态 ID helper 来自 `test_web_element_get_select_options.py`。共享临时目录名为 `.pytest_tmp/bounding_live/<UUID>`，每轮只删除自有 UUID。

公开文档交接按 AGENTS.md 文档门槛另行确认；本文件与索引为本地测试证据，未修改产品仓库。

## 复测

在 `D:\code\元素库\sdk测试` 运行唯一入口：

```powershell
uv run .\web\test_web_element_get_anchor_position.py
```

```powershell
uv run .\web\test_web_element_get_anchor_position.py --contract-only
uv run .\web\test_web_element_get_anchor_position.py --json --report-file .\web\evidence\artifacts\get_anchor_position_manual.json
```

支持 --url、--library、--element；默认即本轮场景。退出码 0 全通过、1 FAIL、2 BLOCKED。若宿主禁止 Named Pipe 或原生窗口测量，先解决宿主访问限制，不将其误判为产品故障。

原始输出与 SHA-256 汇总：[element_get_anchor_position_20261008.txt](artifacts/element_get_anchor_position_20261008.txt)。
