# `WebBrowser.find_by_css()` 初次测试

## 用途

在当前页面查找与 CSS 选择器匹配的**唯一**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `css_selector` | 必填 | CSS 选择器字符串，例如 `#submit` |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `WebElement`。实现上走 `_find(_text_query("css", ...))` → `get_package()._find_web_elements(...)`，
因此**需要已打开的 Package**（元素库作为会话），但**选择器本身与元素库内容无关**。

## 靶场选择：本地静态 fixture

本次使用**本地 fixture 页面**（`http://127.0.0.1:18642/index.html`），由脚本按需自起自停，
而不是公开靶场。理由：

1. 本 API 只关心「在当前页面上按 CSS 选择器定位」，与具体站点无关；
2. 本地 DOM 完全可控（唯一 1 个 / 多命中 4 个或 3 个 / 不存在 0 个），比公开靶场更适合断言选择器语义；
3. **不依赖外网** —— 2026-09-15 本次验收期间公开靶场与全部外网均不可达，
   本地 fixture 让验收得以继续。

原始失败记录（供参考）：该时点直连与系统代理（`127.0.0.1:7897`）访问
`baobaomi900901.github.io`、`example.com`、`github.com` 全部超时/SSL 失败。

`--target-url` 可换成公开靶场等任意页面；此时脚本不会自起本地服务。

### fixture DOM（脚本内置）

| 选择器 | 匹配数 | 说明 |
|---|---|---|
| `#unique-target` | 1 | 文本「唯一目标」 |
| `#wrapper input#solo` | 1 | 复合选择器，`value="solo@example.com"` |
| `input` | 4 | `first` / `second` / `secret` / `solo@example.com` |
| `li.item` | 3 | `alpha` / `beta` / `gamma` |
| `.uiautoma-absent` | 0 | 用于未命中路径 |

## 真实验收结果

**VERIFIED：18/18 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`css_selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `WebElement` |
| 元素库准备 | 通过，打开副本后 `web_count=70` |
| 页面准备 | 通过，本地 fixture 打开成功（`inputs=4`, `li.item=3`） |
| 唯一命中 `#unique-target` | 通过，`name='唯一目标'` |
| 复合选择器 `#wrapper input#solo` | 通过，`name='solo@example.com'` |
| **多命中 `input`** | 通过，`AmbiguousElementError`（"元素匹配结果不唯一"，0.022s） |
| **未命中（`timeout=3`）** | 通过，`ElementNotFoundError`（"未找到匹配元素"，**3.003s** 等满超时） |
| 未命中（`timeout=0`） | 通过，`ElementNotFoundError`（**0.01s** 立即） |
| `timeout=0` 且存在 | 通过，仍命中 |
| 空 / 全空白 / 非字符串选择器 | 通过，`InvalidParamsError`（"选择器不能为空"） |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError` |
| 缺参 / `timeout` 位置传入 | 通过，`TypeError` |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| 资源清理 | 通过，关页、关 Package、删除元素库副本、停止 fixture 服务（端口已释放） |

## 复测

脚本：[test_web_browser_find_by_css.py](../test_web_browser_find_by_css.py)
原始产物：[artifacts/find_by_css_20260915.txt](artifacts/find_by_css_20260915.txt)

```powershell
uv run .\web\test_web_browser_find_by_css.py
uv run .\web\test_web_browser_find_by_css.py --json
uv run .\web\test_web_browser_find_by_css.py --contract-only
```

脚本会：复制元素库到 `sdk测试/.pytest_tmp/<run_id>/`（结束删除）→ 必要时自起本地 fixture →
验收 → 关闭页面与 Package → 停服务与清理。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`timeout=-1`（一直等待）**：未验证（需要元素永不出现且可中断的场景）。
- 复杂 CSS 语法（`:nth-child`、伪类、属性通配 `^=`/`*=`、`:has()` 等）未逐一验证；
  本次仅覆盖 id、复合后代、标签与类选择器。
- Shadow DOM / iframe 内的 CSS 查找（fixture 与靶场均为普通 DOM；元素库路径下的跨 iframe
  场景已在 `find.md` 覆盖，但那是库路径而非 CSS 选择器）。
- 无效 CSS 语法的报错形态（XPath 的对应形态见 `find_by_xpath.md`）。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
