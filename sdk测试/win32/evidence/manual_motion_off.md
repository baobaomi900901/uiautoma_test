# `uiautoma.win32.manual_motion_off()` 验证证据

```yaml
api: "uiautoma.win32.manual_motion_off"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  state_reset: "PASS"
  instant_move_restored: "PASS"
  final_cleanup: "PASS"
  desktop_readonly_notice_absent_after_run: "PASS"
  paired_test_passed: 5
  paired_test_total: 5
  elapsed_ms: 1571.5
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.manual_motion_off 的状态复位与 mouse_move 默认速度恢复路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["manual_motion_off", "manual_motion_on", "mouse_move"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/win32/_motion.py"
      symbols: ["disable", "DEFAULTS", "STATE", "default_speed"]
      fingerprint: "5131d0d264945b297636be763183436a02d893ac"
  verified_contract:
    signature: "manual_motion_off() -> None"
    parameter_order: []
    reset_state:
      motion_move: false
      motion_click: false
      motion_delay: false
      min_time: 0.25
      max_time: 0.65
    return_annotation: "None"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_manual_motion.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "b5c8a7d159b5fecebde4503be7c072ed7fa9c8e0"
  command: 'uv run .\win32\test_win32_manual_motion.py'
paired_api: "uiautoma.win32.manual_motion_on"
observations:
  target: [2722, 772]
  actual: [2722, 772]
  instant_move_action_ms: 0.6
  desktop_readonly_notice_after_run: false
cleanup:
  manual_motion: "disabled"
  cursor: "restored"
  package_connection: "closed without closing Desktop shared Package"
  shooting_range: "left running"
  status: "PASS"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

与 [`manual_motion_on.md`](manual_motion_on.md) 共用 `win32/test_win32_manual_motion.py`。

```powershell
uv run .\win32\test_win32_manual_motion.py
```

脚本借用 UIAutoma 当前启用的 Package，不独占打开元素库；关闭脚本连接后 Desktop
继续保持元素库启用。

## API 参数

```python
win32.manual_motion_off() -> None
```

- 无参数。
- 返回 `None`。
- 将进程内人工轨迹状态恢复为 `motion_move=False`、`motion_click=False`、
  `motion_delay=False`、`min_time=0.25`、`max_time=0.65`。

## 最小实现链

```text
uiautoma.win32.manual_motion_off()
  -> _motion.disable()
  -> _motion.STATE.update(_motion.DEFAULTS)

后续 win32.mouse_move(..., move_speed=None)
  -> _motion.default_speed(action="move")
  -> motion_move=False
  -> instant
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 关闭返回值 | `PASS` | `manual_motion_off()` 返回 `None` |
| 状态复位 | `PASS` | 五项状态恢复为 `DEFAULTS` |
| 瞬移恢复 | `PASS` | 动作耗时 `0.6ms`，落点 `(2722, 772)` |
| 最终清理 | `PASS` | 再次关闭人工轨迹、恢复鼠标并关闭借用连接 |
| Desktop 状态 | `PASS` | 测试后未出现“当前元素库为只读”提示 |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_manual_motion.py`
- 关闭后状态：已恢复默认
- 关闭后移动：瞬移 `0.6ms`
- 目标及实际落点：`(2722, 772)`
- 配对脚本总状态：`PASS`
- 配对脚本通过数：`5/5`
- 配对脚本总耗时：`1571.5ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- Desktop 只读提示：未出现
- 产品源码修改：无

## 明确排除

见 [`manual_motion_on.md`](manual_motion_on.md)。
