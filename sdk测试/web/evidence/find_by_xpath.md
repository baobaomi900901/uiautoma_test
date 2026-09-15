# `WebBrowser.find_by_xpath()` 初次测试

## 用途

在当前页面查找与 XPath 表达式匹配的**唯一**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `xpath_selector` | 必填 | XPath 表达式字符串 |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `WebElement`。靶场为维护者的官方靶场 `.../xpath/#/form-controls`（测试侧不自建页面）。

期望值来自**活 DOM 推导**：先读 `document.querySelectorAll('input').length` 与 `#root` 唯一性，
再与 API 结果比对；「不存在」用每轮随机生成的 id。

## 真实验收结果

**VERIFIED：22/22 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`xpath_selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `WebElement` |
| 元素库准备 / 页面准备 / 活 DOM 推导 | 通过（`input` 37 个、`#root` 唯一、随机 id 不存在） |
| id 谓词 `//*[@id="root"]` | 通过，唯一命中（`rt:web:` 前缀） |
| 多命中 `//input` | 通过，`AmbiguousElementError`（"元素匹配结果不唯一"） |
| 未命中（`timeout=3`） | 通过，`ElementNotFoundError`（等满 3s） |
| 未命中（`timeout=0`） | 通过，`ElementNotFoundError`（立即） |
| `timeout=0` 且存在 | 通过，仍命中 |
| **语法非法 `//[`** | 通过，`RpcProtocolError`（"Web 元素操作失败，请重试"，立即） |
| 语法非法后页面仍可用 | 通过 |
| 空 / 全空白 / 非字符串选择器 | 通过，`InvalidParamsError` |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError` |
| 缺参 / `timeout` 位置传入 | 通过，`TypeError` |
| 页面关闭复核 / Package 关闭复核 | 通过 |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| 资源清理 | 通过，关页（复核无残留）、关 Package、删除副本 |

## XPath 的三种「查不到」语义不同

| 情形 | 异常 | 耗时 |
|---|---|---|
| 语法**非法**（`//[`、`///`） | `RpcProtocolError` | 立即（0.015s） |
| 语法合法但**匹配不到** | `ElementNotFoundError` | 等满 timeout（3.001s） |
| 匹配到**多个**（`//input`） | `AmbiguousElementError` | 立即（0.003s） |

第一行的 `RpcProtocolError` 是协议层异常：**用户写错 XPath 语法时拿到的是协议错误而非参数错误**，
公开文案为「Web 元素操作失败，请重试」。本次仅如实记录，是否改为参数错误由源码侧决定。

## 复测

脚本：[test_web_browser_find_by_xpath.py](../test_web_browser_find_by_xpath.py)
原始产物：[artifacts/find_by_xpath_20260915.txt](artifacts/find_by_xpath_20260915.txt)

```powershell
uv run .\web\test_web_browser_find_by_xpath.py
uv run .\web\test_web_browser_find_by_xpath.py --json
uv run .\web\test_web_browser_find_by_xpath.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`timeout=-1`**：未验证。
- 复杂 XPath 能力（轴、函数、`text()` 精确匹配、`contains()` 等）未逐一验证；本次覆盖 id 谓词。
- Shadow DOM 与 iframe 内的 XPath 查找；XPath 2.0+ 语法（浏览器原生仅支持 1.0）。
- Edge、CEF 与 Auto 模式。

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-09-15 | 首版用测试侧自建本地 fixture 靶场（21/21），按维护者要求**删除重做** |
| 2026-09-15 | 重做为官方靶场 + 活 DOM 推导，加入关闭复核，现为 22/22 |
