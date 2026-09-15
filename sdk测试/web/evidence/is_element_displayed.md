# `WebBrowser.is_element_displayed()` 初次测试

## 用途

判断当前页面是否存在能定位到的匹配元素。返回 `bool`；**只有一个必填参数 `selector`，没有
`timeout` 参数**。

- `selector`：元素库中的名称（`str`）或 Web 类型的 `package.Selector`。

**源码事实**：该方法是 `bool(self.find_all(selector, timeout=0))` 的薄包装，因此口径完全继承
`find_all`（内部固定 `timeout=0`，不等待）。

## 真实验收结果

**VERIFIED：20/20 通过，退出码 0。**

靶场：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
（元素库 `260902_web元素` 中 `web靶场_表单测试_*` 元素所属页面；测试侧不自建页面）

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`selector` 必填、**无 `timeout` 等额外参数**，返回注解 `bool` |
| 元素库准备 | 通过，副本打开后 `web_count=70` |
| 页面准备 | 通过，元素所属靶场页打开成功 |
| **活推导分类** | 通过，库中 70 个元素在本页分成：唯一 **52**、多命中 **10**、本页不存在 **8** |
| 本页唯一命中元素 | 通过，返回 `True`（0.021s） |
| **多命中元素** | 通过，返回 `True`（0.017s）——**不会**像 `find` 那样抛 `AmbiguousElementError` |
| 以 `package.selector()` 传入 | 通过，返回 `True` |
| **库中有但本页不存在** | 通过，返回 `False`（0.018s，**不等待**） |
| **当前页不对**（元素属别页） | 通过，返回 `False`（0.006s） |
| **库中没有该名称** | 通过，抛 `ElementNotFoundError`（"未找到选择器"，0.001s）**而非返回 `False`** |
| 空 / 全空白名称 | 通过，`InvalidParamsError`（"元素名称不能为空"） |
| 非字符串 / `None` | 通过，`InvalidParamsError`（"selector 必须是元素名称字符串或 Selector 对象"） |
| 多余位置参数 | 通过，`TypeError` |
| **传入 `timeout=` 关键字** | 通过，`TypeError`（本 API 无该参数） |
| 页面关闭复核 / Package 关闭复核 | 通过，`web.get_all()` 证实无残留 |
| 未打开 Package | 通过，`NoCurrentPackageError` |
| 资源清理 | 通过，关页（复核无残留）、关 Package、删除元素库副本 |

## 期望值来自活推导

脚本先遍历元素库（`package.elements.list(kind="web")`），对每个名称调用
`find_all(name, timeout=0)` 现场分类，再从三类中各取一个样本用于断言 ——
**脚本内不写死任何元素名或匹配数量**，元素库或靶场变化后仍可复用。

本次分类结果（唯一 52 / 多命中 10 / 本页不存在 8）与 `find_all.md` 中早前的普查结果完全一致，
互为交叉验证。

## 与文档的一处不一致（仅记录，未判定为缺陷）

docstring 写的是「至少一个匹配元素定位成功时为 `True`，否则为 `False`」，但实测
**库中没有该名称时会抛 `ElementNotFoundError`**，不是返回 `False`。也就是说：

| 场景 | 实际返回/抛出 |
|---|---|
| 库中有、本页有匹配（唯一或多命中） | `True` |
| 库中有、本页无匹配 | `False` |
| **库中没有该名称** | **抛 `ElementNotFoundError`** |

调用方若按「永不抛异常，只看 True/False」来写，会在名称写错时被异常打断。同族的 `get_scroll`
也有类似「`Raises` 段与实际不符」的情况，本文件同样只做记录。

## 复测

脚本：[test_web_browser_is_element_displayed.py](../test_web_browser_is_element_displayed.py)
原始产物：[artifacts/is_element_displayed_20260915.txt](artifacts/is_element_displayed_20260915.txt)

```powershell
uv run .\web\test_web_browser_is_element_displayed.py
uv run .\web\test_web_browser_is_element_displayed.py --json
uv run .\web\test_web_browser_is_element_displayed.py --contract-only
```

`--target-url` 可换靶场页；`--library` 可换元素库目录。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **「存在但不可见」的元素**（CSS `display:none` / `visibility:hidden` / 零尺寸）：本 API 名字叫
  `is_element_displayed`，但实现是「能否定位到匹配元素」，**没有做可见性判断**；
  不可见但可定位时的返回值本次未单独构造验证。
- `iframe` 内元素的「可见性」语义（本次元素本身位于 iframe 内且返回 `True`）。
- 页面滚动位置对「可见」的影响。
- 元素库多组、Win 元素与图像元素。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
