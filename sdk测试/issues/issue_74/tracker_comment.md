补充第九批 Cookie 组独立验收结果：已确认 `WebBrowser.set_cookie()` 在当前 URL 不匹配显式 Cookie Path 时，实际写入成功却抛 `ActionError` / `cookie_set_failed`。

按本总单“具体缺陷单独建 Issue 并关联”的约定，新建缺陷单 #74。该单包含复现参数、三轮各 20/21 PASS + 1 FAIL 的结果，以及同版本 Chrome 18 项原生对照和三对 SDK URL 绑定对照；三轮正式测试清理均 PASS。当前状态仍为 `READY_FOR_LIVE`，等待产品修复后独立复验。
