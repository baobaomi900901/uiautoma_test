# `uiautoma.web.remove_cookie()` 测试设计

## 用途

按 URL、Cookie 名称和浏览器模式删除 Cookie；操作返回 `None`。

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 参数顺序、关键字规则和默认值符合源码 |
| 删除已存在 Cookie | 删除后 `get_cookie()` 返回 `{}` |
| 重复删除 | 重复删除安全返回 `None` |
| 删除不存在 Cookie | 返回 `None` |
| 分区参数 | 按合同处理或返回明确环境错误 |
| 参数边界 | 缺少 name、位置传入 partition_key 被拒绝 |
| 资源清理 | 测试 Cookie 和页面已清理 |

## 执行

```powershell
uv run .\web\test_web_remove_cookie.py
```

仅检查合同：

```powershell
uv run .\web\test_web_remove_cookie.py --contract-only
```

## 当前状态

**VERIFIED：9/9 通过，退出码 0。**

本轮已验证：API 合同、删除已存在/不存在 Cookie、重复删除、分区参数、参数边界以及资源清理。
