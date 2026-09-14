# `uiautoma.win32.Win32Window.wait_appear()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.wait_appear"
lifecycle: "VERIFIED"
verification_date: "2026-09-05"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_window: "PASS"
  string_default: "PASS"
  selector_zero: "PASS"
  element_zero: "PASS"
  positional_timeout: "PASS"
  infinite_timeout: "PASS"
  missing_zero: "PASS"
  missing_finite: "PASS"
  invalid_selector: "PASS"
  wrong_framework: "PASS"
  invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 14
  total: 14
  elapsed_ms: 975.8
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.wait_appear 的目标转换、超时和元素查找路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.wait_appear", "Win32Window._selector_from_element", "Win32Window.find_all"]
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
    signature: "wait_appear(self, selector_or_element: str | Selector | Win32Element, timeout: float = 20) -> bool"
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
        positive: "poll until match or deadline"
        minus_one: "wait indefinitely"
        invalid: "less than -1 or non-numeric"
    appeared_result: true
    timeout_result: false
    invalid_parameter_error: "InvalidParamsError"
    return_annotation: "bool"
persistent_script:
  path: "win32/test_win32_wait_appear.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "18b24fd67ea9c0664c7b78bcd22e1bbcb7362b304e5f229c4c783e1b10e8f2f9"
  command: 'uv run .\win32\test_win32_wait_appear.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 262944
  finite_missing_timeout_seconds: 0.5
  element_present_before_wait: true
observations:
  api_contract:
    status: "PASS"
    detail: "目标支持 str、Selector、Win32Element，timeout 默认 20，返回 bool"
    elapsed_ms: 0.0
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 8.4
  target_window:
    status: "PASS"
    handle: 262944
    elapsed_ms: 1.6
  string_default:
    status: "PASS"
    call: 'window.wait_appear("win32靶场输入框")'
    returned: true
    elapsed_ms: 52.3
  selector_zero:
    status: "PASS"
    call: "window.wait_appear(selector, timeout=0)"
    returned: true
    elapsed_ms: 64.7
  element_zero:
    status: "PASS"
    preparation: "window.find_all(selector, timeout=2)[0]"
    call: "window.wait_appear(element, timeout=0)"
    returned: true
    detail: "Win32Element 被转换为源 Selector 后重新查找成功"
    elapsed_ms: 123.7
  positional_timeout:
    status: "PASS"
    call: 'window.wait_appear("win32靶场输入框", 2)'
    returned: true
    elapsed_ms: 58.6
  infinite_timeout:
    status: "PASS"
    call: "window.wait_appear(selector, timeout=-1)"
    returned: true
    elapsed_ms: 63.2
  missing_zero:
    status: "PASS"
    call: 'window.wait_appear("__uiautoma_wait_appear_missing_element__", timeout=0)'
    returned: false
    elapsed_ms: 0.0
  missing_finite:
    status: "PASS"
    call: 'window.wait_appear("__uiautoma_wait_appear_missing_element__", timeout=0.5)'
    returned: false
    elapsed_ms: 601.4
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
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_wait_appear.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_wait_appear.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取用户已经启动的
Win32 靶场窗口，以 `win32靶场输入框` 验证三种目标类型和全部超时规则。测试只读；
结束时关闭借用的 Package，并保持靶场运行。

## API 参数

```python
wait_appear(
    selector_or_element: str | Selector | Win32Element,
    timeout: float = 20,
) -> bool
```

- `selector_or_element` 是必填的位置或关键字参数，支持元素名称字符串、Win32
  `Selector` 和带有源元素 ID 的 `Win32Element`。
- 传入 `Win32Element` 时，方法先读取它的 `source_element_id`，再构造 Win32
  `Selector` 重新查找。
- `timeout` 是位置或关键字参数，默认值为 `20` 秒。
- `timeout=0` 只查询一次；正数在期限内轮询；`timeout=-1` 一直等待。
- 小于 `-1` 或非数字超时抛出 `InvalidParamsError`。
- 超时前找到至少一个匹配元素返回 `True`；超时仍未找到返回 `False`。

## 最小实现链

```text
Win32Window.wait_appear(selector_or_element, timeout)
  -> 参数是 Win32Element：_selector_from_element(element)
     -> 读取 source_element_id
     -> 构造 Selector(framework="win")
  -> Win32Window.find_all(selector, timeout=timeout)
     -> 校验 selector 类型和 framework
     -> timeout_seconds(timeout, 20)
     -> 查询/轮询当前 Package 的实时元素
     -> 返回 list[Win32Element]
  -> bool(matches)
```

因此该 API 只判断“是否至少出现一个匹配项”，不会要求选择器唯一命中。

## 覆盖矩阵

| 场景 | 调用 | 预期 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.wait_appear)` | 三种目标类型、`timeout=20`、返回 `bool` | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | `PASS` |
| 靶场窗口 | `win32.get(...)` | 获取真实 Win32 靶场窗口 | `PASS` |
| 名称与默认超时 | `wait_appear("win32靶场输入框")` | `True` | `PASS` |
| Selector 与零超时 | `wait_appear(selector, timeout=0)` | `True` | `PASS` |
| Win32Element 参数 | `wait_appear(element, timeout=0)` | 转换源 Selector 后返回 `True` | `PASS` |
| 位置超时参数 | `wait_appear(name, 2)` | `True` | `PASS` |
| 无限等待值 | `wait_appear(selector, timeout=-1)` | 已存在目标立即返回 `True` | `PASS` |
| 零超时未出现 | `wait_appear(missing, timeout=0)` | `False` | `PASS` |
| 有限等待未出现 | `wait_appear(missing, timeout=0.5)` | 超时后返回 `False` | `PASS` |
| 非法目标类型 | 列表、整数 | 抛出 `InvalidParamsError` | `PASS` |
| 非 Win Selector | Web `Selector` | 抛出 `InvalidParamsError` | `PASS` |
| 非法超时 | `-2`、`"bad"` | 抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 关闭借用的 Package | 靶场保持运行且未修改 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-05
- 命令：`uv run .\win32\test_win32_wait_appear.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 测试窗口：`Win32 靶场 - UIA`
- 窗口句柄：`262944`
- 目标类型：名称字符串、Win32 `Selector`、`Win32Element`
- 超时值：默认 `20`、`0`、位置参数 `2`、`-1`、未出现 `0.5`
- 总状态：`PASS`
- 通过数：`14/14`
- 总耗时：`975.8ms`
- Package：借用连接已关闭
- 靶场程序：保持运行且未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 元素在等待期间从不存在变为出现；本轮目标在调用前已经存在。
- 在目标不存在时执行 `timeout=-1`；这会按合同永久等待。
- 没有 `source_element_id` 的人工构造 Runtime `Win32Element`。
- 切换靶场页面、隐藏控件或修改元素库来制造动态场景。

