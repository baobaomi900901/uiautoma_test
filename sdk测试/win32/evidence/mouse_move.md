# `uiautoma.win32.mouse_move()` 验证证据

```yaml
api: "uiautoma.win32.mouse_move"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  screen_slow_delay_1: "PASS"
  screen_instant_delay_0: "PASS"
  screen_fast_delay_0: "PASS"
  screen_middle_delay_0: "PASS"
  position_instant_delay_0: "PASS"
  window_instant_delay_0: "PASS"
  cleanup: "PASS"
  passed: 6
  total: 6
  elapsed_ms: 1887.3
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.mouse_move 的最小 SDK→坐标解析→Runtime mouse.move 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["mouse_move", "_resolve_mouse_point", "_active_window_origin", "_normalize_mouse_speed"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/win32/window.py"
      symbols: ["Win32Window.get_detail"]
      fingerprint: "aa04c0827b27171924e93118957f5b26e6a577a7"
    - path: "sdk/src/uiautoma/win32/_motion.py"
      symbols: ["default_speed", "speed_from_seconds"]
      fingerprint: "5131d0d264945b297636be763183436a02d893ac"
  verified_contract:
    signature: "mouse_move(point_x, point_y, relative_to='screen', move_speed=None, delay_after=1) -> None"
    parameter_order:
      - "point_x"
      - "point_y"
      - "relative_to"
      - "move_speed"
      - "delay_after"
    defaults:
      relative_to: "screen"
      move_speed: null
      delay_after: 1
    return_annotation: "None"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_mouse_move.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "f0d9e84aaf5fd36c6290227c3e16378361332492"
  command: 'uv run .\win32\test_win32_mouse_move.py'
test_cases:
  - label: "屏幕慢速"
    call: 'win32.mouse_move(100, 100, "screen", "slow", 1)'
    status: "PASS"
  - label: "屏幕瞬移"
    call: 'win32.mouse_move(150, 100, "screen", "instant", 0)'
    status: "PASS"
  - label: "屏幕快速"
    call: 'win32.mouse_move(200, 100, "screen", "fast", 0)'
    status: "PASS"
  - label: "屏幕中速"
    call: 'win32.mouse_move(250, 100, "screen", "middle", 0)'
    status: "PASS"
  - label: "当前位置偏移"
    call: 'win32.mouse_move(20, 20, "position", "instant", 0)'
    status: "PASS"
  - label: "活动窗口偏移"
    call: 'win32.mouse_move(20, 20, "window", "instant", 0)'
    status: "PASS"
cleanup:
  status: "PASS"
  detail: "脚本不创建文件、进程、窗口或 Package；鼠标终点是本次动作的预期结果"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_mouse_move.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_mouse_move.py
```

脚本只调用 `win32.mouse_move()`，不调用其他 UIAutoma SDK API。每项分别打印调用、
状态和耗时；某项失败后仍继续运行剩余合法参数场景。

## API 参数

```python
win32.mouse_move(
    point_x: int,
    point_y: int,
    relative_to: str = "screen",
    move_speed: str | None = None,
    delay_after: float = 1,
) -> None
```

- `point_x`、`point_y`：屏幕坐标或相对偏移量。
- `relative_to`：本次验证 `screen`、`position`、`window`。
- `move_speed`：本次验证 `instant`、`fast`、`middle`、`slow`。
- `delay_after`：本次验证 `0` 和 `1` 秒。
- 成功调用均未抛异常并返回 `None`。

## 最小实现链

```text
uiautoma.win32.mouse_move
  -> _resolve_mouse_point(relative_to)
       screen: (x, y)
       position: get_mouse_position() + (x, y)
       window: _active_window_origin() + (x, y)
         -> get_active(timeout=0).get_detail("rect")
  -> _mouse_speed_from_manual(move_speed)
  -> get_client().mouse_move(..., relative_to="screen", move_speed=speed)
  -> sleep_after(delay_after)
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| `screen` + `slow` + 延时 1 秒 | `PASS` | 调用完成，返回 `None` |
| `screen` + `instant` + 无延时 | `PASS` | 调用完成，返回 `None` |
| `screen` + `fast` + 无延时 | `PASS` | 调用完成，返回 `None` |
| `screen` + `middle` + 无延时 | `PASS` | 调用完成，返回 `None` |
| `position` + `instant` | `PASS` | 相对当前位置调用完成，返回 `None` |
| `window` + `instant` | `PASS` | 相对当前活动窗口调用完成，返回 `None` |
| 资源清理 | `PASS` | 未创建需要关闭或删除的可拥有资源 |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_mouse_move.py`
- 总状态：`PASS`
- 通过数：`6/6`
- 总耗时：`1887.3ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 旧缺陷复验

旧版本在 `relative_to="window"` 时调用不存在的 `Win32Window.get_bounding()`，曾抛出
`AttributeError`。当前提交改为 `_active_window_origin()` 读取活动窗口的 `rect`，本次
`window` 场景调用成功；旧缺陷不再复现。

## 明确排除

- 非法参数与异常类型矩阵。
- `move_speed=None` 配合 `manual_motion_on/off()` 的全局偏好组合。
- `medium` 兼容别名。
- 对每次最终鼠标坐标进行独立 API 读回断言。
