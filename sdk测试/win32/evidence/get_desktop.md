# `uiautoma.win32.get_desktop()` 验证证据

```yaml
api: "uiautoma.win32.get_desktop"
lifecycle: "VERIFIED"
verification_date: "2026-09-03"
verification_summary:
  api_contract: "PASS"
  runtime_preflight: "PASS"
  package_open: "PASS"
  desktop_with_package_default: "PASS"
  desktop_with_package_positional: "PASS"
  desktop_with_package_keyword: "PASS"
  desktop_no_package_positional: "PASS"
  desktop_no_package_keyword: "PASS"
  desktop_invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 10
  total: 10
  elapsed_ms: 9.9
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.get_desktop 的最小 SDK→Package 元素读取→Desktop 伪窗口路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["get_desktop", "_package_win_elements_or_empty"]
      fingerprint: "74d663274e634604e87b96ece9d6c90d274db35d"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["timeout_seconds"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window", "Win32Window.get_detail"]
      fingerprint: "88c1f4821db340c4fc00268bc4a89e88524b9a6c"
  verified_contract:
    signature: "get_desktop(timeout=5) -> Win32Window"
    parameter_order:
      - "timeout"
    parameter_kind:
      timeout: "POSITIONAL_OR_KEYWORD"
    defaults:
      timeout: 5
    return_annotation: "Win32Window"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_get_desktop.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "6af1d09133ba9ee4716da942a267325af8dbb392"
  command: 'uv run .\win32\test_win32_get_desktop.py'
test_asset:
  library_dir: "D:/code/元素库/260902_win元素"
  element_name: "win32靶场输入框"
  expected_title: "Desktop"
  with_package:
    contains_expected_element: true
    desktop_unverified: true
    native_bound: false
    handle: 0
  without_package:
    item_count: 0
    desktop_unverified: true
    native_bound: false
    handle: 0
source_commit_at_doc_time: "8a974056fdad67d73adb6dea7863a43ff048001e"
```

## 持久化脚本

脚本：`win32/test_win32_get_desktop.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_desktop.py
uv run .\win32\test_win32_get_desktop.py --contract-only
uv run .\win32\test_win32_get_desktop.py --no-color
uv run .\win32\test_win32_get_desktop.py --json
```

默认模式输出带状态颜色的中文对齐表格。`--no-color` 保留友好摘要但关闭颜色；
`--json` 只输出机器可读 JSON，不包含 ANSI 控制字符。

## API 角色划分

- 场景准备：打开 `D:\code\元素库\260902_win元素`，校验元素
  `win32靶场输入框`。
- 目标 API：`win32.get_desktop(timeout=5)`。
- `timeout`：支持位置或关键字传入；默认 `5`，`0` 只查一次，`-1` 一直等待，
  小于 `-1` 抛出 `InvalidParamsError`。
- 有 Package：返回的 Desktop 伪窗口包含当前元素库中的 Win32 元素。
- 无 Package：返回的 Desktop 伪窗口元素列表为空，不抛出未找到异常。
- 公共返回合同：`title == "Desktop"`、`raw.desktop_unverified == true`、
  不绑定原生窗口且句柄为 `0`。
- 清理：关闭本次打开的 Package，不关闭、激活或修改靶场窗口。

## 最小实现链

```text
uiautoma.win32.get_desktop
  -> timeout_seconds(timeout, 5)
  -> _package_win_elements_or_empty
       -> get_package().win_elements() / 无 Package 时返回 []
  -> Win32Window(items, title="Desktop", raw={"desktop_unverified": True})
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `timeout` 的顺序、参数类型、默认值和 `Win32Window` 返回注解 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| Package 打开 | `PASS` | 打开 `260902_win元素` |
| 有 Package，默认参数 | `PASS` | 省略 `timeout`，返回含 `win32靶场输入框` 的 Desktop 伪窗口 |
| 有 Package，位置参数 | `PASS` | 位置传入有限超时，返回含目标元素的 Desktop 伪窗口 |
| 有 Package，关键字参数 | `PASS` | 关键字传入有限超时，返回含目标元素的 Desktop 伪窗口 |
| 无 Package，位置参数 | `PASS` | `get_desktop(0)` 返回空 Desktop 伪窗口 |
| 无 Package，关键字参数 | `PASS` | `get_desktop(timeout=0)` 返回空 Desktop 伪窗口 |
| 非法超时 | `PASS` | `timeout=-2` 抛出 `InvalidParamsError` |
| 资源清理 | `PASS` | 本次打开的 Package 已关闭，靶场窗口未关闭 |

## 最近一次真实验证

- 日期：2026-09-03
- 命令：`uv run .\win32\test_win32_get_desktop.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 校验元素：`win32靶场输入框`
- 总状态：`PASS`
- 通过数：`10/10`
- 总耗时：`9.9ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 状态隔离说明

当前 Package 状态由 Runtime 共享，而不是仅属于启动测试的 Python 进程。脚本先打开并
验证自己拥有的 Package，随后将其关闭，再运行无 Package 用例，从而避免继承其他测试
留下的当前 Package，保证无库断言可重复。

## 明确排除

- `timeout=-1` 无限等待：避免元素库状态异常时脚本永久挂起。
- `desktop.find` 等其他 Win32 API。
- 真实桌面 HWND 绑定：本 API 按合同返回 Desktop 伪窗口。
