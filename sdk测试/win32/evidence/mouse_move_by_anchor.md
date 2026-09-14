# `win32.mouse_move_by_anchor()` 验证证据

```yaml
api: "uiautoma.win32.mouse_move_by_anchor"
lifecycle: "VERIFIED"
verification_date: "2026-09-10"
verification_summary:
  passed: 39
  total: 39
  elapsed_ms: 2272.9
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  mouse_restored: true
  foreground_verified: true
persistent_script:
  path: "win32/test_win32_mouse_move_by_anchor.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "49e1bec2e183090b5731a5d4e0b012a3985fa2fe229386f32efd28e8a4f443fa"
  command: 'uv run .\win32\test_win32_mouse_move_by_anchor.py --non-interactive'
```

## 用途和参数

```python
win32.mouse_move_by_anchor(
    rectangle=(100, 100, 120, 80),
    anchor="middle_center",
    relative_to="screen",
    move_speed="instant",
    delay_after=0,
)
```

将鼠标移到矩形的指定锚点，不执行点击。五参数均可位置或关键字传入，rectangle必填。
rectangle支持(x,y,w,h)元组/列表、x/y/w/h字典、left/top/width/height字典，或带
get_bounding()的对象。本轮对象分支使用固定返回物理矩形的对象，不是真实SDK元素。

anchor默认None表示中心，九宫格使用下划线名称，如top_left、middle_center、bottom_right；
另支持random及三元组/字典偏移。relative_to支持screen、position、window。
move_speed默认None使用全局偏好，显式支持instant/fast/middle/slow。
delay_after默认1秒，None/0不等待；返回None。

## 场景与运行

dev及可见未最小化的Win32靶场运行，在 `D:\code\元素库\sdk测试` 执行：

```powershell
uv run .\win32\test_win32_mouse_move_by_anchor.py --non-interactive
```

无需元素库。使用固定矩形(100,100,120,80)，每次以原生接口将鼠标放到(50,50)，
调用后用GetCursorPos核验。window相对场景先激活靶场，以其原生窗口原点计算预期。
测试期间不要操作鼠标，结束恢复原鼠标及前台，不关闭靶场。

## 最新真实结果

| 场景 | 实际结果 | 结论 |
| --- | --- | --- |
| 默认、位置、关键字调用 | 到达中心(160,140)，返回None | PASS |
| 矩形列表、两种字典、边界对象 | 到达中心(160,140) | PASS |
| 九宫格下划线锚点 | 横坐标100/160/220、纵坐标100/140/180组合均正确 | PASS |
| 随机锚点 | (159,128)，位于矩形内 | PASS |
| 三元组偏移(6,-4) | (166,136) | PASS |
| 字典偏移(-6,4) | (154,144) | PASS |
| position相对 | 起点(50,50)，最终(210,190) | PASS |
| window相对 | 本轮最终(2403,652)，与原生窗口原点换算一致 | PASS |
| 四档速度 | instant=0.4ms、fast=124.7ms、middle=288.1ms、slow=462.3ms | PASS |
| None延时 | 正常到达目标 | PASS |
| 配对延时 | 0.3秒额外等待，差值300.1ms | PASS |
| 非法矩形/尺寸/锚点/坐标系/速度 | InvalidParamsError且保持起点(50,50) | PASS |
| 非法delay_after | 移动至(160,140)后抛InvalidParamsError | PASS |
| 清理 | 原鼠标恢复并核验，前台恢复 | PASS |

39/39通过，总耗时2272.9ms，退出码0，测试者明确确认。
负数延时消息为“delay_after不能小于0”，非数字延时消息为“delay_after必须是数字”；
两次均先移动再抛异常。这是当前实现行为，调用方不能把捕获该异常理解为鼠标未移动。
原终端458888由靶场723350切回，约20.8ms后核验恢复成功。

## 历史与验证边界

此前脚本使用topLeft/middleCenter等旧驼峰写法，当前SDK采用下划线名称，造成14项失败。
这属于测试脚本与当前规则不匹配，脚本已修正，最新对应场景全部通过。

另一次旧日志中负数延时用例观察到鼠标停留起点，但没有保留捕获异常的具体消息，
原因未确认。补充异常类型、消息及前后坐标后本轮未复现，不据此认定或宣称修复产品缺陷。

未验证真实Win32Element的默认96 DPI边界输入、跨显示器/负坐标、多倍率、鼠标被限制在
区域内等情况。速度数据为整次调用耗时，非运动曲线的逐点采样；默认延时及None行为为
本轮观察，只有0.3秒延时作配对断言。动作不点击，脚本没有独立按键事件审计。
