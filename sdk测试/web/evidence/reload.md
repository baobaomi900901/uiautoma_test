# `WebBrowser.reload()` 初次测试

## 用途

刷新页面。刷新后本网页对象仍可使用；刷新前找到的元素必须重新查找后才能操作。

公开签名与同分支的后退/前进不同：`ignore_cache` 是**位置或关键字**参数，默认 `False`；
`load_timeout` 仅限关键字，默认 20 秒（`0` 不等待加载完成，`-1` 一直等待）；成功返回 `None`。

## 真实验收结果

**VERIFIED：12/12 通过，退出码 0。**

靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

被测基线：Desktop worktree `codex/stage6-sdk-runtime`，HEAD `dbe9e015`（2026-09-15）

| 测试项 | 结果 |
|---|---|
| API 合同 | 通过，`ignore_cache` 位置或关键字且默认 `False`，`load_timeout` 仅限关键字且默认 20，返回 `None` |
| 页面准备 | 通过，成功创建测试页面 |
| 初始状态 | 通过，初始 URL 可读、页面 id 非空、`timeOrigin` 探针可用 |
| 默认刷新 `reload()` | 通过，返回 `None`、URL 与页面 id 不变，且独立确证已重新加载（0.50s） |
| 位置参数 `reload(True)` | 通过，同上（3.07s） |
| 关键字 `reload(ignore_cache=False, load_timeout=20)` | 通过，同上（0.61s） |
| `reload(load_timeout=0)` | 通过，返回 `None`，由独立观测确认加载完成（0.38s） |
| 刷新后页面对象可用 | 通过，`get_url` / `get_title` / `get_html` 正常，页面 id 不变 |
| 非法超时 `-2` | 通过，`ValueError` 拒绝 |
| 非法超时类型 `"bad"` | 通过，`ValueError` 拒绝 |
| 未知关键字 | 通过，`TypeError` 拒绝 |
| 资源清理 | 通过，仅关闭本次创建的测试页面 |

## 重新加载的独立确证方式

本脚本不把「命令返回 `None`」当作刷新成功的证据，而是用两项独立观测确证文档确实被重建：

1. `performance.timeOrigin` 变化（文档级身份变化）；
2. 刷新前注入的 JS 标记在刷新后被清除（隔离世界上下文被重建）。

两个条件只要有一项成立即判定已重新加载。四次刷新实测值：

| 用例 | `timeOrigin` | 标记清除 | 耗时 |
|---|---|---|---|
| `reload_default` | `…630654.3` → `…631210.1` 变化 | 是 | 0.50s |
| `reload_positional_ignore_cache` | `…631210.1` → `…631754.9` 变化 | 是 | 3.07s |
| `reload_ignore_cache_keyword` | `…631754.9` → `…634880.2` 变化 | 是 | 0.61s |
| `zero_timeout` | `…634880.2` → `…635535.1` 变化 | 是 | 0.38s |

## 与 issue #58 的关系（对照结论）

`reload()` 与 `go_back()` / `go_forward()` 共用引擎里同一个命令分支
（`chrome/engine/plugin_packages/browser_command_package.js:1663-1671`），但它**不需要
导航历史前置**，本脚本也不调用后退/前进。

实测结果：四次刷新全部成功，未出现任何 `Cannot find a next page in history.` 类失败。

因此可以确认：**#58 只影响依赖浏览器历史项的后退/前进命令，不是该引擎分支的共性问题，
也不是 `waitForTabReady` 位置本身造成的**（`reload` 同样在该分支内、同样使用同一个
`waitForTabReady`）。这与 #58 中「导航历史项未被渲染进程提交」的判断方向一致。

## 复测

脚本：[test_web_browser_reload.py](../test_web_browser_reload.py)
原始产物：[artifacts/reload_20260915.txt](artifacts/reload_20260915.txt)

在 `sdk测试` 目录运行：

```powershell
uv run .\web\test_web_browser_reload.py
uv run .\web\test_web_browser_reload.py --json   # 归档 JSON 报告
uv run .\web\test_web_browser_reload.py --contract-only
```

退出码：`0` = 全部 PASS；`1` = 存在 FAIL；`2` = 无 FAIL 但存在 BLOCKED。

## 明确排除

- **`ignore_cache=True` 是否真的绕过 HTTP 缓存未验证**：本次只验证了参数被接受、命令成功、
  页面确实重新加载，未观测网络层或缓存命中证据。
- 刷新后「此前找到的元素必须重新查找」未验证：需要元素库与本地靶场，而本机
  `localhost:7199` 靶场当前不可达。
- Edge、CEF 与 Auto 模式（脚本 `--mode` 仅开放 `chrome`）。
- `load_timeout=-1`（无限等待）路径。
- 非活动标签页、跨文档页面与带 `beforeunload` 拦截的页面刷新。
