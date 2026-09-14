# `uiautoma.web.delete_cookie()` 测试结果

## 源码检查

当前 SDK `uiautoma.web` 未定义或导出 `delete_cookie`；`__all__` 中也不存在该名称。
现有公开 API 是 `remove_cookie()`，其内部调用 Runtime 的 `web_delete_cookie`。

## 测试脚本

`web/test_web_delete_cookie.py`

脚本只做公开入口检查。API 不存在时不会启动浏览器或修改 Cookie。

## 当前状态

`FAIL`：公开 API 缺失，无法进行运行时验收。需要先明确是否应新增 `delete_cookie`，
或将清单中的该项目移除并继续使用 `remove_cookie`。
