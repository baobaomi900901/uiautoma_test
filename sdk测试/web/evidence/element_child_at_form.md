# WebElement.child_at() 表单场景验收

## 用途与合同

按从 0 开始的索引获取直接子元素；没有对应子元素时返回 None。

```python
element.child_at(index: int, *, timeout: float = 5.0) -> WebElement | None
```

index 必填，可按位置或关键字传入。timeout 仅限关键字，默认 5.0 秒；None 使用默认值。负数或越界索引返回 None，不使用 Python 列表的负数倒序取值语义。负数超时与非数字超时被 InvalidParamsError 拒绝。

当前实现先执行 int(index)，因此也接受部分非 int 输入；本轮将这种兼容行为单独核验，不将它描述为严格的整数类型校验。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。SDK 日志导入路径位于该检出下；日志未提供正在运行的 Runtime 二进制版本。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：40/40 检查通过，退出码 0，总耗时 1609.8ms。**

第 12 项为**零预算边界检查通过，实际发生超时，没有取得子元素**。本结果不表示 timeout=0 成功读取。

依据用户提供的一次完整 Chrome 实测输出登记，登记日期为 2026-09-19。未声称 agent 运行了本轮浏览器验收，也未声称连续三轮全部通过。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：260902_web元素，使用本次临时副本。
- 种子元素：web靶场_表单测试_ant_输入框，DOM id=form-controls-ant-text。
- 独立脚本：[test_web_element_child_at_form.py](../test_web_element_child_at_form.py)。
- [用户提交的终端输出附件归档](artifacts/element_child_at_form_20260919.txt)：保存附件文本，只统一换行并补齐末尾换行；保留附件中的折行空格，不是 agent 重新运行产生的日志。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | index 必填且从 0 起始；timeout 默认 5.0、仅限关键字；返回 WebElement 或 None |
| 02–07 | 元素库、页面、开关、目标、DOM 参照和容器 | 全部通过；动态 ID 初始 false，未点击；容器由 parent() 取得并与原生祖先核对 |
| 08–11 | 默认调用、关键字索引、显式超时、None 超时 | 取得预期直接子元素，outerHTML 与独立 DOM 参照一致 |
| 12 | timeout=0 边界 | ActionError / web_dom_timeout，13.7ms；未取得子元素 |
| 13 | 重复读取 | 连续三次均与原生 DOM 对比通过 |
| 14–15 | 完整直接子元素索引及末项 | 索引 0、1 分别命中对应元素；直接子元素 2 项、全部后代 6 项 |
| 16–18 | 索引等于数量、大索引、负数 | index=2、1002、-1 均返回 None |
| 19–20 | 叶元素 | input 的 index=0 和 1 均返回 None |
| 21 | 返回元素可用性 | 返回的 input 可读取 id 并再次调用 child_at(0)，结果为 None |
| 22–24 | 当前实现的索引转换 | '1'、1.9、True 均按 int(index) 转为 1，取得第二个直接子元素 |
| 25–30 | 不可转换的索引 | None、'bad'、''、[]、{}、'1.5' 均被 InvalidParamsError 拒绝，文案为“index 必须是整数” |
| 31–33 | 非法超时 | -1、-0.1、'bad' 被 InvalidParamsError 拒绝 |
| 34–36 | 调用参数边界 | 缺少 index、多余位置参数、未知关键字被 TypeError 拒绝 |
| 37 | 非法调用后的可用性 | 再次正确取得索引 0 的直接子元素 |
| 38–40 | 资源清理 | 页面和 Package 的 close() 调用成功；临时元素库副本已删除并核对不存在 |

## 期望值来源与独立确证

独立页面脚本进入 iframe 文档的 open shadow，定位文本输入框，以原生 parentElement 建立祖先链，再读取各容器的 children、outerHTML 和全部后代数量。没有使用 child_at() 或 children() 生成预期值。

通过 parent() 取得待测容器，逐层与原生祖先结构核对。实际返回值必须是 WebElement，再检查标签、DOM id、class 和完整 outerHTML；跨调用不按 Runtime .id 判断 DOM 身份。无对应索引时严格要求 None，空列表或其他假值不能代替。

本轮多项容器包含两个可区分的直接子元素：

| 索引 | 原生直接子元素 | 实测 |
| --- | --- | --- |
| 0 | DIV，class=ant-col ant-form-item-label css-mncuj7 | 默认、显式及重复调用均匹配 |
| 1 | DIV，class=ant-col ant-form-item-control css-mncuj7 | 关键字索引、末项及转换行为均匹配 |

容器共有 6 个后代，但索引 2 返回 None，验证的是直接子元素序列。输入框直接父容器的索引 0 则返回 input#form-controls-ant-text。

源码快照中，SDK 将 index 经 int() 转换后发送 web.element.get_child_at；Runtime 使用 related/child_at；页面引擎按原生直接子元素数组检查非负索引及长度范围，超出范围返回空结果，SDK 映射为 None。

## 零预算边界与兼容行为

timeout=0 在 related 调用链中保留为零预算；Runtime 的最小 DOM 等待约为 1ms，可能在结果返回前超时。本方法没有 find(timeout=0) 的单次查询特例。

脚本仅在零预算项接受正确子元素，或明确的 ActionError 且 trace_info=web_dom_timeout。其他错误、错误元素或目标存在却返回 None 均失败。默认和正数预算仍要求成功取得正确元素。

本轮零预算实际结果：

```text
ActionError
trace_info=web_dom_timeout
trace_id=b7069a931ebb45c0abb8a1f4c847b23e
耗时=13.7ms
本次未取得子元素
```

索引转换仅记录当前实现的实测行为：'1' → 1、1.9 → 1、True → 1；字符串 '1.5' 无法由 int() 转换，因此被拒绝。常规调用应使用非负整数；本轮未测试所有可转换对象或非有限数值。

## 范围与限制

本次覆盖已定位的 iframe/open shadow 内元素及其容器，不证明 child_at() 会跨 iframe 或 ShadowRoot 枚举。未覆盖关闭页面后的失效引用、动态重挂载和 Edge。

多项容器的非元素直接子节点数量为 0，因此本轮没有实际覆盖混合文本或注释节点的排除场景。单项容器和两个直接子元素的容器已核验，未实际覆盖三个以上直接子元素的容器。

页面和 Package 清理核对了 close() 调用成功，未额外枚举标签确认无残留；临时目录核对了不存在。

旧场景证据见 [child_at.md](child_at.md)，其历史结论不代替本次表单场景记录。

## 复测命令

在 sdk测试 目录运行：

```powershell
uv run .\web\test_web_element_child_at_form.py
```

仅检查合同，不操作浏览器：

```powershell
uv run .\web\test_web_element_child_at_form.py --contract-only
```
