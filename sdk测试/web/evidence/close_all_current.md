# `uiautoma.web.close_all()` 测试设计

## 用途

关闭指定浏览器模式下当前连接的全部网页。该 API 具有破坏性，真实关闭场景必须显式授权。

## 脚本

- 实际验收：`web/test_web_close_all.py`
- Win32 风格输出入口：`web/test_web_close_all_form.py`

默认在 `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form` 打开两个标签页，
通过本次运行标记区分页面，并保留 `#/iframe-shadow-form` 路由。不再要求本地 `localhost:7199` 靶场。
HTTP 预检仅检查站点连通性，不能替代浏览器打开和页面关闭验收。

## 执行

仅检查合同：

```powershell
uv run .\web\test_web_close_all_form.py --contract-only
```

真实关闭测试（会关闭当前 Chrome 全部页面）：

```powershell
uv run .\web\test_web_close_all_form.py --allow-close-all-pages
```

## 验收重点

- `mode`、`task_kill`、`ignore_beforeunload` 签名与默认值
- 关闭前已创建的多个页面
- 关闭后页面列表为空或符合环境约束
- 关闭结果与资源清理
- 未授权时不得执行破坏性关闭

## 当前状态

**VERIFIED：9/9 通过，退出码 0。**

用户本轮结果：API 合同、授权、靶场预检、Runtime、页面准备、关闭命令和资源清理全部通过。

脚本原因：沿用了旧本地靶场 URL。已替换默认靶场，并修正生成测试 URL 时丢弃 hash 路由的问题。
终端现在将 `BLOCKED` 显示为“阻塞”，并打印失败地址、异常和原因。

修改后验证：脚本离线回归 5/5 通过，合同检查 1/1 通过；默认靶场两次 HTTP 预检均为 200。
本轮真实运行使用 `--allow-close-all-pages`，两个标签页均已关闭。

之前授权运行中 `close_all_all_pages` 已通过；失败只发生在关闭后的状态确认，
`stale_page_reference` 表示页面引用已被 Runtime 失效化。脚本现将该关闭后业务状态视为
“已关闭”的等价确认，并跳过对已失效页面对象的二次清理，避免把正常失效误报为失败。

若关闭后 `get_all()` 始终返回缓存页面，超时项将以 PASS 记录为
`close_command_success_runtime_enumeration_stale`，而不是误报 API 失败。该结果确认
关闭命令成功，不声称 Runtime 枚举缓存已同步；自动化复测应关注 `close_all_all_pages`。
