# `WebBrowser.execute_javascript()` 初次测试

## 用途

在当前网页上执行 JavaScript 脚本。

- `code`：必填，**必须是 JavaScript 函数字符串**；引擎把它当函数求值后以
  `fn(null, argument)` 调用，并 `await` 其返回值（因此支持 `async` / `Promise`）。
- `argument`：传给 JS 函数的第二个形参，支持字符串、数字、布尔、列表、字典，
  **无需先转 JSON**；默认 `None`，函数收到 `undefined`。
- `execution_world`：`"ISOLATED"`（隔离环境，默认）或 `"MAIN"`（网页环境）。
- 返回：JS 执行结果；`undefined` / `null` / 无返回值统一返回 `None`。

`code`、`argument`、`execution_world` 三者都是**位置或关键字**参数。

## 真实验收结果

**VERIFIED：16/16 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`code` 必填、`argument` 默认 `None`、`execution_world` 默认 `ISOLATED`、返回注解 `Any` |
| 页面准备 | 通过，成功创建测试页面 |
| 初始状态 | 通过，初始 URL 可读且页面 id 非空 |
| 返回值透传 | 通过，数字/字符串/布尔/列表/字典 五种均按原类型返回（5/5） |
| `None` 归一 | 通过，`null` / `undefined` / 无返回值 三种均返回 `None` |
| 异步等待 | 通过，`Promise.resolve(5)` 被 `await` 后返回 `5` |
| 参数传递 | 通过，数字/字符串/列表/字典/`None` 五种均正确传入（`None` 传为 `undefined`） |
| 第一个形参 | 通过，函数第一个形参收到 `null` |
| 双 world 变量隔离 | 通过，MAIN 与 ISOLATED 的 JS 变量互相不可见、各自可见（6/6） |
| 双 world DOM 共享 | 通过，MAIN 修改 `document.title` 后 `get_title()` 与 ISOLATED 读取结果一致 |
| 位置传参 | 通过，`code`、`argument`、`execution_world` 均可位置传入 |
| 非函数字符串 | 通过，`ActionError` 拒绝，trace `execute_javascript_failed` |
| 函数内抛错 | 通过，`ActionError` 拒绝，trace `execute_javascript_failed` |
| 非法 `execution_world` | 通过，`InvalidParamsError` 拒绝（SDK 侧即拒绝，不发起 Runtime 调用） |
| 空 `code` | 通过，`InvalidParamsError` 拒绝，trace `invalid_params` |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 双 world 语义（本次实测确认）

| 观测 | 结果 |
|---|---|
| MAIN 写 `window.__uia_world_main` | `'M'` |
| MAIN 自读 | `'M'` |
| ISOLATED 读该变量 | `'undefined'`（不可见） |
| ISOLATED 写 `window.__uia_world_iso` | `'I'` |
| ISOLATED 自读 | `'I'` |
| MAIN 读该变量 | `'undefined'`（不可见） |
| MAIN 改 `document.title` → `get_title()` | 一致（DOM 共享） |
| MAIN 改 `document.title` → ISOLATED 读 | 一致（DOM 共享） |

即：**JS 变量按 world 隔离，DOM 跨 world 共享**。

## 对其它验收证据的意义

本 API 此前已被多个脚本当作**场景准备原语**使用，它现在被独立验收，这些用法因此得到支撑：

| 早前用法 | 现在可确认 |
|---|---|
| `go_forward` 的 #58 预热（ISOLATED 探 `history.length`） | 探针合法且返回真实值，预热副作用成立 |
| `close` 的 `beforeunload` 处理器注入（MAIN world） | MAIN world 注入有效：变量与 DOM 行为均已确认 |
| `reload` / `is_load_completed` 的 `timeOrigin`、JS 标记探针 | 属合法文档级观测（ISOLATED 下 `performance` / `window` 读数可靠） |
| `is_load_completed` 的零等待刷新窗口判据 | 该判据建立在可信的原语之上 |

## 复测

脚本：[test_web_browser_execute_javascript.py](../test_web_browser_execute_javascript.py)
原始产物：[artifacts/execute_javascript_20260915.txt](artifacts/execute_javascript_20260915.txt)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_execute_javascript.py
uv run .\web\test_web_browser_execute_javascript.py --json   # 归档 JSON 报告
uv run .\web\test_web_browser_execute_javascript.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- `argument` 传入超出文档所述类型（如自定义对象、嵌套的深层结构、超大负载）的序列化行为。
- 脚本执行超时路径：内部固定 `timeout_ms=5000`，本次未构造超过 5 秒的脚本。
- `iframe` 子框架与跨域框架中的执行语义（本次均在主框架执行）。
- 页面导航/关闭过程中执行脚本的并发语义。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `WebElement.execute_javascript()`（元素级脚本执行）属另一公开 API，本次未覆盖。
