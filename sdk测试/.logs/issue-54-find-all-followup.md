## 补充：顶层win32.find_all也已实测复现显式Package拒绝

命令：`uv run .\win32\test_win32_module_find_all.py --non-interactive`。
测试者日志确认session类型为Package，由公开current()取得。

第07/21项调用 `win32.find_all(selector, session=package, timeout=0)` 失败：

```text
session 必须是由 uiautoma.open() 或 uiautoma.current() 返回的对象
异常: InvalidParamsError
```

与find共享的session适配问题由源码推测升级为真实复现。
默认上下文及显式None都通过。姓名输入框单项列表、未找到返回空列表、错误参数等检查通过。

新增真实多项场景也通过：表格页“win32靶场_表格数据_list普通单元格_相似元素”，通过名称
和Selector两种调用均返回140个不同Runtime单元格，含首个单元格“1”和普通单元格“用户1”。
这两项分别耗时6634.4ms和6338.1ms，包含逐项读取RuntimeId及文本，不等于find_all单次耗时。

汇总20/21通过，总耗时14820.3ms，退出码1。鼠标、Package及前台恢复通过，保留表格页。
请在修复后同时验收find与find_all的公开Package上下文，不要求测试者使用私有会话字段。
本次仅补充证据，产品代码未修改，API仍为READY_FOR_LIVE。
