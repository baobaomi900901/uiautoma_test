# `uiautoma.web.get_cookie()` 测试设计

## 用途

按 URL 和 Cookie 名称读取单个 Cookie；未找到时返回空字典。

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | `url`、`mode` 可位置传参，`name` 仅限关键字，默认值符合源码 |
| 已存在 Cookie | 返回字典，名称和值正确 |
| 未命中 | 返回 `{}` |
| 重复读取 | 连续三次结果稳定 |
| 缺少 name | `ValueError` 正确拒绝 |
| 参数边界 | `name` 位置传入被 `TypeError` 拒绝 |
| 资源清理 | 测试 Cookie 和页面已清理 |

## 执行

```powershell
uv run .\web\test_web_get_cookie.py
```

仅检查合同：

```powershell
uv run .\web\test_web_get_cookie.py --contract-only
```

## 当前状态

**VERIFIED：8/8 通过，退出码 0。**

本轮已验证：API 合同、已存在 Cookie 读取、未命中空字典、重复读取、缺少 `name`、参数边界和资源清理。
