# `uiautoma.web.get_active()` 测试设计

## 用途

获取浏览器当前选中的网页，并返回 `WebBrowser`；非静默模式下会激活网页所在窗口。

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | `mode` 可位置传参，其余参数仅限关键字，默认值与源码一致 |
| 测试页面准备 | 打开目标页面并将其激活 |
| 默认超时 | 返回当前活动页面且 ID 匹配 |
| 零/None 超时 | 活动页面立即返回且 ID 匹配 |
| 重复读取 | 连续三次返回同一页面 |
| 非法超时 | 负值被拒绝 |
| 参数边界 | 额外位置参数被 `TypeError` 拒绝 |
| 资源清理 | 关闭测试创建的页面 |

## 执行

```powershell
uv run .\web\test_web_get_active.py
```

仅检查合同：

```powershell
uv run .\web\test_web_get_active.py --contract-only
```

## 当前状态

**VERIFIED：9/9 通过，退出码 0。**

本轮已验证：API 合同、活动页面获取、默认/零/None 超时、重复读取、非法超时、位置参数限制和页面资源清理。
