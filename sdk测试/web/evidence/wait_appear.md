# `WebBrowser.wait_appear()` 初次测试

## 用途

等待网页元素**出现**。

| 参数 | 默认 | 说明 |
|---|---|---|
| `selector_or_element` | 必填 | 目标元素：**库元素名称字符串**、`Selector` 对象或 `WebElement` 对象 |
| `timeout` | `20` | 等待秒数；`0` 只检查一次，`-1` 一直等待 |

返回 `bool`：超时前出现返回 `True`，否则 `False`。
注意 `timeout` 是**位置或关键字**参数（不像 `find(..., *, timeout)` 那样仅限关键字）。
实现链：`WebBrowser.wait_appear` → `web.browser.wait_element`
→ `ActionService.web_browser_wait_element`（`timeout_ms` 由秒换算，`-1` 表示不设截止时间）。

## 真实验收结果

**VERIFIED：31/31 通过 + 1 项如实刻画，退出码 0**（**连续 3 次完整运行全绿**）。
默认 `auto` 模式已自动选中靶场自计时页（`delayed-page`），即 canonical 场景是
**由靶场页面自己计时**产生元素出现/消失，测试侧零调度。

靶场：维护者的官方靶场（测试侧不自建页面）
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）
元素库：`D:\code\元素库\260902_web元素`（70 个 web 元素；脚本复制副本后打开，不碰原件）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`selector_or_element` 必填、`timeout` 位置/关键字且默认 20、返回 `bool` |
| 环境 / 元素库 / 页面准备 | 通过，进入时 11 个标签；库 70 个元素与列举一致 |
| 转变来源选择 | 通过，`auto` 探测到自计时页可达（HTTP 200）→ 使用 `delayed-page` |
| **自计时页绑定** | 通过，等 `#delayed-target` 出现用了 1.407s 并绑定为 `WebElement` |
| **页面自计时** | 通过，4.5s 内观测到 3 次切换 `[(1.55, absent), (2.94, present), (4.48, absent)]`，测试侧零调度 |
| **同一节点** | 通过，`#delayed-created-count=1`、`data-created-count=1`（已切换 5 轮） |
| **元素已存在** | 通过，返回 `True`（**0.007s**，未等待） |
| **页面移除元素后** | 通过，等满 1s 返回 `False`（实测 **1.001s**） |
| **`timeout=0`** | 通过，元素已被移除时立即返回 `False`（**0.007s**） |
| **等待期间元素出现（canonical）** | 通过，**页面自己**把同一节点重新挂回 → 返回 `True`，耗时 **0.533s**（测试侧零调度） |
| **`timeout=-1`** | 通过，页面自己让它出现后返回 `True`（**1.461s**），未无限阻塞 |
| 隐藏元素仍算「存在」 | 通过，`display:none`、`getClientRects()=0` 仍返回 `True`（**0.008s**） |
| React 重建同形节点 | 边界（`KNOWN`），见「已知边界 1」 |
| **名称目标：本页不存在** | 通过，等满 2s 返回 `False`（2.001s） |
| **名称目标：导航未完成时开始等待** | 通过，`navigate(load_timeout=0)` 时元素仍不存在 → 路由切换后返回 `True`，耗时 **0.198s** |
| 名称目标：已在当前页 | 通过，返回 `True`（0.03s） |
| `Selector` 目标（`package.selector`） | 通过，返回 `True`（0.01s） |
| **CSS 选择器字符串作为目标** | 通过，被当作库元素名并立即抛 `ActionError`（`未找到选择器`，0.001s） |
| 未知库名 | 通过，同上立即抛错（0.0s） |
| 参数校验 | 通过，`timeout=-2` / `"x"`、目标 `None` / `123` → `InvalidParamsError`；多余位置参数 / 缺参 → `TypeError`（全部 0.0s） |
| 页面关闭后 | 通过，`ActionError`（"网页对象已失效"，0.002s） |
| 关闭 Package 后 | 通过，名称目标在 **SDK 侧**立即抛 `NoCurrentPackageError`（0.0s） |
| 资源清理 | 通过，关闭页面与 Package、删除元素库副本 |

## 转变来源（A/B 方案）

`wait_appear()` 的核心是「**等待期间**元素出现」，所以必须有一个在等待过程中发生的转变。
单线程脚本在等待里阻塞时无法自己触发页面变化，因此：

- **`delayed-page`（canonical，靶场自计时页已部署并实测）**：`public/delayed-element.html`
  每 1.5s 交替插入/移除**同一个** `#delayed-target` 节点，**由页面自己计时，测试侧零调度**。
- **`scheduled`（回退方案）**：测试侧用 `execute_javascript` 注入稳定探针节点并挂在
  `window.__uiautomaWaitNode`，**同一个节点**移除后在 1.2s 后原样插回。
- **`auto`（默认值）**：先探测 `delayed-page` 是否可达，可达则用它，否则回退 `scheduled`。

名称/Selector 目标的「等待出现」不走上面两条：在**导航尚未完成时就开始等待**
（`navigate(..., load_timeout=0)` → `wait_appear(name, N)`），元素随路由切换出现，测试侧同样零调度。

### 自计时页面（B）已落地

| 项 | 内容 |
|---|---|
| 页面文件 | `xpath` 靶场仓库 `WEB/public/delayed-element.html`（与 `slow-load-30s.html` 同级） |
| 目录登记 | `WEB/src/pages/HomePage.tsx` 的 `menuItems` 新增 `menu-delayed-element` 卡片（与 `menu-slow-load-30s` 同风格） |
| 线上地址 | `https://baobaomi900901.github.io/xpath/delayed-element.html`（HTTP 200，5289 字节；`main` 分支 push 后由 `.github/workflows/pages.yml` 自动部署） |
| 页面行为 | 加载后立即 `absent`，之后每 1.5s 交替 present/absent；`?interval=3000` 可调整 |
| 自证信息 | `#delayed-state`、`#delayed-cycles`、`#delayed-created-count` 与 `#delayed-host[data-created-count]`（**节点创建次数恒为 1**） |

**页面设计约束（来自本轮实测）**：节点**只 `createElement` 一次**，之后只用 `appendChild` / `remove`
反复挂载同一个节点 —— 因为元素引用按节点身份绑定，每次新建节点会让旧 `WebElement` 永远等不到。
另外「消失」必须是**真的移出 DOM**，不能用 `display:none`（存在性判定不区分可见性）。

线上同源实测（`auto` 选中该页）：

| 用例 | 实测 |
|---|---|
| 页面自计时 | 4.5s 内 3 次切换 `[(1.55, absent), (2.94, present), (4.48, absent)]`，测试侧零调度 |
| 同一节点 | `#delayed-created-count=1`、`data-created-count=1`（已切换 5 轮） |
| 已存在 / 被移除 / `timeout=0` | `True`（0.007s）/ `False`（1.001s）/ `False`（0.007s） |
| **等待出现（canonical）** | 页面自己把同一节点挂回 → `True`（**0.533s**，零调度） |
| `timeout=-1` | 页面自己让它出现 → `True`（1.461s） |

> 在本地 dev 服务器（`localhost:7199`）上也跑过同一分支：因元素库保存路径绑定部署域名，
> 名称/Selector 用例需 `--skip-name-cases` 跳过，其余用例同样全绿；该轮记录已被线上同源运行取代。

## 已实测确立的判据

| 事实 | 结论 | 证据 |
|---|---|---|
| `exists` 的语义 | **DOM 存在性**，不区分可见性 | 隐藏节点（`display:none`、`getClientRects()=0`）仍返回 `True`；另在 `/keys-click-test` 遮挡弹窗上复现（关闭后 `display:none` 仍 `True`） |
| WebElement 目标的重新解析 | 按**节点身份**绑定 | 同一节点移除后插回 → `True`（1.25s）；React 销毁重建的新节点 → `False` |
| 名称/Selector 目标 | 每轮询按库里的保存路径重新定位 | 路由切换后库元素出现 → `True`（1.41s） |
| 目标入参范围 | 只支持库元素名 / `Selector` / `WebElement` | `wait_appear("#menu-anchor-test", 2)` → `ActionError: 未找到选择器`（0.001s） |
| 轮询粒度 | 运行时 0.1s 一轮 | 1.2s 调度 → 1.254s 返回（附加延迟约 0.05~0.2s） |

## 已知边界 1：WebElement 目标按「节点身份」绑定，节点被销毁重建后不再认领

复现（脚本用例 `recreated_node_not_matched`）：

1. 在靶场首页绑定卡片 `#menu-anchor-test` → 得到 `WebElement`（id A）；
2. 用首页搜索框（原生 setter + `input` 事件触发 React）按标题过滤，使该卡片**从 DOM 移除**
   （实测 `{cards: 1, target: False}`）；
3. 清空搜索，同形卡片重新出现（实测 `{cards: 16, target: True}`）；
4. 对旧引用调用 `wait_appear(element, 2)` → **`False`（2s 超时）**；
   此时重新 `find_by_css` 得到的新 id B 立刻可用（`wait_appear` → `True`）。

对照：注入的探针节点用 `remove()` + `appendChild()` **复用同一节点**时，`wait_appear` 可以等到
（1.25s 返回 `True`）。可见差异不在「元素是否回来了」，而在**是不是同一个节点对象**。

影响：把 `WebElement` 当作长期句柄、等待它「重新出现」在 React/Vue 这类会重建节点的框架下会一直等到超时；
需要等「同选择器的元素再次出现」时应改用**库元素名称或 `Selector` 目标**（每轮重新定位）。
本项作为 API 语义边界如实记录（`KNOWN`，不计入退出码），是否补文档或改行为由维护者决定。

## 已知边界 2：内部轮询一次失败会让等待整体报错（而非继续等到超时）

首轮验收中 `name_on_wrong_page_false` 该项出现一次失败（原文）：

```text
ActionError: 网页操作超时，请检查页面是否加载完成或存在弹窗 [trace=page_runtime_probe_timeout]  (2.002s)
```

即：页面刚导航完、页面运行时正在重新安装时，内部轮询拿到了 `page_runtime_probe_timeout`，
`web_browser_wait_element` 的 `if result.get("error"): return result` 直接把它当成最终结果返回，
于是**等了一轮就抛错**，而不是继续等到 2s 截止时间。此前在路由切换场景还观测到同类现象
`frame_not_found`（`目标域已被移除或重新加载`）。

本项以 `KNOWN` 记录且**只在真实出现时**输出；脚本随后加入「导航后先用 `find_all_by_css("html")`
预热页面运行时」+ 瞬时错误重试，之后 **3 次完整运行未再出现**。对调用方而言，
超时前的一次瞬时失败会变成异常，属健壮性问题；待维护者决定是否改为轮询内重试。
（对照：`frame_not_found` 场景在预热后的 5/5 次复测中都返回了 `True`。）

## 已知边界 3：路由切换期间等待曾撞坏框架绑定（已改用更稳的写法）

早期脚本用 `execute_javascript` 调度 `location.hash` 切换来制造「名称目标稍后出现」，
在部署站同源运行中出现过 `frame_not_found`（`目标域已被移除或重新加载`，1.266s），
且紧随其后的调用也立即失败（0.013s，另一 trace `Frame with ID 0 is showing error page`），
需重新 `navigate` 才恢复。

对照实验（`name_appear_probe`，各 5 轮）：

| 写法 | 结果 |
|---|---|
| **A**：`navigate(iframe 路由, load_timeout=0)` 后立即 `wait_appear(name, 8)` | **5/5 成功**，耗时 0.17~0.23s |
| B：`execute_javascript` 调度 `location.hash` 后 `wait_appear` | 5/5 成功，耗时固定 1.38s |

**已改为写法 A**：它是「不等待导航完成 + 等元素出现」这一自然用法，测试侧完全不注入调度 JS，
耗时还短一个数量级。改用后 `auto` 模式连续 3 次完整运行（31/31）均无重试、无该 trace。
脚本仍保留一次「上下文重置 + 重试」，一旦真的用到就以 `KNOWN`（`route_change_frame_flake`）如实记录。

另有一次专项定位（`frame_state_probe`）说明**跨源往返本身不会触发**：部署站首页 ↔ localhost
自计时页往返后，`wait_appear(name, 3)` 语义正常，再次进入 iframe 路由仍 `True`（0.02s）。
即该现象与「页面自身路由切换 + 等待同时在飞」相关，而非跨源导航本身。

## 与 `wait_disappear()` 的关系

两者共用同一实现 `_wait_element(target, timeout, state)`，仅 `wait_state` 取 `present` / `absent`。
本文件只覆盖 `wait_appear()`；`wait_disappear()` 尚未验收（同族下一个候选）。
由本轮的 `exists` 语义可推断：**隐藏元素不会被判为「消失」**，`wait_disappear` 只对
「节点真的从 DOM 移除」有效——该推断留待其自身验收时实证。

## 复测

脚本：[test_web_browser_wait_appear.py](../test_web_browser_wait_appear.py)
原始产物：[artifacts/wait_appear_20260915.txt](artifacts/wait_appear_20260915.txt)（`auto` 模式，31/31 + 1 边界，退出码 0）

```powershell
uv run .\web\test_web_browser_wait_appear.py                        # auto：探测自计时页，可达即用它（当前为 delayed-page）
uv run .\web\test_web_browser_wait_appear.py --transition-source delayed-page
uv run .\web\test_web_browser_wait_appear.py --transition-source scheduled      # 回退方案：测试侧注入探针节点
uv run .\web\test_web_browser_wait_appear.py --json
uv run .\web\test_web_browser_wait_appear.py --contract-only

# 本地 dev server 上的自计时页：元素库绑定部署域名，需跳过名称/Selector 用例
uv run .\web\test_web_browser_wait_appear.py --transition-source delayed-page `
  --delayed-page-url http://localhost:7199/delayed-element.html --skip-name-cases
```

元素库副本与探针节点都在本次运行内创建并在收尾删除/移除；脚本不写入任何产品文件。

退出码：`0` = 全部 PASS（允许 KNOWN）；`1` = 存在 FAIL；`2` = 无非 FAIL 但存在 BLOCKED。

## 明确排除

- **`wait_disappear()`**：同族另一 API，未测（同族下一个候选）。
- **跨 iframe / 跨 frame 的等待**：库元素本身在 iframe 内（已覆盖），但未覆盖「等待 iframe 自身出现」。
- **元素在等待期间被替换为同形新节点后的自动重新绑定**：见已知边界 1，属当前语义不支持的用法。
- **`timeout=-1` 且元素永不出现**：会一直阻塞，未构造（避免无法收尾）。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `stale_page_reference` 等页面失效路径下的等待语义：仅覆盖了页面关闭后的拒绝。
