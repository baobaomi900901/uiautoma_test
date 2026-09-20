# WebElement.input() 原生表单双靶场验收记录

## 当前结果与证据来源

**READY_FOR_LIVE（本轮覆盖范围）：两种靶场各 18/25 通过，共 36/50 通过；14 项失败，退出码均为 1。**

登记日期：2026-09-20。依据用户提交的两次完整终端输出登记；未声称 agent 运行了浏览器验收或连续三轮通过。

- [双模式完整终端输出归档](artifacts/element_input_native_form_20260920.txt)。
- 独立脚本：[test_web_element_input_native_form.py](../test_web_element_input_native_form.py)。
- 元素库：260902_web元素。
- SDK/Runtime 快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。
- 相关缺陷：[Issue #65](https://github.com/uiautoma/desktop/issues/65)。

## 用途与合同

```python
element.input(
    text: str, *, simulative: bool = True,
    cdp_input: bool = False, append: bool = False,
    contains_hotkey: bool = False, force_ime_eng: bool = False,
    send_key_delay: int = 50, focus_timeout: int = 1000,
    delay_after: float = 1, click_before_input: bool = True,
    anchor: object | None = None, input_check: bool = False,
    retry_times: int = 3, check_value: str = ""
) -> None
```

脚本覆盖所有公开参数的主要路径，并在两种靶场中执行：默认无参数使用非 iframe、非 shadow 表单；传入 `iframe` 使用 iframe/open shadow 表单。

## 两种靶场配置

| 模式 | 页面 | 输入元素 | 提交/重置 |
| --- | --- | --- | --- |
| noniframe | [form-controls](https://baobaomi900901.github.io/xpath/#/form-controls) | web靶场_非iframe_非shadow_表单测试_原生_输入框 | web靶场_非iframe_非shadow_表单测试_原生_按钮_提交 / web靶场_非iframe_非shadow_表单测试_原生_按钮_重置 |
| iframe | [iframe-shadow-form](https://baobaomi900901.github.io/xpath/#/iframe-shadow-form) | web靶场_表单测试_原生_输入框 | web靶场_表单测试_原生_按钮_提交 / web靶场_表单测试_原生_重置 |

每轮均打开并激活页面，核对三个元素，输入后点击提交按钮，从剪贴板 JSON 核对 `text`，再点击重置按钮。元素库路径不变。

## 实测矩阵

两种模式的结果完全一致：

| 用例 | 结果 | 说明 |
| --- | --- | --- |
| background_unicode | FAIL | 元素值已写入，但提交 JSON `text=""` |
| simulative_unicode | PASS | 不含 emoji 的 Unicode 模拟输入提交正确 |
| special_characters | FAIL | 元素值已写入，但提交 JSON `text=""` |
| append | FAIL | 追加值已写入，但提交 JSON `text=""` |
| input_check | FAIL | 元素值已写入，但提交 JSON `text=""` |
| cdp_input | PASS | 含 emoji 的 CDP 输入提交正确 |
| force_ime / send_key_delay / focus_timeout | PASS | 模拟输入路径提交正确 |
| click_before_input_false | FAIL | 元素值已写入，但提交 JSON `text=""` |
| anchor_string / tuple / dict / random | PASS | 模拟输入与锚点路径提交正确 |
| delay_after_none / positive | FAIL | 元素值已写入，但提交 JSON `text=""` |
| cleanup | PASS | 页面、Package、临时元素库均清理成功 |

每种模式：25 项中 18 项通过、7 项失败。失败均集中在 `simulative=False` 的普通 DOM 输入路径。

## 缺陷结论

这不是元素定位或靶场边界问题：

- 非 iframe 和 iframe 两种结构结果一致；
- 输入后通过 `get_value()` 读取的元素值符合预期；
- `simulative=True` 与 `cdp_input=True` 对照通过；
- 失败发生在点击提交后读取的表单 JSON，`text` 为空。

源码快照显示，SDK 的非模拟、非 CDP 路径调用普通 `type_text`；页面引擎普通分支直接设置 `element.value`，但没有像其他路径一样同步受控表单状态。该证据已补充到 [Issue #65](https://github.com/uiautoma/desktop/issues/65)。

当前不将 API 标记为 VERIFIED；等待产品修复或开发者确认预期语义。

## 复测命令

```powershell
uv run .\web\test_web_element_input_native_form.py
uv run .\web\test_web_element_input_native_form.py iframe
```
