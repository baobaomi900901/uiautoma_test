# WebElement.find_all_by_xpath() 表单场景验收

## 用途与合同

以当前 WebElement 为上下文执行 XPath，返回全部匹配元素：

```python
element.find_all_by_xpath(xpath_selector: str, *, timeout: float = 10) -> list[WebElement]
```

`xpath_selector` 必填，可位置或关键字传入；`timeout` 仅限关键字，默认 10 秒。单项和多项命中均返回列表，未命中返回 `[]`；相对路径以当前元素为起点。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。用户输出中的 SDK 来自该检出下 `sdk/src/uiautoma/__init__.py`。日志未包含 Runtime 二进制版本，不额外推定服务构建来源。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：41/41 通过，退出码 0，总耗时 4681.7ms。**

依据用户提供的一次完整 Chrome 实测输出登记，登记日期为 2026-09-19。没有把离线回归计入 41 项，也未声称连续三轮浏览器实测。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：`260902_web元素`，使用临时副本。
- 上下文：已定位的 iframe/open shadow 内 `#shadow-form-content` 以及密码包装节点。
- 目标：Ant 文本、密码、邮箱、数字控件及根容器内全部 input。
- 脚本：[test_web_element_find_all_by_xpath_form.py](../test_web_element_find_all_by_xpath_form.py)。
- 原始输出：[element_find_all_by_xpath_20260919.txt](artifacts/element_find_all_by_xpath_20260919.txt)。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | 签名、默认值及 list[WebElement] 返回注解通过 |
| 02–10 | 库副本、页面、开关、控件、容器、独立 DOM 参照 | 全部通过；开关初始 false，未点击 |
| 11–15 | 5 个 XPath 单项列表 | 文本、密码包装 span、密码 input、邮箱、数字框均命中正确节点 |
| 16–18 | 关键字、零超时、重复读取 | 全部通过；连续三次逐次核对单项列表 |
| 19 | 全部 .//input | 预期 37 项，实际 37 项；属性组合及重复次数一致 |
| 20 | 联合 XPath 去重 | 重复文本框分支仍只返回四个 Ant input 各一次 |
| 21–22 | 未命中 | 零超时、有限等待均返回 []；有限等待实测 300.6ms |
| 23–27 | 上下文与父子路径 | 相对后代范围外及根自身的后代查询返回 []；.、./input、./input/.. 返回正确单项列表 |
| 28–29 | 非法 XPath 及恢复 | RpcProtocolError / xpath_segment_evaluate_failed；随后有效查询成功 |
| 30–35 | 非法选择器及超时 | None、整数、空串、空白、负超时、非数字超时均被 InvalidParamsError 拒绝 |
| 36–38 | 调用参数边界 | 缺参、多余位置参数、未知关键字均被 TypeError 拒绝 |
| 39–41 | 清理 | 页面和 Package 的 close() 调用成功；副本删除并核对不存在 |

## 期望值来源与独立确证

通过元素库定位已知控件，再沿各父级链核对 DOM id 为 `shadow-form-content` 的容器，不比较不同查询返回的 Runtime `.id`。

独立页面脚本取得 iframe 文档和 open shadow 内的上下文元素，直接以原生 `document.evaluate` 计算 XPath 结果。预期数量和属性不由被测 `find_all_by_xpath()` 生成。

- 五个正向 XPath 各命中一项，分别核对元素类型、DOM id 或密码包装结构。
- `.//input` 的预期数量来自实时 DOM，本轮为 37，脚本未写死 37。
- 对全部结果比较 `id/type/role/placeholder` 属性组合及出现次数；仅数量相同不足以通过。
- 联合 XPath 使用四个明确 Ant input id，并额外重复文本框分支；DOM 与 API 均返回四项，无重复。
- 密码库项为无 id 的包装 span，通过 outerHTML 核对其 class 以及内部密码 input。包装节点与内部 input 分别验收。

## 实测边界

| 相对表达式 | 上下文 | 本轮返回 |
| --- | --- | --- |
| `.` | #shadow-form-content | 包含当前容器的一项列表 |
| `.//div[@id='shadow-form-content']` | 同一容器 | []，后代查询不包含根自身 |
| `./input` | 密码包装 span | 包含内部密码 input 的一项列表 |
| `./input/..` | 密码包装 span | 包含该包装 span 的一项列表 |

本轮不要求返回顺序固定，不把 Runtime `.id` 作为跨调用的 DOM 同一性证据。完整性按数量和属性组合比较，未证明属性完全相同的两个节点的内部引用身份。

未覆盖顶层页面自动跨 iframe/shadow 的绝对路径、闭合 Shadow DOM、XPath 标量结果、Edge、无限等待和极大结果集。

非法 XPath 的实际异常为 `RpcProtocolError`，同时核对 `trace=xpath_segment_evaluate_failed`；其他 Runtime 故障不算正确拒绝。

清理时页面和 Package 仅核对 close() 调用成功，未额外枚举标签确认无残留；临时目录核对了不存在。保存的选择器作用域问题仍由 [Issue #64](https://github.com/uiautoma/desktop/issues/64) 跟踪。

## 复测命令

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_element_find_all_by_xpath_form.py
```

仅检查合同，不操作浏览器：

```powershell
uv run .\web\test_web_element_find_all_by_xpath_form.py --contract-only
```
