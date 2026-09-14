# `uiautoma.win32.send_keys()` 验证证据

```yaml
api: "uiautoma.win32.send_keys"
lifecycle: "VERIFIED"
verification_date: "2026-09-04"
verification_summary:
  source_contract: "PASS"
  notepad_launch_and_focus: "PASS"
  plain_text: "PASS"
  hotkey_ctrl_a: "PASS"
  manual_observation: "PASS"
  temp_file_cleanup: "PASS"
  notepad_manual_cleanup: "PASS"
  passed: 2
  total: 2
  elapsed_ms: 1775.2
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.win32.send_keys 的最小 SDK→Runtime input.send_keys 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/win32/__init__.py"
      symbols: ["send_keys"]
      fingerprint: "eb34701ee6379233cf91d406b42f63fc7391333a"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.send_keys"]
      fingerprint: "c18fd209af3bfaa12f250bdc2b12f5d3db415f3b"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.send_keys"]
      fingerprint: "13643d467dfd4ea60a47a1129f886253e5e06756"
  verified_contract:
    signature: "send_keys(keys='', send_key_delay=50, delay_after=1, contains_hotkey=True, force_ime_eng=False) -> None"
    parameter_order:
      - "keys"
      - "send_key_delay"
      - "delay_after"
      - "contains_hotkey"
      - "force_ime_eng"
    defaults:
      keys: ""
      send_key_delay: 50
      delay_after: 1
      contains_hotkey: true
      force_ime_eng: false
    absent_parameters:
      - "hardware_driver_input"
    return_annotation: "None"
    status_model: ["PASS", "FAIL"]
persistent_script:
  path: "win32/test_win32_send_keys.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "8bf7cf857ac9a987c73ff12ab8578c530f89788b"
  command: 'uv run .\win32\test_win32_send_keys.py'
test_asset:
  target: "script-launched notepad.exe"
  plain_text_call: 'win32.send_keys("UIAutoma123", 50, 1, False, True)'
  hotkey_call: 'win32.send_keys("^a", 20, 0, True, False)'
  expected_visual_state: "记事本显示并全选 UIAutoma123"
  manual_observation: "PASS"
cleanup:
  temporary_file: "deleted by script"
  notepad_window: "manually closed by tester without saving"
  status: "PASS"
source_commit_at_doc_time: "75957a1d3625269853cf54d61bccd68260780fbe"
```

## 持久化脚本

脚本：`win32/test_win32_send_keys.py`

从 `D:\code\元素库\sdk测试` 运行：

```powershell
uv run .\win32\test_win32_send_keys.py
```

脚本自动创建临时空文本文件、打开并激活记事本，然后只调用两次
`win32.send_keys()`。窗口枚举与激活使用 Win32 API，不调用 `ping()`、`get_list()`、
`get_selected_text()` 或其他 UIAutoma SDK API。

## API 参数

```python
win32.send_keys(
    keys: str = "",
    send_key_delay: int = 50,
    delay_after: float = 1,
    contains_hotkey: bool = True,
    force_ime_eng: bool = False,
) -> None
```

- `keys`：普通文本或 SendKeys 快捷键表达式。
- `send_key_delay`：每个按键之间的延迟，单位毫秒。
- `delay_after`：动作后的等待秒数。
- `contains_hotkey=False`：按普通文本输入；`True`：解析快捷键。
- `force_ime_eng=True`：发送前尝试切换英文输入布局，结束后尽力恢复。
- 当前公开 API 没有 `hardware_driver_input` 参数。

## 最小实现链

```text
uiautoma.win32.send_keys
  -> get_client().send_keys(
       mode="keyboard",
       restore_clipboard=True,
       contains_hotkey=...,
       send_key_delay_ms=...,
       force_ime_eng=...,
     )
  -> Runtime ActionService.send_keys
  -> sleep_after(delay_after)
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 普通文本 | `PASS` | `"UIAutoma123"`、50ms、等待 1 秒、关闭快捷键解析、启用英文输入法切换；返回 `None` |
| 快捷键 | `PASS` | `"^a"`、20ms、无动作后等待、启用快捷键解析、不切换输入法；返回 `None` |
| 人工观察 | `PASS` | 记事本显示并全选 `UIAutoma123` |
| 临时文件清理 | `PASS` | 脚本删除本次创建的临时 `.txt` |
| 记事本清理 | `PASS` | 测试者确认后手动关闭并选择不保存 |

## 最近一次真实验证

- 日期：2026-09-04
- 命令：`uv run .\win32\test_win32_send_keys.py`
- 测试对象：脚本自动打开并激活的记事本
- 普通文本：`UIAutoma123`
- 快捷键：`Ctrl+A`
- 人工观察：文本显示且已全选
- 总状态：`PASS`
- 通过数：`2/2`
- 总耗时：`1775.2ms`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无

## 明确排除

- 非法参数与异常类型矩阵。
- 更复杂的 SendKeys 快捷键组合。
- 中文输入法内容矩阵。
- `hardware_driver_input`：当前公开 API 不存在该参数。
