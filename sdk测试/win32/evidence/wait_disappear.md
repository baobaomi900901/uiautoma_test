# `uiautoma.win32.Win32Window.wait_disappear()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.wait_disappear"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_window: "PASS"
  string_present_zero: "PASS"
  selector_present_zero: "PASS"
  element_present_zero: "PASS"
  missing_default: "PASS"
  present_finite: "PASS"
  missing_infinite: "PASS"
  missing_zero: "PASS"
  invalid_selector: "PASS"
  wrong_framework: "PASS"
  invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 14
  total: 14
  elapsed_ms: 944.0
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.wait_disappear 的目标转换、窗口存活、轮询和超时路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.wait_disappear", "Win32Window._selector_from_element", "Win32Window.find_all"]
      fingerprint: "d7cf81028692e9f891770481ed7888c26e022397"
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
    signature: "wait_disappear(self, selector_or_element: str | Selector | Win32Element, timeout: float = 20) -> bool"
    public_parameters:
      - name: "selector_or_element"
        type: "str | Selector | Win32Element"
        kind: "positional-or-keyword"
        required: true
      - name: "timeout"
        type: "float"
        kind: "positional-or-keyword"
        default: 20
        zero: "single query"
        positive: "poll until absent or deadline"
        minus_one: "wait indefinitely"
        invalid: "less than -1 or non-numeric"
    disappeared_result: true
    timeout_while_present_result: false
    closed_window_result: true
    poll_interval_seconds: 0.2
    invalid_parameter_error: "InvalidParamsError"
    return_annotation: "bool"
persistent_script:
  path: "win32/test_win32_wait_disappear.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "2eedc66bae52a9a0f9f1ac411fe67aa847c86371628b2754ac5dd7fd1c71ba67"
  command: 'uv run .\win32\test_win32_wait_disappear.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 266094
  finite_present_timeout_seconds: 0.5
  target_element_present_during_test: true
observations:
  api_contract:
    status: "PASS"
    detail: "目标支持 str、Selector、Win32Element，timeout 默认 20，返回 bool"
    elapsed_ms: 0.1
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 7.3
  target_window:
    status: "PASS"
    handle: 266094
    elapsed_ms: 2.0
  string_present_zero:
    status: "PASS"
    call: 'window.wait_disappear("win32靶场输入框", timeout=0)'
    returned: false
    elapsed_ms: 182.7
  selector_present_zero:
    status: "PASS"
    call: "window.wait_disappear(selector, timeout=0)"
    returned: false
    elapsed_ms: 56.0
  element_present_zero:
    status: "PASS"
    preparation: "window.find_all(selector, timeout=2)[0]"
    call: "window.wait_disappear(element, timeout=0)"
    returned: false
    detail: "Win32Element 被转换为源 Selector，目标仍存在"
    elapsed_ms: 120.1
  missing_default:
    status: "PASS"
    call: 'window.wait_disappear("__uiautoma_wait_disappear_missing_element__")'
    returned: true
    elapsed_ms: 0.0
  present_finite:
    status: "PASS"
    call: 'window.wait_disappear("win32靶场输入框", 0.5)'
    returned: false
    elapsed_ms: 573.4
  missing_infinite:
    status: "PASS"
    call: 'window.wait_disappear("__uiautoma_wait_disappear_missing_element__", timeout=-1)'
    returned: true
    elapsed_ms: 0.0
  missing_zero:
    status: "PASS"
    call: 'window.wait_disappear("__uiautoma_wait_disappear_missing_element__", timeout=0)'
    returned: true
    elapsed_ms: 0.0
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
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 0.1
  borrowed_package_closed: true
  target_application_left_running: true
  target_application_modified: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_wait_disappear.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_wait_disappear.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取用户已经启动的
Win32 靶场窗口，以 `win32靶场输入框` 验证三种目标类型和全部安全超时规则。测试只读；
结束时关闭借用的 Package，并保持靶场运行。

## API 参数

```python
wait_disappear(
    selector_or_element: str | Selector | Win32Element,
    timeout: float = 20,
) -> bool
```

- `selector_or_element` 是必填的位置或关键字参数，支持元素名称字符串、Win32
  `Selector` 和带有源元素 ID 的 `Win32Element`。
- 传入 `Win32Element` 时，方法先读取它的 `source_element_id`，再构造 Win32
  `Selector` 重新查找。
- `timeout` 是位置或关键字参数，默认值为 `20` 秒。
- `timeout=0` 只检查一次；正数每隔约 `0.2s` 检查；`timeout=-1` 一直等待。
- 小于 `-1` 或非数字超时抛出 `InvalidParamsError`。
- 元素已经消失或所属窗口已关闭时返回 `True`；期限内始终存在则返回 `False`。

## 最小实现链

```text
Win32Window.wait_disappear(selector_or_element, timeout)
  -> timeout_seconds(timeout, 20)
  -> loop:
       所属窗口已关闭：return True
       参数是 Win32Element：_selector_from_element(element)
         -> 读取 source_element_id
         -> 构造 Selector(framework="win")
       find_all(selector, timeout=0)
       没有匹配项：return True
       timeout=0 或到达期限：return False
       sleep(0.2s)
```

每轮元素检查都固定使用 `find_all(..., timeout=0)`，外层循环负责整体等待时间。

## 覆盖矩阵

| 场景 | 调用 | 预期 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.wait_disappear)` | 三种目标类型、`timeout=20`、返回 `bool` | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | `PASS` |
| 靶场窗口 | `win32.get(...)` | 获取真实 Win32 靶场窗口 | `PASS` |
| 名称目标仍存在 | `wait_disappear(name, timeout=0)` | `False` | `PASS` |
| Selector 仍存在 | `wait_disappear(selector, timeout=0)` | `False` | `PASS` |
| Win32Element 仍存在 | `wait_disappear(element, timeout=0)` | 转换源 Selector 后返回 `False` | `PASS` |
| 默认超时已消失 | `wait_disappear(missing)` | 已不存在，立即返回 `True` | `PASS` |
| 有限等待仍存在 | `wait_disappear(name, 0.5)` | 超时后返回 `False` | `PASS` |
| 无限等待值 | `wait_disappear(missing, timeout=-1)` | 已不存在，立即返回 `True` | `PASS` |
| 零超时已消失 | `wait_disappear(missing, timeout=0)` | `True` | `PASS` |
| 非法目标类型 | 列表、整数 | 抛出 `InvalidParamsError` | `PASS` |
| 非 Win Selector | Web `Selector` | 抛出 `InvalidParamsError` | `PASS` |
| 非法超时 | `-2`、`"bad"` | 抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 关闭借用的 Package | 靶场保持运行且未修改 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_wait_disappear.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 测试窗口：`Win32 靶场 - UIA`
- 窗口句柄：`266094`
- 目标类型：名称字符串、Win32 `Selector`、`Win32Element`
- 超时值：默认 `20`、`0`、位置参数 `0.5`、已消失目标的 `-1`
- 总状态：`PASS`
- 通过数：`14/14`
- 总耗时：`944.0ms`
- Package：借用连接已关闭
- 靶场程序：保持运行且未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 元素在等待期间从存在变为消失；本轮靶场状态保持不变。
- 关闭所属窗口后返回 `True` 的真实场景；本轮没有关闭靶场。
- 对仍存在元素执行 `timeout=-1`；这会按合同永久等待。
- 没有 `source_element_id` 的人工构造 Runtime `Win32Element`。

