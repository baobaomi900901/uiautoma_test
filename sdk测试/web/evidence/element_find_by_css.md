# WebElement.find_by_css() 表单场景验收

## 用途与合同

在已经定位的 WebElement 子树内，以 CSS 选择器查找唯一元素：

```python
element.find_by_css(css_selector: str, *, timeout: float = 10) -> WebElement
```

`css_selector` 必填，可位置或关键字传入；`timeout` 仅限关键字，默认 10 秒。唯一命中返回 WebElement，多项命中抛 AmbiguousElementError，未命中抛 ElementNotFoundError。本次同时核对了默认调用、零超时和有限等待。

只读源码快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。用户日志中的 SDK 导入位置为该检出下 `sdk/src/uiautoma/__init__.py`；日志没有 Runtime 二进制版本，不额外推定正在运行服务的构建来源。

## 真实验收结果

**VERIFIED（本轮覆盖范围）：38/38 通过，退出码 0，总耗时 4436.4ms。**

本记录依据用户提供的一次完整 Chrome 实测输出，登记日期为 2026-09-19。不是 agent 自行执行的完整浏览器验收，也不代表连续三轮运行。

- 靶场：[iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form)。
- 元素库：`260902_web元素`；测试使用临时副本。
- 根容器：已定位的 iframe/open shadow 内 `#shadow-form-content`。
- 库元素：Ant 文本、密码、邮箱、数字输入框以及动态 ID 开关。
- 脚本：[test_web_element_find_by_css_form.py](../test_web_element_find_by_css_form.py)。
- 原始终端输出：[element_find_by_css_20260919.txt](artifacts/element_find_by_css_20260919.txt)。

| 用例编号 | 检查内容 | 实测结果 |
| --- | --- | --- |
| 01 | API 合同 | 签名、默认值、返回注解通过 |
| 02–10 | 元素库副本、开关、页面元素、根容器、独立 DOM 参照 | 全部通过；开关初始 false，未点击 |
| 11–15 | 文本框、密码包装 span、密码 input、邮箱框、数字框 | 5 个 CSS 分别唯一命中正确节点 |
| 16–18 | 关键字调用、零超时、重复读取 | 通过；连续三次均核对正确 DOM id |
| 19 | 多项匹配 | DOM 有 37 个 input，API 抛 AmbiguousElementError |
| 20–21 | 未命中 | 零超时、0.3 秒等待均抛 ElementNotFoundError；有限等待实测 300.6ms |
| 22–24 | 子树边界 | 排除子树外元素、排除根自身；密码包装内的 input 唯一命中 |
| 25–26 | CSS 语法错误及后续可用性 | RpcProtocolError，trace=invalid_css_selector；之后正常 CSS 查询成功 |
| 27–32 | 非法选择器与超时 | None、整数、空串、空白、负超时、非数字超时均被 InvalidParamsError 拒绝 |
| 33–35 | 参数调用规则 | 缺参、多余位置参数、未知关键字均被 TypeError 拒绝 |
| 36–38 | 清理 | 页面与 Package 的 close() 调用成功；临时副本删除并核对不存在 |

## 期望值来源与独立确证

准备阶段用元素库定位已知节点，并读取 DOM 属性；祖先遍历按 DOM id 核对固定容器，不比较每次查询新分配的 Runtime `.id`。

页面 JavaScript 通过 `iframe.contentDocument → host.shadowRoot → #shadow-form-content` 直接执行原生 `querySelectorAll`，没有调用被测 `find_by_css()` 来生成期望值。该参照确认 5 个正向 CSS 各匹配 1 项、`input` 匹配 37 项、未命中选择器和根自身匹配 0 项、密码包装内只有 1 个 input。

结果校验区分两个实际节点：

- 密码库项及包装 CSS 对应 `span.ant-input-affix-wrapper.ant-input-password`，本身没有 id；通过其 outerHTML 核对包含 `input#form-controls-ant-password[type=password]`。
- 密码 input CSS 对应上述内部 input，直接核对 DOM id。

邮箱使用明确的 Ant DOM id 和 placeholder，避免将原生邮箱框误认作 Ant 邮箱框。

## 实测边界

本次证明的是“取得 iframe/open shadow 内的根元素后，在该根子树内执行 CSS 查找”。没有验证从顶层页面仅凭普通 CSS 自动穿越 iframe 或 Shadow DOM，也未覆盖闭合 Shadow DOM、Edge 或无限等待。

非法 CSS 的异常类型按本次源码快照和真实输出记录为 `RpcProtocolError`，同时要求 `trace=invalid_css_selector`；其他 Runtime 错误不能算作正确拒绝。

清理结果中，页面和 Package 只核对 close() 调用成功，未额外枚举浏览器标签以证明无残留；临时目录核对了不存在。保存的选择器在元素作用域内查找的问题仍由 [Issue #64](https://github.com/uiautoma/desktop/issues/64) 跟踪。

## 复测命令

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_element_find_by_css_form.py
```

仅检查合同（不打开浏览器）：

```powershell
uv run .\web\test_web_element_find_by_css_form.py --contract-only
```
