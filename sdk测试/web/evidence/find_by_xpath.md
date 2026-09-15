# `WebBrowser.find_by_xpath()` 初次测试

## 用途

在当前页面查找与 XPath 表达式匹配的**唯一**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `xpath_selector` | 必填 | XPath 表达式字符串，例如 `//button[@id='submit']` |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `WebElement`。靶场：本地静态 fixture（`http://127.0.0.1:18642/index.html`，脚本自起自停），
理由与 DOM 结构见 [`find_by_css.md`](find_by_css.md)。

## 真实验收结果

**VERIFIED：21/21 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`xpath_selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `WebElement` |
| 元素库准备 / 页面准备 | 通过（`web_count=70`；本地 fixture 打开成功） |
| id 谓词 `//*[@id="unique-target"]` | 通过，`name='唯一目标'` |
| **属性谓词** `//input[@type="password"]` | 通过，`name='secret'` |
| **索引谓词** `//ul[@id="list"]/li[2]` | 通过，`name='beta'` |
| 多命中 `//input` | 通过，`AmbiguousElementError`（0.015s，"元素匹配结果不唯一"） |
| 未命中（`timeout=3`） | 通过，`ElementNotFoundError`（"未找到匹配元素"，3.001s 等满超时） |
| 未命中（`timeout=0`） | 通过，`ElementNotFoundError`（0.004s 立即） |
| `timeout=0` 且存在 | 通过，仍命中 |
| **语法非法 `//[`** | 通过，`RpcProtocolError`（"Web 元素操作失败，请重试"，0.016s） |
| 语法非法后页面仍可用 | 通过，`get_title()` 正常返回 |
| 空 / 全空白 / 非字符串选择器 | 通过，`InvalidParamsError`（"选择器不能为空"） |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError` |
| 缺参 / `timeout` 位置传入 | 通过，`TypeError` |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| 资源清理 | 通过，关页、关 Package、删除副本、停止 fixture（端口已释放） |

## XPath 的三种「查不到」语义不同（实测区分）

| 情形 | 异常 | 耗时 | 说明 |
|---|---|---|---|
| 表达式**语法非法**（`//[`、`///`） | `RpcProtocolError` | **0.016s** | 页面侧求值失败，立即返回 |
| 语法**合法但匹配不到**（`//*[@id="x"]`） | `ElementNotFoundError` | **3.001s** | 等满 timeout |
| 匹配到**多个**（`//input`） | `AmbiguousElementError` | 0.015s | 立即返回 |

其中第一行的 `RpcProtocolError`（协议层异常）值得注意：**用户写错 XPath 语法时得到的是
协议错误而不是参数错误**（`InvalidParamsError`），公开文案为「Web 元素操作失败，请重试」。
本次仅如实记录该行为，未判定为缺陷；是否改为参数错误由源码侧决定。

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

- **`timeout=-1`（一直等待）**：未验证（需要元素永不出现且可中断的场景）。
- 复杂 XPath 能力（`following-sibling`、`text()` 精确匹配、`contains()`、轴与函数组合等）
  未逐一验证；本次覆盖 id / 属性 / 索引谓词三条基本路径。
- Shadow DOM 与 iframe 内的 XPath 查找。
- 命名空间、XPath 2.0+ 语法（浏览器原生仅支持 XPath 1.0）。
- Edge、CEF 与 Auto 模式。
