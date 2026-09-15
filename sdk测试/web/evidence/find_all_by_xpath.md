# `WebBrowser.find_all_by_xpath()` 初次测试

## 用途

在当前页面查找与 XPath 表达式匹配的**全部**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `xpath_selector` | 必填 | XPath 表达式字符串 |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `list[WebElement]`；**超时仍未找到时返回空列表**。

靶场为维护者的官方靶场 `.../xpath/#/form-controls`（测试侧不自建页面）；
期望值来自**活 DOM 推导**（先读 `document.querySelectorAll('input').length` 与 `#root` 唯一性）。

## 真实验收结果

**VERIFIED：22/22 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`xpath_selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `list[WebElement]` |
| 元素库准备 / 页面准备 / 活 DOM 推导 | 通过（`input` 37 个、`#root` 唯一、随机 id 不存在） |
| **多命中数量与 DOM 一致** | 通过，`//input` 返回 `list[37]`，与 JS 读数一致 |
| 唯一命中 | 通过，`//*[@id="root"]` 返回 `list[1]` |
| **未匹配（`timeout=3`）** | 通过，**返回空列表且不抛异常**（等满 3s） |
| 未匹配（`timeout=0`） | 通过，返回空列表（立即） |
| `timeout=0` 且存在 | 通过，`list[1]` |
| **语法非法 `///`** | 通过，`RpcProtocolError`（**不返回空列表**） |
| 语法非法后页面仍可用 | 通过 |
| 空 / 全空白 / 非字符串选择器 | 通过，`InvalidParamsError` |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError` |
| 缺参 / `timeout` 位置传入 | 通过，`TypeError` |
| 页面关闭复核 / Package 关闭复核 | 通过 |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| 资源清理 | 通过，关页（复核无残留）、关 Package、删除副本 |

## 与 `find_by_xpath()` 的差异

| 场景 | `find_by_xpath()` | `find_all_by_xpath()` |
|---|---|---|
| 多命中 | 抛 `AmbiguousElementError` | 返回全部 |
| 未匹配 | 抛 `ElementNotFoundError`（等满 timeout） | **返回 `[]`** |
| **语法非法** | 抛 `RpcProtocolError` | **同样抛 `RpcProtocolError`** |
| 唯一命中 | 返回 `WebElement` | 返回 `list[1]` |

第三行是关键坑：`find_all` 并不意味着「查不到就返回空列表」——
**表达式语法非法时它一样抛异常**，只有「语法合法但无匹配」才返回 `[]`。

## 复测

脚本：[test_web_browser_find_all_by_xpath.py](../test_web_browser_find_all_by_xpath.py)
原始产物：[artifacts/find_all_by_xpath_20260915.txt](artifacts/find_all_by_xpath_20260915.txt)

```powershell
uv run .\web\test_web_browser_find_all_by_xpath.py
uv run .\web\test_web_browser_find_all_by_xpath.py --json
uv run .\web\test_web_browser_find_all_by_xpath.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **元素列表上限**：匹配极多时的截断行为未验证。
- **`timeout=-1`**：未验证。
- 复杂 XPath 能力、Shadow DOM / iframe 内查找。
- 非法语法的错误类型是否应改为参数错误（同 `find_by_xpath.md` 的记录）。
- Edge、CEF 与 Auto 模式。

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-09-15 | 首版用测试侧自建本地 fixture 靶场（20/20），按维护者要求**删除重做** |
| 2026-09-15 | 重做为官方靶场 + 活 DOM 推导，加入关闭复核，现为 22/22 |
