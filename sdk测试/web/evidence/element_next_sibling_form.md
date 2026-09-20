# WebElement.next_sibling() 表单场景验收

## 用途与合同

获取同一父节点下紧邻的下一个元素兄弟节点；没有对应元素时返回 None。语义对应原生 nextElementSibling，跳过文本和注释节点。

```python
element.next_sibling(*, timeout: float = 5.0) -> WebElement | None
```

timeout 仅限关键字，默认 5.0 秒；当前实现允许 None 使用默认值。负数（包括 -1）与非数字超时被 InvalidParamsError 拒绝；多余位置参数和未知关键字被 TypeError 拒绝。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。SDK 日志导入路径位于该检出下；日志未提供正在运行的 Runtime 二进制版本。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：28/28 检查通过，退出码 0，总耗时 1535.2ms。**

第 12 项为**零预算边界检查通过，实际发生超时，没有取得兄弟元素**。本结果不表示 timeout=0 能成功读取。

依据用户提供的一次完整 Chrome 实测输出登记，登记日期为 2026-09-19。未声称 agent 运行了本轮浏览器验收，也未声称连续三轮全部通过。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：260902_web元素，使用本次临时副本。
- 种子元素：web靶场_表单测试_ant_输入框，DOM id=form-controls-ant-text。
- 独立脚本：[test_web_element_next_sibling_form.py](../test_web_element_next_sibling_form.py)。
- [用户终端输出转录](artifacts/element_next_sibling_form_20260919.txt)：还原对话中的 Markdown 转义并整理折行，不是原始字节日志。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | 默认值、仅限关键字及 WebElement/None 返回约定通过 |
| 02–08 | 库副本、页面、开关、目标、DOM 参照及同级元素 | 全部通过；动态 ID 初始 false，未点击；同级 2 个元素均与原生 DOM 核对 |
| 09–11 | 默认、显式正数和 None 超时 | 返回预期 DIV，class=ant-col ant-form-item-control css-mncuj7，outerHTML 一致 |
| 12 | timeout=0 边界 | ActionError / web_dom_timeout，13.1ms；未取得兄弟元素 |
| 13 | 重复读取 | 连续三次分别与原生下一个兄弟元素比对通过 |
| 14 | 同级位置 | 2 个元素逐项核对；末项返回 None，第一项返回紧邻的第二个元素 |
| 15–16 | 末项边界及重复读取 | 末项返回 None，连续两次仍为 None，没有返回父元素或其后代 |
| 17 | 输入框本身 | 原生 nextElementSibling=null；实际返回 None |
| 18 | 向后遍历 | 从首项读取 1 个后方兄弟元素，再到 None，顺序与独立 DOM 一致 |
| 19 | 返回元素可用性 | 返回元素可读取 outerHTML 和 parent()，仍属于原生共同父容器 |
| 20–24 | 参数规则 | -1、-0.1、'bad' 超时被 InvalidParamsError 拒绝；位置参数和未知关键字被 TypeError 拒绝 |
| 25 | 非法调用后的可用性 | 再次取得正确的下一个兄弟元素 |
| 26–28 | 资源清理 | 页面和 Package 的 close() 调用成功；临时副本已删除并核对不存在 |

## 期望值来源与独立确证

独立页面脚本进入 iframe 文档的 open shadow，定位文本输入框，读取原生祖先链、直接子元素以及每个节点的 nextElementSibling、标签、DOM id、class 和 outerHTML。原生兄弟关系还与 children 顺序交叉核对；没有使用被测 next_sibling() 生成期望结果。

准备阶段通过 parent() 取得共同父容器，再通过 child_at() 获取同级元素，每一步都与独立 DOM 结构核对。实际返回值必须是 WebElement，属性和完整 outerHTML 均符合原生参照；没有对应兄弟元素时严格要求 None，不能用空列表或其他假值代替。跨调用不以 Runtime .id 作为 DOM 身份依据。

本轮使用 2 个同级元素验证正向与边界场景：第一项的 next_sibling() 返回第二项（控件列 DIV）；第二项返回 None。原始 input 本身也没有下一个元素兄弟节点，返回 None。向后遍历实际跨越 1 个兄弟元素后到达边界。

源码快照中，SDK 使用 web.element.get_next_sibling，Runtime 转交 related/next_sibling，页面引擎读取 element.nextElementSibling 并过滤非元素；SDK 将空结果映射为 None。

## 零预算边界与实际观测

timeout=0 在 related 调用链中保留为零预算；Runtime DOM 等待的最小值约为 1ms，存在目标也可能来不及返回。本方法没有 find(timeout=0) 的单次查询特例。

脚本只在零预算项接受正确兄弟元素，或明确的 ActionError 且 trace_info=web_dom_timeout。其他异常、错误节点或目标存在却返回 None 均失败。默认和正数预算仍要求成功读取。

本轮零预算实际结果：

```text
ActionError
trace_info=web_dom_timeout
trace_id=cabb090adfa04678ba2a389d8d2a4e04
耗时=13.1ms
本次未取得兄弟元素
```

## 范围与限制

本轮多项容器有 2 个直接子元素、6 个后代，非元素直接子节点数量为 0。因此，跳过文本和注释节点的语义有源码依据，但没有在本轮混合节点场景中实际验证；也未覆盖三个以上同级元素的长链遍历。

本次覆盖已定位的 iframe/open shadow 内节点，不证明接口会跨 iframe 或 ShadowRoot 寻找兄弟元素。未覆盖动态重挂载、页面关闭后的失效引用和 Edge。

页面与 Package 清理核对了 close() 调用成功，未额外枚举标签确认无残留；临时目录核对了不存在。

旧场景证据见 [next_sibling.md](next_sibling.md)，其历史结论不代替本次表单场景记录。

## 复测命令

在 sdk测试 目录运行：

```powershell
uv run .\web\test_web_element_next_sibling_form.py
```

仅检查合同，不操作浏览器：

```powershell
uv run .\web\test_web_element_next_sibling_form.py --contract-only
```
