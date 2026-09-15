# `WebBrowser.get_scroll()` 初次测试

## 用途

获取网页滚动条位置。

| 参数 | 默认 | 说明 |
|---|---|---|
| `direction` | `vertical` | `vertical`（上下）、`horizontal`（左右） |
| `location` | `current` | `current`（当前位置）、`bottom`（底部） |

两个参数**仅限关键字**；返回 `float`。非法 `direction` / `location` 在 SDK 侧即抛
`InvalidParamsError("滚动条方向或位置无效")`。

**语义要点**：`location="current"` 返回当前偏移（`scrollTop` / `scrollLeft`）；
`location="bottom"` 返回**滚动内容的总高/总宽**（`scrollHeight` / `scrollWidth`），
**不是**最大可滚动偏移。因此本脚本对 `bottom` 的断言是与内容尺寸相等，而不是与视口相关的最大偏移。

## 真实验收结果

**VERIFIED：15/15 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/form-controls`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`direction`/`location` 仅限关键字（默认 `vertical`/`current`），返回注解 `float` |
| 页面准备 / 初始状态 | 通过 |
| 可滚动准备 | 通过，注入 spacer 后 `scrollHeight=9766`、`scrollWidth=4000` |
| 位于顶部时默认读数 | 通过，返回 `float 0.0` |
| `current` 与 JS 读数一致 | 通过，`scroll_to(point top=300)` 后返回 `float 300.0`，与 `window.scrollY` 相等 |
| `vertical/bottom` | 通过，返回 `float 9766.0` == `documentElement.scrollHeight` |
| `horizontal/current` | 通过，`scroll_to(point left=250)` 后返回 `float 250.0`，与 `window.scrollX` 相等 |
| `horizontal/bottom` | 通过，返回 `float 4000.0` == `documentElement.scrollWidth` |
| 四种参数组合 | 通过，`vertical/horizontal` × `current/bottom` 全部返回 `float` |
| 非法 `direction` / `location` | 通过，`InvalidParamsError` 拒绝 |
| 位置参数 / 未知关键字 | 通过，`TypeError` / `TypeError` |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 交叉核对方式

本 API 的每个读数都与**同页面的独立 JS 读数**核对（`execute_javascript()` 已独立验收）：

| 用例 | API 读数 | 独立 JS 读数 |
|---|---|---|
| `current`（纵向，point 300） | `300.0` | `window.scrollY = 300` |
| `current`（横向，point 250） | `250.0` | `window.scrollX = 250` |
| `bottom`（纵向） | `9766.0` | `documentElement.scrollHeight = 9766` |
| `bottom`（横向） | `4000.0` | `documentElement.scrollWidth = 4000` |

## 与文档的一处不一致（仅记录，未判定为缺陷）

公开 docstring 的 `Raises` 只写了 `ActionError`，而实际非法参数抛的是 SDK 侧的
`InvalidParamsError("滚动条方向或位置无效")`（校验发生在 SDK 内，不发起 Runtime 调用）。
同族的 `scroll_to()` 文档则同时写了 `InvalidParamsError`。是否补齐文档由源码侧决定，
测试侧未改源码。

## 环境说明（影响后续验收）

本次运行时 Chrome 主窗口最小化，标签页视口为 0×0（`window.innerHeight === 0`，
MAIN 与 ISOLATED 两个世界读数一致）。这不影响 `get_scroll` 的断言（读数以内容尺寸与
`scrollY/scrollX` 为准，且均已用关系式而非固定视口假设），但会让 `bottom` 的数值恰好等于
内容总尺寸。依赖真实视口的 API 验收前应先还原 Chrome 窗口。

## 复测

脚本：[test_web_browser_get_scroll.py](../test_web_browser_get_scroll.py)
原始产物：[artifacts/get_scroll_20260915.txt](artifacts/get_scroll_20260915.txt)

```powershell
uv run .\web\test_web_browser_get_scroll.py
uv run .\web\test_web_browser_get_scroll.py --json
uv run .\web\test_web_browser_get_scroll.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- 页面内部滚动容器（非文档根元素）的滚动位置读取。
- `iframe` 子框架内的滚动位置。
- 平滑滚动过程中的中间值采样（依赖合成器，最小化窗口下不可靠）。
- 页面缩放（zoom）与设备像素比影响下的读数换算。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `WebElement.get_scroll()`（元素级滚动位置）属另一公开 API，本次未覆盖。
