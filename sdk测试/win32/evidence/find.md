# `uiautoma.win32.Win32Window.find()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.find"
lifecycle: "VERIFIED"
verification_date: "2026-09-05"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_window: "PASS"
  string_default: "PASS"
  selector_zero: "PASS"
  positive_timeout: "PASS"
  infinite_timeout: "PASS"
  missing_zero: "PASS"
  missing_finite: "PASS"
  invalid_selector: "PASS"
  wrong_framework: "PASS"
  invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 13
  total: 13
  elapsed_ms: 800.8
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.find 的选择器、超时、唯一性检查和重试路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.find", "Win32Window._find", "Win32Window._find_all_once"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/selector.py"
      symbols: ["Selector", "_require_element_selector"]
      fingerprint: "98de256ad75491a100f8fb57ef89e358a6d147f5"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["timeout_seconds", "retry_until"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/package.py"
      symbols: ["Package.selector"]
      fingerprint: "fb4e05e2e895befb26f8f756fbaa5def1025c32c"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "find(self, selector: str | Selector, *, timeout: float = 20) -> Win32Element"
    public_parameters:
      - name: "selector"
        type: "str | Selector"
        kind: "positional-or-keyword"
        required: true
      - name: "timeout"
        type: "float"
        kind: "keyword-only"
        default: 20
        zero: "single query"
        positive: "retry until unique match or deadline"
        minus_one: "wait indefinitely"
        invalid: "less than -1 or non-numeric"
    unique_match_result: "Win32Element"
    no_match_error: "ElementNotFoundError"
    multiple_match_error: "AmbiguousElementError"
    invalid_parameter_error: "InvalidParamsError"
    return_annotation: "Win32Element"
persistent_script:
  path: "win32/test_win32_find.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "d87c5c035f6465b61efe6b2deb76095e875144fc45d8ac0fb0ccab799122785e"
  command: 'uv run .\win32\test_win32_find.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 262944
  finite_missing_timeout_seconds: 0.5
  current_selector_cardinality: 1
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名为 find(selector: str | Selector, *, timeout=20)"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 7.2
  target_window:
    status: "PASS"
    handle: 262944
    elapsed_ms: 1.5
  string_default:
    status: "PASS"
    call: 'window.find("win32靶场输入框")'
    returned: "Win32Element"
    detail: "元素名称与默认 timeout=20 返回唯一 Runtime 元素"
    elapsed_ms: 74.6
  selector_zero:
    status: "PASS"
    call: "window.find(selector, timeout=0)"
    returned: "Win32Element"
    detail: "Selector 对象单次查询返回目标元素"
    elapsed_ms: 54.7
  positive_timeout:
    status: "PASS"
    call: 'window.find("win32靶场输入框", timeout=2)'
    returned: "Win32Element"
    elapsed_ms: 57.4
  infinite_timeout:
    status: "PASS"
    call: "window.find(selector, timeout=-1)"
    returned: "Win32Element"
    elapsed_ms: 57.8
  missing_zero:
    status: "PASS"
    call: 'window.find("__uiautoma_find_missing_element__", timeout=0)'
    error: "ElementNotFoundError"
    elapsed_ms: 0.6
  missing_finite:
    status: "PASS"
    call: 'window.find("__uiautoma_find_missing_element__", timeout=0.5)'
    error: "ElementNotFoundError"
    elapsed_ms: 501.1
  invalid_selector:
    status: "PASS"
    values: ["list", "int"]
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  wrong_framework:
    status: "PASS"
    value: "Selector(framework='web')"
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  invalid_timeout:
    status: "PASS"
    values: [-2, "bad"]
    expected_error: "InvalidParamsError"
    elapsed_ms: 1.3
cleanup:
  status: "PASS"
  elapsed_ms: 42.9
  borrowed_package_closed: true
  original_foreground_restored: true
  target_application_left_running: true
  target_application_modified: false
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_find.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_find.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取用户已经启动的
Win32 靶场窗口，并以 `win32靶场输入框` 验证名称字符串和 `Selector` 两种选择器。
测试只读；结束时关闭借用的 Package、恢复原前台窗口，并保持靶场运行。

## API 参数

```python
find(
    selector: str | Selector,
    *,
    timeout: float = 20,
) -> Win32Element
```

- `selector` 是必填的位置或关键字参数，支持元素名称字符串和 `Selector` 对象。
- `Selector` 必须指向 Win32 元素；其他类型或 Web `Selector` 抛出 `InvalidParamsError`。
- `timeout` 是仅限关键字参数，默认值为 `20` 秒。
- `timeout=0` 只查询一次；正数在期限内重试；`timeout=-1` 一直等待。
- 小于 `-1` 或非数字超时抛出 `InvalidParamsError`。
- 唯一命中时返回一个 `Win32Element`；未命中抛出 `ElementNotFoundError`。
- 命中多个实时元素时抛出 `AmbiguousElementError`。该分支已由源码和产品单元测试确认，
  但当前真实元素库不具备多项命中条件，因此不计入本次真实验收。

## 最小实现链

```text
Win32Window.find(selector, *, timeout)
  -> _require_element_selector(selector)
  -> Selector framework 必须为 win
  -> 尝试激活当前窗口
  -> retry_until(resolve, timeout, default_timeout=20)
     -> _find_all_with_cold_retry(..., max_results=2)
        -> 从当前 Package 读取并过滤 Win32 候选项
        -> element.find_all Runtime RPC
     -> 0 项：抛出 ElementNotFoundError，按 timeout 决定是否重试
     -> 1 项：返回 Win32Element
     -> 2 项：抛出 AmbiguousElementError
```

实现只读取最多两个匹配项，因为 `find()` 只需区分未找到、唯一命中和多项命中。

## 覆盖矩阵

| 场景 | 调用 | 预期 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.find)` | 必填 `selector`、仅限关键字 `timeout=20`、返回单个元素 | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | `PASS` |
| 靶场窗口 | `win32.get(...)` | 获取真实 Win32 靶场窗口 | `PASS` |
| 名称与默认超时 | `find("win32靶场输入框")` | 返回唯一 Runtime `Win32Element` | `PASS` |
| Selector 与零超时 | `find(selector, timeout=0)` | 单次查询返回目标元素 | `PASS` |
| 正数超时 | `find(..., timeout=2)` | 期限内返回目标元素 | `PASS` |
| 无限等待值 | `find(selector, timeout=-1)` | 已存在目标立即返回 | `PASS` |
| 零超时未找到 | `find(missing, timeout=0)` | 抛出 `ElementNotFoundError` | `PASS` |
| 有限等待未找到 | `find(missing, timeout=0.5)` | 约 `0.5s` 后抛出 `ElementNotFoundError` | `PASS` |
| 非法选择器类型 | 列表、整数 | 抛出 `InvalidParamsError` | `PASS` |
| 非 Win Selector | Web `Selector` | 抛出 `InvalidParamsError` | `PASS` |
| 非法超时 | `-2`、`"bad"` | 抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 关闭 Package、恢复焦点 | 靶场保持运行且未修改 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-05
- 命令：`uv run .\win32\test_win32_find.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 测试窗口：`Win32 靶场 - UIA`
- 窗口句柄：`262944`
- 选择器类型：名称字符串、Win32 `Selector`
- 超时值：默认 `20`、`0`、`2`、`-1`、未命中 `0.5`
- 总状态：`PASS`
- 通过数：`13/13`
- 总耗时：`800.8ms`
- Package：借用连接已关闭
- 前台窗口：已恢复
- 靶场程序：保持运行且未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- `AmbiguousElementError` 真实场景；当前 `win32靶场输入框` 只命中一个实时元素。
- 修改或复制元素库以制造重复、宽泛选择器。
- 在目标不存在时执行 `timeout=-1`；这会按合同永久等待。
- 对返回元素继续执行点击、输入等动作。

