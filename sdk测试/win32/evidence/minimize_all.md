# `uiautoma.win32.minimize_all()` 验证证据

```yaml
api: "uiautoma.win32.minimize_all"
lifecycle: "VERIFIED"
verification_date: "2026-09-03"
verification_summary:
  api_contract: "PASS"
  runtime_preflight: "PASS"
  sample_setup: "PASS"
  minimize_all_effect: "PASS"
  minimize_all_toggle_restore: "PASS"
  cleanup: "PASS"
  passed: 6
  total: 6
  elapsed_ms: 1685.9
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.minimize_all 的最小 SDK→native Win+D 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["minimize_all"]
      fingerprint: "74d663274e634604e87b96ece9d6c90d274db35d"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["minimize_all"]
      fingerprint: "c425101cb7ca55df3f5b54f319f693a5f6cdd3e1"
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.set_state"]
      fingerprint: "88c1f4821db340c4fc00268bc4a89e88524b9a6c"
  verified_contract:
    signature: "minimize_all() -> None"
    parameter_order: []
    defaults: {}
    return_annotation: "None"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_minimize_all.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "7143286b2e8859bb41e31d65f6d2588b228cc952"
  command: 'uv run .\win32\test_win32_minimize_all.py'
test_asset:
  title: "微信"
  class_name: "Qt51514QWindowIcon"
  process_name: "Weixin.exe"
  after_first_call:
    return_is_none: true
    is_iconic: true
  after_second_call:
    return_is_none: true
    is_iconic: false
  cleanup_confirmed: true
source_commit_at_doc_time: "8a974056fdad67d73adb6dea7863a43ff048001e"
```

## 持久化脚本

脚本：`win32/test_win32_minimize_all.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_minimize_all.py
uv run .\win32\test_win32_minimize_all.py --contract-only
uv run .\win32\test_win32_minimize_all.py --no-color
uv run .\win32\test_win32_minimize_all.py --json
```

默认模式输出带状态颜色的中文对齐表格。`--no-color` 保留友好摘要但关闭颜色；
`--json` 只输出机器可读 JSON，不包含 ANSI 控制字符。

## API 角色划分

- 场景准备：使用标题 `微信`、类名 `Qt51514QWindowIcon` 和进程名 `Weixin.exe`
  定位微信窗口，并确保测试前未最小化。
- 目标 API：`win32.minimize_all()`，没有 API 参数，成功时返回 `None`。
- 第一次调用：等价于 Win+D，显示桌面并使微信窗口进入最小化状态。
- 第二次调用：再次触发 Win+D，验证微信窗口恢复。
- 观测：Win32 `IsIconic`，仅用于检查状态，不是公开 SDK API。
- 清理：确认微信已恢复；必要时使用 `set_state("restore")` 兜底，不关闭微信。

## 最小实现链

```text
uiautoma.win32.minimize_all
  -> native_window.minimize_all
  -> require_windows("win32.minimize_all")
  -> keybd_event(Win+D 按下与释放)
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 无参数，返回注解为 `None` |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 微信窗口准备 | `PASS` | 标题、类名、进程名及有效句柄匹配，调用前未最小化 |
| 第一次调用 | `PASS` | 返回 `None`，微信窗口 `IsIconic=True` |
| 第二次调用 | `PASS` | 返回 `None`，微信窗口切换恢复，`IsIconic=False` |
| 资源清理 | `PASS` | 微信窗口最终处于恢复状态 |

## 最近一次真实验证

- 日期：2026-09-03
- 命令：`uv run .\win32\test_win32_minimize_all.py`
- 测试对象：`微信` / `Qt51514QWindowIcon` / `Weixin.exe`
- 第一次调用：返回 `None`，微信窗口已最小化
- 第二次调用：返回 `None`，微信窗口已恢复
- 总状态：`PASS`
- 通过数：`6/6`
- 总耗时：`1685.9ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 安全与清理

`minimize_all()` 是 Win+D 切换而不是单向“只最小化”命令。测试期间不要手动触发
Win+D 或改变桌面显示状态；否则第二次调用的恢复方向可能被外部操作反转。无论测试调用
是否完整通过，脚本最后都会检查微信状态，并在必要时使用 `set_state("restore")` 恢复。

## 明确排除

- 微信以外的桌面窗口枚举与状态断言。
- 用户在两次 Win+D 调用之间主动切换桌面状态。
- 非 Windows 平台。
