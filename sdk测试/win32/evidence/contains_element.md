# `uiautoma.win32.Win32Window.contains_element()` 验证证据

```yaml
api: "uiautoma.win32.Win32Window.contains_element"
lifecycle: "VERIFIED"
verification_date: "2026-09-06"
verification_summary:
  source_contract: "PASS"
  current_package: "PASS"
  target_window: "PASS"
  string_present: "PASS"
  selector_present: "PASS"
  string_missing: "PASS"
  invalid_selector: "PASS"
  element_rejected: "PASS"
  wrong_framework: "PASS"
  extra_timeout: "PASS"
  cleanup: "PASS"
  passed: 11
  total: 11
  elapsed_ms: 308.4
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Window.contains_element 的选择器校验和单次元素查询路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.contains_element", "Win32Window.find_all"]
      fingerprint: "d7cf81028692e9f891770481ed7888c26e022397"
    - path: "sdk/src/uiautoma/selector.py"
      symbols: ["Selector", "_require_element_selector"]
      fingerprint: "98de256ad75491a100f8fb57ef89e358a6d147f5"
    - path: "sdk/src/uiautoma/package.py"
      symbols: ["Package.selector"]
      fingerprint: "fb4e05e2e895befb26f8f756fbaa5def1025c32c"
  verified_contract:
    owner: "uiautoma.win32.Win32Window"
    signature: "contains_element(self, selector: str | Selector) -> bool"
    public_parameters:
      - name: "selector"
        type: "str | Selector"
        kind: "positional-or-keyword"
        required: true
    query_timeout_seconds: 0
    present_result: true
    missing_result: false
    closed_window_result: false
    invalid_selector_error: "InvalidParamsError"
    extra_argument_error: "TypeError"
    return_annotation: "bool"
persistent_script:
  path: "win32/test_win32_contains_element.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "14fef721ee06810bf36aa7c524b1a31f7239d4d9aa976d22183444894ffc3a2d"
  command: 'uv run .\win32\test_win32_contains_element.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场输入框"
  target_application: "Win32 靶场 - UIA"
  target_process: "win32-shooting-range-uia.exe"
  target_class: "XPathWin32ShootingRange"
  target_handle: 266094
observations:
  api_contract:
    status: "PASS"
    detail: "公开签名只有必填 selector: str | Selector，并返回 bool"
    elapsed_ms: 0.1
  current_package:
    status: "PASS"
    detail: "当前启用元素库与测试库一致"
    elapsed_ms: 7.1
  target_window:
    status: "PASS"
    handle: 266094
    elapsed_ms: 1.8
  string_present:
    status: "PASS"
    call: 'window.contains_element("win32靶场输入框")'
    returned: true
    elapsed_ms: 177.2
  selector_present:
    status: "PASS"
    call: "window.contains_element(selector)"
    returned: true
    elapsed_ms: 60.4
  string_missing:
    status: "PASS"
    call: 'window.contains_element("__uiautoma_contains_element_missing__")'
    returned: false
    elapsed_ms: 0.0
  invalid_selector:
    status: "PASS"
    values: ["list", "int"]
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  element_rejected:
    status: "PASS"
    preparation: "window.find_all(selector, timeout=2)[0]"
    call: "window.contains_element(element)"
    value_type: "Win32Element"
    expected_error: "InvalidParamsError"
    elapsed_ms: 60.6
  wrong_framework:
    status: "PASS"
    value: "Selector(framework='web')"
    expected_error: "InvalidParamsError"
    elapsed_ms: 0.0
  extra_timeout:
    status: "PASS"
    calls:
      - 'window.contains_element("win32靶场输入框", 0)'
      - 'window.contains_element("win32靶场输入框", timeout=0)'
    expected_error: "TypeError"
    elapsed_ms: 0.0
cleanup:
  status: "PASS"
  elapsed_ms: 0.0
  borrowed_package_closed: true
  target_application_left_running: true
  target_application_modified: false
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_contains_element.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_contains_element.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，获取用户已经启动的
Win32 靶场窗口，以 `win32靶场输入框` 验证存在、不存在和非法选择器行为。测试只读；
结束时关闭借用的 Package，并保持靶场运行。

## API 参数

```python
contains_element(selector: str | Selector) -> bool
```

- `selector` 是唯一的必填位置或关键字参数。
- 支持元素名称字符串和 Win32 `Selector`，不支持 `Win32Element`。
- 找到至少一个匹配元素返回 `True`；没有匹配项返回 `False`。
- Web `Selector`、列表、整数或 `Win32Element` 抛出 `InvalidParamsError`。
- API 没有 `timeout` 参数；额外位置参数或 `timeout=` 关键字由 Python 抛出
  `TypeError`。
- 查询固定使用 `timeout=0`，只执行一次，不等待。

## 最小实现链

```text
Win32Window.contains_element(selector)
  -> Win32Window.find_all(selector, timeout=0)
     -> _require_element_selector(selector)
     -> Selector framework 必须为 win
     -> 单次查询当前 Package 的实时元素
     -> 窗口已关闭或没有匹配项：[]
  -> bool(matches)
```

因此该 API 适合即时存在性判断；需要等待状态变化时应使用 `wait_appear()` 或
`wait_disappear()`。

## 覆盖矩阵

| 场景 | 调用 | 预期 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Window.contains_element)` | 只有必填 `selector`，返回 `bool` | `PASS` |
| 当前元素库 | `uiautoma.current(...)` | 当前库为 `260902_win元素` | `PASS` |
| 靶场窗口 | `win32.get(...)` | 获取真实 Win32 靶场窗口 | `PASS` |
| 名称存在 | `contains_element("win32靶场输入框")` | `True` | `PASS` |
| Selector 存在 | `contains_element(selector)` | `True` | `PASS` |
| 名称不存在 | `contains_element(missing)` | `False` | `PASS` |
| 非法选择器类型 | 列表、整数 | 抛出 `InvalidParamsError` | `PASS` |
| Win32Element 被拒绝 | `contains_element(element)` | 抛出 `InvalidParamsError` | `PASS` |
| 非 Win Selector | Web `Selector` | 抛出 `InvalidParamsError` | `PASS` |
| 不支持 timeout | 额外位置参数、`timeout=0` | 抛出 `TypeError` | `PASS` |
| 资源清理 | 关闭借用的 Package | 靶场保持运行且未修改 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-06
- 命令：`uv run .\win32\test_win32_contains_element.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场输入框`
- 测试窗口：`Win32 靶场 - UIA`
- 窗口句柄：`266094`
- 合法选择器：名称字符串、Win32 `Selector`
- 非法值：列表、整数、`Win32Element`、Web `Selector`、额外超时参数
- 总状态：`PASS`
- 通过数：`11/11`
- 总耗时：`308.4ms`
- Package：借用连接已关闭
- 靶场程序：保持运行且未修改
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志
- 产品源码修改：无

## 明确排除

- 所属窗口关闭后返回 `False` 的真实场景；本轮没有关闭靶场。
- 等待元素出现或消失；该 API 固定为零超时单次查询。
- 对返回元素继续执行点击、输入等动作。

