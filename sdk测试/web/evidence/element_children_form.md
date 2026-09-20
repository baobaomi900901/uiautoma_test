# WebElement.children() 表单场景验收

## 用途与合同

获取当前元素的直接子元素，按 DOM 顺序返回 WebElement 列表；没有子元素时返回空列表。

```python
element.children(*, timeout: float = 5.0) -> list[WebElement]
```

timeout 仅限关键字，默认 5.0 秒；当前实现允许 None 使用默认值，负数（包括 -1）及非数字值被 InvalidParamsError 拒绝。它返回直接子元素，不是全部后代，也不返回文本节点或注释节点。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。SDK 日志导入路径位于该检出下；日志未提供正在运行的 Runtime 二进制版本。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：25/25 检查通过，退出码 0，总耗时 2705.5ms。**

第 11 项是**零预算边界检查通过，实际发生超时，没有取得子元素列表**。本结果不表示 timeout=0 能成功读取。

依据用户提供的一次完整 Chrome 实测输出登记，登记日期为 2026-09-19。未声称 agent 运行了本轮浏览器验收，也未声称连续三轮全部通过。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：260902_web元素，使用本次临时副本。
- 种子元素：web靶场_表单测试_ant_输入框，DOM id=form-controls-ant-text。
- 脚本：[test_web_element_children_form.py](../test_web_element_children_form.py)。
- [用户终端输出转录](artifacts/element_children_form_20260919.txt)：还原对话中的 Markdown 转义并整理折行，不是原始字节日志。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | 默认值、仅限关键字及 list[WebElement] 返回约定通过 |
| 02–07 | 库副本、页面、开关、目标、DOM 参照和容器 | 全部通过；动态 ID 初始 false，未点击；容器经 parent() 取得并与原生祖先核对 |
| 08–10 | 默认、显式正数和 None 超时 | 均返回 1 个直接子元素，按顺序核对 outerHTML 一致 |
| 11 | timeout=0 边界 | ActionError / web_dom_timeout，14.2ms；符合零预算边界预期，未取得列表 |
| 12 | 重复读取 | 连续三次分别核对类型、数量、顺序和结构通过 |
| 13 | 多个直接子元素 | 返回 2 项，与独立 DOM 顺序和结构一致；该容器全部后代共 6 项，未将后代全部返回 |
| 14–15 | 叶元素及重复读取 | input 返回 []，连续两次仍为 [] |
| 16 | 返回元素可用性 | 返回的 input 可继续调用 children()，结果为 [] |
| 17–21 | 参数规则 | 负数和非数字超时被 InvalidParamsError 拒绝；位置参数和未知关键字被 TypeError 拒绝 |
| 22 | 非法调用后的可用性 | 再次返回正确的 1 个直接子元素 |
| 23–25 | 清理 | 页面和 Package 的 close() 调用成功；副本已删除并核对不存在 |

## 期望值来源与独立确证

独立页面脚本在 iframe 文档的 open shadow 内定位目标 input，读取原生 parentElement 祖先链、各容器的 children、全部后代数量以及节点的标签、id、class 和 outerHTML。没有调用被测 children() 生成期望列表。

用公开 parent() 获取待测容器，并逐层与原生祖先结构核对。children() 的实际结果必须是列表，长度与预期相同，每项都是 WebElement，再按 DOM 顺序核对各项 outerHTML 和节点属性；不以 Runtime .id 作为跨调用的 DOM 身份依据。

本轮独立参照为：input 的直接子元素 0 项，直接父容器的子元素 1 项，多项容器的直接子元素 2 项、全部后代 6 项。多项容器用于验证数量、顺序，以及“直接子元素”与“全部后代”的区别。

源码快照中的 related/children 分支使用 Array.from(element.children).filter(isElementNode)，与上述原生 DOM 参照相符。

## 零预算边界与实际观测

SDK 将 timeout=0 转为 timeout_ms=0，related 调用继续传递该预算；Runtime DOM 桥接等待的最小值约为 1ms。因此即使子元素存在，也可能在响应返回前超时。本方法没有 find(timeout=0) 的单次查询特例。

零预算用例仅接受正确列表，或明确的 ActionError 且 trace_info=web_dom_timeout。其他异常、错误列表仍然失败。默认及正数预算用例仍要求成功取得正确结果。

本轮实际走的是超时分支：

```text
ActionError
trace_info=web_dom_timeout
trace_id=ce7e9f02cae341fca00b3589612ca69e
耗时=14.2ms
本次未取得子元素列表
```

## 范围与限制

本次覆盖上述 iframe/open shadow 内已经定位的元素及其容器，不证明 children() 会跨 iframe 或 ShadowRoot 枚举内部元素。未覆盖关闭页面后的失效引用、动态重挂载或 Edge。

多项容器的非元素直接子节点数量为 0，因此本轮没有实际验证“混有文本节点或注释节点时将其排除”的场景；此行为在本记录中仅有源码和 DOM 合同依据。

页面及 Package 清理核对了 close() 调用成功，未额外枚举标签确认无残留；临时目录核对了不存在。

旧场景证据仍见 [children.md](children.md)，其历史结论不代替本次表单场景记录。

## 复测命令

在 sdk测试 目录运行：

```powershell
uv run .\web\test_web_element_children_form.py
```

仅检查合同，不操作浏览器：

```powershell
uv run .\web\test_web_element_children_form.py --contract-only
```
