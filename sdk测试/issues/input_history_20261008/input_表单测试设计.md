# WebElement.input() 表单测试设计

## 目标

在 GitHub 表单靶场的 Ant Design 与原生 HTML 两侧普通文本框上，验证当前 SDK
`WebElement.input()` 的输入、提交回读、重置恢复和参数边界。两侧分别执行同一组用例，
任何一侧失败都单独记录，不用另一侧结果替代。

## 测试对象

页面：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

元素库：`D:\code\元素库\260902_web元素`

| 侧别 | 输入框 | 提交按钮 | 重置按钮 |
| --- | --- | --- | --- |
| Ant | `web靶场_表单测试_ant_输入框` | `web靶场_表单测试_ant_按钮_提交` | `web靶场_表单测试_ant_按钮_重置` |
| 原生 | `web靶场_表单测试_原生_输入框` | `web靶场_表单测试_原生_按钮_提交` | `web靶场_表单测试_原生_重置` |

公共开关：`web靶场_表单测试_控制表单组件id是否为动态的开关`。
脚本先读取开关状态，仅当开启时点击一次关闭；已关闭时不点击。

## 被测合同

元素库采用当前 `groups[].elements[]` manifest 结构；测试准备阶段先校验三类元素名称，校验通过后才打开 Chrome、关闭动态 ID 开关、获取运行时元素并执行输入/提交/重置场景。

```python
element.input(
    text,
    *,
    simulative=True,
    cdp_input=False,
    append=False,
    contains_hotkey=False,
    force_ime_eng=False,
    send_key_delay=50,
    focus_timeout=1000,
    delay_after=1,
    click_before_input=True,
    anchor=None,
    input_check=False,
    retry_times=3,
    check_value="",
) -> None
```

`text` 必填，其余参数仅限关键字。当前源码合同包含
`force_ime_eng`（下划线小写）参数；`driver_input`、`force_ime_ENG`、`force_img_ENG`
等旧脚本参数不属于当前合同。

## 用例设计

每个正常用例都按“重置 → 输入 → 提交 → 读取提交 JSON → 与预期比较 → 重置”执行。

1. 默认覆盖：`input("UIAutoma_Input_01")`。
2. 追加：先输入 `Base`，再 `input("_Append", append=True)`，提交值应为 `Base_Append`。
3. 全关键字：显式传入 `simulative=True`、`append=False`、`delay_after=0`、
   `click_before_input=True`。
4. CDP 输入：`cdp_input=True`，提交值应精确一致。
5. 输入校验：`input_check=True, check_value="Check_01", retry_times=1`。
6. Unicode：中文、Emoji、符号和多行文本。
7. 快捷键：`contains_hotkey=True` 配合 `^a`，替换已有值；验证完整提交值。
8. 聚焦与点击：`click_before_input=False/True` 各一次，确认输入成功。
9. 毫秒参数：`send_key_delay=0/30`、`focus_timeout=0/200`，记录耗时差异。
10. 动作后等待：`delay_after=None/0/0.2`，用配对调用测量差值。
11. 类型转换：数字 `text` 按当前实现转换为字符串；不打印敏感数据。
12. 锚点：普通输入的 `anchor` 使用下划线九宫格、`random`、三元组和字典；
    仅在点击前输入生效的模式下核对落点。
13. 非法参数：负数/非数字毫秒、非法锚点、负数/非数字延时、错误校验组合；
    明确动作发生前还是发生后报错。

每侧执行以上用例；密码、邮箱、数字及文本域不在本脚本范围，留给后续脚本。

## 独立校验

- 提交按钮复制的 JSON 是主要业务验收来源；用 `win32.clipboard.get_text()` 读取后
  立即恢复原剪贴板文本。
- 用 Playwright/浏览器 DOM 仅作辅助诊断，确认输入框当前 value；不能只用 SDK
  `get_value()` 回读证明 `input()` 成功。
- 每侧重置按钮必须在正常及预期动作后异常用例中执行；异常清理放在 finally。

## 清理与生命周期

测试结束确认两侧普通文本框均为空或初始值、剪贴板恢复、浏览器页面关闭、Package
连接释放。若自动焦点恢复失败，自动模式只记录警告，不等待人工；输入值、页面关闭、
临时资源清理失败仍判测试失败。

只有 Ant 和原生两侧全部正常用例、边界、提交回读和清理通过，且测试者确认日志后，
才将 `web/evidence/input.md` 和 `sdk测试/index.md` 中的状态更新为 `VERIFIED`。
失败时保留完整日志，区分测试脚本错误、环境阻塞和产品缺陷并决定是否提交 issue。

## 执行顺序

先完成公共页面/开关前置，再按上述 1–13 执行 Ant，随后按相同顺序执行原生。
两侧均完成后再汇总；不把两侧合并成无法定位的单一失败项。
