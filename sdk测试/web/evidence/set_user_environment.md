# `uiautoma.web.set_user_environment()` 测试设计

## 用途

选择后续 `web.create/get/get_active` 使用的浏览器用户环境，可按环境名称或指定用户数据目录定位现有 Chrome/Edge Profile。该 API 只更新当前 SDK 会话配置，不主动启动浏览器；测试结束调用 `reset_user_environment()` 恢复配置。

## 测试脚本

`web/test_web_set_user_environment.py`

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 四个位置参数、默认值和返回 None 符合源码 |
| 默认 Profile | 选择 `Default` 环境成功 |
| 指定用户目录 | 指定当前 Chrome/Edge User Data 目录成功（目录存在时） |
| 非法参数 | 非法浏览器、空环境名、缺少目录、非布尔值被拒绝 |
| 参数边界 | 多余位置参数被 `TypeError` 拒绝 |
| 资源恢复 | 测试结束恢复原浏览器环境选择 |

## 执行

```powershell
uv run .\web\test_web_set_user_environment.py
```

仅检查合同：

```powershell
uv run .\web\test_web_set_user_environment.py --contract-only
```

## 当前状态

该 API 会修改当前 SDK 会话环境选择，脚本会在 finally 阶段恢复；若本机没有指定 Profile 或插件未连接，相关场景标记为 `BLOCKED`，不判定为产品缺陷。

### Chrome Profile 全量复测（2026-09-14）

脚本：`web/test_web_set_user_environment_profiles.py`

结果：**6/6 通过，退出码 0**。

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过 |
| Profile 查询 | 通过，发现 3 个：`Default（Rengar）`、`Profile 1（用户1）`、`Profile 4（棉花糖）` |
| Default | 通过，成功打开并关闭百度标签页 |
| Profile 1 | 通过，成功打开并关闭百度标签页 |
| Profile 4 | 通过（预期环境状态）：`web_environment_unavailable`；该用户的 UIAutoma Chrome 插件被人工关闭，按预期跳过打开 |
| 环境恢复 | 通过，已调用 `reset_user_environment("chrome")` |

该结果与人工观察一致：`Profile 4（棉花糖）` 的浏览器窗口仍存在，但插件关闭后无法连接自动化服务；按本轮验收约定，这属于预期环境状态，计为通过但不声称百度已打开。若要严格要求每个 Profile 都可用，使用 `--strict-profile-availability`，该项将按失败处理。该状态不属于 `set_user_environment()` 的参数或选择逻辑失败。
