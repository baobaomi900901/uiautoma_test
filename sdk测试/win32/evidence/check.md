# `uiautoma.win32.Win32Element.check()` 验证证据

```yaml
api: "uiautoma.win32.Win32Element.check"
lifecycle: "VERIFIED"
verification_date: "2026-09-07"
verification_summary:
  source_contract: "PASS"
  target_element: "PASS"
  default_check: "PASS"
  idempotent_check: "PASS"
  uncheck: "PASS"
  idempotent_uncheck: "PASS"
  toggle_on: "PASS"
  toggle_off: "PASS"
  normalized_modes: "PASS"
  delay_after: "PASS"
  invalid_mode: "PASS"
  invalid_delay: "PASS"
  cleanup: "PASS"
  passed: 16
  total: 16
  elapsed_ms: 7497.8
  full_log_provided: true
  tester_confirmed: true
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.Win32Element.check 的模式规范化、动作结果、状态模式和 Runtime 执行路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.check", "Win32Element._finish"]
      fingerprint: "bb2f43e03bbbf4b439df8832e1ecbfcdf79ed681"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["sleep_after"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WinElement.check", "Session._run_win_action"]
      fingerprint: "c3654931c53594f73d9106eb58fe5a9742065593"
    - path: "sdk/src/uiautoma/_core/models.py"
      symbols: ["ActionResult"]
      fingerprint: "d0d5b2c074943a825f1a9514ff333a62666acf10"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.check_element", "ActionService._run_win_pattern_action"]
      fingerprint: "a2c498ee69bd6d05a8055f358157da35c6f69b49"
    - path: "runtime/bridge/worker.py"
      symbols: ["handle_check_element", "_handle_check_element"]
      fingerprint: "40f5c291cd3a6df6e56f4e1d8f5967e56382d197"
  verified_contract:
    owner: "uiautoma.win32.Win32Element"
    signature: 'check(self, mode: str = "check", delay_after: float = 1) -> None'
    parameters_are_positional_or_keyword: true
    modes: ["check", "uncheck", "toggle"]
    mode_trimmed: true
    mode_case_insensitive: true
    default_delay_after_seconds: 1
    no_delay_values: [null, 0]
    return_value: null
    action_result_property: "last_result"
    state_result_fields: ["before_checked", "checked"]
    internal_action_timeout_seconds: 5
    invalid_parameter_error: "InvalidParamsError"
    action_error: "ActionError"
persistent_script:
  path: "win32/test_win32_check.py"
  fingerprint_kind: "SHA-256 of current file content"
  fingerprint: "ba7cc395c1b0764865875e88c423a8ff0cbe930627df70a00e116b76b85536e3"
  command: 'uv run .\win32\test_win32_check.py'
test_environment:
  package_dir: "D:\\code\\元素库\\260902_win元素"
  target_element: "win32靶场北京多选"
  target_control_type: "CheckBox"
  target_application: "Win32 靶场 - UIA"
  initial_checked: false
  state_observation: "ActionResult.before_checked + ActionResult.checked"
observations:
  api_contract:
    status: "PASS"
    detail: "mode 和 delay_after 均为位置或关键字参数，默认值及返回 None 符合合同"
    elapsed_ms: 0.0
  element_setup:
    status: "PASS"
    detail: "当前元素库正确，已获取北京复选框"
    elapsed_ms: 191.7
  default_check:
    status: "PASS"
    call: "element.check()"
    before_checked: false
    checked: true
    effective_mode: "check"
    effective_delay_after_seconds: 1
    elapsed_ms: 1517.3
  idempotent_check:
    status: "PASS"
    call: 'element.check("check", 0)'
    before_checked: true
    checked: true
    elapsed_ms: 6.4
  uncheck:
    status: "PASS"
    call: 'element.check("uncheck", 0)'
    before_checked: true
    checked: false
    elapsed_ms: 506.0
  idempotent_uncheck:
    status: "PASS"
    call: 'element.check("uncheck", 0)'
    before_checked: false
    checked: false
    elapsed_ms: 6.7
  toggle_on:
    status: "PASS"
    call: 'element.check("toggle", 0)'
    before_checked: false
    checked: true
    elapsed_ms: 507.2
  toggle_off:
    status: "PASS"
    call: 'element.check("toggle", 0)'
    before_checked: true
    checked: false
    elapsed_ms: 507.0
  normalized_check:
    status: "PASS"
    input: "  CHECK  "
    before_checked: false
    checked: true
    elapsed_ms: 506.8
  normalized_uncheck:
    status: "PASS"
    input: "  UnChEcK  "
    before_checked: true
    checked: false
    elapsed_ms: 506.6
  normalized_toggle:
    status: "PASS"
    input: "  ToGgLe  "
    before_checked: false
    checked: true
    elapsed_ms: 507.6
  delay_none:
    status: "PASS"
    call: 'element.check("uncheck", None)'
    before_checked: true
    checked: false
    elapsed_ms: 506.3
  delay_positive:
    status: "PASS"
    call: 'element.check("check", 0.2)'
    before_checked: false
    checked: true
    elapsed_ms: 706.7
  invalid_mode:
    status: "PASS"
    values: ["", "invalid", null, 123]
    expected_error: "InvalidParamsError"
    action_result_unchanged: true
    elapsed_ms: 0.0
  invalid_delay:
    status: "PASS"
    values: [-0.1, "bad"]
    expected_error: "InvalidParamsError"
    state_action_completed_before_error: true
    elapsed_ms: 1013.3
cleanup:
  status: "PASS"
  elapsed_ms: 506.9
  initial_checked_restored: false
  borrowed_package_closed: true
  target_application_left_running: true
source_commit_at_doc_time: "16c3fe649e325c7ade3de2e0c2354daa57226b88"
```

## 持久化脚本

脚本：`win32/test_win32_check.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_check.py
```

脚本借用 UIAutoma 当前启用的 `D:\code\元素库\260902_win元素`，使用
`win32靶场北京多选` 执行真实状态操作。每次调用通过 `ActionResult.before_checked` 和
`checked` 核对操作前后状态；结束时恢复复选框初始状态、关闭借用的 Package，并保持
靶场运行。

## API 参数

```python
check(
    mode: str = "check",
    delay_after: float = 1,
) -> None
```

- 两个参数都是位置或关键字参数；成功返回 `None`，动作详情保存在 `last_result`。
- `mode="check"` 设置选中，`"uncheck"` 设置未选中，`"toggle"` 切换状态。
- `mode` 会去除首尾空格并忽略大小写；空值或非法值抛出 `InvalidParamsError`。
- `delay_after` 默认等待 1 秒；`None` 或 `0` 不等待，非负数字按秒等待。
- 当前实现先执行状态操作并保存 `last_result`，再校验及执行动作后延时。因此负数或
  非数字延时会先完成真实状态操作，再抛出 `InvalidParamsError`。
- Runtime 的 `before_checked` 与 `checked` 分别表示操作前后状态。
- 公开 API 不提供 `timeout` 参数；底层状态操作固定使用 5 秒超时。

## 最小实现链

```text
Win32Element.check(mode, delay_after)
  -> RawWinElement.check(mode)
     -> 规范化 mode：strip + casefold
     -> 校验 check / uncheck / toggle
     -> Runtime action.check_element（内部 timeout=5s）
        -> ActionService._run_win_pattern_action(..., op="check")
        -> TogglePattern / SelectionItemPattern / Invoke / Click fallback
        -> 返回 before_checked、checked、strategy
  -> Win32Element._finish(result, delay_after)
     -> 保存 last_result
     -> 抛出动作错误（如有）
     -> 校验并执行动作后延时
```

## 覆盖矩阵

| 场景 | 主要输入 | 验收条件 | 结果 |
| --- | --- | --- | --- |
| API 合同 | `inspect.signature(Win32Element.check)` | 两个参数、默认值和返回标注一致 | `PASS` |
| 元素准备 | 当前 Package 与北京复选框 | 元素库一致且元素可定位 | `PASS` |
| 默认勾选 | `element.check()` | 未选中变为选中，默认约 1 秒延时 | `PASS` |
| 重复勾选 | `check("check", 0)` | 已选中保持选中 | `PASS` |
| 取消勾选 | `check("uncheck", 0)` | 已选中变为未选中 | `PASS` |
| 重复取消 | `check("uncheck", 0)` | 未选中保持未选中 | `PASS` |
| 切换为选中 | `check("toggle", 0)` | 未选中变为选中 | `PASS` |
| 切换为未选中 | `check("toggle", 0)` | 选中变为未选中 | `PASS` |
| 模式归一化 | 大小写混合并带首尾空格 | 三种模式均被正确归一化 | `PASS` |
| 无动作后延时 | `delay_after=None/0` | 不增加额外等待 | `PASS` |
| 正数动作后延时 | `delay_after=0.2` | 状态操作后等待约 0.2 秒 | `PASS` |
| 非法模式 | 空值、非法名称、`None`、整数 | 动作前抛出 `InvalidParamsError` | `PASS` |
| 非法延时 | `-0.1`、`"bad"` | 状态操作后抛出 `InvalidParamsError` | `PASS` |
| 资源清理 | 恢复本次测试状态 | 初始状态恢复、Package 关闭、靶场保持运行 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-07
- 命令：`uv run .\win32\test_win32_check.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 测试元素：`win32靶场北京多选`
- 控件类型：`CheckBox`
- 初始状态：未选中
- 默认调用：`1517.3ms`，设置为选中且默认动作后延时生效
- 三种模式：`check`、`uncheck`、`toggle` 全部通过
- 幂等行为：重复勾选和重复取消勾选均保持目标状态
- 模式归一化：大小写和首尾空格兼容通过
- 总状态：`PASS`
- 通过数：`16/16`
- 总耗时：`7497.8ms`
- 复选框状态：已恢复为未选中
- Package：借用连接已关闭
- 靶场程序：保持运行
- 退出码：`0`
- 生命周期：`VERIFIED`
- 验收来源：测试者完整运行日志及明确确认
- 产品源码修改：无

## 明确排除

- 单选按钮的取消选择语义；本轮只使用可独立选中和取消的复选框。
- 三态复选框的 `Indeterminate` 状态；测试目标只有选中和未选中两态。
- 在不支持选择模式的普通控件上验证 `ActionError`；本轮真实目标支持状态操作。
- 强制指定底层 5 秒动作超时；公开 `check()` 没有 `timeout` 参数。

