# set_cookie Path 结果判定确认探针

本目录归档实际执行过的诊断材料，正式 API 验收入口仍唯一：`web/test_web_browser_set_cookie.py`。
这两个探针分别观察原生 Chrome 返回值和当前 SDK 的网页绑定对照，不能当作产品修复通过记录。

## 环境与结果

- 同一安装文件：`C:\Program Files\Google\Chrome\Application\chrome.exe`，154.0.8037.95。
- 原生比较器使用已有 Playwright 1.62.1，仅用于驱动独立无窗口 Chrome，不加载 UIAutoma 包。
- 原生比较器通过 CDP Extensions.loadUnpacked 加载临时 MV3 扩展；只授予 cookies 权限与靶场域名 HTTP/HTTPS 主机权限。
- 临时配置与用户 Chrome 配置完全分开。原生测试不打开靶场文档，URL 仅作为 Cookie API 参数。
- 三轮 × 三个 URL/Path 情形 × callback/Promise，共 18 个原生调用，结果与预期一致。
- SDK 比较器在当前 dev Chrome 后台创建主/观察两页，用同一名称、值、Path、会话参数仅改变 WebBrowser 绑定，三对均复现。
- 第二对先调用匹配页面，再调用不匹配页面，排除“新建与覆盖不同”作为本次现象的解释。

原生比较器：不匹配 Path 时 callback/Promise 均返回 undefined，callback 的 runtime.lastError 为空，Promise 不拒绝。
Cookie 同时可被独立 CDP 读取。匹配 URL 时返回 Cookie 对象。
SDK：不匹配 URL 时已经写入却抛 cookie_set_failed；匹配 URL 时返回 None。

[完整证据](../../../web/evidence/browser_set_cookie.md)，含源代码快照、原始 JSON 和清理结果。

## 复现步骤

从 `D:\code\元素库\sdk测试` 执行；必须把材料复制到忽略的临时目录后运行，避免浏览器配置生成到 Issue 目录。
若该临时目录已存在，先查看内容并选新的空目录；SDK 探针要求位于 `.pytest_tmp` 下一级，以找到本工作区 `web/`。

```powershell
New-Item -ItemType Directory -Path .\.pytest_tmp\set_cookie_confirmation -Force
Copy-Item -LiteralPath .\issues\issue_74\confirmation_probe\native_cookie_probe.cjs -Destination .\.pytest_tmp\set_cookie_confirmation\native_cookie_probe.cjs
Copy-Item -LiteralPath .\issues\issue_74\confirmation_probe\sdk_path_probe.py -Destination .\.pytest_tmp\set_cookie_confirmation\sdk_path_probe.py
Copy-Item -LiteralPath .\issues\issue_74\confirmation_probe\extension -Destination .\.pytest_tmp\set_cookie_confirmation\extension -Recurse
& 'C:\Program Files\nodejs\node.exe' .\.pytest_tmp\set_cookie_confirmation\native_cookie_probe.cjs .\web\evidence\artifacts\browser_set_cookie_native_manual.json
uv run .\.pytest_tmp\set_cookie_confirmation\sdk_path_probe.py
```

原生探针需要本机已有 Node/Playwright 路径；源码中保留本次实际运行路径。
SDK 探针需要 build-test.py 启动的当前 dev 环境；报告文件固定为本轮 SDK 确认 JSON，复现前请另行备份原报告。
不安装扩展到用户配置、不控制用户鼠标/键盘；关闭独立浏览器后按已核对的绝对路径清理本次临时目录。
