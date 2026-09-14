# `uiautoma.win32.exists()` 验证证据

```yaml
api: "uiautoma.win32.exists"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  controlled_notepad_created: "PASS"
  live_window_true: "PASS"
  closed_window_false: "PASS"
  notepad_cleanup: "PASS"
  temp_file_cleanup: "PASS"
  passed: 2
  total: 2
  elapsed_ms: 152.2
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.exists 的 Win32Window→native IsWindow 最小路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["exists"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window", "Win32Window.exists"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["NativeWindow", "exists"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
  verified_contract:
    signature: "exists(window) -> bool"
    parameter_order:
      - "window"
    required_parameters:
      - "window"
    accepted_types:
      - "Win32Window"
      - "Win32Element"
      - "RawWinElement"
    tested_type:
      - "Win32Window"
    return_annotation: "bool"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_exists.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "871410e894fb4ef48e966f6b1e26b48fdedfcacd"
  command: 'uv run .\win32\test_win32_exists.py'
test_asset:
  target: "script-launched notepad.exe"
  object_type: "Win32Window"
  handle: 1906836
  process_id: 209820
  launcher_process_id: 205412
  fixture_construction: "NativeWindow created from a Win32-enumerated handle and wrapped as Win32Window"
cleanup:
  notepad_window: "closed by script"
  temporary_file: "deleted by script"
  status: "PASS"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_exists.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_exists.py
```

脚本自动创建并打开一个临时记事本，通过原生 Win32 API 获得窗口句柄，并用该句柄
构造 `Win32Window` 测试对象。测试过程只调用 UIAutoma SDK 的 `win32.exists()`，
不调用 `win32.get()`、`win32.get_list()` 或其他 UIAutoma SDK API。

## API 参数

```python
win32.exists(
    window: object,
) -> bool
```

- `window` 是必填参数。
- 当前源码接受 `Win32Window`、`Win32Element` 和 `RawWinElement`。
- 本次使用真实句柄绑定的 `Win32Window` 验证存活和关闭状态。
- 存活时返回 `True`，关闭后对同一对象再次调用返回 `False`。

## 最小实现链

```text
uiautoma.win32.exists(Win32Window)
  -> Win32Window.exists()
  -> native_window.exists(_native)
  -> user32.IsWindow(handle)
  -> bool
```

源码中的另外两条分派路径为：

```text
uiautoma.win32.exists(Win32Element)
  -> Win32Element.exists(timeout=0)

uiautoma.win32.exists(RawWinElement)
  -> RawWinElement.exists(timeout=0)
```

## 覆盖矩阵

| 场景 | 调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| 关闭前存在 | `win32.exists(window)` | `True` | `True` | `PASS` |
| 关闭后不存在 | `win32.exists(window)` | `False` | `False` | `PASS` |
| 资源清理 | — | 关闭记事本并删除临时文件 | 均已完成 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_exists.py`
- 测试对象：脚本自动打开的记事本 `Win32Window`
- 窗口句柄：`1906836`
- 关闭前：`True`
- 关闭后：`False`
- 总状态：`PASS`
- 通过数：`2/2`
- 总耗时：`152.2ms`
- 记事本：已关闭
- 临时文件：已删除
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- `Win32Element` 和 `RawWinElement` 的元素库定位场景。
- 无原生句柄的纯元素库绑定 `Win32Window`。
- 非法参数与异常类型矩阵。
