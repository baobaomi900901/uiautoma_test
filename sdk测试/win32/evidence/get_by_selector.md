# `uiautoma.win32.get_by_selector()` 验证证据

```yaml
api: "uiautoma.win32.get_by_selector"
lifecycle: "VERIFIED"
verification_date: "2026-09-03"
verification_summary:
  api_contract: "PASS"
  runtime_preflight: "PASS"
  package_open: "PASS"
  get_selector_string_default_timeout: "PASS"
  get_selector_object: "PASS"
  get_selector_mapping_name: "PASS"
  get_selector_mapping_id: "PASS"
  get_selector_mapping_process: "PASS"
  get_selector_mapping_contains: "PASS"
  get_selector_default_none: "PASS"
  get_timeout_zero: "PASS"
  get_missing_element: "PASS"
  get_invalid_selector_type: "PASS"
  get_invalid_timeout: "PASS"
  cleanup: "PASS"
  passed: 15
  total: 15
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.get_by_selector 的最小 SDK→Package 元素过滤→窗口绑定路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["get_by_selector", "_window_for_items", "_native_window_for_items"]
      fingerprint: "74d663274e634604e87b96ece9d6c90d274db35d"
    - path: "sdk/src/uiautoma/_compat.py"
      symbols: ["selector_parts", "filter_elements", "retry_until"]
      fingerprint: "dc4c567c63322c75701b0671226bb157c340313c"
    - path: "sdk/src/uiautoma/package.py"
      symbols: ["selector", "_selector_from_session"]
      fingerprint: "fb4e05e2e895befb26f8f756fbaa5def1025c32c"
    - path: "sdk/src/uiautoma/selector.py"
      symbols: ["Selector"]
      fingerprint: "0ba5ce5a9bc2e9c3635b14ee39687d2899eb2270"
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window", "Win32Window.get_detail"]
      fingerprint: "88c1f4821db340c4fc00268bc4a89e88524b9a6c"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["get_by_handle", "list_windows"]
      fingerprint: "413554db0b49f571dc0672f50a6e04f74be4a8da"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["get_by_handle", "list_windows"]
      fingerprint: "c425101cb7ca55df3f5b54f319f693a5f6cdd3e1"
  verified_contract:
    signature: "get_by_selector(selector=None, *, timeout=5) -> Win32Window"
    parameter_order:
      - "selector"
      - "timeout"
    defaults:
      selector: null
      timeout: 5
    return_annotation: "Win32Window"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "win32/test_win32_get_by_selector.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "1e96f299fa0d661a42988639905ccc0d0a5ee958"
  command: 'uv run .\win32\test_win32_get_by_selector.py'
test_asset:
  library_dir: "D:/code/元素库/260902_win元素"
  element_name: "win32靶场输入框"
  element_id: "df849752-32d7-46a0-9bec-7bcd6d0d7d7d"
  actual_title: "Win32 靶场 - UIA"
  class_name: "XPathWin32ShootingRange"
  process_name: "win32-shooting-range-uia.exe"
  native_bound: true
source_commit_at_doc_time: "8a974056fdad67d73adb6dea7863a43ff048001e"
```

## 持久化脚本

脚本：`win32/test_win32_get_by_selector.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_by_selector.py
uv run .\win32\test_win32_get_by_selector.py --contract-only
uv run .\win32\test_win32_get_by_selector.py --no-color
uv run .\win32\test_win32_get_by_selector.py --json
```

默认模式输出带状态颜色的中文对齐表格。`--no-color` 保留友好摘要但关闭颜色；
`--json` 只输出机器可读 JSON，不包含 ANSI 控制字符。

## API 角色划分

- 场景准备：打开 `D:\code\元素库\260902_win元素`；靶场窗口保持运行。
- 目标 API：`win32.get_by_selector(selector, *, timeout=5)`。
- selector 类型：默认 `None`、元素名称字符串、`package.Selector` 和字段过滤 Mapping。
- 验收：返回 `Win32Window`，包含目标元素库项，并绑定标题、类名、进程名一致的
  真实靶场窗口及有效句柄。
- 负例：不存在元素、不支持的 selector 类型和非法超时返回约定异常。
- 清理：关闭本次打开的 Package，不关闭、激活或修改靶场窗口。

## 最小实现链

```text
uiautoma.win32.get_by_selector
  -> filter_elements(get_package().win_elements(), selector)
  -> selector_parts（None / str / Selector / Mapping）
  -> _window_for_items
       -> _native_window_for_items（句柄 / 标题·类名·进程 尽力绑定）
  -> Win32Window(items, ..., _native=...)
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `selector`、keyword-only `timeout`、默认值和返回注解 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| Package 打开 | `PASS` | 打开 `260902_win元素` |
| 字符串及默认超时 | `PASS` | `"win32靶场输入框"`，省略 `timeout`，返回所属窗口 |
| `Selector` 对象 | `PASS` | 元素名称与 ID 唯一解析，返回所属窗口 |
| 名称 Mapping | `PASS` | `{"name": "win32靶场输入框"}` |
| ID Mapping | `PASS` | `{"id": "df849752-..."}` |
| 进程名 Mapping | `PASS` | `{"process_name": "win32-shooting-range-uia.exe"}` |
| 包含匹配 Mapping | `PASS` | `{"process_name_contains": "shooting-range"}` |
| 默认 `None` | `PASS` | 当前唯一 Win32 库元素返回靶场窗口 |
| 零超时 | `PASS` | ID Mapping 配合 `timeout=0` 单次查询成功 |
| 不存在元素 | `PASS` | `timeout=0` 抛出 `ElementNotFoundError` |
| 非法 selector 类型 | `PASS` | `list` 输入抛出 `InvalidParamsError` |
| 非法超时 | `PASS` | `timeout=-2` 抛出 `InvalidParamsError` |
| 资源清理 | `PASS` | 本次打开的 Package 已关闭，靶场窗口未关闭 |

## 最近一次真实验证

- 日期：2026-09-03
- 命令：`uv run .\win32\test_win32_get_by_selector.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 元素：`win32靶场输入框`
- 窗口：`Win32 靶场 - UIA` / `XPathWin32ShootingRange` /
  `win32-shooting-range-uia.exe`
- 原生窗口绑定：成功
- 总状态：`PASS`
- 通过数：`15/15`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 实现差异记录

源码注释列出 selector 多项命中时可能抛出 `AmbiguousElementError`；当前
`get_by_selector()` 直接实现会聚合 `filter_elements()` 返回的全部匹配项。此次元素库
只有一个 Win32 元素，未验证多项命中行为，也未将其记录为已验证合同。

## 明确排除

- `timeout=-1` 无限等待：避免元素不存在时测试脚本永久挂起。
- 多项命中矩阵：当前元素库只有一个 Win32 元素。
- 关闭、激活或修改靶场窗口。
