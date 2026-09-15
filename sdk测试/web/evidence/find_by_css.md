# `WebBrowser.find_by_css()` 初次测试

## 用途

在当前页面查找与 CSS 选择器匹配的**唯一**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `css_selector` | 必填 | CSS 选择器字符串 |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `WebElement`。实现走 `_find(_text_query("css", ...))` → `get_package()._find_web_elements(...)`，
因此**需要已打开的 Package**（作为会话），但选择器本身与元素库内容无关。

## 靶场与期望值来源

- **靶场**：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/#/form-controls`
  （**不由测试侧自建页面**；靶场由维护者维护，push 后自动部署）。
- **期望值来自活 DOM 推导**：脚本先用 `execute_javascript()` 现场读取
  `document.querySelectorAll('input').length`、`#root` 是否唯一、随机 id 是否存在，
  再与 API 结果比对 —— 脚本内**不写死任何匹配数量**，靶场改版后仍可复用。
- **「不存在」的选择器**：每次运行随机生成 `#uiautomata-absent-<uuid>`，无需靶场预留类名。

本次实测的活 DOM 事实：`input` 37 个、`#root` 唯一、随机 id 匹配 0 个。

## 真实验收结果

**VERIFIED：22/22 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`css_selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `WebElement` |
| 元素库准备 | 通过，副本打开后 `web_count=70` |
| 页面准备 | 通过，官方靶场页打开成功 |
| 活 DOM 推导 | 通过，`input` 匹配 37 个、`#root` 唯一、随机 id 确认不存在 |
| 唯一命中 `#root` | 通过，运行时 id 前缀 `rt:web:` |
| **多命中 `input`** | 通过，`AmbiguousElementError`（"元素匹配结果不唯一"，0.003s） |
| 未命中（`timeout=3`） | 通过，`ElementNotFoundError`（**3.001s** 等满超时） |
| 未命中（`timeout=0`） | 通过，`ElementNotFoundError`（0.029s 立即） |
| `timeout=0` 且存在 | 通过，仍命中 |
| **CSS 语法非法 `input[`** | 通过，`RpcProtocolError`（0.015s，"Web 元素操作失败，请重试"） |
| 语法非法后页面仍可用 | 通过，`get_title()` 正常 |
| 空 / 全空白 / 非字符串选择器 | 通过，`InvalidParamsError`（"选择器不能为空"） |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError` |
| 缺参 / `timeout` 位置传入 | 通过，`TypeError` |
| **页面关闭复核** | 通过，`close()` 后 `web.get_all()` 证实无残留 |
| **Package 关闭复核** | 通过 |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| 资源清理 | 通过，关页（复核无残留）、关 Package、删除元素库副本 |

本次为**重做**（首版用测试侧自建 fixture 靶场，已按维护者要求删除重做）。

## 复测

脚本：[test_web_browser_find_by_css.py](../test_web_browser_find_by_css.py)
原始产物：[artifacts/find_by_css_20260915.txt](artifacts/find_by_css_20260915.txt)

```powershell
uv run .\web\test_web_browser_find_by_css.py
uv run .\web\test_web_browser_find_by_css.py --json
uv run .\web\test_web_browser_find_by_css.py --contract-only
```

`--target-url` 可换其它靶场页；`--library` 可换元素库目录。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`timeout=-1`（一直等待）**：未验证。
- 复杂 CSS 语法（`:nth-child`、伪类、`:has()`、属性通配等）未逐一验证；本次覆盖 id 与标签选择器。
- Shadow DOM / iframe 内的 CSS 查找。
- 匹配数量极大的截断行为。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-09-15 | 首版用测试侧自建本地 fixture 靶场（18/18），按维护者要求**删除重做** |
| 2026-09-15 | 重做为官方靶场 + 活 DOM 推导，并加入页面关闭复核与真实清理判定，现为 22/22 |
