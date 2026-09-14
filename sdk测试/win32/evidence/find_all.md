# `uiautoma.win32.Win32Window.find_all()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.find_all"
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
  elapsed_ms: 1028.3
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.find_all 的选择器、超时、元素库候选项和实时查找路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.find_all", "Win32Window._find_all", "Win32Window._find_all_once"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/selector.py"
      symbols: ["Selector", "_require_element_selector"]
      fingerprint: "98de256ad75491a100f8fb57ef89e358a6d147f5"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["timeout_seconds"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/package.py"
      symbols: ["Package.selector"]
      fingerprint: "fb4e05e2e895befb26f8f756fbaa5def1025c32c"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "find_all(self, selector: str | Selector, *, timeout: float = 20) -> list[Win32Element]"
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
        positive: "poll until match or deadline"
        minus_one: "wait indefinitely"
        invalid: "less than -1 or non-numeric"
    no_match_result: "empty list"
    invalid_parameter_error: "InvalidParamsError"
    return_annotation: "list[Win32Element]"
persistent_script:
  path: "win32/test_win32_find_all.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "f29b488be72c8f24caf77c2bc57ef8e20631c1bde9996cc2e52452792180e2be"
  command: 'uv run .\win32\test_win32_find_all.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  finite_missing_timeout_seconds: 0.5
  current_selector_cardinality: 1
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名为 find_all(selector: str | Selector, *, timeout=20)"
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
  target_window:
    status: "PASS"
    detail: "已获取用户启动的 Win32 靶场窗口"
  string_default:
    status: "PASS"
    call: 'window.find_all("win32靶场输入框")'
    returned_count: 1
    detail: "元素名称与默认 timeout=20 返回 Runtime Win32Element 列表"
  selector_zero:
    status: "PASS"
    call: "window.find_all(selector, timeout=0)"
    returned_count: 1
    detail: "Selector 对象单次查询返回目标元素"
  positive_timeout:
    status: "PASS"
    call: 'window.find_all("win32靶场输入框", timeout=2)'
    returned_count: 1
    detail: "正数超时在期限内返回目标元素"
  infinite_timeout:
    status: "PASS"
    call: "window.find_all(selector, timeout=-1)"
    returned_count: 1
    detail: "对已存在元素使用无限等待值后正常返回"
  missing_zero:
    status: "PASS"
    call: 'window.find_all("__uiautoma_find_all_missing_element__", timeout=0)'
    returned: []
  missing_finite:
    status: "PASS"
    call: 'window.find_all("__uiautoma_find_all_missing_element__", timeout=0.5)'
    returned: []
  invalid_selector:
    status: "PASS"
    values: ["list", "int"]
    expected_error: "InvalidParamsError"
  wrong_framework:
    status: "PASS"
    value: "Selector(framework='web')"
    expected_error: "InvalidParamsError"
  invalid_timeout:
    status: "PASS"
    values: [-2, "bad"]
    expected_error: "InvalidParamsError"
cleanup:
  status: "PASS"
  borrowed_package_closed: true
  target_application_left_running: true
  target_application_modified: false
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_find_all.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_find_all.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取用户已经启动的
Win32 靶场窗口，并以 `win32靶场输入框` 验证名称字符串和 `Selector` 两种选择器。
测试只读，不关闭或修改靶场；结束时关闭借用的 Package 连接。

## API 参数

```python
find_all(
    selector: str | Selector,
    *,
    timeout: float = 20,
) -> list[Win32Element]
```

- `selector` 是必填的位置或关键字参数，支持元素名称字符串和 `Selector` 对象。
- `Selector` 必须指向 Win32 元素；其他类型或 Web `Selector` 抛出 `InvalidParamsError`。
- `timeout` 是仅限关键字参数，默认值为 `20` 秒。
- `timeout=0` 只查询一次；正数在期限内轮询；`timeout=-1` 一直等待。
- 小于 `-1` 或非数字超时抛出 `InvalidParamsError`。
- 找到元素时返回全部匹配项组成的 `list[Win32Element]`；超时未找到返回空列表。

## 最小实现链

```text
Win32Window.find_all(selector, *, timeout)
  -> _require_element_selector(selector)
  -> Selector framework 必须为 win
  -> timeout_seconds(timeout, 20)
  -> _find_all_with_cold_retry(..., max_results=0)
     -> _find_all_once(...)
        -> 从当前 Package 读取 Win32 候选项
        -> filter_elements(items, selector)
        -> element.find_all Runtime RPC
        -> 将每个实时结果包装为 Win32Element
  -> 有匹配项：返回完整列表
  -> 到达期限：返回 []
```

`max_results=0` 表示实现不限制返回数量。当前真实元素库的测试选择器只有一个抓取项，
因此本次验收确认的是列表合同和单项实时结果，不等同于多项命中验收。

## 覆盖矩阵

| 场景 | 调用 | 预期 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.find_all)` | 必填 `selector`、仅限关键字 `timeout=20`、返回列表 | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | `PASS` |
| 靶场窗口 | `win32.get(...)` | 获取真实 Win32 靶场窗口 | `PASS` |
| 名称与默认超时 | `find_all("win32靶场输入框")` | 返回 1 个 Runtime `Win32Element` | `PASS` |
| Selector 与零超时 | `find_all(selector, timeout=0)` | 单次查询返回目标元素 | `PASS` |
| 正数超时 | `find_all(..., timeout=2)` | 期限内返回目标元素 | `PASS` |
| 无限等待值 | `find_all(selector, timeout=-1)` | 已存在目标立即返回 | `PASS` |
| 零超时未命中 | `find_all(missing, timeout=0)` | 返回 `[]` | `PASS` |
| 有限等待未命中 | `find_all(missing, timeout=0.5)` | 超时后返回 `[]` | `PASS` |
| 非法选择器类型 | 列表、整数 | 抛出 `InvalidParamsError` | `PASS` |
| 非 Win Selector | Web `Selector` | 抛出 `InvalidParamsError` | `PASS` |
| 非法超时 | `-2`、`"bad"` | 抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 关闭借用的 Package | 靶场保持运行且未修改 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-05
- 命令：`uv run .\win32\test_win32_find_all.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 测试窗口：`Win32 靶场 - UIA`
- 选择器类型：名称字符串、Win32 `Selector`
- 超时值：默认 `20`、`0`、`2`、`-1`、未命中 `0.5`
- 总状态：`PASS`
- 通过数：`13/13`
- 总耗时：`1028.3ms`
- Package：借用连接已关闭
- 靶场程序：保持运行且未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 同一个已抓取选择器同时命中多个实时元素；当前 `win32靶场输入框` 只返回 1 项。
- 在目标不存在时执行 `timeout=-1`；这会按合同永久等待。
- 修改元素库以制造重复选择器或多项命中场景。
- 对返回元素继续执行点击、输入等动作。

