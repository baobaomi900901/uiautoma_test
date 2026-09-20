# WebElement.find_by_xpath() 表单场景验收

## 用途与合同

以当前 WebElement 为上下文执行 XPath，查找唯一元素：

```python
element.find_by_xpath(xpath_selector: str, *, timeout: float = 10) -> WebElement
```

`xpath_selector` 必填，可位置或关键字传入；`timeout` 仅限关键字，默认 10 秒。唯一命中返回 WebElement；多项命中抛 AmbiguousElementError，未命中抛 ElementNotFoundError。相对路径以当前元素为起点。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。用户日志中的 SDK 导入位置为该检出下 `sdk/src/uiautoma/__init__.py`；日志未包含 Runtime 二进制版本，不能据此推定服务构建来源。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：40/40 通过，退出码 0，总耗时 4104.9ms。**

依据用户提供的一次完整 Chrome 实测输出登记，登记日期为 2026-09-19。本记录不代表连续三轮浏览器实测；其中重复读取用例是在同一轮内执行三次查询。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：`260902_web元素`，测试打开临时副本。
- 上下文：已定位的 iframe/open shadow 内 `#shadow-form-content`，以及密码框包装节点。
- 目标：Ant 文本、密码、邮箱、数字控件；密码包装 span 和内部 input 分别验收。
- 脚本：[test_web_element_find_by_xpath_form.py](../test_web_element_find_by_xpath_form.py)。
- 原始输出：[element_find_by_xpath_20260919.txt](artifacts/element_find_by_xpath_20260919.txt)。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | 签名、默认值及 WebElement 返回注解通过 |
| 02–10 | 库副本、页面、开关、已知节点、容器、独立 DOM 参照 | 全部通过；开关初始 false，未点击 |
| 11–15 | 5 个正向相对 XPath | 文本、密码包装 span、密码 input、邮箱、数字框均唯一命中正确节点 |
| 16–18 | 关键字、零超时、重复读取 | 全部通过；三次查询均核对正确 DOM id |
| 19 | 多项命中 | DOM 中 .//input 有 37 项；API 抛 AmbiguousElementError |
| 20–21 | 未命中 | 零超时与有限等待均抛 ElementNotFoundError；有限等待实测 300.9ms |
| 22–26 | 上下文与父子路径 | 排除相对后代范围外节点；.// 不包含根自身；. 返回根；./input 与 ./input/.. 分别返回密码 input 和包装 span |
| 27–28 | 非法 XPath 及恢复 | RpcProtocolError / xpath_segment_evaluate_failed；之后有效查询成功 |
| 29–34 | 非法选择器及超时 | None、整数、空串、空白、负超时、非数字超时均被 InvalidParamsError 拒绝 |
| 35–37 | 调用参数规则 | 缺参、多余位置参数、未知关键字均被 TypeError 拒绝 |
| 38–40 | 清理 | 页面及 Package 的 close() 调用成功；临时副本删除并核对不存在 |

## 期望值来源与独立确证

准备阶段使用元素库定位已知节点，按真实 DOM id 验证控件与共同容器，不比较跨调用重新分配的 Runtime `.id`。

独立页面脚本取得 iframe 文档与 open shadow 中的上下文元素后，直接使用原生 `document.evaluate` 查询。期望结果不通过被测 `find_by_xpath()` 生成。该参照确认五个正向 XPath 各命中一项、`.//input` 命中 37 项，并单独确认未命中、当前节点、直接子节点和父路径结果。

密码库项实际为无 id 的 `span.ant-input-affix-wrapper`。脚本通过 outerHTML 核对包装节点及其内部 `input#form-controls-ant-password[type=password]`，不会用内部 input 代替包装节点的命中结果。邮箱按明确 Ant id 与 placeholder 查询，不依赖它具有原生 email 类型。

## 实测边界

| 相对表达式 | 当前上下文 | 本轮结果 |
| --- | --- | --- |
| `.` | #shadow-form-content | 返回当前容器 |
| `.//div[@id='shadow-form-content']` | 同一容器 | 未命中，后代查询不包含自身 |
| `./input` | 密码包装 span | 返回内部密码 input |
| `./input/..` | 密码包装 span | 返回该包装 span |

不能将上述相对路径测试概括为所有 XPath 都只能查后代；本轮明确验证了当前节点和父路径语义。

本次未验证从顶层页面自动跨 iframe/shadow 的绝对路径、闭合 Shadow DOM、XPath 标量结果、Edge 或无限等待。

非法 XPath 的实际异常为 `RpcProtocolError`，同时要求 `trace=xpath_segment_evaluate_failed`；其他 Runtime 故障不算正确拒绝。

清理时页面和 Package 仅核对 close() 调用成功，未额外枚举标签确认无残留；临时目录核对了不存在。保存的选择器作用域问题仍由 [Issue #64](https://github.com/uiautoma/desktop/issues/64) 跟踪。

## 复测命令

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_element_find_by_xpath_form.py
```

仅检查合同，不操作浏览器：

```powershell
uv run .\web\test_web_element_find_by_xpath_form.py --contract-only
```
