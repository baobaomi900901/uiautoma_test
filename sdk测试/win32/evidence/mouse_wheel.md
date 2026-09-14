# `uiautoma.win32.mouse_wheel()` 验证证据

```yaml
api: "uiautoma.win32.mouse_wheel"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  controlled_notepad_launch_and_focus: "PASS"
  default_down: "PASS"
  down_three_times: "PASS"
  up_two_times: "PASS"
  ctrl_wheel_up: "PASS"
  scroll_and_zoom_manual_observation: "PASS"
  cursor_restore: "PASS"
  temp_file_cleanup: "PASS"
  notepad_manual_cleanup: "PASS"
  passed: 4
  total: 4
  elapsed_ms: 3163.5
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.mouse_wheel 的最小 SDK→Runtime mouse.wheel 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["mouse_wheel", "_normalize_wheel_direction", "_normalize_modifier_keys"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.mouse_wheel"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.mouse_wheel"]
      fingerprint: "13643d467dfd4ea60a47a1129f886253e5e06756"
  verified_contract:
    signature: "mouse_wheel(wheel_direction='down', wheel_times=1, keys='none', delay_after=1) -> None"
    parameter_order:
      - "wheel_direction"
      - "wheel_times"
      - "keys"
      - "delay_after"
    defaults:
      wheel_direction: "down"
      wheel_times: 1
      keys: "none"
      delay_after: 1
    canonical_directions: ["down", "up"]
    return_annotation: "None"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_mouse_wheel.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "52f59b7ca045e0d949d7281a0faed29aa526b2c5"
  command: 'uv run .\win32\test_win32_mouse_wheel.py'
test_asset:
  target: "script-launched notepad.exe with 300 numbered lines"
  native_setup: "Win32 API activates the window, computes a safe client point, and positions the cursor"
  observed_point: [780, 789]
  expected_visual_state: "content scrolls down and up; the final Ctrl+wheel-up enlarges the text"
  manual_observation: "PASS"
cleanup:
  cursor: "restored by script"
  temporary_file: "deleted by script"
  notepad_window: "manually closed by tester"
  status: "PASS"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_mouse_wheel.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_mouse_wheel.py
```

脚本创建包含 300 行测试文字的临时文件并打开记事本。窗口查找、激活、滚动位置计算、
鼠标定位和鼠标位置恢复均使用原生 Win32 API；测试过程只调用 UIAutoma SDK 的
`win32.mouse_wheel()`，不调用其他 UIAutoma SDK API。

## API 参数

```python
win32.mouse_wheel(
    wheel_direction: str = "down",
    wheel_times: int = 1,
    keys: str = "none",
    delay_after: float = 1,
) -> None
```

- `wheel_direction`：本次验证 `down` 和 `up`。
- `wheel_times`：本次验证默认值 `1`、显式值 `2` 和 `3`。
- `keys`：本次验证 `none` 和 `ctrl`。
- `delay_after`：默认调用验证 1 秒等待，其余调用显式设为 0。
- 四次成功调用均未抛异常并返回 `None`。

## 最小实现链

```text
uiautoma.win32.mouse_wheel
  -> _normalize_wheel_direction(wheel_direction)
  -> int(wheel_times) 并校验大于 0
  -> _normalize_modifier_keys(keys)
  -> UIAutomaCoreClient.mouse_wheel(...)
  -> Runtime ActionService.mouse_wheel
       -> 将 up/down 转换为 +120/-120
       -> 按下修饰键（如有）
       -> 按 wheel_times 重复发送滚轮动作
       -> 释放修饰键（如有）
  -> sleep_after(delay_after)
```

## 覆盖矩阵

| 场景 | 调用 | 结果 | 验收内容 |
| --- | --- | --- | --- |
| 默认向下滚动 | `win32.mouse_wheel()` | `PASS` | 四个默认参数生效；返回 `None` |
| 向下滚动三次 | `win32.mouse_wheel("down", 3, "none", 0)` | `PASS` | 向下滚动完成；返回 `None` |
| 向上滚动两次 | `win32.mouse_wheel("up", 2, "none", 0)` | `PASS` | 向上滚动完成；返回 `None` |
| Ctrl+滚轮向上 | `win32.mouse_wheel("up", 1, "ctrl", 0)` | `PASS` | 组合键滚轮完成；返回 `None`，文字被放大 |
| 人工观察 | — | `PASS` | 内容先向下、再向上滚动，最后文字被放大 |
| 资源清理 | — | `PASS` | 鼠标位置已恢复，临时文件已删除，记事本由测试者关闭 |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_mouse_wheel.py`
- 测试对象：脚本自动打开并激活的长文本记事本
- 滚轮位置：`(780, 789)`
- 人工观察：内容先向下、再向上滚动，最后文字被放大
- 总状态：`PASS`
- 通过数：`4/4`
- 总耗时：`3163.5ms`
- 鼠标位置：已恢复
- 临时文件：已删除
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 非法参数与异常类型矩阵。
- `forward`、`backward` 方向兼容别名。
- `shift`、`alt`、`win` 及多修饰键组合矩阵。
- 滚动像素或内容位移的程序化量化断言。
