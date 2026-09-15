# `WebBrowser.http_request()` 初次测试

## 用途

在被测网页的上下文里发送 HTTP 请求（引擎侧在页面的 ISOLATED 世界里用 `fetch` 执行）。

| 参数 | 默认 | 说明 |
|---|---|---|
| `url` | 必填 | 请求网址，**支持相对路径**（按当前页面 URL 解析） |
| `method` | `"GET"` | 请求方法；会被规范化为大写 |
| `headers` | `None` | 字符串字典 |
| `body` | `None` | 请求内容，**必须为字符串**（JSON 需先序列化） |
| `save_filename` | `None` | 响应内容保存路径；给了它就会把响应按二进制接收并落盘 |
| `connect_timeout` | `30` | 连接/等待响应头的超时，≥ 1 秒 |
| `download_timeout` | `300` | 读取响应体的超时，≥ 1 秒 |

返回 `dict`：`status_code`、`content_type`、`content_encoding`、`content`。
**不保存时 `content` 为 `str`；成功保存时为 `bytes`**；非 2xx 时 `content` 为空字符串且不落盘。

## 真实验收结果

**VERIFIED：42/42 通过，退出码 0**（**连续 3 次完整运行全绿**）。

靶场：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/`（同源、相对路径、非 2xx、HEAD、保存、gzip）
回显服务：`https://httpbin.org`（请求方法/请求头/请求体是否真的送达、超时语义、大文件与二进制）
被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

> **为什么需要外部回显服务**：靶场是 GitHub Pages 静态托管，没有服务端可回显请求，
> POST 静态文件只会得到 405。请求头/请求体「确实发出去了」这一核心语义必须有回显才能证实，
> 因此这几条走 `httpbin.org`；脚本会先探测它是否可达，不可达时相关用例如实记 `BLOCKED`（不误判为 FAIL）。
> 其余全部用官方靶场静态文件覆盖。

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`url` 位置参数，其余 6 个仅限关键字，返回注解 `dict` |
| 环境基线 | 通过，**本脚本不打开任何元素库**——`http_request` 只用 `page_ref`，无需 Package |
| 回显服务探测 | 通过，`httpbin.org` 可达（HTTP 200） |
| 独立参考下载 | 通过，用 `urllib` 独立下载 `delayed-element.html`（5289 字节）作对照 |
| **相对路径（前导斜杠）** | 通过，`/xpath/delayed-element.html` → 200、`text/html; charset=utf-8`，**内容与独立下载的文本逐字符一致** |
| **gzip 传输但内容已解码** | 通过，`content_encoding='gzip'` 而 `content` 是解码后的文本（4777 字符 ≠ 磁盘 5289 字节，含中文多字节） |
| **相对路径（无前导斜杠）** | 通过，`delayed-element.html` 命中同一文件 → 证明按页面 URL 解析 base |
| 绝对 URL | 通过，200 且内容非空 |
| **404 语义** | 通过，`status_code=404` 且 `content` 为**空字符串** |
| HEAD | 通过，200 且无响应体 |
| 对静态文件 POST | 通过，405（非 2xx）且无内容 |
| **POST 回显校验** | 通过，`data` 为原始请求体、`X-Probe: uiautomata-42` 与 `Content-Type: application/json` 均出现在服务端收到的请求头里 |
| PUT / PATCH / DELETE | 通过，方法送达且响应体回显正确 |
| 小写方法名 `get` | 通过，被规范化为大写并成功 |
| **GET 带 body** | 通过，`ActionError`（内含 JS 的 `Request with GET/HEAD method cannot have body`），0.007s |
| **跨源 Cookie 不外泄** | 通过，先设置靶场 Cookie，再跨源请求 → 回显 `cookies={}`（默认 `credentials: same-origin`） |
| **connect_timeout 约束到响应头** | 通过，`/delay/4` + `connect_timeout=1` → 1.03s 中止 |
| **download_timeout 只约束读体** | 通过，`/delay/2` 默认超时下 2.26s 成功（TTFB 不受 download_timeout 约束） |
| **download_timeout 约束读体** | 通过，`/drip?duration=5` + `download_timeout=1` → 1.27s 中止 |
| 分块响应在超时内读完 | 通过，`/drip?duration=2` + `download_timeout=6` → 200，50 字节完整 |
| 挂起地址被 connect_timeout 约束 | 通过，`10.255.255.1` + `connect_timeout=1` → 1.03s 中止（`download_timeout=5` 未生效） |
| **保存到嵌套新目录** | 通过，`content` 为 `bytes`（5289），落盘文件与**独立下载的字节完全一致** |
| **100000 字节二进制（跨分块）** | 通过，`content` 为 `bytes` 且长度 100000，落盘同长度且逐字节一致（覆盖 32768 分块路径） |
| 二进制不保存时的形态 | 通过，`content` 为 `str`（1885 字符 ≠ 2000 字节，**有损**）→ 想拿原始字节必须传 `save_filename` |
| 非 2xx 不落盘 | 通过，404 + `save_filename` → 文件未创建、`content` 为空字符串 |
| HEAD + `save_filename` | 通过，落盘 **0 字节**文件（如实记录该行为） |
| `save_filename` 指向已存在目录 | 通过，`InvalidParamsError`（"保存路径必须包含文件名"） |
| 参数校验（9 项） | 通过，全部 `InvalidParamsError` 且 0.0s：`url` 空/`None` → `missing url`；`method=''`、请求头值非字符串、`body` 非字符串、`connect_timeout=0/0.5`、`download_timeout=True`、`save_filename=''` |
| 页面关闭复核 | 通过，`web.get_all()` 证实无残留 |
| 页面关闭后调用 | 通过，`ActionError`（"网页对象已失效"，0.0s） |
| 资源清理 | 通过，删除本次临时目录（含 3 个落盘产物） |

## 独立确证方式

- **内容正确性**：用 `urllib` 独立下载同一 URL，与 `content` 逐字符/逐字节比对
  （文本用解码后文本比对，保存的文件用原始字节比对）——不依赖产品的自述。
- **请求确实送达**：用第三方回显服务读回服务端实际收到的 `data`、`X-Probe`、`Content-Type`、`url`。
- **超时确实生效**：既看异常形态，也断言耗时区间（如 `connect_timeout=1` 必须在 ~1s 内中止，
  而不是等满 `download_timeout`）。
- **大文件分块路径**：用 100000 字节响应跨越引擎的 32768 字节 base64 分块循环，
  并核对 `content` 长度、文件长度与二者逐字节一致。

## 关键语义（与源码逐条核对）

| 语义 | 依据 |
|---|---|
| 相对路径按当前页面 URL 解析 | 引擎用页面内 `fetch(url, ...)`，`url` 交给浏览器解析 |
| 默认 `credentials: 'same-origin'` | 引擎未传 `credentials`；实测跨源请求不带出靶场 Cookie |
| `connect_timeout` 约束到响应头 | 引擎在 `fetch` 前起 AbortController 计时，收到响应头后 `clearTimeout` |
| `download_timeout` 只约束读体 | 收到响应头后重新起计时，覆盖 `response.text()`/`arrayBuffer()` |
| 非 2xx 立即返回空内容、不落盘 | 引擎 `if (!response.ok) return result`；Runtime `save_response()` 再判一次 |
| `save_filename` 决定二进制路径 | 引擎据此把 `content` 换成 base64（32768 分块）并置 `content_base64`，SDK 解码为 `bytes` |
| 落盘为原子写 | `runtime/web/http_response.py:save_response()`：临时文件 + `os.replace`，自动建父目录 |
| 参数校验位置 | `validate_request()`（Runtime）；`url` 缺失更早被传输层拒绝，故消息为英文 `missing url` |

## 实测行为记录（非缺陷，但值得写进文档）

1. **`download_timeout` 不是总超时**：它只约束「收到响应头之后读响应体」的时间。
   响应头来得很慢（TTFB 大）时由 `connect_timeout` 兜底。文档措辞「读取响应内容的超时时间」
   与实测一致，但容易被理解成总超时，建议文档补一句显式说明。
2. **超时中止的异常文案有两种**：`AbortError: signal is aborted without reason` /
   `AbortError: The user aborted a request.`；挂起地址偶发先抛出 `TypeError: Failed to fetch`
   （网络层错误先于 abort）。三者都落到 `ActionError` + `trace=execute_javascript_failed`，
   语义关键在**耗时被超时参数约束住**。脚本对此同时接受两种形态并记录实际形态（首次运行曾因
   断言只认 `abort` 而误报一次 FAIL，已修正）。
3. **`GET` 带 body 的报错会带出 JS 栈文本**：消息形如
   `TypeError: Failed to execute 'fetch' on 'Window': Request with GET/HEAD method cannot have body.\n at eval (eval at <anonymous> …)`。
   规则本身正确（由浏览器的 fetch 强制），但公开 message 里混入 `eval`/`<anonymous>` 这类内部细节，
   建议 Runtime 侧收敛成可读文案。
4. **`HEAD` + `save_filename` 会创建 0 字节文件**：`response.ok` 为真 → 走二进制路径 →
   `arrayBuffer()` 为空 → 写出 0 字节文件。调用方需自行判断。
5. **二进制不保存即有损**：不传 `save_filename` 时引擎用 `response.text()` 解码，
   二进制内容会变成替换字符组成的字符串（2000 字节 → 1885 字符）。
6. **无需元素库**：本 API 只用 `page_ref`，本次全程未打开 Package 也能正常工作
   （与 `find` 系列不同，后者要求已打开元素库）。

## 复测

脚本：[test_web_browser_http_request.py](../test_web_browser_http_request.py)
原始产物：[artifacts/http_request_20260915.txt](artifacts/http_request_20260915.txt)（42/42，退出码 0）

```powershell
uv run .\web\test_web_browser_http_request.py
uv run .\web\test_web_browser_http_request.py --json
uv run .\web\test_web_browser_http_request.py --contract-only
```

脚本不写入工作区外的任何文件；落盘产物写在 `sdk测试/.pytest_tmp/<run_id>/saved/` 下，收尾整目录删除。
外网不可达时：`echo_service_probe` 记 `BLOCKED`，依赖它的 10 条用例一并 `BLOCKED`（退出码 2），
其余靶场相关用例照常执行。

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无非 FAIL 但存在 BLOCKED。

## 明确排除

- **HTTP 认证、代理、重定向跟随策略**：未构造（`fetch` 默认 `redirect: follow`，未验证跳转链）。
- **超大响应**：本次最大 100000 字节；未测更大量级与 Runtime 报文上限。
- **multipart / 文件上传下载**：`body` 只接受字符串，未覆盖表单文件上传。
- **HTTP/2、缓存与 `Cache-Control` 语义**：未覆盖。
- **跨源 Cookie（`credentials: include`）与自定义 Cookie 头**：产品未暴露该开关，未测。
- **同源请求是否携带 Cookie**：静态站无法回显，只确认请求成功（同源默认会带，但未实证）。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- 与 `start_monitor_network()` 的交互（该 API 发出的请求是否被网络监听记录）：未覆盖。
