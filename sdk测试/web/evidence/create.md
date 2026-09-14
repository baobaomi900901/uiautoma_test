# `uiautoma.web.create()` 测试设计

## 用途

打开一个新的浏览器网页，按指定模式和超时等待加载，并返回可继续操作的 `WebBrowser` 对象。

## 测试目标

脚本：`web/test_web_create.py`

目标页面：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 参数顺序、位置/关键字规则、默认值和返回注解与源码一致 |
| 默认打开 | `web.create()` 成功返回 `WebBrowser` |
| 页面元数据 | 返回对象可读取 URL 和标题 |
| 重复读取 | 同一页面重复读取 URL 结果稳定 |
| 资源清理 | 测试结束关闭 `create()` 打开的页面 |
| 参数边界 | 后续补充非法 URL、非法 mode、非法 timeout、非法 arguments 场景 |

## 执行

```powershell
uv run .\web\test_web_create.py
```

仅检查公开签名：

```powershell
uv run .\web\test_web_create.py --contract-only
```

## 输出约定

终端采用 Win32 API 测试格式：`进度 / 状态 / 测试项 / 测试结果`，每项显示通过或失败，末尾显示总结果与退出码。浏览器页面由 `web.create()` 实际打开，脚本结束时自动关闭。

## 当前状态

**VERIFIED：5/5 通过，退出码 0。**

本轮真实运行结果：

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过 |
| `create()` 默认打开 | 通过，成功返回 `WebBrowser` |
| 页面元数据 | 通过，可读取 URL 和标题 |
| 重复读取 | 通过，URL 稳定 |
| 资源清理 | 通过，页面已关闭 |

运行页面：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
