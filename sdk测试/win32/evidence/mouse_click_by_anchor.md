# `win32.mouse_click_by_anchor()` 验证证据

```yaml
api: "uiautoma.win32.mouse_click_by_anchor"
lifecycle: "VERIFIED"
verification_date: "2026-09-10"
verification_summary:
  passed: 42
  total: 42
  elapsed_ms: 9147.2
  exit_code: 0
  full_log_provided: true
  tester_confirmed: true
  native_click_events_verified: true
  modifiers_at_button_down_verified: true
  necessary_cleanup: "PASS"
  foreground_restore: "未恢复；自动模式警告"
persistent_script:
  path: "win32/test_win32_mouse_click_by_anchor.py"
  fingerprint_kind: "SHA-256 at documentation time; execution-time hash not supplied"
  fingerprint: "64638369777ec09d24aad72e76758c50bc991e5772c86ecc915af3bd5a72f643"
  command: 'uv run .\win32\test_win32_mouse_click_by_anchor.py --non-interactive'
event_probe:
  path: "win32/_mouse_event_probe.py"
  sha256: "d82b1c5235609ba6994091b7d767a2b24d0cb37fc520d43b479149a27da27701"
```

## 用途与参数

```python
win32.mouse_click_by_anchor(
    rectangle, anchor=None, relative_to="screen", button="left",
    click_type="click", keys="none", delay_after=1, move_mouse=True,
)
```

在矩形指定锚点点击，返回None。八参数均支持位置或关键字，rectangle必填。
矩形支持元组、列表、两种字段字典和get_bounding对象。
anchor使用snake_case九宫格名称，支持random及三元组/字典偏移。
relative_to支持screen/window/position；鼠标键left/right/middle；本轮双击写法
doubleClick、dbclick、dblclick均测试。修饰键测试none、ctrl、shift、ctrl+shift。
delay_after为动作后秒数；move_mouse=False用例预先将鼠标置于目标点。

## 场景与原生事件校验

保持dev、靶场运行并启用 `D:\code\元素库\260902_win元素`，在测试根目录执行：

```powershell
uv run .\win32\test_win32_mouse_click_by_anchor.py --non-interactive
```

脚本打开拖拽页，在drag-target内缩20物理像素的矩形中点击，避免边缘点落到目标外。
本轮目标边界(982,375,120,80)，测试矩形(1002,395,80,40)，中心(1042,415)。

每次调用期间安装只读WH_MOUSE_LL钩子，记录左右中键的按下/抬起及坐标，按下时读取
Ctrl/Shift等修饰键状态，事件继续传递。调用结束后卸载钩子并停止观察线程。
除API返回、原生光标位置外，还核验单击一组/双击两组事件、鼠标键、修饰键及最终释放。

## 本轮结果

| 场景 | 观察 | 结果 |
| --- | --- | --- |
| 默认、位置、关键字及矩形写法 | 中心点击正确，返回None | PASS |
| 九宫格 | 九个事件落点与矩形锚点一致 | PASS |
| random | 事件点(1029,424)在矩形内 | PASS |
| 三元组偏移(4,-3) | (1046,412) | PASS |
| 字典偏移(-4,3) | (1038,418) | PASS |
| 左/右/中单击 | 正确鼠标键，一次按下加一次抬起 | PASS |
| 三种双击写法 | 两次按下、两次抬起，顺序和位置一致 | PASS |
| Ctrl/Shift/Ctrl+Shift | 按下时原生状态与参数一致，结束已释放 | PASS |
| move_mouse=False | 起点已在目标，仍记录一次真实点击 | PASS |
| window/position相对 | 正确换算至中心，事件坐标一致 | PASS |
| None延时 | 正常点击并释放 | PASS |
| 0.3秒配对延时 | 增加300.5ms | PASS |
| 非法键/类型/修饰键/锚点/坐标系 | InvalidParamsError，原生点击事件为空 | PASS |
| 负数/非数字延时 | InvalidParamsError，但此前已发生一次完整左键点击 | PASS |
| 必要清理 | 按键释放、鼠标恢复、Package释放，靶场保持运行 | PASS |

汇总42/42通过，总耗时9147.2ms，退出码0，测试者明确确认。
原终端458888自动恢复失败，前台留在靶场723350，按自动模式记录警告，不冒充焦点已恢复。
脚本日志仍输出READY_FOR_LIVE作为待人工确认状态，本文件在确认后记录本轮VERIFIED。

## 历史与验证范围

首次未加事件观察器的运行42/42、6456.7ms，仅证明位置、返回和最终按键释放；
本次补齐系统鼠标事件计数和修饰键检查后才记录此范围的验收。

低级钩子证明输入流中的按下/抬起，不证明靶场业务逻辑已消费点击，也未直接核验
WM_*DBLCLK消息或业务双击响应。未测试Alt/Windows组合键、多倍率、真实元素的默认
96 DPI矩形、越界偏移、输入竞争或不可见目标。
move_mouse=False仅在预先对准目标时测试，不用于证明从其他位置自动移动的行为。
非法延时的点击副作用已记录，调用者不能将此异常等同于没有点击。
