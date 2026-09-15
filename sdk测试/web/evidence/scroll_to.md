# `WebBrowser.scroll_to()` 初次测试

## 用途

滚动页面到指定位置。

| 参数 | 默认 | 说明 |
|---|---|---|
| `location` | `bottom` | `bottom`（底部）、`top`（顶部）、`point`（指定位置） |
| `behavior` | `instant` | `instant`（瞬间）、`smooth`（平滑） |
| `top` | `0` | 距页面顶部的 CSS 像素，仅 `point` 生效 |
| `left` | `0` | 距页面左侧的 CSS 像素，仅 `point` 生效 |

四个参数**全部仅限关键字**；返回 `None`。非法 `location` / `behavior` 在 SDK 侧即
抛 `InvalidParamsError`（trace `invalid_params`）。

## 真实验收结果

**VERIFIED：16/16 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/form-controls`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，四个参数均为仅限关键字（默认 `bottom`/`instant`/`0`/`0`），返回 `None` |
| 页面准备 / 初始状态 | 通过 |
| 可滚动准备 | 通过，注入 spacer 后 `scrollHeight=9766`、`scrollWidth=4000` |
| 默认滚到底部 | 通过，`scrollY=9766`、`scrollX=4000`（纵向与横向均到底） |
| `location="top"` | 通过，`scrollY=0` 且**保留横向位置** `scrollX=4000` |
| `point(top=300,left=250)` | 通过，精确落点 `scrollY=300`、`scrollX=250` |
| `point(left=120)`（只给 left） | 通过，`scrollX=120` 且 `scrollY` 归 `0` |
| 越界 `point(999999,999999)` | 通过，被浏览器夹取到底部（`scrollY=9766`、`scrollX=4000`） |
| 负值 `point(-50,-50)` | 通过，被夹取到 `scrollY=0`、`scrollX=0` |
| `behavior="smooth"` | 通过，与原生 `window.scrollTo({behavior:'smooth'})` **行为一致**（见下节） |
| 非法 `location` / `behavior` | 通过，`InvalidParamsError`（trace `invalid_params`） |
| 位置参数 / 未知关键字 | 通过，`TypeError` / `TypeError` |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 场景准备与断言方式

- **可滚动条件**：靶场页面本身很高但不横向溢出，因此脚本用已验证的
  `execute_javascript()` 注入 4000×4000 的 spacer 保证双向可滚动。这是场景准备，
  不属于被测 API 的内容。
- **独立量具**：位置读数取自同页面的 JS（`window.scrollY/scrollX`、
  `documentElement.scrollHeight/scrollWidth`），不只看 `scroll_to` 自身返回值。
- **底部判定用关系式** `scrollY + clientHeight >= scrollHeight`，避免依赖特定视口高度。

## `behavior="smooth"` 的验证方式（重要）

首次运行时「smooth 应从 1500 收敛到 0」未通过。对照实验证明**不是产品缺陷**：

| 对照 | 结果 |
|---|---|
| 产品 `scroll_to(location="top", behavior="smooth")` | `scrollY` 保持 1500，不推进 |
| **原生** `window.scrollTo({top:0, behavior:'smooth'})`（引擎用的同一条语句） | `scrollY` 同样保持 1500，不推进 |
| 原生 `behavior:'instant'` 同目标 | 立即到 0 |
| 环境 `prefers-reduced-motion` / `documentElement` CSS `scroll-behavior` | `false` / `auto`（均非抑制因素） |

即产品把 `behavior` **忠实透传**给浏览器 API，未推进动画是浏览器侧行为。因此该用例最终
断言改为**「产品行为 == 原生同语句行为」**（终值相等），并把是否收敛记入产物；不硬要求动画收敛。

根因与环境有关：`window.innerHeight === 0`（MAIN 与 ISOLATED 两个世界读数一致），
Chrome 主窗口当时处于**最小化**状态（`IsIconic=True`，窗口矩形 160×28），合成器不为
0 尺寸视口驱动平滑滚动动画。详见下节。

## 环境说明（影响后续验收）

本次运行时 Chrome 主窗口最小化，标签页视口为 0×0：

- `scroll_to(location="bottom")` 恰好落在 `scrollHeight`（最大偏移 = 内容高 − 视口高 = 9766）；
- `behavior="smooth"` 无法验证收敛，只能验证与原生行为一致；
- **依赖真实视口的 API**（页面/元素截图、`get_bounding`、`highlight`、`drag_to` 的像素语义等）
  在最小化窗口下语义可能不同或不可验证，开始这些 API 的验收前应先还原并置前 Chrome 窗口。

## 复测

脚本：[test_web_browser_scroll_to.py](../test_web_browser_scroll_to.py)
原始产物：[artifacts/scroll_to_20260915.txt](artifacts/scroll_to_20260915.txt)

```powershell
uv run .\web\test_web_browser_scroll_to.py
uv run .\web\test_web_browser_scroll_to.py --json
uv run .\web\test_web_browser_scroll_to.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`behavior="smooth"` 的动画收敛**：最小化窗口下浏览器不驱动动画，本次只能验证透传保真。
- 页面内部滚动容器（非文档根元素）的滚动语义。
- `iframe` 子框架内的滚动。
- 触摸板/滚轮引起的惯性滚动与用户交互并发。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `WebElement.scroll_to()`（元素级滚动）属另一公开 API，本次未覆盖。
