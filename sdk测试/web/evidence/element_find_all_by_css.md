# WebElement.find_all_by_css() 表单场景验收

## 用途与合同

在已经定位的 WebElement 子树内，以 CSS 选择器查找全部匹配元素：

```python
element.find_all_by_css(css_selector: str, *, timeout: float = 10) -> list[WebElement]
```

`css_selector` 必填，可位置或关键字传入；`timeout` 仅限关键字，默认 10 秒。单项和多项命中均返回列表；未命中返回 `[]`。本轮核对了默认调用、零超时和有限等待。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。用户日志中的 SDK 导入位置为该检出下 `sdk/src/uiautoma/__init__.py`。日志未包含 Runtime 二进制版本，不据此推定服务构建来源。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：39/39 通过，退出码 0，总耗时 5714.2ms。**

依据用户提供的一次完整 Chrome 实测输出登记，登记日期为 2026-09-19。没有将离线回归计入这 39 项，也未声称连续三轮浏览器实测。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：`260902_web元素`，使用本次临时副本。
- 根容器：已定位的 iframe/open shadow 内 `#shadow-form-content`。
- 目标：Ant 文本、密码、邮箱、数字输入框，以及容器内全部 input。
- 脚本：[test_web_element_find_all_by_css_form.py](../test_web_element_find_all_by_css_form.py)。
- 原始输出：[element_find_all_by_css_20260919.txt](artifacts/element_find_all_by_css_20260919.txt)。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | 签名、默认值及 list[WebElement] 返回注解通过 |
| 02–10 | 库副本、开关、已知节点、共同容器、独立 DOM 参照 | 全部通过；开关初始 false，未点击 |
| 11–15 | 5 个 CSS 单项列表 | 文本、密码包装 span、密码 input、邮箱、数字框均返回正确单项列表 |
| 16–18 | 关键字、零超时、重复读取 | 全部通过；连续三次逐次核对单项列表 |
| 19 | 全部 input | 预期 37 项，实际 37 项；属性组合及重复次数与 DOM 一致 |
| 20 | 四项分组 CSS | 返回四个 Ant 输入框各一次，无漏项或重复 |
| 21–22 | 未命中 | 零超时及有限等待均返回 []；有限等待实测 300.8ms |
| 23–25 | 子树范围 | 子树外元素、根自身均返回 []；密码包装内 input 返回正确单项列表 |
| 26–27 | 非法 CSS 及恢复 | RpcProtocolError / invalid_css_selector；随后有效 CSS 仍可查询 |
| 28–33 | 非法选择器及超时 | None、整数、空串、空白、负超时、非数字超时均被 InvalidParamsError 拒绝 |
| 34–36 | 调用参数边界 | 缺参、多余位置参数、未知关键字均被 TypeError 拒绝 |
| 37–39 | 清理 | 页面和 Package 的 close() 调用成功；副本已删除并核对不存在 |

## 期望值来源与独立确证

先通过元素库定位四个已知控件，用 DOM id 核对共同容器。密码库项实际是无 id 的包装 span，通过 outerHTML 确认其 class 和内部密码 input；内部 input 则独立核对 `form-controls-ant-password`，不混淆两种节点。

独立页面 JavaScript 进入 `iframe.contentDocument → host.shadowRoot` 后，在容器内执行原生 `querySelectorAll`。预期数量和属性不由被测 `find_all_by_css()` 生成。

- 五个正向选择器在 DOM 中各命中一项。
- `input` 的预期数量由本次 DOM 实时读取，实际为 37，脚本未写死 37。
- 37 项逐项读取 `id/type/role/placeholder`，按属性组合及出现次数比较；同样数量但内容不同会失败。
- 四个明确 Ant input id 组成分组选择器，单独核对四项均出现一次。
- 未命中、排除根自身和密码包装内 input 的数量分别独立确认为 0、0、1。

## 实测边界

本次范围是已定位的 iframe/open shadow 容器子树内 CSS 查找，不包含从顶层页面用普通 CSS 自动跨 iframe/shadow、闭合 Shadow DOM、Edge、无限等待及极大结果集。

列表比较不要求顺序不变，不比较 Runtime `.id` 跨调用是否相同。全部 input 的完整性依据数量和属性组合比较，不等同于逐节点浏览器内部引用同一性证明。

非法 CSS 的实际拒绝为 `RpcProtocolError`，且必须携带 `invalid_css_selector`；其他 Runtime 错误仍按失败处理。

清理中页面和 Package 核对 close() 调用成功，未另行枚举标签确认无残留；临时目录额外核对不存在。保存的选择器作用域问题仍由 [Issue #64](https://github.com/uiautoma/desktop/issues/64) 跟踪。

## 复测命令

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_element_find_all_by_css_form.py
```

仅检查合同，不操作浏览器：

```powershell
uv run .\web\test_web_element_find_all_by_css_form.py --contract-only
```
