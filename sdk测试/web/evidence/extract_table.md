# `WebBrowser.extract_table()` 初次测试（按合同拒绝）

## 用途与现状

文档声明「提取页面表格」，返回 `list[list[str]]`；但**当前源码中是尚未实现的桩**：

```python
def extract_table(self, table_selector, *, exclude_thead=False, timeout=20) -> list[list[str]]:
    """..."""
    raise unsupported("web.browser.extract_table")
```

因此本次验收的目标不是「能否提取表格」，而是**核对它按合同拒绝**。

| 参数 | 默认 | 说明 |
|---|---|---|
| `table_selector` | 必填 | 表格元素选择器（位置或关键字） |
| `exclude_thead` | `False` | 仅限关键字 |
| `timeout` | `20` | 仅限关键字 |

## 真实验收结果

**VERIFIED（仅「按合同拒绝」结论）：11/11 通过，退出码 0。**

> 注意：本结论**不表示该功能可用** —— 功能未实现，调用必定抛 `UnsupportedActionError`。
> 状态仅表示「文档声明的未实现契约与实际行为一致」。

靶场：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/#/table-test`
（该页确含 **2 个真实 `<table>`**，用于证明拒绝不是「找不到表格」）

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`table_selector` 必填（位置或关键字），`exclude_thead` / `timeout` 仅限关键字（默认 `False` / `20`），返回注解 `list[list[str]]` |
| **零 Runtime 交互拒绝** | 通过，在**手工构造**的 `WebBrowser`（假页面引用、无 Package、无页面、不连 Runtime）上调用即抛 `UnsupportedActionError`（0.0s） |
| 拒绝形态正确 | 通过，是 `UnsupportedActionError` 而**非** `NoCurrentPackageError`（未走到 Package 检查） |
| **任何参数形态均拒绝** | 通过，7 种形态（正常/空串/`None`/数字/`exclude_thead=True`/`timeout=0`/`exclude_thead` 传非法类型）均抛同一异常 |
| 参数绑定仍生效 | 通过，缺 `table_selector`、多余位置参数、未知关键字 → `TypeError` |
| 含真实表格的靶场页 | 通过，页内 2 个 `<table>`，调用仍抛 `UnsupportedActionError` |
| 页面关闭复核 | 通过，`web.get_all()` 证实无残留 |
| 资源清理 | 通过；本 API 为桩，**未创建 Package 与其它资源** |

### 异常形态（实测）

```
type        : UnsupportedActionError
message     : web.browser.extract_table 当前版本暂不支持
method      : web.browser.extract_table
trace_info  : None
trace_id    : ''
MRO         : UnsupportedActionError → UIAutomaError → RuntimeError → Exception
```

## 三点实测结论

1. **拒绝发生在 SDK 侧、早于一切校验**：连 Runtime 都没连（手工构造的页面对象）就抛异常，
   说明它不是「运行时发现没有表格」而是「SDK 直接声明不支持」。
2. **不做参数校验**：`exclude_thead="not-bool"` 这类明显非法类型也照样得到同一个
   `UnsupportedActionError` —— 与其它已实现 API（非法参数抛 `InvalidParamsError`）不同。
3. **不是「找不到表格」**：在确有 2 个 `<table>` 的页面上调用仍然拒绝。

## 复测

脚本：[test_web_browser_extract_table.py](../test_web_browser_extract_table.py)
原始产物：[artifacts/extract_table_20260915.txt](artifacts/extract_table_20260915.txt)

```powershell
uv run .\web\test_web_browser_extract_table.py
uv run .\web\test_web_browser_extract_table.py --json
uv run .\web\test_web_browser_extract_table.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **表格提取功能本身**：未实现，无从验证（若后续实现，需要重新做真实场景验收并重写本文件）。
- `WebElement.extract_table()` 与 `WebElement.get_basetable_value()`：探针显示它们也是同类桩
  （`raise unsupported("web.element.extract_table")`），但**未作为独立验收**，属下一个候选。
- 其它未实现入口（环境指纹、弹窗自动处理等）：见 `web api 清单.md` 中标注「未实现」的条目。
- Edge、CEF 与 Auto 模式。
