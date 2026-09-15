# `WebBrowser.find_all()` 初次测试

## 用途

在当前页面查找与已保存选择器匹配的**全部**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `selector` | 必填 | 元素库中的名称（`str`）或 Web 类型的 `package.Selector` |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `list[WebElement]`；**超时仍未找到时返回空列表**。

## 前置条件

| 项 | 值 |
|---|---|
| 元素库 | `D:\code\元素库\260902_web元素`（Schema2，70 个 web 元素） |
| 靶场页 | `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form` |
| 库用法 | 复制到本工作区 `.pytest_tmp/<run_id>/` 后再 `uiautoma.open()`，结束时删除；不写原件 |

## 真实验收结果

**VERIFIED：20/20 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `list[WebElement]` |
| 元素库准备 | 通过，`web_count=70` 与列举数一致 |
| 页面准备 | 通过，打开元素所属靶场页 |
| 唯一命中 | 通过，返回 `list[1]`（标签 `INPUT`） |
| **多命中** | 通过，`ant_radio_label_相似元素` 返回 **3 个**（男 / 女 / 其他） |
| `package.Selector` 入参 | 通过，返回 `list[1]` |
| `timeout=0` 且元素存在 | 通过，返回 `list[1]` |
| **页面不匹配（核心差异）** | 通过，**返回 `[]` 且不抛异常**（`timeout=3` 耗时 3.001s） |
| 同上但 `timeout=0` | 通过，返回 `[]`（耗时 0.006s） |
| 库中不存在的名称 | 通过，`ElementNotFoundError`（"未找到选择器"，**0.001s 立即返回**） |
| 空名称 / 全空白名称 | 通过，`InvalidParamsError` |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError` |
| 缺少 `selector` / `timeout` 位置传入 | 通过，`TypeError` |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| **页面关闭复核** | 通过，`close()` 后用 `web.get_all()` 实证页面已消失（无残留） |
| **Package 关闭复核** | 通过 |
| 资源清理 | 通过，关页（`get_all` 复核无残留）、关 Package、删除元素库副本 |

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-09-15 | 初次验收 18/18 |
| 2026-09-15 | **同 `find` 的清理缺陷一并修正**：先关 Package 会释放共享连接，导致随后的 `page.close()` 抛 `HostUnavailableError` 且被静默吞掉（标签页泄漏、`cleanup` 假 PASS）。已改为「先关页面并 `get_all` 复核 → 再关 Package」，新增 `page_close_verified` / `package_close_verified`，现为 20/20。**此前版本的「资源清理 PASS」不成立，特此更正。** |

## 与 `find()` 的语义差异（本次实测确认）

| 场景 | `find()` | `find_all()` |
|---|---|---|
| 唯一命中 | 返回 `WebElement` | 返回 `list[1]` |
| **页面匹配不到** | 抛 `ElementNotFoundError`（等满 timeout） | **返回 `[]`**（等满 timeout） |
| **同一元素路径命中多个节点** | 抛 `AmbiguousElementError` | **返回全部匹配**（本库该元素为 3 个） |
| 库中没有该名称 | 抛 `ElementNotFoundError`（立即） | 抛 `ElementNotFoundError`（立即） |

其中最容易被误用的是第二行：**在 `find_all` 上写 `try/except ElementNotFoundError` 等不到异常，
只会拿到空列表**；反过来在 `find` 上依赖空列表也会被异常打断。

## 库内元素在目标页的命中分布（探针统计）

遍历库中 70 个元素（`timeout=0`，目标页 `#/iframe-shadow-form`）：

| 结果 | 数量 | 说明 |
|---|---|---|
| 单命中 | 52 | 常规元素 |
| 多命中 | **10** | 带 `_相似元素` 后缀者，例如 `ant_radio_label_相似元素`（3 个）、`原生_select多选_options_相似元素`（4 个） |
| 未命中 | 8 | 属于其它靶场页（下载/上传对话框、部分 select 选项等） |

因此多命中返回路径由真实场景覆盖，而非构造。

## 环境说明

依赖元素库与页面 DOM，**不依赖像素/合成器**，Chrome 窗口最小化时依然可用；
无导航历史前置，**不受 issue #58 影响**。

## 复测

脚本：[test_web_browser_find_all.py](../test_web_browser_find_all.py)
原始产物：[artifacts/find_all_20260915.txt](artifacts/find_all_20260915.txt)

```powershell
uv run .\web\test_web_browser_find_all.py
uv run .\web\test_web_browser_find_all.py --json
uv run .\web\test_web_browser_find_all.py --contract-only
```

`--library` 可换库目录（默认 `D:\code\元素库\260902_web元素`）；`--timeout` 控制 `find_all` 的超时（默认 8）。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`timeout=-1`（一直等待）**：未验证（需要元素永不出现且可中断的场景）。
- **返回元素之间的顺序**：未断言多命中结果是否按 DOM 顺序排列（本次仅核对数量与标签）。
- 元素列表上限（若靶场存在大量匹配节点时的截断行为）。
- 页面刷新后需重新查找（既有约定，未单独验证）。
- 元素库多组、Win 元素、图像元素；Edge/CEF/Auto 模式。
