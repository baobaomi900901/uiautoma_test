# `uiautoma.web.WebElement.get_bounding()` 验证证据

## 当前结论（2026-10-08）

**VERIFIED（Chrome、96 DPI 范围）：连续三轮正式完整运行，每轮 38/38 PASS，退出码均为 0。**

- 靶场：[iframe/open Shadow 表单](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：`D:\code\元素库\260902_web元素`；元素：`web靶场_表单测试_ant_输入框`。
- 三轮库选择器均唯一命中 `INPUT#form-controls-ant-text`；实际使用库选择器查找，不用 CSS 替换被测对象。
- SDK/Runtime 只读 worktree：`D:\code\desktop`；commit：`7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- Provider 只读 worktree：`D:\code\rust_uia`；commit：`b700f9238134f57da83ab478a5ee55337ade1082`。
- 结论绑定上述源码快照和本次实际 dev Runtime/Chrome，未独立核验正在运行的 Provider 二进制是否精确来自该 commit。
- 使用 `silent_running=True` 的自有标签；没有调用窗口激活、移动窗口、系统鼠标/键盘或剪贴板操作。Win32 测量只改测试 Python 线程的 DPI 感知上下文，收尾恢复。
- 每轮清理 PASS：标签 **6→6**；没有外部新增/删除；关闭自有页面与库连接、删除临时库副本，源 elements.json SHA-256 不变，动态 ID 开关及 localStorage 精确恢复。

| 正式轮次 | 结果 | 原始日志 | 完整观测数据 |
|---|---|---|---|
| 1 | 38/38 PASS，退出码 0 | [run1.txt](artifacts/element_get_bounding_20261008_run1.txt) | [run1.json](artifacts/element_get_bounding_20261008_run1.json) |
| 2 | 38/38 PASS，退出码 0 | [run2.txt](artifacts/element_get_bounding_20261008_run2.txt) | [run2.json](artifacts/element_get_bounding_20261008_run2.json) |
| 3 | 38/38 PASS，退出码 0 | [run3.txt](artifacts/element_get_bounding_20261008_run3.txt) | [run3.json](artifacts/element_get_bounding_20261008_run3.json) |

每轮 22 次独立坐标对照，`x/y/width/height` 差值全部为 **0**。前两轮 22/22 次前台窗口不变；第三轮 21/22 次不变，一次由测试 Chrome（HWND 6886240）切到其他窗口（HWND 65874）。没有一次在测量期间由其他窗口切到测试 Chrome；不能将这条记录写成“全部前台不变”，也不推断外部切换的具体原因。

## 用途与合同

获取网页元素位置和尺寸，返回包含 **x、y、width、height** 四项的整数矩形。

```python
get_bounding(self, to96dpi: bool = True,
             relative_to: str = "screen") -> dict[str, int]
```

| 参数/返回 | 合同与本轮覆盖 |
|---|---|
| to96dpi=True | 按浏览器原生窗口 DPI 将位置及尺寸换算到 96 DPI；本轮原生窗口恰为 96，True/False 相同，没有验收非 96 DPI 的实际换算 |
| to96dpi=False | 原生物理屏幕像素位置及尺寸 |
| relative_to="screen" | 相对于物理屏幕原点，按 to96dpi 决定是否换算 |
| relative_to="window" | 相对于浏览器**原生客户区**左上角，包含工具栏对应的偏移；不是网页 viewport 原点 |
| 参数传法 | 两个可选参数均支持位置传参；默认参数和显式四组合均验收 |
| 返回字段 | 恰为 x、y、width、height；各值为 int 且不是 bool |

| 失败路径 | 当前冻结合同 | 本轮是否实测 |
|---|---|---|
| 非法参照字符串、空串、SCREEN、None | SDK 在 RPC 前抛 InvalidParamsError；`relative_to 必须是 screen 或 window` | 是 |
| 多余位置参数、未知关键字 | Python TypeError | 是 |
| 关闭页面后使用旧元素 | ActionError / stale_page_reference，`网页对象已失效` | 是 |
| 关闭库连接后使用元素 | HostUnavailableError，消息包含“连接已关闭” | 是 |
| Provider 不可用 | ActionError / uiautomation_provider_unavailable | 仅源码合同和 10-04 历史记录，本轮未故障注入 |
| 无效/缺失几何元数据 | ActionError / browser_viewport_conversion_failed，`无法获取网页元素坐标` | 仅源码合同，本轮未故障注入 |

不为 to96dpi 的注解自行添加源码没有的严格 bool 校验；未声明非 bool 参数验收。

## 期望值来源与独立确证

1. 从真实同源 iframe 的 open ShadowRoot 内读取原生 `getBoundingClientRect()`；加上 iframe 外层矩形和 clientLeft/clientTop，得到目标在顶层网页 viewport 的 CSS 矩形。读取发生在独立 JavaScript 观测函数中，不调用被测 get_bounding。
2. 用 ctypes 直接调用 Win32：GetWindowRect、GetClientRect、ClientToScreen、GetDpiForWindow。按真实进程名 chrome.exe、DOM 的窗口位置/外框尺寸和 viewport 尺寸，唯一识别 Chrome 主窗口及对应 Chrome_RenderWidgetHostHWND。无法唯一识别或不在当前支持的 96 DPI 参考范围时记 BLOCKED，不取第一个窗口。
3. 根据 DOM 矩形 × devicePixelRatio 的最近像素值，加上**独立测得的网页 viewport 屏幕原点**，推导 screen 物理矩形。window 参照再减去主窗口客户区屏幕原点；归一化因子为 96 / GetDpiForWindow。当前冻结快照采用 floor(v + 0.5) 的像素取整，负坐标和 0.5 小数尺寸均有实测支持。
4. 每次 API 调用前后都读取 DOM 和 native 参考，要求完全稳定；数据变化记 BLOCKED。实际值必须与独立期望四字段完全相同，没有像素容差或对 API 调用的隐式重试。
5. 连续三次只读调用另行核对滚动位置、value、焦点和 style 不变。原始 JSON 保存每次 DOM 前后、原生窗口、DPI、预期、实际、差值和前台状态。

第一轮默认例：screen 物理矩形为 `{x:992,y:644,width:490,height:32}`；window 为 `{x:99,y:622,width:490,height:32}`。独立测得主窗口客户区原点 `{x:893,y:22}`，网页 viewport 原点 `{x:893,y:199}`；二者垂直差为 **177 px**，因此 window.y 并不是 DOM viewport 的 445。这些数字是运行时样例，不写死到脚本。

## 正式矩阵（38 项）

| 类别 | 数量 | 覆盖 |
|---|---:|---|
| 合同与参数 | 7 | 源码/签名/默认值/两仓库 commit 和源文件 hash；四种非法参照、多余位置参数、未知关键字 |
| 环境与独立参考 | 3 | 静默页面和库副本、目标唯一映射、唯一 Win32 主窗口/viewport |
| 几何值 | 22 | 默认、位置传参；下列 5 场景各覆盖 screen/window × to96dpi=False/True |
| 只读稳定性 | 1 | 连读三次矩形一致；滚动/value/focus/style 不变 |
| 恢复准备状态 | 2 | 自有 input 和 iframe 样式/滚动恢复，动态 ID 开关/localStorage 恢复 |
| 生命周期 | 2 | 页面关闭与连接关闭后的错误类型和 trace/消息 |
| 清理 | 1 | 自有资源删除、源库 hash 和外部标签基线复核 |

五个几何场景：

- baseline：原始 input。
- top_scroll：只在自有标签临时增高**现有 iframe**以形成足够滚动空间，顶层页面 instant 滚动 60 px。
- iframe_scroll：现有 iframe 内部 instant 滚动 73 px。
- translate_resize：现有 Ant input 临时平移 `(13.25,17.75)` CSS px，border-box 宽高设为 `237.5×37.5`；当前物理结果为 `238×38`。
- negative_position：现有 Ant input 临时平移 `(-200.25,-550.75)` CSS px，顶层 viewport 的 x/y 为负；API 返回完整矩形，不自动滚回可视区。window 示例为 `{x:-101,y:71,width:490,height:32}`，原生客户区包含工具栏偏移，所以 window.y 仍可为正。

后四项含明确测试干预；目标仍是同一个真实库元素，未新增替代 DOM 靶场。样式/滚动全部恢复后才进入生命周期测试。

## 探针发现与判据修正

- [初始探针](artifacts/element_get_bounding_20261008_initial_probe.json)：四组合成功，清理 6→6；确认原生客户区与网页 viewport 的原点不同。
- [矩阵探针 1](artifacts/element_get_bounding_20261008_matrix_probe1.json)：24/37 PASS、12 FAIL、1 BLOCKED，退出码 1。四次 top_scroll 准备断言失败，因为此轮 viewport 高 1070、页面没有顶层滚动空间；八次样式场景准备断言失败，因为 Ant transition 让宽度和 transform 正在插值；一次位置传参参考正在移动，记 BLOCKED。没有把这些失败归为 API 缺陷或悄悄删除记录。
- 修正为临时增高自有现有 iframe、instant 滚动；仅在自有目标样式干预时禁用 transition/animation，等待连续三份 DOM 观测相同后开始测量。恢复原样式也等布局稳定，不放宽坐标断言。
- [矩阵探针 2](artifacts/element_get_bounding_20261008_matrix_probe2.json)：38/38 PASS，退出码 0；之后才安装正式无日期入口并连续跑三轮。
- 当前四字段、screen/window 合同取代 2026-08 的八字段和仅 screen 历史语义；旧脚本/旧证据保留在[历史归档](../../issues/get_bounding_history_20261008/README.md)。2026-10-04 的 [SKIPPED 记录](element_get_bounding_20261004.md) 不改为通过；本次为新的独立验收。

## 源码快照链路

[冻结合同](../element_get_bounding_contract_20261008.json) 保存签名、docstring、源方法、失败路径以及文件 hash/片段；[引擎补充只读快照](artifacts/element_get_bounding_engine_review_20261008.json) 保存 DOM 与 iframe 几何链路。下面位置分别限定于首节列出的 worktree 与 commit，不代表其他分支。

| 仓库 | 位置与职责 |
|---|---|
| desktop | `sdk/src/uiautoma/web/element.py:749` → _raw.geometry(kind="bounding") |
| desktop | `sdk/src/uiautoma/_core/client.py:3903` → web.get_geometry；四整数协议校验 |
| desktop | `runtime/services/pipe_server.py:2106` → action_service.web_get_geometry |
| desktop | `runtime/services/action_service.py:2487` → Provider web.resolve_element(read_geometry=True)；:2500 几何参照/取整/96 DPI 换算 |
| rust_uia | `src/main.rs:6077` → geometry 只读请求；:6123 只读不激活，scrollIntoView=false；:6159 Win32 DPI/原点/scale |
| desktop | `chrome/engine/shared/dom_xpath_core.js:1434` 原生元素矩形与 frame_viewport_css；`chrome/engine/plugin_packages/command_legacy_package.js:926` 映射到顶层 viewport |

## 覆盖边界与复测

- 真实测试窗口 DPI=96、devicePixelRatio=1。**120/144/192 DPI、跨屏、浏览器缩放未验收**；本次无法用 True/False 相同的结果证明非 96 DPI 换算正确。脚本原生参考当前明确只支持 96 DPI，否则报告 BLOCKED。
- 仅 Chrome、指定同源 iframe/open Shadow 的 Ant input；未覆盖 Edge、跨域 iframe、closed Shadow、旋转/缩放的 iframe、display:none、零尺寸节点、原生窗口最小化等。
- Provider 不可用和协议/元数据异常仅列源码合同；本轮未模拟此类故障。
- 没有改产品源码。公开 API [文档交接稿](../../issues/drafts/get_bounding_public_doc_handoff.md)已按用户确认生成于本地，尚未提交 Issue；本文件为本地测试证据。

在 `D:\code\元素库\sdk测试` 运行唯一脚本：

```powershell
uv run .\web\test_web_element_get_bounding.py
```

合同检查或完整 JSON 归档：

```powershell
uv run .\web\test_web_element_get_bounding.py --contract-only
uv run .\web\test_web_element_get_bounding.py --json --report-file .\web\evidence\artifacts\get_bounding_manual.json
```

还支持 --url、--library、--element；默认即本轮指定靶场/元素。退出码 0 全通过、1 FAIL、2 BLOCKED。若运行宿主阻止本机 Named Pipe，则先解决宿主访问限制，不将 HostUnavailableError 误记成产品缺陷。

原始 UTF-8 输出及 SHA-256 总清单：[element_get_bounding_20261008.txt](artifacts/element_get_bounding_20261008.txt)。
