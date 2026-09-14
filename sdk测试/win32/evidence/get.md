# `uiautoma.win32.get()` 验证证据

```yaml
api: "uiautoma.win32.get"
lifecycle: "VERIFIED"
verification_date: "2026-09-03"
verification_summary:
  api_contract: "PASS"
  runtime_preflight: "PASS"
  get_title_defaults: "PASS"
  get_class_name: "PASS"
  get_process_name: "PASS"
  get_combined_filters: "PASS"
  get_wildcard_filters: "PASS"
  get_timeout_zero: "PASS"
  get_invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 10
  total: 10
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.get 的最小 SDK→runtime/native 窗口枚举路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["get"]
      fingerprint: "74d663274e634604e87b96ece9d6c90d274db35d"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["find_window", "list_windows"]
      fingerprint: "413554db0b49f571dc0672f50a6e04f74be4a8da"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["find_window", "list_windows", "match_text"]
      fingerprint: "c425101cb7ca55df3f5b54f319f693a5f6cdd3e1"
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window", "Win32Window.get_detail"]
      fingerprint: "88c1f4821db340c4fc00268bc4a89e88524b9a6c"
  verified_contract:
    signature: "get(title=None, class_name=None, use_wildcard=False, *, process_name=None, timeout=5) -> Win32Window"
    parameter_order:
      - "title"
      - "class_name"
      - "use_wildcard"
      - "process_name"
      - "timeout"
    defaults:
      title: null
      class_name: null
      use_wildcard: false
      process_name: null
      timeout: 5
    return_annotation: "Win32Window"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_get.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "467c463a55ac5c10ddf774b6b9158d1ae68e5824"
  command: "uv run .\\win32\\test_win32_get.py"
test_asset:
  title: "微信"
  class_name: "Qt51514QWindowIcon"
  process_name: "Weixin.exe"
source_commit_at_doc_time: "8a974056fdad67d73adb6dea7863a43ff048001e"
```

## 持久化脚本

脚本：`win32/test_win32_get.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get.py
uv run .\win32\test_win32_get.py --contract-only
uv run .\win32\test_win32_get.py --no-color
uv run .\win32\test_win32_get.py --json
```

默认模式输出带状态颜色的中文对齐表格。`--no-color` 保留友好摘要但关闭颜色；
`--json` 只输出机器可读 JSON，不包含 ANSI 控制字符。

## API 角色划分

- 场景准备：微信主窗口已运行；Runtime 与 Automation Pipe 可响应。
- 目标 API：调用
  `win32.get(title, class_name=None, use_wildcard=False, *, process_name=None, timeout=5)`。
- 验收：返回 `Win32Window`，且标题、类名、进程名和有效句柄均属于目标微信窗口。
- 清理：只读获取窗口，不创建、激活、关闭或修改微信窗口。
- Package：`get()` 不要求打开 Package；指定元素库
  `D:\code\元素库\260902_win元素` 当前为空，本轮不执行元素库绑定。

## 最小实现链

```text
uiautoma.win32.get
  -> runtime_window.find_window / native_window.find_window
  -> list_windows + match_text(fuzzy/wildcard)
  -> Win32Window(_native=...)
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、参数种类、返回注解及无多余参数 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 标题及默认参数 | `PASS` | `get("微信")` 返回目标微信窗口 |
| 类名过滤 | `PASS` | 仅以 `class_name="Qt51514QWindowIcon"` 返回目标微信窗口 |
| 进程名过滤 | `PASS` | 仅以 `process_name="Weixin.exe"` 返回目标微信窗口 |
| 全参数组合 | `PASS` | 标题、类名、`use_wildcard=False`、进程名和有限超时组合 |
| 通配符过滤 | `PASS` | 标题/类名使用 `*`，进程名使用 `?`，均返回目标微信窗口 |
| 零超时 | `PASS` | `timeout=0` 单次查询已打开微信 |
| 非法超时 | `PASS` | `timeout=-2` 抛出 `InvalidParamsError` |
| 资源清理 | `PASS` | 未创建或关闭任何窗口 |

## 最近一次真实验证

- 日期：2026-09-03
- 命令：`uv run .\win32\test_win32_get.py`
- 测试对象：`微信` / `Qt51514QWindowIcon` / `Weixin.exe`
- 总状态：`PASS`
- 通过数：`10/10`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- `timeout=-1` 无限等待：避免目标窗口关闭时测试脚本永久挂起。
- 元素库绑定：`get()` 不要求 Package，且指定元素库当前为空。
- 关闭、激活或修改微信窗口。
