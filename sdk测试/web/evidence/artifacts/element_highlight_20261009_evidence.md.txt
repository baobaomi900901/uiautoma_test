# `uiautoma.web.WebElement.highlight()` 验证证据

## 当前结论（2026-10-09）

**VERIFIED：最终脚本连续三轮完整验收，每轮 8/8 PASS、0 FAIL、0 BLOCKED，退出码 0。**
验证范围是用户提供的 keys-click-test 单击按钮、Windows Chrome、96 DPI。

- 靶场：[keys-click-test](https://baobaomi900901.github.io/xpath/#/keys-click-test)。
- 元素库：`D:\code\元素库\260902_web元素`；连接临时副本，仅清空副本内陈旧 session/BrowserPid，保留原选择器。
- 库名称：`web靶场_测试点击_单击触发`，唯一命中 `BUTTON#btn-click-target`。
- **所有正式运行与默认观察运行均为 `silent_running=False`**：可见打开靶场、按库名称定位、实际调用 `highlight()`。
- desktop 只读 worktree：`D:\code\desktop`；commit `7f148f27c0efa8bbba1f18d86c14845ea7d639fa`。
- rust_uia 只读 worktree：`D:\code\rust_uia`；commit `b700f9238134f57da83ab478a5ee55337ade1082`。
- 结论绑定上述只读源码文件 SHA-256 和本次 dev Runtime/Provider/Chrome；未独立证明运行时二进制的构建 commit。

| 正式轮次（原始文件编号） | duration / delay_after | 可见时间采样区间 | 消失后至返回 | 结果 |
|---|---|---|---|---|
| 1（run3） | 1 / 0 秒 | 0.961–1.202 秒 | 0.0003 秒 | 8/8 PASS；[日志](artifacts/element_highlight_20261009_run3.txt)、[JSON](artifacts/element_highlight_20261009_run3.json) |
| 2（run4） | 3 / 0 秒 | 2.937–3.107 秒 | 0.063 秒 | 8/8 PASS；[日志](artifacts/element_highlight_20261009_run4.txt)、[JSON](artifacts/element_highlight_20261009_run4.json) |
| 3（run5） | 0.6 / 0.25 秒 | 0.493–0.750 秒 | 0.259 秒 | 8/8 PASS；[日志](artifacts/element_highlight_20261009_run5.txt)、[JSON](artifacts/element_highlight_20261009_run5.json) |

三轮均使用 `--close-page`：标签 **1→1**；本次页面/连接关闭、观察器移除、副本删除、无可见高亮残留、源 elements.json 哈希不变，无外部标签增删。按钮属性/文字/焦点不变，click/input/change/keydown 事件均为 0。合同检查另为 **3/3 PASS、SKIPPED**，不计入视觉验收。

默认观察模式单独跑通 **8/8 PASS、退出码 0**：[日志](artifacts/element_highlight_20261009_observe2.txt)、[JSON](artifacts/element_highlight_20261009_observe2.json)。高亮 3 秒后消失，按用户要求保留一个页面，标签 **1→2**；其余资源清理 PASS。该单次报告使用 `READY_FOR_LIVE`，因为主动保留页面；API 索引的 VERIFIED 来自上述三轮完整关闭页面的验收。

## 用途与源码合同

```python
highlight(self, duration: float = 1.0, delay_after: float = 0) -> None
```

激活元素所在页面和浏览器窗口，将元素滚动到可见区域后显示原生高亮框，成功返回 None。API 默认 1 秒；为了方便人工观察，测试脚本默认传入 **3 秒**。`delay_after` 是高亮结束后的等待秒数。

[合同快照](../element_highlight_contract_20261009.json) 保存签名、docstring、方法源码、26 段完整调用链片段及文件哈希。
在上述 worktree/commit 中：

1. `sdk/src/uiautoma/web/element.py:1109` → raw.highlight → `_finish` 检查 ActionResult，再执行 sleep_after。
2. `sdk/src/uiautoma/_core/client.py:3560` 检查 duration，按秒四舍五入为整数毫秒，RPC `web.action.highlight`，定位 timeout 5000ms；实时元素会话传 `locator_kind=runtime_ref`。
3. `runtime/services/pipe_server.py:2073` → `ActionService.web_highlight_element`（`:2452`）。Runtime 校验参数、解析实时引用与页面，要求唯一物理屏幕矩形；动作 strategy 为 `web_highlight`。
4. Provider `web.resolve_element` → rust_uia `src/main.rs:6077`：激活窗口、执行 locate 和 scrollIntoView、读取网页几何并转换为物理屏幕坐标。页面引擎位于 desktop `chrome/engine/engine_packages/page_engine_runtime.js:2556`。
5. Runtime `HighlightBackend`（`action_service.py:247`）请求 Provider `elementtree/operation=highlight` 显示，等待 duration 后在 finally 隐藏。rust_uia `src/main.rs:8672` → `src/highlight_win32.rs` 原生覆盖窗口。

| 条件 | 类型 / 文案 / 路径 | 本轮覆盖 |
|---|---|---|
| duration 负数、bool、非有限数、非数字 | `InvalidParamsError`；`duration 必须是非负的有限秒数`；SDK raw 参数校验 | 9 种值正式通过，均未到达 RPC；一个用例含 9 个子项 |
| duration=0 | 合法；成功返回 None，返回后高亮移除 | 补充探针通过；可能短暂闪现，未宣称从不显示 |
| 连接关闭后的旧元素 | `HostUnavailableError`；`元素对象所属连接已关闭，请重新获取对象` | 三轮正式通过，无新增高亮 |
| 隐藏目标无几何 | `ActionError`；`无法定位网页元素`；`browser_viewport_evidence_missing` | 补充探针通过，耗时 0.131 秒；未执行 delay_after=0.6 秒 |
| 页面引用失效 | `ActionError`；`网页对象已失效`；`stale_page_reference` | 已读源码，未在本轮正式注入 |
| 无法激活浏览器 | `ActionError`；`无法激活浏览器窗口，已取消操作`；`browser_window_activation_failed` | 先行探针遇到；保留失败，不算正常路径通过 |
| 返回匹配数量不唯一 / 缺物理矩形 / 高亮后端失败 | `ActionError`；分别为 `无法确定唯一的网页元素` / `无法获取网页元素的高亮位置` / `网页元素高亮失败` | 已读分支，未注入故障 |
| 非法 RPC 毫秒/timeout、非实时引用 | `InvalidParamsError`（trace `invalid_params`）；Runtime 参数或引用校验 | 已读分支，未绕过公开 SDK 注入 |
| delay_after 负数或无法转为数字 | 成功动作之后由 sleep_after 抛 `InvalidParamsError`；`delay_after 不能小于 0` / `delay_after 必须是数字` | 未正式实测；源码没有有限数检查，不宣称非有限值统一抛本类型 |

## 独立确证与用例

被测调用只使用 `page.find_all(库名称)` 获得的唯一真实元素对象，不用临时 CSS 选择器替代被测定位。
参考通道是 DOM 的 `getBoundingClientRect()`、devicePixelRatio，以及 ctypes 读取的 Chrome 原生 viewport 屏幕原点。最大化窗口使用 DWM 可见边界，避免不可见调整边框影响几何。没有调用 SDK get_bounding 或 get_anchor_position。

独立枚举真实原生 `RustPerPixelAlphaHighlightClass` / `RustFullscreenHighlightClass`，确认显示及移除；读取四条边中点附近各 7 个像素，四边均出现红色。只读取目标边缘小范围像素，没有采集其他应用截图。四周对称外扩预算 0–8px，中心误差不超过 1px，不复制产品边框布局公式。
三轮 DOM+native 参考矩形均为 **(2971,384,96,40)**，原生覆盖窗为 **(2968,381,102,46)**，四边红色像素均为 True。

采样同时记录枚举前后时刻：可见时间下界为末次可见开始减首次可见结束，上界为首次不可见结束减此前不可见开始。轮询及单次像素读取的不确定性包含在区间中，不能把一次窗口存在当作全部持续时间。判据允许少量显示/隐藏 IPC 开销：下界不超过 duration+0.18，上界不小于 duration−0.05，下界不小于 duration−0.3；消失至返回为 delay_after−0.03 至 delay_after+0.35。
读取像素时要求目标 Chrome 在前台；API 不锁定后续用户切换窗口。

| 用例 | 数量 | 正式结果 |
|---|---:|---|
| API 合同、非法 duration（9 子项） | 2 | 2 PASS |
| 可见开页/库副本、唯一映射及独立原生参考 | 2 | 2 PASS |
| 真高亮：返回/策略/红色/位置/时间/消失 | 1 | 1 PASS |
| 属性文字焦点和输入事件不变 | 1 | 1 PASS |
| 关闭连接的旧对象、最终资源复核 | 2 | 2 PASS |
| **每轮总计** | **8** | **8 PASS** |

## 加固记录与覆盖边界

原始试跑和失败记录均保留，未计入最终三轮通过数：

- [trial1](artifacts/element_highlight_20261009_trial1.txt) 高亮通过，cleanup 失败：脚本先关闭了页面所属连接，再尝试页面操作。已调整为先移除观察器/按参数关闭页面，再关闭连接和验收旧对象；通过独立连接关闭遗留的唯一自有页面，[恢复记录](artifacts/element_highlight_20261009_trial1_recovery.json)。属于测试顺序错误。
- [run1](artifacts/element_highlight_20261009_run1.txt) 修正收尾后 8/8 PASS；[run2](artifacts/element_highlight_20261009_run2.txt) 7 PASS、1 BLOCKED，cleanup PASS。旧判据要求整个高亮期间始终前台，超出了 API 的激活语义。已改为读取像素时确认前台；保存[旧脚本](artifacts/element_highlight_20261009_pre_foreground_scope.py.txt)，之后 run3–5 连续通过。
- 默认观察模式[首次开页](artifacts/element_highlight_20261009_observe.txt) 在 `web.create(..., silent_running=False)` 返回 `activate_tab_failed`，未执行 highlight，且留下一个新增页面；[独立恢复](artifacts/element_highlight_20261009_observe_recovery.json)只关闭已记录 ID/URL 的页面。此为开页准备失败，未确认其根因；独立重跑 observe2 完整通过。遇到类似开页失败应先复核标签，不能把它算作 highlight 已执行。
- 2026-10-08 [初始探针](artifacts/element_highlight_20261008_probe.json)前两次 activation_failed，当时前台曾为 0；后续调用成功。未将这些失败删除或提升为通过。
- [probe2](artifacts/element_highlight_20261008_probe2.json)探索时长、delay_after、duration=0；[probe3](artifacts/element_highlight_20261008_probe3.json)临时 marginTop 准备后未等 Ant transition 完成，几何参考无效；[probe4](artifacts/element_highlight_20261008_probe4.json)等待布局稳定后，屏外按钮被滚动到可见区域并正确高亮；[probe5](artifacts/element_highlight_20261008_probe5.json)隐藏目标按上表失败。均为补充单次探针，不代表三轮正式覆盖屏外/隐藏分支。

正式流程没有临时改 CSS、没有点击按钮或发送系统键鼠；默认只进行一次正向高亮。未验收 Edge、非 96 DPI、跨显示器、iframe/Shadow DOM、浏览器最小化、节点移除、多匹配或后端显示/隐藏失败、超长 duration、delay_after 非有限值等。保留用户页面是观察模式的要求；完整资源验收加 `--close-page`。
历史 2026-10-04 Provider 不可用的 SKIPPED 证据保存在[历史记录](element_highlight_20261004.md)，原始日志不变。

## 当前唯一入口

[test_web_element_highlight.py](../test_web_element_highlight.py)。在 `D:\code\元素库\sdk测试` 运行：

```powershell
# 用户观察：可见开页，按库名定位，高亮 3 秒，保留页面
uv run .\web\test_web_element_highlight.py

# 延长高亮便于观察
uv run .\web\test_web_element_highlight.py --duration 10

# 完整清理验收（仍非静默）
uv run .\web\test_web_element_highlight.py --close-page
```

每项输出期望、实际、耗时；退出码 0 为全通过，1 为失败，2 为仅存在阻塞。
[汇总与文件 SHA-256 清单](artifacts/element_highlight_20261009.txt)保存正式运行、探针、修正记录及最终脚本副本。
测试侧证据和索引已同步；公开 API 文档交接稿等待用户确认。未修改产品源码或发布 Issue。
