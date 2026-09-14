# `uiautoma.win32.get_mouse_position()` 验证证据

```yaml
api: "uiautoma.win32.get_mouse_position"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  controlled_notepad_launch_and_focus: "PASS"
  screen_default: "PASS"
  screen_explicit: "PASS"
  window_relative: "PASS"
  cursor_restore: "PASS"
  notepad_cleanup: "PASS"
  temp_file_cleanup: "PASS"
  passed: 3
  total: 3
  elapsed_ms: 308.2
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.get_mouse_position 的最小 SDK→runtime/native 读标及窗口原点路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["get_mouse_position", "_active_window_origin"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/win32/runtime_window.py"
      symbols: ["get_mouse_position"]
      fingerprint: "d438a6b8c106805818a609d67a845f69524f11d0"
    - path: "sdk/src/uiautoma/win32/native_window.py"
      symbols: ["get_mouse_position"]
      fingerprint: "7b2f6a721d21a532bae3cfe72a0c47f1f989d457"
  verified_contract:
    signature: "get_mouse_position(relative_to='screen') -> tuple[int, int]"
    parameter_order:
      - "relative_to"
    defaults:
      relative_to: "screen"
    supported_relative_to:
      - "screen"
      - "window"
    return_annotation: "tuple[int, int]"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_get_mouse_position.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "afa7efbe4889df350f59c53bc182825e0ebb08bf"
  command: 'uv run .\win32\test_win32_get_mouse_position.py'
test_asset:
  target: "script-launched notepad.exe"
  window_origin: [90, 252]
  screen_point: [780, 792]
  expected_window_point: [690, 540]
  native_setup: "Win32 API activates the window, positions the cursor, and computes expected coordinates"
cleanup:
  cursor: "restored by script"
  notepad_window: "closed by script"
  temporary_file: "deleted by script"
  status: "PASS"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_get_mouse_position.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_get_mouse_position.py
```

脚本自动打开并激活记事本，使用原生 Win32 API 获取窗口矩形、将鼠标放到确定的屏幕
坐标并计算预期结果。测试过程只调用 UIAutoma SDK 的
`win32.get_mouse_position()`，不调用其他 UIAutoma SDK API。

## API 参数

```python
win32.get_mouse_position(
    relative_to: str = "screen",
) -> tuple[int, int]
```

- `relative_to="screen"`：返回相对于屏幕左上角的鼠标坐标。
- `relative_to="window"`：返回相对于当前活动窗口左上角的鼠标坐标。
- 不传参数时默认使用 `screen`。
- 三次调用均返回由两个整数构成的坐标元组。

## 最小实现链

```text
uiautoma.win32.get_mouse_position(relative_to)
  -> 校验 relative_to 为 screen 或 window
  -> runtime_window.get_mouse_position()
       Runtime 不可用时回退 native_window.get_mouse_position()
  -> screen: 直接返回屏幕坐标
  -> window: _active_window_origin()
       -> get_active(timeout=0).get_detail("rect")
       -> 屏幕坐标减去活动窗口左上角
```

## 覆盖矩阵

| 场景 | 调用 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| 默认屏幕坐标 | `win32.get_mouse_position()` | `(780, 792)` | `(780, 792)` | `PASS` |
| 显式屏幕坐标 | `win32.get_mouse_position("screen")` | `(780, 792)` | `(780, 792)` | `PASS` |
| 活动窗口坐标 | `win32.get_mouse_position("window")` | `(690, 540)` | `(690, 540)` | `PASS` |
| 资源清理 | — | 恢复鼠标并删除受控资源 | 鼠标已恢复，记事本已关闭，临时文件已删除 | `PASS` |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_get_mouse_position.py`
- 测试对象：脚本自动打开并激活的记事本
- 窗口原点：`(90, 252)`
- 屏幕坐标：`(780, 792)`
- 窗口相对坐标：`(690, 540)`
- 总状态：`PASS`
- 通过数：`3/3`
- 总耗时：`308.2ms`
- 鼠标位置：已恢复
- 记事本：已关闭
- 临时文件：已删除
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 与旧验证的差异

旧验证基于当时仅支持 `screen` 的实现，并记录 `currentactivatedwindow` 被拒绝。当前源码
已支持规范值 `window`；本次通过真实活动窗口对其相对坐标进行了精确复验。

## 明确排除

- 非法参数与异常类型矩阵。
- 多显示器负坐标场景。
- 大于当前容差的 DPI/窗口不可见边框差异矩阵。
