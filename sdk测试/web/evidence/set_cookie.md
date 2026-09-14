# `uiautoma.web.set_cookie()` 测试设计

## 用途

向浏览器写入 Cookie，支持会话/持久生命周期、域名、路径、`httpOnly` 和 `secure` 属性。

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 参数顺序、关键字规则和默认值符合源码 |
| 会话 Cookie | 设置成功，返回 `None`，值可读回 |
| 持久 Cookie | 设置非会话 Cookie，值可读回 |
| 属性设置 | `httpOnly` 与 `secure` 属性可读回 |
| `value=None` | 不修改已有 Cookie，返回 `None` |
| 缺少 name | `ValueError` 正确拒绝 |
| 非法 expires | 非法有效期被拒绝 |
| 参数边界 | name/value 位置传入被 `TypeError` 拒绝 |
| 资源清理 | 测试 Cookie 和页面已清理 |

## 执行

```powershell
uv run .\web\test_web_set_cookie.py
```

仅检查合同：

```powershell
uv run .\web\test_web_set_cookie.py --contract-only
```

## 当前状态

**VERIFIED：10/10 通过，退出码 0。**

本轮已验证：API 合同、会话/持久 Cookie、`httpOnly`/`secure` 属性、`value=None`、非法参数、位置参数规则及资源清理。
