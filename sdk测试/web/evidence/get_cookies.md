# `uiautoma.web.get_cookies()` 测试设计

## 用途

读取浏览器 Cookie，并按名称、URL、域名、路径、分区、安全属性和会话属性筛选。

## 测试脚本

`web/test_web_get_cookies.py`

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 参数顺序、关键字规则和默认值符合源码 |
| Cookie 准备 | 在 cookie-test 页面写入会话和持久 Cookie |
| 全量读取 | 返回列表包含两个测试 Cookie |
| 名称筛选 | 只返回指定 Cookie |
| session 筛选 | `session=True/False` 结果正确 |
| domain/path 筛选 | 返回列表并包含测试 Cookie |
| 未命中 | 返回空列表 |
| 重复读取 | 结果稳定 |
| 参数边界 | 筛选参数位置传入被拒绝 |
| 资源清理 | 测试 Cookie 和页面已清理 |

## 执行

```powershell
uv run .\web\test_web_get_cookies.py
```

仅检查合同：

```powershell
uv run .\web\test_web_get_cookies.py --contract-only
```

## 当前状态

**VERIFIED：12/12 通过，退出码 0。**

本轮已验证：API 合同、Cookie 准备与全量读取、名称/session/domain/path 筛选、未命中、重复读取、参数边界、分区筛选调用和资源清理。
