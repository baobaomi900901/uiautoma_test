# `uiautoma.win32.mouse_click()` 验证证据

```yaml
api: "uiautoma.win32.mouse_click"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  controlled_notepad_launch_and_focus: "PASS"
  default_left_click: "PASS"
  left_double_click: "PASS"
  middle_click: "PASS"
  ctrl_left_click: "PASS"
  right_click: "PASS"
  right_click_manual_observation: "PASS"
  temp_file_cleanup: "PASS"
  notepad_manual_cleanup: "PASS"
  passed: 5
  total: 5
  elapsed_ms: 2426.3
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.mouse_click 的最小 SDK→Runtime mouse.click 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["mouse_click", "_normalize_mouse_button", "_normalize_click_type", "_normalize_modifier_keys"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.mouse_click"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.mouse_click"]
      fingerprint: "13643d467dfd4ea60a47a1129f886253e5e06756"
  verified_contract:
    signature: "mouse_click(button='left', click_type='click', keys='none', delay_after=1) -> None"
    parameter_order:
      - "button"
      - "click_type"
      - "keys"
      - "delay_after"
    defaults:
      button: "left"
      click_type: "click"
      keys: "none"
      delay_after: 1
    canonical_buttons: ["left", "right", "middle"]
    canonical_click_types: ["click", "doubleClick"]
    return_annotation: "None"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_mouse_click.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "167e04392b8c0fe32b6e881cf83bf461a5879c8e"
  command: 'uv run .\win32\test_win32_mouse_click.py'
test_asset:
  target: "script-launched notepad.exe"
  native_setup: "Win32 API activates the window, computes a safe client point, and positions the cursor"
  observed_point: [780, 789]
  expected_visual_state: "the final right click leaves the Notepad context menu visible"
  manual_observation: "PASS"
cleanup:
  temporary_file: "deleted by script"
  notepad_window: "manually closed by tester"
  status: "PASS"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_mouse_click.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_mouse_click.py
```

脚本创建带测试文字的临时文件并打开记事本。窗口查找、激活、点击坐标计算、鼠标定位
和位置读回均使用原生 Win32 API；测试过程只调用 UIAutoma SDK 的
`win32.mouse_click()`，不调用其他 UIAutoma SDK API。

## API 参数

```python
win32.mouse_click(
    button: str = "left",
    click_type: str = "click",
    keys: str = "none",
    delay_after: float = 1,
) -> None
```

- `button`：本次验证 `left`、`middle`、`right` 三个规范值。
- `click_type`：本次验证 `click` 和 `doubleClick`。
- `keys`：本次验证 `none` 和 `ctrl`。
- `delay_after`：默认调用验证 1 秒等待，其余调用显式设为 0。
- 五次成功调用均未抛异常并返回 `None`。

## 最小实现链

```text
uiautoma.win32.mouse_click
  -> _normalize_mouse_button(button)
  -> _normalize_click_type(click_type)
  -> _normalize_modifier_keys(keys)
  -> UIAutomaCoreClient.mouse_click(...)
  -> Runtime ActionService.mouse_click
       -> 读取当前鼠标位置
       -> 按下修饰键（如有）
       -> 执行单击或双击
       -> 释放修饰键（如有）
  -> sleep_after(delay_after)
```

## 覆盖矩阵

| 场景 | 调用 | 结果 | 验收内容 |
| --- | --- | --- | --- |
| 默认左键单击 | `win32.mouse_click()` | `PASS` | 四个默认参数生效；返回 `None` |
| 左键双击 | `win32.mouse_click("left", "doubleClick", "none", 0)` | `PASS` | 双击完成；返回 `None` |
| 中键单击 | `win32.mouse_click("middle", "click", "none", 0)` | `PASS` | 中键单击完成；返回 `None` |
| Ctrl+左键 | `win32.mouse_click("left", "click", "ctrl", 0)` | `PASS` | 修饰键组合点击完成；返回 `None` |
| 右键单击 | `win32.mouse_click("right", "click", "none", 0)` | `PASS` | 返回 `None`，记事本显示右键菜单 |
| 临时文件清理 | — | `PASS` | 脚本删除本次创建的临时 `.txt` |
| 记事本清理 | — | `PASS` | 测试者人工确认后关闭记事本 |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_mouse_click.py`
- 测试对象：脚本自动打开并激活的记事本
- 点击位置：`(780, 789)`
- 人工观察：最后一次右键单击后，记事本显示右键菜单
- 总状态：`PASS`
- 通过数：`5/5`
- 总耗时：`2426.3ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 非法参数与异常类型矩阵。
- `primary`、`secondary` 等按钮兼容别名。
- `single`、`double`、`dbclick`、`dblclick` 等点击类型兼容别名。
- `shift`、`alt`、`win` 及多修饰键组合矩阵。
- 对记事本文本选择状态的程序化断言。
