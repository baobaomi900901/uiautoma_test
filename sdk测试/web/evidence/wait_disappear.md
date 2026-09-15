# `WebBrowser.wait_disappear()` 初次测试

## 用途

等待网页元素**消失**。

| 参数 | 默认 | 说明 |
|---|---|---|
| `selector_or_element` | 必填 | 目标元素：**库元素名称字符串**、`Selector` 对象或 `WebElement` 对象 |
| `timeout` | `20` | 等待秒数；`0` 只检查一次，`-1` 一直等待 |

返回 `bool`：超时前消失返回 `True`，否则 `False`。
`timeout` 是**位置或关键字**参数（与 `find(..., *, timeout)` 不同）。
实现链与 `wait_appear()` 完全共用：`WebBrowser.wait_disappear` → `_wait_element(target, timeout, "absent")`
→ `web.browser.wait_element`，仅 `wait_state` 取 `absent`。

## 真实验收结果

**VERIFIED：32/32 通过，退出码 0**（`auto` 模式**连续 3 次完整运行全绿**，**无任何边界项**）；
回退来源 `scheduled` 模式另跑一轮 **30/30 通过，退出码 0**。

靶场：维护者的官方靶场（测试侧不自建页面）
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）
元素库：`D:\code\元素库\260902_web元素`（70 个 web 元素；脚本复制副本后打开，不碰原件）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`selector_or_element` 必填、`timeout` 位置/关键字且默认 20、返回 `bool` |
| 环境 / 元素库 / 页面准备 | 通过，进入时 11 个标签；库 70 个元素与列举一致 |
| 转变来源 | 通过，`auto` 探测到自计时页可达（HTTP 200）→ 使用 `delayed-page`（页面自己计时移除） |
| 自计时页绑定 / 自计时 / 同一节点 | 通过，等出现 1.56s；4.5s 内 3 次切换 `[(1.4, absent), (2.94, present), (4.48, absent)]`；`#delayed-created-count=1` |
| **元素已被移除** | 通过，返回 `True`（**0.017s**，未等待） |
| **`timeout=0` 且已移除** | 通过，立即返回 `True`（**0.018s**） |
| **元素在场** | 通过，等满 1s 返回 `False`（实测 **1.001s**） |
| **等待期间页面自己移除（canonical）** | 通过，返回 `True`，耗时 **0.429s**（测试侧零调度） |
| **`timeout=-1`** | 通过，页面自己移除后返回 `True`（**1.46s**），未无限阻塞 |
| **隐藏 ≠ 消失** | 通过，`display:none`、`getClientRects()=0` 的节点**不算消失**：等满 1s 返回 `False`（1.001s） |
| **React 销毁节点** | 通过，卡片被销毁后旧引用**立即**判为消失：`True`（0.012s） |
| **名称目标：本页不存在** | 通过，立即返回 `True`（0.007s） |
| **名称目标：在场** | 通过，等满 2s 返回 `False`（实测 2.0s） |
| **名称目标：随导航消失** | 通过，`navigate(load_timeout=0)` 时元素仍在场 → 页面切换后返回 `True`（**0.079s**） |
| `Selector` 目标：本页不存在 | 通过，返回 `True`（0.016s） |
| **CSS 选择器字符串作为目标** | 通过，被当作库元素名并立即抛 `ActionError`（`未找到选择器`，0.001s） |
| 未知库名 | 通过，同上立即抛错（0.001s） |
| 参数校验 | 通过，`timeout=-2` / `"x"`、目标 `None` / `123` → `InvalidParamsError`；多余位置参数 / 缺参 → `TypeError`（全部 0.0s） |
| 页面关闭后 | 通过，`ActionError`（"网页对象已失效"，0.002s） |
| 关闭 Package 后 | 通过，名称目标在 **SDK 侧**立即抛 `NoCurrentPackageError`（0.0s） |
| 资源清理 | 通过，关闭页面与 Package、删除元素库副本 |

## 转变来源

元素必须**真的被移出 DOM**（见下「判据」），因此需要等待期间发生一次移除：

- **`delayed-page`（canonical，已部署）**：`public/delayed-element.html` 每 1.5s 把**同一个**
  `#delayed-target` 节点 `remove()` / `appendChild()` 交替，**由页面自己计时，测试侧零调度**。
- **`scheduled`（回退方案）**：测试侧注入探针节点（挂 `window.__uiautomaWaitNode`），
  再用 `execute_javascript` 在 1.2s 后把同一节点移除（实测 `True`@1.256s）。
- **`auto`（默认值）**：先探测自计时页是否可达，可达则用它，否则回退 `scheduled`。

名称/Selector 目标的「等待消失」：在**导航尚未离开时就开始等待**
（`navigate(..., load_timeout=0)` → `wait_disappear(name, N)`），元素随页面切换消失（0.079s）。

## 已实测确立的判据

| 事实 | 结论 | 证据 |
|---|---|---|
| **隐藏不等于消失** | `exists` 是 **DOM 存在性**判定，不区分可见性 | `display:none`、`getClientRects()=0` 的节点：`wait_disappear(..., 1)` → `False`（1.001s） |
| WebElement 目标按节点身份 | 节点被移除即判为消失；被销毁重建后旧引用同样是「已消失」 | React 销毁卡片 → `True`（0.012s） |
| 名称/Selector 目标 | 每轮询按库里保存路径重新定位，页面离开即视为消失 | 导航切换 → `True`（0.079s） |
| 目标入参范围 | 只支持库元素名 / `Selector` / `WebElement` | `wait_disappear("#menu-anchor-test", 2)` → `ActionError`（0.001s） |
| 轮询粒度 | 运行时约 0.1s | 页面在 1.4s 处移除 → 0.429s 内从「开始等到返回」完成 |

## 与 `wait_appear()` 的关系：同一实现的两个方向

两条 API 共用 `_wait_element(target, timeout, state)`，本轮实测显示两者的语义正好互为镜像：

| | `wait_appear` | `wait_disappear` |
|---|---|---|
| 目标已处于目标态 | 立即 `True`（0.005~0.02s） | 立即 `True`（0.007~0.017s） |
| 目标一直不满足 | 等满超时 `False` | 等满超时 `False`（1.001s / 2.0s） |
| 等待期间发生转变 | 页面自计时插入 → `True`@0.533s | 页面自计时移除 → `True`@0.429s |
| `timeout=-1` 且转变发生 | `True`@1.461s | `True`@1.46s |
| `display:none` | **算存在**（`True`） | **不算消失**（`False`） |
| 节点被 React 销毁重建 | 旧引用**永远等不到**（记为边界） | 旧引用**立即判为消失**（`True`@0.012s） |

最后一行是同一「节点身份」规则在两个方向上的必然结果，已分别记录，
`wait_appear` 侧见 [`wait_appear.md`](wait_appear.md)「已知边界 1」。

## 实测行为记录

1. **元素库没有「延迟元素」条目**：`#delayed-target` 尚未采集进元素库，因此自计时页的 canonical
   场景使用 **WebElement 目标**；名称/Selector 目标的等待消失通过「导航离开」覆盖。
   若日后把 `#delayed-target` 采集为库元素（例如 `web靶场_延迟元素`），可让名称目标也走自计时页。
   注：SDK **没有**公开的「向元素库新增元素」接口（`capture`/`validate` 为暂缓模块），
   该采集需在桌面应用中完成。
2. **在场时用 1s 超时是安全的**：自计时页周期 1.5s，`timeout=1` 的等待必在下次移除前结束，
   实测 `False`@1.001s，3 次运行一致。
3. **自然写法优于调度写法**：名称目标的「等待消失」用 `navigate(load_timeout=0)` 后立即等待，
   耗时 0.079s 且不需要注入任何调度 JS。
4. **页面关闭后立即拒绝**：`ActionError: 网页对象已失效`（0.002s）；关闭 Package 后名称目标在
   SDK 侧抛 `NoCurrentPackageError`（0.0s，未发起 RPC）。

## 复测

脚本：[test_web_browser_wait_disappear.py](../test_web_browser_wait_disappear.py)
原始产物：[artifacts/wait_disappear_20260915.txt](artifacts/wait_disappear_20260915.txt)（`auto` 模式，32/32，退出码 0）

```powershell
uv run .\web\test_web_browser_wait_disappear.py                      # auto：探测自计时页，可达即用它
uv run .\web\test_web_browser_wait_disappear.py --transition-source scheduled
uv run .\web\test_web_browser_wait_disappear.py --json
uv run .\web\test_web_browser_wait_disappear.py --contract-only

# 本地 dev server 上的自计时页：元素库绑定部署域名，需跳过名称/Selector 用例
uv run .\web\test_web_browser_wait_disappear.py --transition-source delayed-page `
  --delayed-page-url http://localhost:7199/delayed-element.html --skip-name-cases
```

元素库副本与探针节点都在本次运行内创建并在收尾删除/移除；脚本不写入任何产品文件。

退出码：`0` = 全部 PASS（允许 KNOWN）；`1` = 存在 FAIL；`2` = 无非 FAIL 但存在 BLOCKED。

## 明确排除

- **`display:none` 之外的其他「不可见」形态**（`visibility:hidden`、`opacity:0`、被遮挡）：
  未逐一覆盖，但由「存在性判定」的结论可推断同样不算消失。
- **元素被移出 DOM 后又原地插回的「闪断」**：`wait_disappear` 是否能在闪断窗口内命中未构造。
- **跨 iframe / 跨 frame 的等待**：库元素本身在 iframe 内（已覆盖），未覆盖「等待 iframe 自身消失」。
- **`timeout=-1` 且元素永不消失**：会一直阻塞，未构造（避免无法收尾）。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
