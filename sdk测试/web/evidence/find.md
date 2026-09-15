# `WebBrowser.find()` 初次测试

## 用途

在当前页面查找与已保存选择器匹配的**唯一**元素。

| 参数 | 默认 | 说明 |
|---|---|---|
| `selector` | 必填 | 元素库中的名称（`str`）或 Web 类型的 `package.Selector` |
| `timeout` | `20` | 查找秒数；`0` 只查一次，`-1` 一直等待；**仅限关键字** |

返回 `WebElement`（页面刷新后需要重新查找）。

## 前置条件（本次实测可用）

| 项 | 值 |
|---|---|
| 元素库 | `D:\code\元素库\260902_web元素`（Schema2，70 个 web 元素，1 个组） |
| 靶场页 | `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form` |
| 元素位置 | 库中 `web靶场_表单测试_*` 元素位于该页的 **iframe 内**（页面有 1 个 iframe） |
| 库用法 | 复制到本工作区 `.pytest_tmp/<run_id>/` 后再 `uiautoma.open()`，结束时删除；**不写入原件** |

本次复制的副本**无需清空 session 字段**（清空数 = 0），即该库没有陈旧会话数据。

## 真实验收结果

**VERIFIED：19/19 通过，退出码 0。**

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`selector` 必填，`timeout` 仅限关键字且默认 20，返回注解 `WebElement` |
| 元素库准备 | 通过，打开副本后 `web_count=70`，与 `elements.list(kind="web")` 列举数一致 |
| 页面准备 | 通过，打开元素所属靶场页 |
| 按库中名称定位 | 通过，命中元素（标签 `INPUT`，运行时 id 前缀 `rt:web:`） |
| `package.Selector` 入参 | 通过，`selector.framework()='web'`，定位结果与名称入参一致 |
| 重复定位一致性 | 通过，标签一致（**注意 `element_id` 每次都会重新生成**，见下节） |
| `find_all` 同目标 | 通过，返回 1 个元素且包含目标 |
| 库中第二个元素 | 通过，同样可定位 |
| `timeout=0` 且元素存在 | 通过，仍能命中 |
| 库中不存在的名称 | 通过，`ElementNotFoundError`，**0.001s 立即返回** |
| 名称存在但页面不匹配 | 通过，`ElementNotFoundError`，**等满 3.001s** 后返回 |
| 空名称 / 全空白名称 | 通过，`InvalidParamsError`（"元素名称不能为空"） |
| `timeout=-2` / `timeout="bad"` | 通过，`InvalidParamsError`（"必须为 -1 或非负数" / "必须是秒数"） |
| 缺少 `selector` | 通过，`TypeError` |
| `timeout` 用位置传入 | 通过，`TypeError`（仅限关键字） |
| 未打开 Package | 通过，`NoCurrentPackageError`（"当前没有打开的 Package"） |
| 资源清理 | 通过，关闭页面与 Package，并删除元素库副本 |

## 两种 `ElementNotFoundError` 语义不同（实测区分）

| 场景 | 消息 | 耗时 | 原因 |
|---|---|---|---|
| **库里没有这个名称** | `未找到选择器，选择器名："..."` | **0.001s** | SDK/Runtime 在库侧就查不到，立即拒绝 |
| **名称在库里，但当前页面匹配不到** | `未找到匹配元素` | **3.001s**（等满 timeout） | 库侧找到定义，页面侧定位失败 |

这一区分对排查很有用：立即返回说明**名称写错或库不对**；等满超时说明**页面不对或元素已失效**。

## 一个重要观察：`element_id` 每次 `find` 都会重新生成

```
find(NAME) → rt:web:bd05563bde8f4dcc94c2af1dce595fb8
find(NAME) → rt:web:7bc16803559a4ceda41cf8dd69ed1348
find(NAME) → rt:web:1359b5811dfc4c76adb3aae71f1fa2e7
```

同一名称、同一页面、同一 Package，重复定位得到的 `element_id` **每次不同**（`element_id_changed=True`）。
因此：

- **不能把 `element_id` 当作跨调用的稳定标识**来比较「是不是同一个元素」（本脚本据此改为按标签一致性判定）；
- 同一元素的逻辑一致性应通过其它方式确认（例如标签名、位置或直接在同一个元素对象上做后续操作）。

本脚本未把这条判为缺陷（源码未承诺该 id 跨调用稳定），但它是使用时的实际约束，故记录在此。

## 环境说明

- 本 API 依赖元素库与页面 DOM，**不依赖像素/合成器**，因此在 Chrome 窗口最小化时依然可用
  （与 `scroll_to(behavior="smooth")` 形成对比，见 `scroll_to.md`）；
- 无导航历史前置，**不受 issue #58 影响**。

## 复测

脚本：[test_web_browser_find.py](../test_web_browser_find.py)
原始产物：[artifacts/find_20260915.txt](artifacts/find_20260915.txt)

```powershell
uv run .\web\test_web_browser_find.py
uv run .\web\test_web_browser_find.py --json
uv run .\web\test_web_browser_find.py --library "D:\code\元素库\260902_web元素" --contract-only
```

`--library` 可换库目录（默认 `D:\code\元素库\260902_web元素`）；`--timeout` 控制 `find` 的超时（默认 8）。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`AmbiguousElementError`（同名/多命中）**：本次所用元素库**没有任何同名元素**（同名组数 = 0），
  无法构造歧义场景；需要一份含同名元素的库才能覆盖。
- **`timeout=-1`（一直等待）**：未验证（需要元素永不出现且可中断的场景）。
- **页面刷新后需重新查找**：文档说明的行为未在本脚本中单独验证（属元素生命周期的既有约定）。
- 元素库的多组场景、Win 元素（`kind="win"`）、图像元素。
- 跨 iframe 的层级归属细节：本次元素确实位于 iframe 内且能命中，但未对多 iframe / 嵌套 iframe
  的定位选择策略单独断言。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
