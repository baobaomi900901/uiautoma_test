# WebElement.clipboard_input() 双靶场验收记录

## 当前结果与证据来源

**VERIFIED（本轮覆盖范围）：非 iframe 22/22、iframe 22/22，共 44/44 检查通过；两次退出码均为 0。**

登记日期：2026-09-20。依据用户提交的一次完整双模式终端输出登记；未声称 agent 运行浏览器验收或连续三轮通过。

- [双模式完整终端输出归档](artifacts/element_clipboard_input_native_form_20260920.txt)。
- 独立脚本：[test_web_clipboard_input_native_form.py](../test_web_clipboard_input_native_form.py)。
- 元素库：260902_web元素。
- SDK/Runtime 快照：检出目录 `D:\code\desktop`，commit `c101caa9dcd115a461fc71ecaed351b0dea880b8`。

## 合同与靶场模式

```python
element.clipboard_input(
    text: str, *, append: bool = False,
    focus_timeout: int = 1000, delay_after: float = 1,
    send_key_delay: int = 50, click_before_input: bool = True,
    anchor: object | None = None, input_check: bool = False,
    retry_times: int = 3, check_value: str = ""
) -> None
```

默认模式不带参数使用非 iframe、非 shadow 靶场；命令末尾传入 `iframe` 使用 iframe/open shadow 靶场。每轮均执行：打开并激活页面、绑定输入/提交/重置元素、调用 `clipboard_input()`、点击提交读取 JSON 的 `text`，再点击重置。

| 模式 | 靶场 | 元素 |
| --- | --- | --- |
| noniframe | https://baobaomi900901.github.io/xpath/#/form-controls | web靶场_非iframe_非shadow_表单测试_原生_输入框 / 按钮_提交 / 按钮_重置 |
| iframe | https://baobaomi900901.github.io/xpath/#/iframe-shadow-form | web靶场_表单测试_原生_输入框 / 按钮_提交 / 重置 |

## 实测矩阵

两种模式各 22/22 通过：

| 范围 | 实测结果 |
| --- | --- |
| 基础剪贴板输入 | 提交 JSON 的 `text` 与输入内容一致，含中文、emoji 和符号 |
| append | 两段输入追加后提交值正确 |
| input_check / retry_times / check_value | 提交值正确 |
| focus_timeout=0 / send_key_delay=0 | 提交值正确 |
| click_before_input=False | 提交值正确 |
| anchor 字符串、元组、字典、random | 提交值正确 |
| delay_after=None / 0.2 | 提交值正确 |
| 页面和元素准备 | 两种靶场均成功；iframe 模式动态 ID 开关确认关闭 |
| 资源清理 | 页面、Package、临时元素库均清理成功 |

两次完整运行的总耗时分别为 32509.4ms 和 32740.1ms；这是本轮实测值，不是性能承诺。

## 期望值与独立确证

输入结果不是通过元素对象返回值判断，而是点击原生提交按钮后，从 Windows 剪贴板读取靶场生成的 JSON，并严格核对其 `text` 字段。每个用例执行重置，避免前一轮内容污染后一轮。

## 范围与限制

本轮覆盖 Chrome、非 iframe 和 iframe/open shadow 两种靶场。未覆盖 Edge、静默页面和其他表单字段。剪贴板提交 JSON 的其他字段仅作为载荷存在，不作为本轮目标断言。

## 复测命令

```powershell
uv run .\web\test_web_clipboard_input_native_form.py
uv run .\web\test_web_clipboard_input_native_form.py iframe
```

兼容的元素脚本文件名也可运行：

```powershell
uv run .\web\test_web_element_clipboard_input_native_form.py
uv run .\web\test_web_element_clipboard_input_native_form.py iframe
```
