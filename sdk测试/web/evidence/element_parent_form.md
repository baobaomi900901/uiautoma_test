# WebElement.parent() 表单场景验收

## 用途与合同

获取当前元素的直接父元素；没有父元素时返回 None。

```python
element.parent(*, timeout: float = 5.0) -> WebElement | None
```

timeout 仅限关键字。默认值为 5.0 秒；当前实现允许 None 使用默认值，并拒绝负数（包括 -1）及非数字值。本方法没有 find(timeout=0) 的单次查询特例。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。SDK 日志导入路径位于该检出下；日志未提供正在运行的 Runtime 二进制版本。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：23/23 检查通过，退出码 0，总耗时 5216.6ms。**

其中第 09 项是**零预算边界检查通过，实际发生超时，没有取得父元素**。本结果不表示 timeout=0 能成功读取父节点。

依据用户提供的一次完整 Chrome 实测输出登记，登记日期为 2026-09-19。未声称 agent 运行了本轮浏览器验收，也未声称连续三轮全部通过。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：260902_web元素，使用本次临时副本。
- 目标：web靶场_表单测试_ant_输入框，DOM id=form-controls-ant-text。
- 原生直接父元素：DIV，id 为空，class=ant-form-item-control-input-content。
- 原生祖先共 11 层，终点为 #shadow-form-content。
- 脚本：[test_web_element_parent_form.py](../test_web_element_parent_form.py)。
- [用户终端输出转录](artifacts/element_parent_form_20260919.txt)：还原对话中的 Markdown 转义并整理折行，未将其描述为原始字节日志。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | 默认值、仅限关键字及 WebElement/None 返回约定通过 |
| 02–06 | 库副本、页面、开关、目标、原生 DOM 参照 | 全部通过；动态 ID 初始 false，未点击 |
| 07–08 | 默认及显式正数超时 | 返回父元素，与独立 DOM 的属性和 outerHTML 一致 |
| 09 | timeout=0 边界 | ActionError / web_dom_timeout，11.5ms；符合零预算边界预期，未取得父元素 |
| 10–11 | None 超时、重复读取 | 返回正确父元素；三次读取分别核对通过 |
| 12 | 完整祖先链 | 11 层逐层与原生 DOM 比对通过 |
| 13–14 | 无父元素与重复读取 | 返回 None；重复两次仍为 None，没有返回 Shadow host |
| 15–19 | 参数规则 | 负数、非数字超时被 InvalidParamsError 拒绝；位置参数及未知关键字被 TypeError 拒绝 |
| 20 | 非法调用后的可用性 | 再次读取正确父元素 |
| 21–23 | 清理 | 页面及 Package 的 close() 调用成功；副本已删除并核对不存在 |

## 期望值来源与独立确证

独立页面脚本在 iframe 文档的 open shadow 内定位目标 input，以原生 parentElement 向上建立参照链，并记录各层的标签、id、class 和 outerHTML。没有调用被测 parent() 来生成期望父节点。

SDK 返回的每个父元素与该层原生结构逐项比较；不按 Runtime `.id` 比较跨调用身份，也不要求运行时名称等于元素库名称。完整 outerHTML 对比用于区分“class 一样但包含不同输入框”的父节点。

边界同时读取 parentElement 与 parentNode：终点的 parentElement 为 null，而 parentNode 是 nodeType=11 的 ShadowRoot，host id=form-shadow-host。因此预期是 None，不是跨过 ShadowRoot 返回 host 元素。

## 零超时判据修正及实际观测

前一版脚本要求 timeout=0 必须返回父元素，导致前一轮 22/23。源码核对表明此要求过强：

- SDK 将 0 转为 timeout_ms=0。
- related 调用将该预算向下传递。
- `runtime/web/bridge_state.py` 的 DOM 等待使用 `max(0.001, timeout_sec)`，零预算对应最小约 1ms 等待；整体调用耗时还包含通信和调度。
- 因而父元素实际存在，也可能来不及返回。此语义不同于 find 系列对零超时单次查询的专门处理。

修正后，仅零预算用例允许两种结果：返回父元素且身份校验通过，或抛出明确的 ActionError 且 trace_info=web_dom_timeout。其他异常、错误节点、在已知存在父元素时返回 None，都仍然失败。默认及正数预算用例仍要求成功读取。

本轮实际走的是超时分支：

```text
ActionError
trace_info=web_dom_timeout
trace_id=8657221bd756470fb54f0b4e73bc5dd1
耗时=11.5ms
本次未取得父元素
```

这是测试判据修正后的复测记录，不是 SDK 修复后零超时读取恢复成功的记录。

## 范围与限制

本次只覆盖所给文本框及其 iframe/open shadow 内的父级链，不证明 parent() 会跨 ShadowRoot 或 iframe 回到宿主节点。未覆盖页面关闭后的失效引用、Edge 或动态重挂载场景。

页面及 Package 清理核对了 close() 调用成功，未额外枚举浏览器标签确认无残留；临时目录核对了不存在。

旧的九宫格场景证据仍见 [parent.md](parent.md)，其历史签名和结论不代替本次表单场景记录。

## 复测命令

在 sdk测试 目录运行：

```powershell
uv run .\web\test_web_element_parent_form.py
```

仅检查合同，不操作浏览器：

```powershell
uv run .\web\test_web_element_parent_form.py --contract-only
```
