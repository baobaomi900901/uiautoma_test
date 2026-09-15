# `WebBrowser.find_all_by_css()` 初次测试

## 用途

在当前页面查找与 CSS 选择器匹配的**全部**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `css_selector` | 必填 | CSS 选择器字符串 |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `list[WebElement]`；**超时仍未找到时返回空列表**。

靶场：本地静态 fixture（`http://127.0.0.1:18642/index.html`，脚本自起自停），
理由与 DOM 结构见 [`find_by_css.md`](find_by_css.md)；`--target-url` 可换任意页面。

## 真实验收结果

**VERIFIED：18/18 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`css_selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `list[WebElement]` |
| 元素库准备 / 页面准备 | 通过（`web_count=70`；`inputs=4`, `li.item=3`） |
| 多命中 `input` | 通过，返回 `list[4]`，且顺序为 **DOM 顺序**：`['first', 'second', 'secret', 'solo@example.com']` |
| 类选择器 `li.item` | 通过，返回 `list[3]`：`['alpha', 'beta', 'gamma']` |
| 唯一命中 `#unique-target` | 通过，返回 `list[1]`：`['唯一目标']` |
| **未匹配（`timeout=3`）** | 通过，**返回空列表且不抛异常**（3.001s） |
| 未匹配（`timeout=0`） | 通过，返回空列表（0.004s） |
| `timeout=0` 且存在 | 通过，返回 `list[1]` |
| 空 / 全空白 / 非字符串选择器 | 通过，`InvalidParamsError`（"选择器不能为空"） |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError` |
| 缺参 / `timeout` 位置传入 | 通过，`TypeError` |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| 资源清理 | 通过，关页、关 Package、删除副本、停止 fixture（端口已释放） |

## 与 `find_by_css()` 的差异

| 场景 | `find_by_css()` | `find_all_by_css()` |
|---|---|---|
| 多命中 | 抛 `AmbiguousElementError` | **返回全部**（本次 4 个 / 3 个） |
| 未匹配 | 抛 `ElementNotFoundError`（等满 timeout） | **返回 `[]`**（等满 timeout） |
| 唯一命中 | 返回 `WebElement` | 返回 `list[1]` |

## 附带验证：返回顺序 = DOM 顺序

`input` 与 `li.item` 两组多命中的返回顺序与文档顺序完全一致
（`first → second → secret → solo@example.com`；`alpha → beta → gamma`）。
这一条在元素库路径的 `find_all.md` 中被列为「未断言顺序」，此处用可控 fixture 补齐了结论，
但注意**结论范围仅限 CSS 选择器**。

## 复测

脚本：[test_web_browser_find_all_by_css.py](../test_web_browser_find_all_by_css.py)
原始产物：[artifacts/find_all_by_css_20260915.txt](artifacts/find_all_by_css_20260915.txt)

```powershell
uv run .\web\test_web_browser_find_all_by_css.py
uv run .\web\test_web_browser_find_all_by_css.py --json
uv run .\web\test_web_browser_find_all_by_css.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **元素列表上限**：若匹配节点极多时的截断行为未验证（fixture 最多 4 个）。
- **`timeout=-1`（一直等待）**：未验证。
- 复杂 CSS 语法、Shadow DOM、iframe 内的多命中（同 `find_by_css.md`）。
- 无效 CSS 语法的报错形态。
- Edge、CEF 与 Auto 模式。
