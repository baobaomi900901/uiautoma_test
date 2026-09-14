# `uiautoma.web.get()` 测试设计

## 用途

从已连接的浏览器标签页中按标题、URL 或两者组合查找网页，并返回 `WebBrowser`。未命中时默认不新建页面；`open_page=True` 时可按 `page_url` 新建。

## 测试脚本

`web/test_web_get.py`

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 参数顺序、位置/关键字规则、默认值和返回类型符合源码 |
| 测试页面准备 | 通过 `web.create()` 打开 Web 表单靶场 |
| URL 匹配 | `url` 能获取已打开页面 |
| 标题匹配 | `title` 能获取已打开页面 |
| 联合匹配 | `title + url` 同时匹配 |
| 通配符 | `use_wildcard=True` 的筛选行为正确 |
| 未命中 | `open_page=False` 时报告未找到 |
| 参数规则 | `page_url` 未配合 `open_page=True` 时被拒绝 |
| 资源清理 | 关闭脚本创建的测试页面 |

## 执行

```powershell
uv run .\web\test_web_get.py
```

仅检查合同：

```powershell
uv run .\web\test_web_get.py --contract-only
```

## 当前状态

**VERIFIED：9/9 通过，退出码 0。**

本轮已验证：API 合同、页面准备、URL/标题/联合匹配、通配符筛选、未命中异常、`page_url` 参数规则，以及测试页面资源清理。
