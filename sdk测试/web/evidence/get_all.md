# `uiautoma.web.get_all()` 测试设计

## 用途

获取已连接浏览器中符合标题或 URL 条件的全部网页，返回 `list[WebBrowser]`；未命中时返回空列表。

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | `mode` 可位置传参，其余筛选参数仅限关键字，默认值符合源码 |
| URL 筛选 | 返回列表包含已打开的目标页面 |
| 标题筛选 | 标题筛选包含目标页面 |
| 通配符 | `use_wildcard=True` 筛选正确 |
| 未命中 | 返回空列表 |
| 重复读取 | 返回页面 ID 和顺序稳定 |
| 参数边界 | 额外位置参数被 `TypeError` 拒绝 |
| 资源清理 | 关闭脚本创建的页面 |

## 执行

```powershell
uv run .\web\test_web_get_all.py
```

仅检查合同：

```powershell
uv run .\web\test_web_get_all.py --contract-only
```

## 当前状态

**VERIFIED：9/9 通过，退出码 0。**

本轮已验证：API 合同、URL/标题筛选、通配符、未命中空列表、重复读取稳定性、参数边界和页面资源清理。
