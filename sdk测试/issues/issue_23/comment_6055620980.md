### 2026-10-08 复测补充：空串已正常，`disabled="false"` 仍误判

使用公开靶场 [keys-click-test](https://baobaomi900901.github.io/xpath/#/keys-click-test) 的两个真实按钮，SDK 通过元素库定位后调用 `WebElement.is_enabled()`。

连续三轮结果均为 **30/32 PASS、2 FAIL、0 BLOCKED，退出码 1**：

| 场景 | 浏览器 `button.disabled` / `:disabled` | API 实际 | API 期望 |
|---|---|---|---|
| 原始禁用按钮（`disabled=""`） | True / True | False | False |
| 原始可用按钮（无 disabled） | False / False | True | True |
| 对两个按钮分别设置 `disabled="false"` | True / True | **True** | **False** |

动态启用/禁用、`aria-disabled` true/false/缺失、重复只读、关闭页面和连接的生命周期用例均通过。每项属性恢复；三轮清理均通过，标签 2→2，无点击或输入事件。

请修正文中 Request 第 1 条将 `disabled="false"` / `"False"` 视为可用的验收口径。HTML 布尔属性由是否存在决定；表示 False 必须移除属性。字符串 true/false 不是合法的布尔属性写法，但属性存在时浏览器仍按禁用处理。依据：[HTML Standard，Boolean attributes](https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#boolean-attributes)。ARIA 属性的 true/false 字符串语义应另行处理。

本次仅修改测试侧脚本和证据，没有修改产品源码。测试状态保持 `READY_FOR_LIVE`。
