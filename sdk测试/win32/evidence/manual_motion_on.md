# `uiautoma.win32.manual_motion_on()` 验证证据

```yaml
api: "uiautoma.win32.manual_motion_on"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  current_package_borrowed: "PASS"
  default_parameters: "PASS"
  custom_parameters: "PASS"
  slow_move_effect: "PASS"
  random_click_effect: "PASS"
  paired_off_reset: "PASS"
  desktop_readonly_notice_absent_after_run: "PASS"
  motion_state_cleanup: "PASS"
  cursor_restore: "PASS"
  package_connection_cleanup: "PASS"
  passed: 5
  total: 5
  elapsed_ms: 1571.5
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.manual_motion_on/off 的进程内偏好、mouse_move 与元素 click 生效路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["manual_motion_on", "manual_motion_off", "mouse_move"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/win32/_motion.py"
      symbols: ["enable", "disable", "STATE", "DEFAULTS", "default_speed", "click_anchor"]
      fingerprint: "5131d0d264945b297636be763183436a02d893ac"
    - path: "sdk/src/uiautoma/win32/element.py"
      symbols: ["Win32Element.click"]
      fingerprint: "8f9d9a00fdf1f5a9c7ea0160186828bbaf094b32"
    - path: "sdk/src/uiautoma/__init__.py"
      symbols: ["current"]
      fingerprint: "4e3b52b1263b010558241439a93e33c576e9b099"
    - path: "sdk/src/uiautoma/package.py"
      symbols: ["Package.close"]
      fingerprint: "fb4e05e2e895befb26f8f756fbaa5def1025c32c"
  verified_contract:
    signature: "manual_motion_on(motion_move=True, motion_click=True, motion_delay=False, min_time=0.25, max_time=0.65) -> None"
    parameter_order:
      - "motion_move"
      - "motion_click"
      - "motion_delay"
      - "min_time"
      - "max_time"
    defaults:
      motion_move: true
      motion_click: true
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
paired_api: "uiautoma.win32.manual_motion_off"
test_asset:
  library_dir: "D:\\code\\元素库\\260902_win元素"
  package_mode: "borrowed from UIAutoma by uiautoma.current()"
  element: "win32靶场输入框"
  element_rect: [2507, 757, 430, 30]
  element_center: [2722, 772]
observations:
  slow_move_action_ms: 465.9
  slow_move_target: [2722, 772]
  slow_move_actual: [2722, 772]
  random_click_actual: [2739, 780]
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

脚本：`win32/test_win32_manual_motion.py`，与 `manual_motion_off()` 共用。

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_manual_motion.py
```

运行前需要在 UIAutoma 中打开 `D:\code\元素库\260902_win元素` 并点击一次
“使用当前元素库”。脚本通过 `uiautoma.current()` 借用 Desktop 已启用的共享 Package；
结束时关闭的只是测试脚本自己的连接，不会将 Desktop 元素库切换为只读。

## API 参数

```python
win32.manual_motion_on(
    motion_move: bool = True,
    motion_click: bool = True,
    motion_delay: bool = False,
    min_time: float = 0.25,
    max_time: float = 0.65,
) -> None
```

- `motion_move`：控制未显式指定速度的鼠标移动是否使用人工轨迹。
- `motion_click`：控制元素点击是否使用随机锚点并启用模拟鼠标动作。
- `motion_delay`：当前会保存配置，但暂不改变动作后的等待时间。
- `min_time`：非负秒数；小于 `0.35` 映射为 `fast`，`0.35～0.55` 映射为
  `middle`，大于等于 `0.55` 映射为 `slow`。
- `max_time`：必须大于等于 `min_time`；当前保存但不参与速度档位计算。
- 配置只影响当前 Python 进程。

## 最小实现链

```text
uiautoma.win32.manual_motion_on(...)
  -> _motion.enable(...)
  -> 校验 min_time / max_time
  -> 更新进程内 _motion.STATE

win32.mouse_move(..., move_speed=None)
  -> _motion.default_speed(action="move")
  -> 根据 motion_move / min_time 选择 instant/fast/middle/slow

Win32Element.click(..., move_mouse=None, anchor=None)
  -> _motion.default_bool(..., key="motion_move")
  -> _motion.click_anchor(None)
  -> motion_click=True 时使用 random 锚点
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 默认开启 | `PASS` | `manual_motion_on()` 返回 `None`，五个默认配置正确 |
| 自定义参数 | `PASS` | `False, False, True, 0.35, 0.70` 五项均写入状态 |
| 开启后慢速移动 | `PASS` | 移动到 `(2722, 772)`，动作耗时 `465.9ms` |
| 开启后随机点击 | `PASS` | 点击落点 `(2739, 780)` 位于目标元素矩形内 |
| 关闭后恢复瞬移 | `PASS` | 配置复位，动作耗时 `0.6ms`，落点正确 |
| 资源清理 | `PASS` | 人工轨迹关闭、鼠标恢复、借用连接关闭、靶场保持运行 |
| Desktop 状态 | `PASS` | 测试后未出现“当前元素库为只读”提示 |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_manual_motion.py`
- 元素库：`D:\code\元素库\260902_win元素`
- 元素：`win32靶场输入框`
- 默认配置：`PASS`
- 自定义配置：`PASS`
- 慢速移动：`465.9ms`，落点 `(2722, 772)`
- 随机点击：落点 `(2739, 780)`，位于元素范围内
- 关闭后瞬移：`0.6ms`，落点 `(2722, 772)`
- 总状态：`PASS`
- 通过数：`5/5`
- 总耗时：`1571.5ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- Desktop 只读提示：未出现
- 产品源码修改：无

## 明确排除

- 非法参数与异常类型矩阵。
- 元素 `hover`、`double_click`、`long_press`、`drag_to` 的人工轨迹矩阵。
- `motion_delay` 的实际节奏变化：当前源码仅保存该配置。
- `min_time` 三个速度阈值的完整边界矩阵。
