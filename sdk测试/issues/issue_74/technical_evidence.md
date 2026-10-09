# WebBrowser.set_cookie：非当前 URL 匹配 Path 已写入，却返回 cookie_set_failed

状态：本地完整技术证据；已提交 [desktop Issue #74](https://github.com/uiautoma/desktop/issues/74)，远端正文精简，未披露本地路径、原始产物和具体源码定位。

## 环境与复现

- 被测只读 worktree：`D:\code\desktop`。
- 源码快照 commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`。
- dev Runtime、Windows、Chrome 154.0.8037.95（网页 UA 缩减为 154.0.0.0）；测试日期按本对话为 2026-10-06。
- 当前网页：`https://baobaomi900901.github.io/xpath/#/cookie-test`，实际 Path 为 `/xpath/`。
- 独立观察网页：`https://baobaomi900901.github.io/xpath/stop-load-test/slow.svg`。
- 所有标签通过 `silent_running=True` 创建；不操作鼠标、键盘或文件对话框。

运行测试侧唯一脚本：

```powershell
cd "D:\code\元素库\sdk测试"
uv run .\web\test_web_browser_set_cookie.py --report-file .\web\evidence\artifacts\browser_set_cookie_manual.json
```

其中 `other_path_write` 用例调用：

```python
page.set_cookie(
    name="本次随机唯一名称",
    value="other-path",
    path="/xpath/stop-load-test/",
    sessionCookie=True,
)
```

## 期望与实测

期望：合法的显式 Path 写入成功、返回 `None`；当前网页看不到它，匹配该 Path 的真实文档能读取正确值。

实际：抛 `ActionError: 浏览器操作失败，请重试`，`trace_info=cookie_set_failed`。
随后另一真实文档的原生 `cookieStore.getAll()` 已读到：

```json
{"domain":null,"expires":null,"partitioned":false,"path":"/xpath/stop-load-test/","sameSite":"lax","secure":false,"value":"other-path"}
```

该 Cookie 的 name 与本次请求的随机 name 相同；当前网页原生观察没有该名称。
这说明错误发生时已经产生写入副作用。调用方根据失败重试，可能误判写入状态。

最后连续三轮 run2/run3/run4 均为 **20/21 PASS + 1 FAIL，退出码 1**；唯一失败均为此项。
清理均为 PASS：本次 Cookie 原生确认删除、外部 Cookie 基线保留、标签数 3→3。
第一轮清理脚本曾错误使用 Cookie Store 删除默认 Path，修正后连续三轮清理 PASS；该测试侧问题与本产品缺陷分开记录。

## 源码快照定位与根因确认

以下位置均相对于上述 worktree/commit：

1. `sdk/src/uiautoma/web/browser.py:515`：公开 `set_cookie` 传递 `path`，成功返回 `None`。
2. `sdk/src/uiautoma/_core/client.py:1176`：RPC `web.cookie.set`，传入 `page_ref`。
3. `runtime/services/pipe_server.py:2212` → `runtime/services/action_service.py:3294` → `:5727`：校验后转发 `cookie_set`。
4. `chrome/engine/plugin_packages/browser_command_package.js:1785`：live page 分支把 `cmd.url` 设为当前标签 URL。
5. 同文件 `:1813` 的 `await chrome.cookies.set(details)` 与 `:1814`：返回值为空便返回 `cookie_set_failed`。

初轮结合“已写入但返回该 trace”的原生证据推断此分支；现在已追加直接原生确认：

| 场景 | 原生 set 返回 | 实际 Cookie | 当前 SDK 返回 |
|---|---|---|---|
| 当前 URL 与显式 Path 匹配 | Cookie 对象 | 已写入 | None |
| 当前 URL 不匹配另一显式 Path | undefined，无 lastError/Promise rejection | 已写入 | ActionError / cookie_set_failed |
| 换成匹配另一 Path 的 URL，其他 Cookie 参数相同 | Cookie 对象 | 已写入 | None |

原生组用同一 Chrome 154.0.8037.95 可执行文件，在独立无窗口配置中直接调用 Chrome API，
未加载 UIAutoma 包与靶场代码。三轮 callback/Promise 对照共 18 项符合预期；每项独立 CDP 确认写入。
SDK 组三对仅改变 WebBrowser 网页绑定，包含一次反转调用顺序，均复现表中差异。
原生组删除 18 个本次 Cookie 并关闭独立浏览器；SDK 组清理 PASS、标签 3→3。

根因是 UIAutoma 把原生成功的 undefined 返回直接当成失败。
Chrome [官方合同](https://developer.chrome.com/docs/extensions/reference/api/cookies#method-set) 允许 undefined；
[Chromium 实现](https://raw.githubusercontent.com/chromium/chromium/main/extensions/browser/api/cookies/cookies_api.cc)
在写入后按传入 URL 查询返回项，写入成功但该 URL 没匹配项时返回 NoArguments。
外部源码为查阅时 main；同版本 Chrome 的实际空返回已由探针确认，不依赖推测 release 与 main 完全一致。

测试侧未修改产品实现，也未把异常吞掉或改为通过。产品侧应尊重原生 Promise 的成功/失败结果，
避免单用空返回判写入失败；如需额外校验，应按 name/domain/path/store 精确核对，并保留真正拒绝/异常的错误处理。

## 材料

- [完整测试证据](../../web/evidence/browser_set_cookie.md)
- [冻结合同与链路](../../web/browser_cookie_contracts_20261006.json)
- [run2 完整 JSON](../../web/evidence/artifacts/browser_set_cookie_20261006_run2.json)
- [run3 完整 JSON](../../web/evidence/artifacts/browser_set_cookie_20261006_run3.json)
- [run4 完整 JSON](../../web/evidence/artifacts/browser_set_cookie_20261006_run4.json)
- [18 项原生确认 JSON](../../web/evidence/artifacts/browser_set_cookie_native_confirmation_20261006.json)
- [三对 SDK URL 确认 JSON](../../web/evidence/artifacts/browser_set_cookie_sdk_path_confirmation_20261006.json)
- [归档探针与复现步骤](confirmation_probe/README.md)

修复验收建议：当前网页 Path 与显式 Cookie Path 匹配/不匹配两种情况均成功返回；另一真实文档原生确认写入；每轮精确 Path 清理仍 PASS。
